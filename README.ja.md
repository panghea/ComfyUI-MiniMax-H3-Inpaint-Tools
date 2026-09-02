# comfyui-minimax-h3-inpaint-tools

[English](README.md) · **日本語**

ComfyUI 上で **MiniMax H3** の潜在を直接編集するノード群です。完成したクリップの映像に触れずに
音声だけ振り直す、ショットの一区間だけ書き直す、潜在を空間的にリサイズする — いずれもフレームへ
デコードして再エンコードすることなく行います。

モデルでもサンプラーでもありません。H3 の潜在フォーマットの性質ひとつに対処する 10 個の小さな
ノードと、ComfyUI が既に持っているのに誰も使っていない仕組みひとつの組み合わせです。

> [!IMPORTANT]
> **ノード自体は誰でも無料です。その下のライブラリは全員が無料ではありません。**
> このリポジトリは GPL-3.0 で、企業規模にかかわらず無料のままです。ただし
> [`minimax-h3-latent-core`](https://github.com/panghea/minimax-h3-latent-core) に依存しており、
> こちらは PolyForm Small Business 1.0.0 です。個人と、**従業員・業務委託の合計が 100 名未満**
> かつ**前課税年度の総収入が 100 万米ドル未満**の企業は無料。それを超える場合は有償ライセンスが
> 必要です（[COMMERCIAL.md](COMMERCIAL.md)）。
> **このノードパックを入れるとそのライブラリも入る**ので、ノードが動いた時点で基準の対象です。
> 基準内であれば商用利用に制限はありません。PolyForm Small Business は規模の線引きであって、
> 非商用限定の条項ではありません。生成物についてはどちらの場合もあなたのもので、ライセンスは
> 出力に対して何も主張しません。
---

## 何が起きるのか

完成した 15 秒の CM に、ロゴの破綻が見つかりました。エンブレムの円弧に沿った文字に余分な字が
生えていて、価格比較となるべきところが 価◯格比較 になっている。よりによって、クライアントが
必ず読む場所です。

<img src="https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/logo-fix.webp" width="820" alt="エンブレムの修正前（上）と修正後（下）。円弧の文字に余分な字が生えている状態と、修正後">

作り直せば誤字は直りますが、それ以外もすべて変わります。H3 のサンプルは seed と解像度に従うので
あって、前回の出力にどれだけ近いかには従いません。再生成は「同じ映像の直った版」ではなく別の
クリップです。カメラの揺れ方が変わり、光の粒が変わり、芝居が変わる。すでに OK が出ている尺で
それは修正になりません。

そこで、作り直しませんでした。そのショットの潜在を読み戻し、エンブレムの上に矩形を引いて、
**その矩形の内側だけ**をサンプラーに動かさせています。

<img src="https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/logo-zoom.webp" width="700" alt="エンブレムへのズーム。上が修正前、下が修正後">

### マスクの外は同じクリップのまま

赤は、2 つのレンダリングで差が出た画素です。

<img src="https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/diff-highlight.webp" width="760" alt="変化した画素を赤で示した CM。書き換えた領域だけが光る">

解放した領域だけが光ります。空も、価格のカードも、コピーの文字も再生成されていません。そもそも
サンプラーに渡されていないからです。マスクの外側では、元の潜在が毎ステップ書き戻されます。

```python
out = out * denoise_mask + latent_image * (1 - denoise_mask)
```

マスク値 `0` の領域は、開始時の潜在に固定されます。最後に合成しているのではなく、スケジュールの
全ステップで強制されます。だから触れていない部分は「似ている」ではなく「同一」で戻ってきます。

### 文字だけの話ではありません

同じ仕組みで、矩形をエンブレムではなく人物に置いた例です。ここでは画面右側だけを解放して
います。衣装は変わり、左下のコピーとその背後の空はそのままです。

<img src="https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/scene-swap.webp" width="560" alt="あるカットの前後。人物の衣装が変わり、コピーは変わらない">

### 尺全体での前後比較

<img src="https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/before-after.webp" width="460" alt="15 秒の CM 全体。上が元、下が書き換え後">

音声つきのフル画質:
[ロゴ](https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/compare-logo-zoom.mp4) ·
[差分](https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/diff-highlight.mp4) ·
[カット](https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/compare-scene3.mp4) ·
[尺全体](https://raw.githubusercontent.com/panghea/ComfyUI-MiniMax-H3-Inpaint-Tools/main/docs/media/compare-final-vs-r2v.mp4)

上記の映像はノードの説明のために置いているサンプル素材です。このリポジトリのライセンスの対象外
であり、再利用は許諾していません。
---

## 音声だけを振り直す

音声は映像とは別のテンソルで、長さは解像度に依存しません。そのため単独で再サンプルできます。
`[zeros_like(video), ones_like(audio)]` というマスクは全画素を静止させ、音声だけを動かします。

これはアフレコではありません。固定された映像は**全サンプリングステップで参照される**ので、
新しいテイクは後から被せるのではなく、すでに画面にある口の動きに対して書かれます。

CM シーン 1、1664×928、107 フレーム、RTX 3090:

| | 時間 |
|---|---|
| フル生成、PDD 8 ステップ | **845 秒** |
| 音声のみ振り直し、4 ステップ、plain モデル | **360 秒**（−57%） |

映像は元に対して **PSNR ≈ 40 dB** で戻りました。目視では区別できません。この差は潜在が動いたの
ではなく VAE デコードのノイズです。

潜在を読み込み、**Partial Denoise Mask** を `audio only` にし、サンプラーに新しい seed を渡して
4 ステップ。グラフの他の部分は変えません。



---

## なぜこれらのノードが必要か

H3 は素の潜在テンソルを返しません。返ってくるのは `comfy.nested_tensor.NestedTensor` で、これは
テンソルの**リスト**の薄いラッパーです。

```
[0] video   (B, 24, T, H, W)     H,W = ピクセル数 / 16
[1] audio   (B, 32, 2, L)        L は解像度に依存しない
```

ここから 2 つの帰結が出て、どちらも役に立ちます。

**標準の潜在ノードが壊れます。** `LatentUpscale` は潜在に対して `.reshape` を呼び、
`'NestedTensor' object has no attribute 'reshape'` で落ちます。テンソルが 1 本だと仮定している
ものはすべて同じです。

**2 つのトラックは独立しています。** 音声潜在は独立したテンソルなので、映像テンソルにいっさい
触れずに差し替え・マスク・再サンプルができます。長さは解像度に依存せず、同じショットの 0.4 MP
実行と 1.5 MP 実行はどちらも `(1, 32, 2, 178)` を返します。

そして、ComfyUI が既に持っている仕組みがこれです。

```python
# comfy/samplers.py
if denoise_mask.is_nested:
    denoise_masks = denoise_mask.unbind()
...
x   = x   * denoise_mask + scale_latent_inpaint(...) * (1 - denoise_mask)
out = out * denoise_mask + latent_image              * (1 - denoise_mask)
```

サンプラーは**ネストされた** denoise マスクを受け取り、各要素を対応するテンソルに適用します。
マスク `0` はその領域を全ステップで `latent_image` に固定し、`1` は自由に動かします。つまり
`[zeros_like(video), ones_like(audio)]` というマスクは、映像を完全に静止させたまま音声だけを
振り直します。しかも全ステップで実際の映像が参照されるので、新しい音声は**すでに画面にある口の
動きに対して**書かれます。

これが仕組みのすべてです。ノードはマスクを組み立てて潜在を動かしているだけです。

---

## ノード一覧

| ノード | 役割 |
|---|---|
| **Partial Denoise Mask** | 潜在の大部分を固定し、選んだ部分だけを再サンプルします。トラック（音声 / 映像 / 両方）、時間範囲、矩形を指定。中核のノードです。 |
| **Time Range (frames)** | フレーム番号を入れると割合が出ます。実際に動くフレームがノード上に表示されます。時間分解能は潜在 1 フレームなので、端はスナップします。 |
| **Region Picker** | 4 つの割合を打ち込む代わりに、画像の上で矩形をドラッグします。上流が `LoadImage` / `LoadVideo` なら、グラフを実行せずにブラウザ側がフレームを取得して表示します。 |
| **Save Latent** | H3 の潜在を safetensors に書き出します。既定は bf16。 |
| **Load Latent** | 書き出したものを読み戻します。 |
| **Pack Latent** | 個別にエンコードした映像潜在と音声潜在からネスト潜在を組み立てます。潜在を保存していなかったクリップ向け。 |
| **Latent Composite** | 完成した 2 つの潜在を、矩形および / または時間範囲でブレンドします。事後的な手段で、マスクのほうが望ましい。 |
| **Latent Spatial Resize** | ネスト構造を保ち、音声に触れずに潜在を空間的にリサイズします。 |
| **Latent Extend** | 潜在を時間方向に伸ばし、元の区間を固定したまま続きを生成します。初回で成立しました（39 → 73 フレーム、固定部分 37.3 dB）が、再現性を主張できるほどの回数は試していません。 |
| **Latent Inspect** | ネスト潜在の中身のシェイプと dtype を出力します。 |

### Partial Denoise Mask

重要なのはこれです。残したい潜在とサンプラーの間に挟みます。

```
完成した潜在 ────────► Partial Denoise Mask ──► SamplerCustomAdvanced.latent_image
RandomNoise（新しい seed）──────────────────► SamplerCustomAdvanced.noise
```

| 入力 | 説明 |
|---|---|
| `track` | `audio only` / `video only` / `both` |
| `strength` | `1.0` で選択領域は完全に自由。下げると毎ステップ元の潜在へ引き戻されます。 |
| `t_start_pct`, `t_end_pct` | 書き換える区間。クリップ全体に対する割合。 |
| `t_feather_pct` | 時間方向のソフトエッジ。無いと継ぎ目が見えます。 |
| `x/y/w/h_pct`, `feather_pct` | 矩形。映像トラックのみ。音声に幾何情報はありません。 |

固定された領域は全サンプリングステップで存在するので、書き換え対象は**それに対して**書かれます。
2 回生成して合成するのとは違います。書き換えた時間区間は、生成中に前後のフレームを見ています。

**このパスには本物のノイズが必要です。** マスクは
`x = x*mask + scale_latent_inpaint(x, sigma, noise, latent_image)*(1-mask)` として適用されるため、
固定領域は現在の sigma で**サンプラーのノイズから**再構成されます。`DisableNoise` を渡すとこの項
が潰れ、サンプラーがまだ高 sigma にいる段階で固定領域にノイズのない値が入り、出力は崩壊します。
絵ではなく色のブロックの羅列になります。これにより 2 段階の PDD ウォームアップ（workflow 005）は
使えません。第 2 段階が設計上 `DisableNoise` で走るためです。実測では、同じマスクでも単一の
plain パスは綺麗に出たのに対し、ウォームアップ版は完全に破壊された状態で返ってきました。

**PDD はマスクありでも動きますが、細部には使わないこと。** マスクはスケジュールに触れないので、
`MiniMaxH3PDDAccApply` が自前の 8 ステップ sigma を駆動するのは問題ありません（仮定ではなく実測）。
駄目なのは**短縮された**スケジュールです。`BasicScheduler` に `denoise < 1` を与えると学習済み
グリッドから外れ、`model evaluated at sigma …, which is not a trained PDD block boundary` が出ます。
また文字修正では、同じステップ数でも蒸留パスのほうが plain モデルより明確に悪く、文字がまた崩れ
ました。細部は plain モデル、PDD は書き換え領域が粗いときだけ。

---

## 実測

上と同じショット。CM シーン 1、1664×928、107 フレーム、RTX 3090。

### うまくいかなかったこと

「小さく生成 → 潜在をアップスケール → フルサイズで仕上げ」の 2 段階パス — `Latent Spatial Resize`
を作る動機になった手法 — は、**このモデルでは割に合いません**。

| | 結果 |
|---|---|
| 1.5 MP 直接 | 845 秒 |
| 0.4 MP → 1.5 MP、仕上げ 4 ステップ | 705 秒。ただし**別のショット** |
| 0.75 MP → 1.5 MP、仕上げ 4 ステップ | 820 秒。3% しか縮まらない |

理由は 2 つ。第 2 段階は plain モデルで走らせるしかなく（上の PDD の注記）、1 ステップ約 90 秒
かかって節約分を食い潰します。もう 1 つ、H3 のサンプルは解像度に依存するので、小さく始めても
「同じクリップの安い版」にはならず、別のクリップになります。読める日本語のような細部は、第 1 段階
が小さすぎればそもそも形成されません。

もう一点。**`BasicScheduler` は `denoise < 1` でも `steps` 回まわります。** 短くなるのは sigma の
範囲であってステップ数ではありません。ステップ数は明示的に指定してください。

---

## レシピ

**完成クリップの音声を振り直す。** `audio only`、新しい seed、4 ステップ。詳しくは
[音声だけを振り直す](#音声だけを振り直す)。

**15 秒ショットの 3〜5 秒目を書き直す。** `both` でマスクし、`t_start_pct` / `t_end_pct` を区間に
合わせ、フェザーは 4〜6%。外側は完全にそのままです。

**画面の一角だけ直す。** `video only` でマスクし、矩形を指定、フェザー 6%。

**置き換えるのではなく寄せる。** `strength` を 0.4〜0.6 に下げるか、スケジューラの `denoise` を
下げます。`strength` は毎ステップ元に向けてブレンドし、`denoise` は部分的にノイズを乗せた状態から
始めます。同じレバーではありません。

**潜在を失ったクリップを編集する。** `LoadVideo` → `VAEEncode`（映像 VAE）と `VAEEncodeAudio`
（音声 VAE）→ **Pack Latent**。クリップ全体に VAE 往復のコストがかかるので、触っていない領域も
わずかに劣化します。生成時に潜在を保存しておくほうが良い。

---

## 注意点

- Contex Loop チェーン（`MiniMaxH3ChainSegmentSave`）は、チェックポイントにクリップごとの潜在を
  すでに保存しています。単発の R2V / I2V / T2V グラフは保存しないので、SaveVideo ノードの隣に
  **Save Latent** を足してください。
- bf16 はファイルサイズを半分にし（1.5 MP の 4.5 秒で約 215 MB）、モデルが実際に走る精度でも
  あります。元の dtype は記録され、読み込み時に復元されます。
- 潜在の幾何は空間方向が `ピクセル数 / 16`。時間方向は 107 フレームが `T = 32` になったので、
  潜在 1 フレームは実フレーム約 3.3 枚、24 fps で約 0.14 秒です。これがマスクで指定できる
  最小の時間単位です。

## 動作要件

MiniMax H3 に対応した ComfyUI（ノードが `comfy.nested_tensor` を import します）と、Python
パッケージ [`minimax-h3-latent-core`](https://pypi.org/project/minimax-h3-latent-core/) が 1 つ。
これらのノードが包んでいるアルゴリズム本体です。それ以外は ComfyUI に付属しています。

## インストール

```
git clone <this repo> ComfyUI/custom_nodes/comfyui-minimax-h3-inpaint-tools
pip install -r ComfyUI/custom_nodes/comfyui-minimax-h3-inpaint-tools/requirements.txt
```

2 行目は ComfyUI を動かしているのと同じ Python で実行してください。ComfyUI Manager から
インストールすれば両方とも自動で行われます。

ComfyUI を再起動すると、ノードが **MiniMax H3/latent** の下に現れます。

## サンプルワークフロー

`workflows/` に、収録前に実際に走らせた 6 本が入っています。mp4 を起点とした領域書き換え
（R2V、I2V、そして示唆的に失敗した T2V 版）、クリップの延長、Contex Loop チェーンの
チェックポイントを起点とする 2 本です。それぞれのコストと、実行前に差し替えるべき箇所は
`workflows/README.md` に書いてあります。

## ライセンス

このリポジトリは全体が GPL-3.0 です。ノードが依存するライブラリ
[`minimax-h3-latent-core`](https://github.com/panghea/minimax-h3-latent-core) は PolyForm Small
Business 1.0.0 で、個人および**従業員・業務委託の合計が 100 名未満**かつ**前課税年度の総収入が
100 万米ドル未満**の企業は無料です。それを超える場合は [COMMERCIAL.md](COMMERCIAL.md) を
参照してください。分割の理由は [LICENSING.md](LICENSING.md) にあります。
