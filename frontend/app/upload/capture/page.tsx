import Link from "next/link";
import PhoneFrame from "@/components/PhoneFrame";

const imgShutterOuter = "/icons/camera/shutter-outer.svg";
const imgShutterInner = "/icons/camera/shutter-inner.svg";
const imgFlash = "/icons/camera/flash-button.svg";
const imgGallery = "/icons/camera/gallery-button.svg";
const imgBack = "/icons/camera/back-arrow.svg";

export default function Capture() {
  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      {/* Live camera feed goes here once capture is wired up (no real device/photo
          embedded here — the Figma mock used a real printed report with a visible
          gym name and member ID; issue #29's privacy stance for Track B says data
          like that must never ship in the app, so it's a placeholder instead). */}
      <div className="absolute inset-x-0 top-8 bottom-6 flex items-center justify-center bg-black">
        <p className="px-10 text-center text-[12px] text-white/40">Camera preview</p>
      </div>

      <Link
        href="/upload"
        className="absolute left-[30px] top-[61px] flex size-8 items-center justify-center rounded-full bg-white shadow-md"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="Back" className="size-[18px]" src={imgBack} />
      </Link>

      <div className="absolute left-[61px] top-[562px] flex h-[53px] w-[280px] items-center justify-center rounded-[15px] border border-[#309487] bg-[#117d6999] px-4">
        <p className="text-center text-[12px] font-bold tracking-[0.02em] text-white">
          Make sure the report is well-lit, fully visible, and easy to read.
        </p>
      </div>

      <div className="absolute inset-x-0 bottom-[52px] flex items-center justify-center">
        <button
          type="button"
          aria-label="Open gallery"
          className="absolute left-[62px] size-[42px]"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" className="size-full" src={imgGallery} />
        </button>

        <Link href="/upload/analyzing" aria-label="Capture photo" className="relative block">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" className="size-[85px]" src={imgShutterOuter} />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            alt=""
            className="absolute left-1/2 top-1/2 size-[61px] -translate-x-1/2 -translate-y-1/2"
            src={imgShutterInner}
          />
        </Link>

        <button
          type="button"
          aria-label="Toggle flash"
          className="absolute right-[62px] size-[42px]"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" className="size-full" src={imgFlash} />
        </button>
      </div>
    </PhoneFrame>
  );
}
