// Drag a rectangle on the frame shown by MiniMaxH3RegionPicker and write it into the widgets.
//
// The node is an OUTPUT_NODE that returns a preview image, so after one run ComfyUI has put the
// frame in `node.imgs`. This extension draws that image inside the node body, overlays the
// current rectangle, and lets you drag a new one. The four percentage widgets are the source of
// truth - dragging just writes to them, so everything is saved with the workflow as usual.

import { app } from "../../scripts/app.js";
import { findSource, loadFrame, widgetsBottom as sharedBottom } from "./h3_source.js";

const NODE = "MiniMaxH3RegionPicker";
const PAD = 8;
const HANDLE = 10;

function widgetsBottom(node) {
  return sharedBottom(node, PAD);
}

function widgets(node) {
  const get = (n) => node.widgets?.find((w) => w.name === n);
  return { x: get("x_pct"), y: get("y_pct"), w: get("w_pct"), h: get("h_pct") };
}

// Show the source frame without running anything (see h3_source.js).
function loadPreview(node) {
  if (node._h3loading) return;
  const src = findSource(node, ["images", "video"]);
  if (!src) return;
  const frame = node.widgets?.find((w) => w.name === "frame")?.value ?? 0;
  const key = `${src.file}|${frame}`;
  if (node._h3loadedFrom === key) return;
  node._h3loading = true;
  loadFrame(src, frame)
    .then((img) => {
      node._h3preview = img;
      node._h3loadedFrom = key;
      node._h3loading = false;
      node.setDirtyCanvas(true, true);
    })
    .catch(() => (node._h3loading = false));
}

function imageRect(node) {
  // where the frame is drawn inside the node body
  const img = node.imgs?.[0] || node._h3preview;
  if (!img || !img.width) return null;
  const top = widgetsBottom(node);
  const wArea = node.size[0] - PAD * 2;
  const hArea = node.size[1] - top - PAD;
  if (wArea <= 0 || hArea <= 20) return null;
  const scale = Math.min(wArea / img.width, hArea / img.height);
  const dw = img.width * scale;
  const dh = img.height * scale;
  return { x: PAD + (wArea - dw) / 2, y: top + (hArea - dh) / 2, w: dw, h: dh, img };
}

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

