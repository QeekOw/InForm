import Link from "next/link";

/**
 * Shared iPhone frame that wraps every screen.
 * Embeds the Global Navigation Bar with the InForm brand logo link pushing to "/"
 * in the top-left corner across all views so the user is never trapped.
 */
export default function PhoneFrame({
  children,
  bg = "bg-white",
  showNav = false,
  scrollable = true,
}: {
  children: React.ReactNode;
  bg?: string;
  /**
   * Whether to render the global navigation bar with the logo link.
   * Off by default since the Figma redesign: screens carry a "back" pill or
   * their own branding instead of a shared logo bar.
   */
  showNav?: boolean;
  scrollable?: boolean;
}) {
  return (
    <div className="flex h-full min-h-0 w-full flex-1 items-center justify-center bg-[#0a0a0a]">
      <div
        className="relative h-full max-h-[874px] w-[min(430px,49.2dvh)] overflow-hidden rounded-[48px] border-[8px] border-[#252525] bg-[#050505] p-[4px] shadow-[0_24px_80px_rgba(0,0,0,0.65)] max-[430px]:max-h-none max-[430px]:w-full max-[430px]:rounded-none max-[430px]:border-0 max-[430px]:p-0 max-[430px]:shadow-none"
      >
        <div
          className={`phone-screen relative h-full w-full overflow-x-hidden ${
            scrollable ? "overflow-y-auto overscroll-contain" : "overflow-y-hidden"
          } rounded-[38px] max-[430px]:rounded-none ${bg}`}
        >
          {/* Global Navigation Bar: persists across all views so the user is never trapped */}
          {showNav && (
            <header className="relative z-30 flex h-[48px] w-full shrink-0 items-center justify-between px-6 pt-3">
              <Link
                href="/"
                className="inline-flex items-center transition-opacity hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-[#117d69] focus:ring-offset-2 focus:ring-offset-transparent rounded"
                aria-label="InForm Home"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src="/brand/inform-logo-on-dark.png"
                  alt="InForm"
                  className="h-[22px] w-auto"
                />
              </Link>
            </header>
          )}

          {children}
        </div>
      </div>
    </div>
  );
}
