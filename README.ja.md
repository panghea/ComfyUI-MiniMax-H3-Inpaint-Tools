# ComfyUI-MiniMax-H3-Inpaint-Tools

[English](README.md)

完成した MiniMax H3 のクリップを、作り直さずに一部だけ書き直します。ノード 10 個。

<img src="https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/logo-fix.webp" width="760" alt="エンブレムの修正前と修正後">

この CM のロゴに余分な字が生えていました。作り直せば直りますが、カメラの揺れも光の粒も芝居も
変わります。そこで潜在を読み戻し、その矩形だけを振り直しました。

<img src="https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/diff-highlight.webp" width="700" alt="変化した画素を赤で示した CM">

赤が、2 つのレンダリングで差が出た画素です。
[音声つきの動画](docs/media)。素材はサンプルで、このリポジトリのライセンスの対象外です。

## できること

**領域の inpaint。** 矩形、時間範囲、またはその両方。端はフェザーをかけないと継ぎ目が見えます。

**音声だけの差し替え。** 同じショットでフル生成 845 秒に対し、音声の振り直しは 360 秒
（1664x928、107 フレーム、RTX 3090）。映像はビット単位で保存されます。固定した映像が全ステップで
参照されるので、新しいテイクは後から被せるのではなく、画面にある口の動きに対して書かれます。

**尺の延長。** 元の区間を固定したまま続きを生成します。39 から 73 フレームで成立し、固定部分は
37.3 dB、継ぎ目も連続でした。1 回成功しただけでは再現性とは言えず、主張できるほどの回数は
試していません。

### 仕組み

H3 は単一のテンソルではなく `comfy.nested_tensor.NestedTensor` に `[video, audio]` を包んで
返します。そして ComfyUI のサンプラーは、ネストされた denoise マスクを既に受け取れます。

```python
out = out * denoise_mask + latent_image * (1 - denoise_mask)
```

マスク値 `0` の領域は、最後に合成するのではなく全ステップで元の潜在に固定されます。触れていない
部分が「似ている」ではなく「同一」で戻るのはこのためです。ここのノードはマスクを組んで潜在を
動かすだけで、デノイズには一切触れていません。

2 つのトラックは別テンソルなので、`[zeros_like(video), ones_like(audio)]` は映像を完全に静止させ
たまま音声だけを再サンプルします。音声の長さは解像度に比例せず、同じショットの 0.4 MP と 1.5 MP
はどちらも `(1, 32, 2, 178)` です。

### ノード

| ノード | 役割 |
|---|---|
| **Partial Denoise Mask** | 中核。潜在を固定して一部だけ解放します。トラック、時間範囲、矩形。 |
| **Time Range (frames)** | フレーム番号を入れると割合が出ます。実際に動くフレームを表示します。 |
| **Region Picker** | 画像の上で矩形をドラッグ。上流が `LoadImage` / `LoadVideo` ならブラウザがフレームを取得します。 |
| **Save / Load Latent** | safetensors、既定は bf16。元の dtype は読み込み時に復元されます。 |
| **Pack Latent** | 個別にエンコードした映像・音声潜在からネスト潜在を組みます。 |
| **Latent Composite** | 完成した 2 つの潜在をブレンド。事後手段で、マスクのほうが望ましい。 |
| **Latent Spatial Resize** | 音声に触れずに空間方向だけリサイズ。 |
| **Latent Extend** | 時間方向に伸ばして続きを生成。 |
| **Latent Inspect** | シェイプと dtype を出します。 |

マスクは、残したい潜在とサンプラーの間に挟みます。

```
完成した潜在 ────────► Partial Denoise Mask ──► SamplerCustomAdvanced.latent_image
RandomNoise（新しい seed）──────────────────► SamplerCustomAdvanced.noise
```

### 時間を取られた点

- **音声潜在は 4 次元**で、画像潜在と同じ階数です。「4 次元か 5 次元なら」でリサイズするものは
  音声を引き伸ばします。5 次元だけ触ってください。
