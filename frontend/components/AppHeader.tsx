import Link from "next/link";
import Icon from "./Icon";

/**
 * Top bar on signed-in screens (Dashboard). Logo on the left; History and
 * Profile on the right.
 */
export default function AppHeader() {
  return (
    <header className="relative flex h-[120px] items-start justify-between bg-gradient-to-b from-black/60 to-transparent px-[30px] pt-[59px]">
      <Link href="/" aria-label="InForm home" className="rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-[#7ee0cf]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="InForm" src="/brand/inform-logo-on-dark.png" className="h-[37px] w-auto" />
      </Link>
      <nav aria-label="Account" className="flex items-center gap-[27px] text-[#fcfcfc]">
        <Link href="/history" aria-label="Scan history" className="rounded-full hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#7ee0cf]">
          <Icon name="history" size={32} />
        </Link>
        <Link href="/account" aria-label="Your profile" className="rounded-full hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#7ee0cf]">
          <Icon name="accountCircle" size={32} />
        </Link>
      </nav>
    </header>
  );
}
