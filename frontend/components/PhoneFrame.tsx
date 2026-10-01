import Link from "next/link";

/**
 * Shared phone-width column that wraps every screen.
 * Embeds the Global Navigation Bar with the InForm brand logo link pushing to "/"
 * in the top-left corner across all views so the user is never trapped.
 */
export default function PhoneFrame({
  children,
  bg = "bg-white",
  scrollable = false,
  showNav = false,
}: {
  children: React.ReactNode;
  bg?: string;
  /**
   * Let the frame grow past the design's fixed 874px and scroll.
   *
   * Off by default, and the off case must stay exactly what it has always been:
   * this component wraps every screen, and several of them position content
   * absolutely against the fixed height. Screens that opt in are the ones whose
   * content is genuinely longer than the viewport (Requirement 2.5).
   *
   * Screens that scroll their own inner container (`max-h-screen overflow-y-auto`)
   * do not need this and should not set it, or they end up with two scrollbars.
   */
  scrollable?: boolean;
  /**
   * Whether to render the global navigation bar with the logo link.
   * Off by default since the Figma redesign: screens carry a "back" pill or
   * their own branding instead of a shared logo bar.
   */
  showNav?: boolean;
}) {
  return (
    <div className="flex flex-1 justify-center bg-[#0a0a0a]">
      {/* `overflow-x-hidden` rather than plain `overflow-hidden` when scrollable:
          the frame still clips the decorative artwork that deliberately hangs
          past its edges, but is free to grow taller than 874px so the document
          scrolls normally. */}
      <div
        className={`relative min-h-[874px] w-full max-w-[402px] ${
          scrollable ? "overflow-x-hidden" : "overflow-hidden"
        } ${bg}`}
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
  );
}
