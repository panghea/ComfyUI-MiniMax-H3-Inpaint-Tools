// Show the first and last frame of the range on the MiniMaxH3TimeRange node.
//
// The node converts frame numbers into the percentages the mask wants. Without seeing the frames
// those numbers are guesses, and a range that starts two frames late looks in the output exactly
// like a rewrite that did not take. So: two thumbnails, updated as the widgets change, fetched
// from the source file with no execution.

import { app } from "../../scripts/app.js";
import { findSource, loadFrame, sourceLength, widgetsBottom } from "./h3_source.js";

const NODE = "MiniMaxH3TimeRange";
const PAD = 8;
const CAP = 18;

function nums(node) {
  const get = (n) => node.widgets?.find((w) => w.name === n)?.value;
  const start = get("start_frame") ?? 0;
  const end = get("end_frame") ?? 0;
  return { start, last: Math.max(start, end - 1), total: get("total_frames") ?? 0 };
}

function refresh(node) {
  const src = findSource(node, ["video", "images"]);
  if (!src) {
    node._h3thumbs = null;
    return;
  }
  const { start, last } = nums(node);
  node._h3thumbs = node._h3thumbs || [null, null];
  node._h3keys = node._h3keys || [null, null];

  // Each side is fetched on its own key, so moving end_frame leaves the start thumbnail alone.
  [start, last].forEach((frame, i) => {
    const key = `${src.file}|${frame}`;
    if (node._h3keys[i] === key || node._h3pending?.[i]) return;
    node._h3pending = node._h3pending || [false, false];
    node._h3pending[i] = true;
    loadFrame(src, frame)
      .then((img) => {
        node._h3thumbs[i] = img;
        node._h3keys[i] = key;
        node._h3pending[i] = false;
        node.setDirtyCanvas(true, true);
      })
      .catch(() => {
        node._h3pending[i] = false;
      });
  });

  if (!node._h3total && !node._h3lenBusy) {
    node._h3lenBusy = true;
    sourceLength(src)
      .then((n) => {
        node._h3total = n;
        // fill the widget in so the number is visible. Harmless if the estimate is off by a
        // frame: the node reads the real count off the connected clip and ignores this.
        const tw = node.widgets?.find((w) => w.name === "total_frames");
        if (tw && n && tw.value !== n) {
          tw.value = n;
          node._h3estimated = true;
        }
        node._h3lenBusy = false;
        node.setDirtyCanvas(true, true);
      })
      .catch(() => {
        node._h3lenBusy = false;
      });
  }
}

app.registerExtension({
  name: "h3.time.range",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE) return;

    const onCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      onCreated?.apply(this, arguments);
      this.size = [420, 420];
      for (const name of ["start_frame", "end_frame", "total_frames"]) {
        const w = this.widgets?.find((x) => x.name === name);
        if (!w) continue;
        const prev = w.callback;
        w.callback = (...a) => {
          const r = prev?.apply(w, a);
          // the per-side cache key already contains the frame number, so the side that moved
          // re-seeks by itself and the other one is left alone. Nothing to invalidate here.
          if (name === "total_frames") this._h3estimated = false;
          this.setDirtyCanvas(true, true);
          return r;
        };
      }
      return this;
    };

    const onDraw = nodeType.prototype.onDrawForeground;
    nodeType.prototype.onDrawForeground = function (ctx) {
      onDraw?.apply(this, arguments);
      if (this.flags?.collapsed) return;
      refresh(this);

      const top = widgetsBottom(this, PAD) + 14;   // room for the total line
      const need = top + 150;
      if (this.size[1] < need) this.size[1] = need;

      const { start, last } = nums(this);
      const thumbs = this._h3thumbs;
      if (this._h3total) {
        ctx.fillStyle = "#8fb";
        ctx.font = "11px monospace";
        ctx.fillText(
          `total ${this._h3total} frames` + (this._h3estimated ? "  (from the clip, 24 fps)" : ""),
          PAD,
          top - 4
        );
      }
      if (!thumbs || (!thumbs[0] && !thumbs[1])) {
        ctx.fillStyle = "#888";
        ctx.font = "12px sans-serif";
        ctx.fillText("connect video or images to see the frames", PAD, top + 16);
        return;
      }

      const areaW = this.size[0] - PAD * 3;
      const areaH = this.size[1] - top - PAD - CAP;
      const cellW = areaW / 2;
      const labels = [`start  ${start}`, `last  ${last}`];

      thumbs.forEach((img, i) => {
        if (!img) return;
        const iw = img.width || 1;
        const ih = img.height || 1;
        const scale = Math.min(cellW / iw, areaH / ih);
        const dw = iw * scale;
        const dh = ih * scale;
        const x = PAD + i * (cellW + PAD) + (cellW - dw) / 2;
        const y = top + (areaH - dh) / 2;
        ctx.drawImage(img, x, y, dw, dh);
        ctx.strokeStyle = i === 0 ? "#3fa9ff" : "#ff4419";
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, dw, dh);
        ctx.fillStyle = i === 0 ? "#3fa9ff" : "#ff4419";
        ctx.font = "12px monospace";
        ctx.fillText(labels[i], x, y + dh + 14);
      });
    };
  },
});
