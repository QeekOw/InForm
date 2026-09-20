import { describe, expect, it, vi } from "vitest";
import {
  classifyPickedFile,
  MAX_DIMENSION,
  pdfRenderScale,
  fileToSheetImage,
  pagesReadNotice,
  SheetPickError,
  sheetPickMessage,
} from "./photo";

function pick(name: string, type: string): File {
  return new File([new Uint8Array([1, 2, 3])], name, { type });
}

const RENDERED = "data:image/jpeg;base64,AAAA";

describe("classifyPickedFile", () => {
  it("treats any image MIME type as an image", () => {
    expect(classifyPickedFile(pick("sheet.jpg", "image/jpeg"))).toBe("image");
    expect(classifyPickedFile(pick("sheet.png", "image/png"))).toBe("image");
    expect(classifyPickedFile(pick("sheet.heic", "image/heic"))).toBe("image");
  });

  it("recognises a PDF by MIME type", () => {
    expect(classifyPickedFile(pick("sheet.pdf", "application/pdf"))).toBe("pdf");
  });

  it("recognises a PDF by extension when the browser reports no MIME type", () => {
    // Some mobile file pickers hand over an empty `type`.
    expect(classifyPickedFile(pick("sheet.pdf", ""))).toBe("pdf");
    expect(classifyPickedFile(pick("SHEET.PDF", ""))).toBe("pdf");
  });

  it("rejects anything else", () => {
    expect(classifyPickedFile(pick("notes.txt", "text/plain"))).toBe("unsupported");
    expect(classifyPickedFile(pick("scan.docx", "application/msword"))).toBe("unsupported");
  });
});

describe("sheetPickMessage", () => {
  // Acceptance criterion 4.
  it("says what InForm accepts when the file type is unsupported", () => {
    const message = sheetPickMessage("unsupported-type");
    expect(message).toMatch(/JPG/);
    expect(message).toMatch(/PNG/);
    expect(message).toMatch(/PDF/);
  });

  // Acceptance criterion 3: the failure is attributed to the PDF, not to a
  // photo the person never took.
  it("blames the PDF, not the photo, when a PDF cannot be opened", () => {
    const message = sheetPickMessage("unreadable-pdf");
    expect(message).toMatch(/PDF/);
    expect(message).not.toMatch(/unreadable photo/i);
    expect(message).not.toMatch(/retake/i);
  });

  it("blames the image when an image cannot be opened", () => {
    expect(sheetPickMessage("unreadable-image")).toMatch(/image|photo/i);
  });
});

describe("pagesReadNotice", () => {
  // Acceptance criterion 2.
  it("says nothing for a single-page PDF", () => {
    expect(pagesReadNotice(1)).toBeNull();
  });

  it("names the page that was read, and the total, for a multi-page PDF", () => {
    expect(pagesReadNotice(3)).toBe("Read page 1 of 3");
    expect(pagesReadNotice(2)).toBe("Read page 1 of 2");
  });
});

describe("pdfRenderScale", () => {
  const longestRenderedSide = (w: number, h: number) => {
    const scale = pdfRenderScale(w, h);
    return Math.max(Math.ceil(w * scale), Math.ceil(h * scale));
  };

  it("renders an A4 page straight to the submitted size", () => {
    // A4 at 72dpi. Rendering vector text at the target size beats rendering
    // large and resampling it down.
    expect(longestRenderedSide(595, 842)).toBe(MAX_DIMENSION);
  });

  it("handles landscape the same way as portrait", () => {
    expect(longestRenderedSide(842, 595)).toBe(MAX_DIMENSION);
  });

  it("scales a huge page down rather than blowing the canvas limit", () => {
    // A0 at 72dpi. At a fixed 2x this would be a 6740px canvas, past mobile
    // Safari's limit, where the canvas silently comes back blank.
    expect(pdfRenderScale(2384, 3370)).toBeLessThan(1);
    expect(longestRenderedSide(2384, 3370)).toBe(MAX_DIMENSION);
  });

  it("scales a small page up, since the page is vector art", () => {
    expect(pdfRenderScale(200, 300)).toBeGreaterThan(1);
    expect(longestRenderedSide(200, 300)).toBe(MAX_DIMENSION);
  });
});

describe("fileToSheetImage", () => {
  // Acceptance criterion 1.
  it("renders a single-page PDF and reports one page", async () => {
    const readPdf = vi.fn().mockResolvedValue({ dataUrl: RENDERED, pageCount: 1 });
    const sheet = await fileToSheetImage(pick("sheet.pdf", "application/pdf"), {
      readPdf,
      readImage: vi.fn(),
    });

    expect(sheet).toEqual({ dataUrl: RENDERED, pageCount: 1 });
    expect(readPdf).toHaveBeenCalledOnce();
  });

  // Acceptance criterion 5: what leaves for /reads is a rendered raster image,
  // never the PDF's own bytes.
  it("submits rendered image data rather than the PDF itself", async () => {
    const sheet = await fileToSheetImage(pick("sheet.pdf", "application/pdf"), {
      readPdf: vi.fn().mockResolvedValue({ dataUrl: RENDERED, pageCount: 1 }),
      readImage: vi.fn(),
    });

    expect(sheet.dataUrl.startsWith("data:image/")).toBe(true);
    expect(sheet.dataUrl).not.toMatch(/application\/pdf/);
  });

  // Acceptance criterion 2.
  it("carries the page count through for a multi-page PDF", async () => {
    const sheet = await fileToSheetImage(pick("sheet.pdf", "application/pdf"), {
      readPdf: vi.fn().mockResolvedValue({ dataUrl: RENDERED, pageCount: 3 }),
      readImage: vi.fn(),
    });

    expect(sheet.pageCount).toBe(3);
    expect(pagesReadNotice(sheet.pageCount)).toBe("Read page 1 of 3");
  });

  it("passes an image straight through as a single page", async () => {
    const readImage = vi.fn().mockResolvedValue(RENDERED);
    const sheet = await fileToSheetImage(pick("sheet.jpg", "image/jpeg"), {
      readPdf: vi.fn(),
      readImage,
    });

    expect(sheet).toEqual({ dataUrl: RENDERED, pageCount: 1 });
    expect(readImage).toHaveBeenCalledOnce();
  });

  // Acceptance criterion 3.
  it("reports a PDF that cannot be opened as a PDF failure", async () => {
    const failure = fileToSheetImage(pick("locked.pdf", "application/pdf"), {
      readPdf: vi.fn().mockRejectedValue(new Error("PasswordException")),
      readImage: vi.fn(),
    });

    await expect(failure).rejects.toBeInstanceOf(SheetPickError);
    await expect(failure).rejects.toMatchObject({ code: "unreadable-pdf" });
  });

  it("reports an image that cannot be opened as an image failure", async () => {
    const failure = fileToSheetImage(pick("broken.jpg", "image/jpeg"), {
      readPdf: vi.fn(),
      readImage: vi.fn().mockRejectedValue(new Error("decode failed")),
    });

    await expect(failure).rejects.toMatchObject({ code: "unreadable-image" });
  });

  // Acceptance criterion 4.
  it("refuses an unsupported file without trying to read it", async () => {
    const readPdf = vi.fn();
    const readImage = vi.fn();
    const failure = fileToSheetImage(pick("notes.txt", "text/plain"), { readPdf, readImage });

    await expect(failure).rejects.toMatchObject({ code: "unsupported-type" });
    expect(readPdf).not.toHaveBeenCalled();
    expect(readImage).not.toHaveBeenCalled();
  });
});
