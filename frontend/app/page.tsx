"use client";

import Link from "next/link";
import Icon from "@/components/Icon";
import PhoneFrame from "@/components/PhoneFrame";
import { btn, cardClass } from "@/components/ui";
import { useAuth } from "@/lib/AuthProvider";

const imgLogo = "/brand/inform-logo-on-dark.png";

const KEY_READINGS = [
  {
    title: "Lean Body Mass",
    body: "drives the calorie maths, through the Katch–McArdle equation.",
  },
  {
    title: "Left / Right Limb Readings",
    body: "surface muscle imbalances, which decide the corrective exercises.",
  },
  {
    title: "Body Fat Percentage",
    body: "shapes the calorie deficit or surplus for your goal.",
  },
];

export default function Home() {
  const { account, loading } = useAuth();
  // Signed-in people land on their dashboard; everyone else signs in or
  // continues as a guest from there.
  const startHref = account ? "/dashboard" : "/sign-in";

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <div id="top" />

      {/* First screen: photo, brand, headline, CTA */}
      <section className="relative h-full overflow-hidden">
        <div aria-hidden="true" className="absolute inset-0">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" src="/bg/hero.jpg" className="size-full object-cover" />
          <div className="absolute inset-x-0 top-0 h-[271px] bg-gradient-to-b from-black/70 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#3e3e3e]/40 to-[#3e3e3e]" />
        </div>

        <div className="relative flex h-full flex-col px-[30px]">
          <div className="mt-[64px] flex justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="InForm" src={imgLogo} className="h-[46px] w-auto" />
          </div>

          <div className="mt-auto">
            <h1 className="text-[32px] font-bold leading-[1.18] tracking-[0.02em] text-[#fcfcfc]">
              Know Your Body. Move With Purpose.
            </h1>
            <p className="mt-[10px] text-[16px] leading-[1.4] tracking-[0.02em] text-[#fcfcfc]">
              Upload your InBody result and discover exercises tailored to your body composition
              and fitness goals.
            </p>

            {loading ? (
              <div className="mt-[18px] h-[40px] w-full animate-pulse rounded-[8px] bg-white/10" />
            ) : (
              <Link href={startHref} className={`${btn.primary} mt-[18px]`}>
                Get Started
                <Icon name="arrowRight" size={20} />
              </Link>
            )}
          </div>

          <a
            href="#about"
            className="mb-[30px] mt-[69px] flex items-center justify-center gap-[5px] text-[12px] text-[#fcfcfc]/80 hover:text-[#fcfcfc]"
          >
            Explore more
            <Icon name="chevronsDown" size={12} />
          </a>
        </div>
      </section>

      {/* What is an InBody report? */}
      <section id="about" className="scroll-mt-4 px-[30px] pt-[49px] text-[#fcfcfc]">
        <h2 className="text-[32px] font-bold leading-[1.18] tracking-[0.02em]">
          What is an InBody report?
        </h2>
        <p className="mt-[10px] text-[13px] leading-[1.5]">
          An InBody machine measures your body composition by passing a small electrical current
          through you and reading how easily it travels. Muscle holds a lot of water and conducts
          well; fat does not. From that, it prints a sheet breaking your total weight down into
          skeletal muscle, body fat, and body water, limb by limb.
        </p>
        <p className="mt-3 text-[13px] leading-[1.5]">
          Those numbers are more useful than weight alone, and they&apos;re what this app works
          from. It reads your sheet, then builds a daily calorie and macronutrient target and an
          exercise list around what it actually measured.
        </p>
        <ul className="mt-[15px] space-y-[10px]">
          {KEY_READINGS.map((item) => (
            <li
              key={item.title}
              className="rounded-[8px] bg-gradient-to-b from-[#117d69] to-[#116e5d] px-[15px] py-[10px]"
            >
              <p className="text-[12px] font-bold">{item.title}</p>
              <p className="mt-[3px] text-[10px] text-[#fcfcfc]/90">{item.body}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* Consent and disclaimer, before anyone hands over anything */}
      <section className={`${cardClass} mx-[30px] mt-[64px] p-[24px]`}>
        <h2 className="flex items-center gap-[11px] text-[16px] font-bold text-[#117d69]">
          <Icon name="school" size={24} />
          A student passion project
        </h2>
        <p className="mt-[10px] text-[11px] leading-[1.5] text-black/80">
          InForm is an academic research prototype built by a student, not a product and not a
          company. It&apos;s shared openly so you can see how it works and judge it for yourself.
        </p>

        <h3 className="mt-[24px] text-[12px] font-bold">What happens to your sheet?</h3>
        <ul className="mt-[10px] list-disc space-y-[6px] pl-4 text-[11px] leading-[1.5] text-black/80">
          <li>
            <strong>This session only.</strong> If you upload or photograph a sheet, the image is
            held in memory just long enough for you to check the extracted numbers against it.
          </li>
          <li>
            <strong>Never stored.</strong> The image is never written to a database, cloud
            storage, disk, or logs.
          </li>
          <li>
            <strong>Dropped when you&apos;re done.</strong> Once you save or discard a scan, the
            image is gone. Only the numbers remain, and only if you saved them.
          </li>
          <li>
            <strong>An account is optional.</strong> The whole flow works without one. Signing up
            only adds saving your scans so you can see changes over time.
          </li>
        </ul>

        <h3 className="mt-[24px] text-[12px] font-bold">Not medical advice</h3>
        <p className="mt-[10px] text-[11px] leading-[1.5] text-black/80">
          The calorie targets, macronutrient splits and exercises here are produced by published
          formulas and fixed rules. They are general fitness information, not a diagnosis,
          prescription, or treatment plan, and they take no account of any medical condition,
          medication, injury, pregnancy, or eating disorder. Talk to a doctor or a registered
          dietitian before acting on any of it, especially if you have a health condition.
        </p>
        <p className="mt-2 text-[11px] leading-[1.5] text-black/80">
          Nothing here is a clinical measurement either. The numbers are only as good as the
          sheet they were read from. When a reading looks doubtful, the app will say so and ask
          you to check it against your sheet rather than quietly guessing.
        </p>
      </section>

      <a
        href="#top"
        className="mt-[64px] flex items-center justify-center gap-[5px] text-[12px] text-[#fcfcfc]/80 hover:text-[#fcfcfc]"
      >
        Back to top
        <Icon name="chevronsUp" size={12} />
      </a>
      <p className="mb-[30px] mt-[28px] text-center text-[10px] text-[#fcfcfc]/60">
        © 2026 InForm. For educational purposes only.
      </p>
    </PhoneFrame>
  );
}
