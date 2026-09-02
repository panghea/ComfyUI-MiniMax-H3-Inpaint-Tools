// Shared: fetch a frame straight out of the input directory, with no execution.
//
// ComfyUI only puts an image on a node after a run, which is useless for a node whose whole job
// is to help you decide what to run. But when the upstream is a LoadImage or LoadVideo, the file
// is already sitting in the input directory and /view will serve it - so the browser can show
// the frame on its own.

import { api } from "../../scripts/api.js";

// node type -> which widget holds the filename, and what kind of file it is
export const SOURCES = {
  LoadImage: { widget: "image", kind: "image" },
  LoadImageMask: { widget: "image", kind: "image" },
  LoadVideo: { widget: "file", kind: "video" },
};

export function viewURL(name) {
  return api.apiURL(
    `/view?filename=${encodeURIComponent(name)}&type=input&subfolder=`
  );
}

// Walk back from an input to the node feeding it, stepping over reroutes.
export function upstream(node, inputName) {
  const slot = node.inputs?.findIndex((i) => i.name === inputName);
  if (slot === undefined || slot < 0) return null;
  const link = node.graph?.links?.[node.inputs[slot].link];
  if (!link) return null;
  let src = node.graph.getNodeById(link.origin_id);
  let guard = 0;
  while (src && /^Reroute/.test(src.type) && guard++ < 8) {
    const l = node.graph.links?.[src.inputs?.[0]?.link];
    if (!l) return null;
    src = node.graph.getNodeById(l.origin_id);
  }
  return src;
}

// First upstream node among `inputNames` that the browser can read by itself.
export function findSource(node, inputNames) {
  for (const name of inputNames) {
    const src = upstream(node, name);
    const spec = src && SOURCES[src.type];
    if (!spec) continue;
    const file = src.widgets?.find((w) => w.name === spec.widget)?.value;
    if (file) return { node: src, file, kind: spec.kind };
  }
  return null;
}

const videoCache = new Map();
// One <video> is shared per file, so two callers seeking it at once would fight: the second
// seek moves the element before the first has drawn, and both end up with the same frame.
// Everything that touches a given file goes through this queue, one at a time.
const seekQueue = new Map();

function serialise(url, fn) {
  const prev = seekQueue.get(url) || Promise.resolve();
  const next = prev.then(fn, fn);
  seekQueue.set(url, next.then(() => {}, () => {}));
  return next;
}

function getVideo(url) {
  let entry = videoCache.get(url);
  if (entry) return entry;
  const v = document.createElement("video");
  v.muted = true;
  v.preload = "auto";
  v.src = url;
  entry = new Promise((resolve, reject) => {
    v.addEventListener("loadedmetadata", () => resolve(v), { once: true });
    v.addEventListener("error", reject, { once: true });
  });
  videoCache.set(url, entry);
  return entry;
}

// -> Promise<Image | HTMLCanvasElement>. `frame` is ignored for stills.
export async function loadFrame(source, frame, fps = 24) {
  const url = viewURL(source.file);
  if (source.kind === "image") {
    return await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = url;
    });
  }
  const v = await getVideo(url);
  return serialise(url, async () => {
    await new Promise((resolve, reject) => {
      const done = () => {
        v.removeEventListener("seeked", done);
        resolve();
      };
      v.addEventListener("seeked", done);
      v.addEventListener("error", reject, { once: true });
      const t = Math.min(Math.max(frame / fps, 0), Math.max(v.duration - 0.001, 0));
      if (Math.abs(v.currentTime - t) < 1e-4) done();
      else v.currentTime = t;
    });
    const c = document.createElement("canvas");
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    c.getContext("2d").drawImage(v, 0, 0);
    return c;
  });
}

// Bottom of the last visible widget: anything drawn above this gets painted over.
export function widgetsBottom(node, pad = 8) {
  const LG = window.LiteGraph || {};
  const WH = LG.NODE_WIDGET_HEIGHT || 20;
  const list = node.widgets || [];
  const start = node.widgets_start_y ?? (LG.NODE_TITLE_HEIGHT || 30);
  let bottom = start;
  let measured = false;
  for (const w of list) {
    if (w.hidden || w.type === "converted-widget") continue;
    const h = w.computeSize ? w.computeSize(node.size[0])[1] : WH;
    if (typeof w.last_y === "number") {
      measured = true;
      bottom = Math.max(bottom, w.last_y + h);
    }
  }
  if (!measured) {
    const visible = list.filter((w) => !w.hidden && w.type !== "converted-widget").length;
    bottom = start + visible * (WH + 4);
  }
  return bottom + pad;
}

// Rendered frame count of a source, as far as the browser can tell.
//
// There is no ComfyUI endpoint for video metadata and no browser API for a frame count, so for a
// clip this is duration x fps - an estimate. It is good enough to show and to seek with; the
// server reads the real count off the decoded tensor and always overrides it.
export async function sourceLength(source, fps = 24) {
  if (source.kind === "image") return 1;
  const v = await getVideo(viewURL(source.file));
  if (!isFinite(v.duration)) return 0;
  return Math.max(1, Math.round(v.duration * fps));
}