- **マスク付きのパスには本物のノイズが要ります。** `DisableNoise` を渡すと inpaint 項が潰れ、
  領域が色のブロックで返ってきます。2 段階の PDD ウォームアップが使えないのはこのためです。
  第 2 段階が設計上 `DisableNoise` で走ります。
- **PDD はマスクと併用できますが、細部には使えません。** 短縮したスケジュール（`BasicScheduler`
  に `denoise < 1`）は学習済みグリッドを外れ、`not a trained PDD block boundary` が出ます。
  文字修正では、同じステップ数でも蒸留パスが plain モデルより悪くなりました。
- `BasicScheduler` は `denoise < 1` でも `steps` 回まわります。短くなるのは sigma の範囲です。
- mp4 を潜在に戻すときは `length % 17 == 5`。無効な長さは黙って短くなって返ります。
- **小さく生成してから潜在をアップスケールする手は割に合いません。** H3 のサンプルは解像度に
  依存するので、同じクリップの安い版ではなく別のクリップになります。0.4 MP から 1.5 MP は
  845 秒に対して 705 秒でしたが、読める日本語は形成されませんでした。
- 25 ステップは 8 ステップより悪くなりました。

## ワークフロー

`workflows/` に 6 本。すべて収録前に実際に走らせています。mp4 を起点とした領域書き換え（R2V、
I2V、示唆的に失敗した T2V）、クリップの延長、Contex Loop チェーンのチェックポイントを起点とする
2 本です。上の映像に一番近いのは `136_r2v_cut-rewrite-from-mp4.json` です。コストと差し替えるべき
箇所は `workflows/README.md` にあります。

### インストール

ComfyUI Manager から：**MiniMax H3 Inpaint Tools** で検索。依存も一緒に入ります。

手動の場合：

```
cd ComfyUI/custom_nodes
git clone https://github.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools
cd ComfyUI-MiniMax-H3-Inpaint-Tools && pip install -r requirements.txt
```

2 行目は ComfyUI を動かしている Python で実行してください。再起動すると
**MiniMax H3/latent** にノードが出ます。

必要なのは MiniMax H3 対応の ComfyUI（ノードが `comfy.nested_tensor` を import します）と、
アルゴリズム本体である
[`minimax-h3-latent-core`](https://pypi.org/project/minimax-h3-latent-core/) です。他は ComfyUI
に付属しています。

### 潜在の保存について

Contex Loop チェーンはチェックポイントにクリップごとの潜在を保存しています。単発の R2V / I2V /
T2V グラフは保存しないので、SaveVideo の隣に **Save Latent** を足してください。潜在を失った場合は
`LoadVideo` を `VAEEncode` と `VAEEncodeAudio` に通してから **Pack Latent** です。クリップ全体に
VAE 往復のコストがかかるので、触っていない領域もわずかに劣化します。

潜在の幾何は空間方向が `ピクセル数 / 16`。107 フレームが `T = 32` になったので、潜在 1 フレームは
実フレーム約 3.3 枚、24 fps で約 0.14 秒です。これがマスクで指定できる最小の時間単位です。

## ライセンスとコントリビューション

このリポジトリは GPL-3.0 で、企業規模にかかわらず無料のままです。ワークフローも同様で、制限を
かけている部分はありません。

依存している [`minimax-h3-latent-core`](https://github.com/panghea/minimax-h3-latent-core) は
GPL ではありません。こちらは PolyForm Small Business 1.0.0 で、個人と、従業員・業務委託の合計が
100 名未満かつ前課税年度の総収入が 100 万米ドル未満の企業は商用利用込みで無料、それを超える場合は
有償です（[COMMERCIAL.md](COMMERCIAL.md)）。このノードパックを入れるとそのライブラリも入るので、
ノードが動いた時点で基準の対象になります。生成物についてはどちらのライセンスも何も主張しません。

分割の理由は [LICENSING.md](LICENSING.md)、GPL 7 条の追加許諾は `LICENSE-EXCEPTION.txt` に
あります。

こちらのリポジトリは pull request を受け付けます。DCO サインオフ（`git commit -s`）だけ
お願いします。コアライブラリは issue のみで pull request を受けません。理由は
[CONTRIBUTING.md](CONTRIBUTING.md) にあります。
