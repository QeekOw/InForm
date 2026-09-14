// Client-only helpers for turning a live camera frame or a picked file into a
// small data URL. Downscaled deliberately — sessionStorage has a ~5-10MB
// per-origin quota, and a raw phone photo can blow past that on its own.
// The photo never leaves the browser: Donut is deployed to Hugging Face Hub and
// Space (issue #33), with full browser integration tracked in PR #57.
// Per ADR-0011 §3 (Zero Image Persistence for User Uploads), the image exists
// transiently during the review session only and is cleared upon confirmation.

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

/** Generates a visual placeholder data URL for uploaded PDF documents so the scan
 * animation and preview do not encounter broken/empty image frames. */
export function createPdfDataUrl(fileName: string): string {
  const cleanName = fileName.replace(/[<>&"]/g, "").slice(0, 30);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="500" viewBox="0 0 400 500">
    <rect width="100%" height="100%" fill="#262626"/>
    <rect x="30" y="30" width="340" height="440" rx="12" fill="#ffffff" fill-opacity="0.06" stroke="#404040" stroke-width="2"/>
    <rect x="60" y="60" width="60" height="28" rx="6" fill="#e53e3e"/>
    <text x="90" y="79" font-family="system-ui, -apple-system, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">PDF</text>
    <path d="M160 190h80v120h-80z" fill="#ffffff" fill-opacity="0.1"/>
    <path d="M175 220h50M175 245h50M175 270h30" stroke="#117d69" stroke-width="3" stroke-linecap="round"/>
    <text x="200" y="350" font-family="system-ui, -apple-system, sans-serif" font-size="15" font-weight="600" fill="#fcfcfc" text-anchor="middle">${cleanName}</text>
    <text x="200" y="375" font-family="system-ui, -apple-system, sans-serif" font-size="11" fill="#a3a3a3" text-anchor="middle">InBody Report Document</text>
  </svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}
