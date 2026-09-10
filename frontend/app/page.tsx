import Link from "next/link";
import PhoneFrame from "@/components/PhoneFrame";
import ApiStatus from "@/components/ApiStatus";

const imgArrow = "/hero/vector-arrow.svg";
const imgBlob = "/hero/vector-blob.svg";

// The Figma illustration is a two-layer composite: a black/20%-opacity
// "shadow" pass (illus-a-*, offset left:-5 top:611) sits under the actual
// colored artwork (illus-b-*, offset left:-2 top:613) for a soft-shadow
// depth effect — not two alternatives, both layers are required. Each pass
// ships as five overlapping cutout pieces positioned as a percentage inset
// of a shared 407x263 canvas.
const illustrationLayout = [
  { inset: "63.06% 66.18% 0 14.76%" },
  { inset: "55.45% 9.58% 0 69.54%" },
  { inset: "24.41% 36.75% 0 34.77%" },
  { inset: "8.43% 69.5% 18.94% 0" },
  { inset: "5.66% 0 17.9% 67.79%" },
];

function IllustrationLayer({
  pieces,
  left,
  top,
}: {
  pieces: string[];
  left: string;
  top: string;
}) {
  return (
    <div className="absolute h-[263px] w-[407px] overflow-hidden" style={{ left, top }}>
      {pieces.map((src, i) => (
        <div key={src} className="absolute" style={{ inset: illustrationLayout[i].inset }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" className="absolute inset-0 block size-full max-w-none" src={src} />
        </div>
      ))}
    </div>
  );
}

export default function Home() {
  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      {/* Live backend status — proves the deployed frontend is talking to the deployed API */}
      <div className="mt-4 flex justify-center">
        <ApiStatus />
      </div>

      {/* Logo */}
      <div className="mt-8 flex justify-center">
        <p className="text-[35px] font-bold tracking-wide whitespace-nowrap">
          <span className="text-[#fcfcfc]">In</span>
          <span className="text-[#117d69]">Form</span>
        </p>
      </div>

      {/* Headline + subtext */}
      <div className="mt-10 px-[44px] text-center">
        <h1 className="text-[32px] leading-[1.15] font-bold tracking-[0.02em] text-[#fcfcfc]">
          Know Your Body. Move With Purpose.
        </h1>
        <p className="mt-6 text-[16px] leading-[1.4] tracking-[0.02em] text-[#fcfcfc]">
          Upload your InBody result and discover exercises tailored to your body composition
          and fitness goals.
        </p>
      </div>

      {/* Get Started -> start of the sign-in / intake flow */}
      <div className="mt-9 flex justify-center px-[61px]">
        <Link
          href="/sign-in"
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#117d69] p-[10px] text-[14px] font-bold tracking-[0.02em] text-[#fcfcfc]"
        >
          Get Started
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" className="h-[6px] w-5" src={imgArrow} />
        </Link>
      </div>

      {/* Decorative illustration */}
      <div className="pointer-events-none absolute left-[-16.5px] top-[597.89px] h-[287.608px] w-[444.287px]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="" className="absolute inset-0 block size-full max-w-none" src={imgBlob} />
      </div>
      <div className="pointer-events-none">
        <IllustrationLayer
          left="-5px"
          top="611px"
          pieces={[
            "/hero/illus-a-5.svg",
            "/hero/illus-a-4.svg",
            "/hero/illus-a-3.svg",
            "/hero/illus-a-2.svg",
            "/hero/illus-a-1.svg",
          ]}
        />
        <IllustrationLayer
          left="-2px"
          top="613px"
          pieces={[
            "/hero/illus-b-5.svg",
            "/hero/illus-b-4.svg",
            "/hero/illus-b-3.svg",
            "/hero/illus-b-2.svg",
            "/hero/illus-b-1.svg",
          ]}
        />
      </div>
    </PhoneFrame>
  );
}
