// Client-only helpers for turning a live camera frame or a picked file into a
// small JPEG data URL. Downscaled deliberately — sessionStorage has a ~5-10MB
// per-origin quota, and a raw phone photo can blow past that on its own.
// The photo never leaves the browser: no OCR is wired yet (Module 1 needs a
// deployed Donut checkpoint, see backend/README.md), so this exists purely so
// Preview/Result can show what was actually captured/uploaded instead of a
// placeholder box — which also happens to match the product's own intended
// design (issue #29): the image is never persisted or sent to a server.

const MAX_DIMENSION = 1000;
const JPEG_QUALITY = 0.8;

function drawToDataUrl(
  source: CanvasImageSource,
  sourceWidth: number,
  sourceHeight: number,
): string {
  const scale = Math.min(1, MAX_DIMENSION / Math.max(sourceWidth, sourceHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(sourceWidth * scale);
  canvas.height = Math.round(sourceHeight * scale);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas 2D context unavailable");
  ctx.drawImage(source, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", JPEG_QUALITY);
}

export function captureFromVideo(video: HTMLVideoElement): string {
  return drawToDataUrl(video, video.videoWidth, video.videoHeight);
}

export function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const objectUrl = URL.createObjectURL(file);
    img.onload = () => {
      try {
        resolve(drawToDataUrl(img, img.naturalWidth, img.naturalHeight));
      } catch (err) {
        reject(err instanceof Error ? err : new Error(String(err)));
      } finally {
        URL.revokeObjectURL(objectUrl);
      }
    };
    img.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error("Could not read the selected file as an image"));
    };
    img.src = objectUrl;
  });
}