app.registerExtension({
  name: "h3.region.picker",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE) return;

    const onCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      onCreated?.apply(this, arguments);
      this.size = [380, 560];
      this._h3drag = null;
      const fw = this.widgets?.find((w) => w.name === "frame");
      if (fw) {
        const prev = fw.callback;
        fw.callback = function () {
          const r = prev?.apply(this, arguments);
          this._h3loadedFrom = null;      // force a re-seek at the new frame
          return r;
        }.bind(this);
      }
      return this;
    };

    // paint the frame plus the rectangle under the widgets
    const onDraw = nodeType.prototype.onDrawForeground;
    nodeType.prototype.onDrawForeground = function (ctx) {
      onDraw?.apply(this, arguments);
      if (this.flags?.collapsed) return;
      if (!this.imgs?.[0]) loadPreview(this);
      const need = widgetsBottom(this) + 160;
      if (this.size[1] < need) {
        this.size[1] = need;              // never let the widgets sit on top of the frame
      }
      const r = imageRect(this);
      if (!r) {
        ctx.fillStyle = "#888";
        ctx.font = "12px sans-serif";
        ctx.fillText("connect LoadImage or LoadVideo, or run once", PAD, widgetsBottom(this) + 16);
        return;
      }
      ctx.drawImage(r.img, r.x, r.y, r.w, r.h);

      const wd = widgets(this);
      const bx = r.x + (r.w * (wd.x?.value ?? 0)) / 100;
      const by = r.y + (r.h * (wd.y?.value ?? 0)) / 100;
      const bw = (r.w * (wd.w?.value ?? 0)) / 100;
      const bh = (r.h * (wd.h?.value ?? 0)) / 100;

      ctx.save();
      // dim everything outside the rectangle so the selection reads at a glance
      ctx.fillStyle = "rgba(0,0,0,0.45)";
      ctx.beginPath();
      ctx.rect(r.x, r.y, r.w, r.h);
      ctx.rect(bx + bw, by, -bw, bh);          // reverse winding punches the hole
      ctx.fill("evenodd");

      ctx.strokeStyle = "#ff4419";
      ctx.lineWidth = 2;
      ctx.strokeRect(bx, by, bw, bh);
      ctx.fillStyle = "#ff4419";
      ctx.fillRect(bx + bw - HANDLE, by + bh - HANDLE, HANDLE, HANDLE);

      ctx.fillStyle = "#fff";
      ctx.font = "11px monospace";
      ctx.fillText(
        `${(wd.x?.value ?? 0).toFixed(1)}, ${(wd.y?.value ?? 0).toFixed(1)}  ` +
          `${(wd.w?.value ?? 0).toFixed(1)} x ${(wd.h?.value ?? 0).toFixed(1)}`,
        r.x + 4,
        r.y + r.h - 6
      );
      ctx.restore();
    };

    const onMouseDown = nodeType.prototype.onMouseDown;
    nodeType.prototype.onMouseDown = function (e, pos) {
      const r = imageRect(this);
      if (r && pos[0] >= r.x && pos[0] <= r.x + r.w && pos[1] >= r.y && pos[1] <= r.y + r.h) {
        const wd = widgets(this);
        const bx = r.x + (r.w * (wd.x?.value ?? 0)) / 100;
        const by = r.y + (r.h * (wd.y?.value ?? 0)) / 100;
        const bw = (r.w * (wd.w?.value ?? 0)) / 100;
        const bh = (r.h * (wd.h?.value ?? 0)) / 100;
        const onHandle =
          pos[0] > bx + bw - HANDLE * 1.5 && pos[1] > by + bh - HANDLE * 1.5 &&
          pos[0] < bx + bw + HANDLE * 0.5 && pos[1] < by + bh + HANDLE * 0.5;
        this._h3drag = onHandle
          ? { mode: "resize", ox: bx, oy: by }
          : { mode: "new", ox: pos[0], oy: pos[1] };
        if (this._h3drag.mode === "new") {
          wd.x.value = ((pos[0] - r.x) / r.w) * 100;
          wd.y.value = ((pos[1] - r.y) / r.h) * 100;
          wd.w.value = 0;
          wd.h.value = 0;
        }
        return true;   // swallow the click so the canvas does not start a selection
      }
      return onMouseDown?.apply(this, arguments) ?? false;
    };

    const onMouseMove = nodeType.prototype.onMouseMove;
    nodeType.prototype.onMouseMove = function (e, pos) {
      if (this._h3drag) {
        const r = imageRect(this);
        if (r) {
          const wd = widgets(this);
          const px = clamp(((pos[0] - r.x) / r.w) * 100, 0, 100);
          const py = clamp(((pos[1] - r.y) / r.h) * 100, 0, 100);
          const ax = this._h3drag.mode === "resize"
            ? ((this._h3drag.ox - r.x) / r.w) * 100
            : ((this._h3drag.ox - r.x) / r.w) * 100;
          const ay = this._h3drag.mode === "resize"
            ? ((this._h3drag.oy - r.y) / r.h) * 100
            : ((this._h3drag.oy - r.y) / r.h) * 100;
          wd.x.value = Math.round(Math.min(ax, px) * 2) / 2;
          wd.y.value = Math.round(Math.min(ay, py) * 2) / 2;
          wd.w.value = Math.round(Math.abs(px - ax) * 2) / 2;
          wd.h.value = Math.round(Math.abs(py - ay) * 2) / 2;
          this.setDirtyCanvas(true, true);
        }
        return true;
      }
      return onMouseMove?.apply(this, arguments) ?? false;
    };

    const onMouseUp = nodeType.prototype.onMouseUp;
    nodeType.prototype.onMouseUp = function () {
      if (this._h3drag) {
        this._h3drag = null;
        this.setDirtyCanvas(true, true);
        return true;
      }
      return onMouseUp?.apply(this, arguments) ?? false;
    };
  },
});
