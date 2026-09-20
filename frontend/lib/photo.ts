// Client-only helpers for turning a live camera frame or a picked file into a
// small data URL. Downscaled deliberately: sessionStorage has a ~5-10MB
// per-origin quota, and a raw phone photo can blow past that on its own.
// The picked file itself never leaves the browser. Only the rendered raster
// below is submitted to /reads, and the copy kept in sessionStorage so
// Analyzing and Preview can show the sheet is dropped when the reading is
// confirmed (ADR-0011 §3).

export const MAX_DIMENSION = 1000;
const JPEG_QUALITY = 0.8;

function context2d(canvas: HTMLCanvasElement): CanvasRenderingContext2D {
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas 2D context unavailable");
  return ctx;
}

function drawToDataUrl(
  source: CanvasImageSource,
  sourceWidth: number,
  sourceHeight: number,
): string {
  const scale = Math.min(1, MAX_DIMENSION / Math.max(sourceWidth, sourceHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(sourceWidth * scale);
  canvas.height = Math.round(sourceHeight * scale);
  const ctx = context2d(canvas);
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

/** What InForm can do with a file the person picked. */
export type PickedFileKind = "image" | "pdf" | "unsupported";

export function classifyPickedFile(file: File): PickedFileKind {
  if (file.type.startsWith("image/")) return "image";
  // Some mobile pickers hand over an empty `type`, so fall back to the name.
  if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) return "pdf";
  return "unsupported";
}

/** Why a picked file could not become sheet image data. Each code names its
 * real cause: a PDF that will not open is never reported as a bad photo. */
export type SheetPickCode = "unsupported-type" | "unreadable-image" | "unreadable-pdf";

export function sheetPickMessage(code: SheetPickCode): string {
  switch (code) {
    case "unsupported-type":
      return "InForm reads a JPG, PNG or PDF of an InBody 270 sheet. Pick one of those and try again.";
    case "unreadable-image":
      return "That image could not be opened. Try another photo of the sheet.";
    case "unreadable-pdf":
      return "That PDF could not be opened. It may be damaged or password-protected, so try a photo of the sheet instead.";
  }
}

export class SheetPickError extends Error {
  readonly code: SheetPickCode;

  constructor(code: SheetPickCode) {
    super(sheetPickMessage(code));
    this.name = "SheetPickError";
    this.code = code;
  }
}

/** A sheet ready to submit to /reads: raster image data, plus how many pages
 * the source had. A photo, and a one-page PDF, are both 1. */
export type SheetImage = { dataUrl: string; pageCount: number };

/** What to tell the person about which page was read, or null when there was
 * only ever one. */
export function pagesReadNotice(pageCount: number): string | null {
  return pageCount > 1 ? `Read page 1 of ${pageCount}` : null;
}

/** The scale to render a PDF page at so its longest side lands exactly on
 * MAX_DIMENSION. Rendering vector art straight to the submitted size beats
 * rendering large and resampling down, and it keeps the canvas clear of mobile
 * Safari's area limit, past which a canvas silently comes back blank. */
export function pdfRenderScale(pageWidth: number, pageHeight: number): number {
  return MAX_DIMENSION / Math.max(pageWidth, pageHeight);
}

/** Renders page 1 of a PDF to image data. Everything happens in the browser:
 * the PDF's own bytes never reach the server (ADR-0011 §3). */
export async function pdfToDataUrl(file: File): Promise<SheetImage> {
  // The legacy build, not the default one: pdf.js 6's modern build calls
  // `Promise.try`, which needs Chrome 128 / Safari 18.2 / Firefox 134. On an
  // older phone that throws, and this flow would then blame the PDF for a
  // browser problem — the exact misattribution this module exists to avoid.
  // Imported dynamically, so its extra weight only loads for a picked PDF.
  const pdfjs = await import("pdfjs-dist/legacy/build/pdf.mjs");
  // Resolved by the bundler, so the worker is emitted for both `next dev` and
  // a production build rather than fetched from a CDN at runtime.
  pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    "pdfjs-dist/legacy/build/pdf.worker.min.mjs",
    import.meta.url,
  ).toString();

  // Held so the worker is torn down with `destroy()` even when a page fails to
  // render; `PDFDocumentProxy` itself only offers `cleanup()`.
  const loadingTask = pdfjs.getDocument({ data: await file.arrayBuffer() });
  try {
    const pdf = await loadingTask.promise;
    const page = await pdf.getPage(1);
    const unscaled = page.getViewport({ scale: 1 });
    const viewport = page.getViewport({
      scale: pdfRenderScale(unscaled.width, unscaled.height),
    });
    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);
    await page.render({ canvas, canvasContext: context2d(canvas), viewport }).promise;
    return {
      dataUrl: drawToDataUrl(canvas, canvas.width, canvas.height),
      pageCount: pdf.numPages,
    };
  } finally {
    await loadingTask.destroy();
  }
}

/** The one entry point the Upload flow needs: turn whatever was picked into
 * submittable image data, or refuse it with its real reason.
 *
 * The two readers are injected so the branching and the failure attribution —
 * the part worth testing — can be exercised without a browser. */
export async function fileToSheetImage(
  file: File,
  deps: {
    readImage: (file: File) => Promise<string>;
    readPdf: (file: File) => Promise<SheetImage>;
  } = { readImage: fileToDataUrl, readPdf: pdfToDataUrl },
): Promise<SheetImage> {
  const kind = classifyPickedFile(file);

  if (kind === "unsupported") {
    throw new SheetPickError("unsupported-type");
  }

  if (kind === "pdf") {
    try {
      return await deps.readPdf(file);
    } catch (err) {
      console.error("Could not render the picked PDF:", err);
      throw new SheetPickError("unreadable-pdf");
    }
  }

  try {
    return { dataUrl: await deps.readImage(file), pageCount: 1 };
  } catch (err) {
    console.error("Could not read the picked image:", err);
    throw new SheetPickError("unreadable-image");
  }
}
