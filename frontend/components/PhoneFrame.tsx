import React from "react";

/**
 * Shared phone-width column and desktop iPhone frame that wraps every screen.
 *
 * On desktop (>= 640px):
 *   Renders an iPhone 16 Pro at its real point size (402 x 874 screen) inside a
 *   titanium band and black glass bezel, with the Action button, volume keys, side
 *   button, Camera Control, Dynamic Island, status bar and home indicator. The whole
 *   device is scaled down to fit the window height (see `.phone-fit` in globals.css),
 *   so the page never scrolls and the app scrolls inside the screen, like a real phone.
 *   The screen is also the containing block for `position: fixed` overlays, so modals
 *   cover the phone screen rather than the browser window.
 *
 * On mobile (< 640px):
 *   Renders edge-to-edge as a native full-screen view without the device chrome.
 */

// Left: Action button, volume up, volume down. Right: side button, Camera Control.
const LEFT_BUTTONS = [
  { top: 150, height: 32 },
  { top: 208, height: 62 },
  { top: 284, height: 62 },
];
const RIGHT_BUTTONS = [
  { top: 244, height: 100 },
  { top: 506, height: 64, flush: true },
];

// Antenna breaks cut into the titanium band near each corner.
const ANTENNA_LINES = [
  "left-0 top-[86px]",
  "right-0 top-[86px]",
  "left-0 bottom-[86px]",
  "right-0 bottom-[86px]",
];

function StatusIcons() {
  return (
    <div className="flex items-center gap-[6px]">
      {/* Cellular */}
      <svg width="19" height="12" viewBox="0 0 19 12" fill="currentColor" aria-hidden="true">
        <rect x="0" y="7.5" width="3.2" height="4.5" rx="1" />
        <rect x="5.2" y="5" width="3.2" height="7" rx="1" />
        <rect x="10.4" y="2.5" width="3.2" height="9.5" rx="1" />
        <rect x="15.6" y="0" width="3.2" height="12" rx="1" />
      </svg>
      {/* Wi-Fi */}
      <svg width="17" height="12" viewBox="0 0 17 12" fill="currentColor" aria-hidden="true">
        <path d="M8.5 2.47c2.3 0 4.4.87 5.99 2.3a.4.4 0 0 0 .55-.02l1.13-1.14a.4.4 0 0 0 0-.58A11.1 11.1 0 0 0 8.5 0 11.1 11.1 0 0 0 .83 3.03a.4.4 0 0 0 0 .58l1.13 1.14c.15.15.4.16.55.02A8.8 8.8 0 0 1 8.5 2.47Z" />
        <path d="M8.5 6.2c1.26 0 2.42.46 3.3 1.23a.4.4 0 0 0 .55-.01l1.13-1.14a.4.4 0 0 0-.01-.59 7.1 7.1 0 0 0-9.94 0 .4.4 0 0 0-.01.59l1.13 1.14c.15.15.39.16.55.01A5 5 0 0 1 8.5 6.2Z" />
        <path d="M10.73 9.13a.4.4 0 0 0-.02-.58 3.3 3.3 0 0 0-4.42 0 .4.4 0 0 0-.02.58l1.94 1.96a.4.4 0 0 0 .58 0l1.94-1.96Z" />
      </svg>
      {/* Battery */}
      <svg width="27" height="13" viewBox="0 0 27 13" aria-hidden="true">
        <rect x="0.5" y="0.5" width="23" height="12" rx="3.8" fill="none" stroke="currentColor" strokeOpacity="0.4" />
        <rect x="2" y="2" width="20" height="9" rx="2.5" fill="currentColor" />
        <path d="M25 4.5v4c.8-.3 1.5-1.1 1.5-2s-.7-1.7-1.5-2Z" fill="currentColor" fillOpacity="0.45" />
      </svg>
    </div>
  );
}

export default function PhoneFrame({
  children,
  bg = "bg-[#3e3e3e]",
}: {
  children: React.ReactNode;
  bg?: string;
}) {
  return (
    <div className="relative flex min-h-screen w-full flex-col items-center bg-[#0c0e12] sm:py-5 selection:bg-[#117d69] selection:text-white">
      {/* Soft spotlight behind the device on desktop */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 z-0 hidden opacity-40 sm:block"
        style={{
          background:
            "radial-gradient(circle at 50% 35%, rgba(17, 125, 105, 0.22) 0%, rgba(12, 14, 18, 0.7) 60%, #0c0e12 100%)",
        }}
      />

      {/* Layout box sized to the scaled device; the device itself is scaled inside it */}
      <div className="phone-fit relative z-10 w-full sm:my-auto">
        <div className="phone-device relative w-full sm:h-[902px] sm:w-[436px] sm:px-[3px]">
          {/* Hardware buttons */}
          {LEFT_BUTTONS.map((b) => (
            <div
              key={b.top}
              aria-hidden="true"
              className="absolute left-0 hidden w-[4px] rounded-l-[3px] bg-[linear-gradient(90deg,#1c1d20,#5d6066_45%,#2a2b2f)] shadow-[inset_0_1px_0_rgba(255,255,255,0.18),inset_0_-1px_0_rgba(0,0,0,0.5)] sm:block"
              style={{ top: b.top, height: b.height }}
            />
          ))}
          {RIGHT_BUTTONS.map((b) => (
            <div
              key={b.top}
              aria-hidden="true"
              className={`absolute right-0 hidden rounded-r-[3px] bg-[linear-gradient(270deg,#1c1d20,#5d6066_45%,#2a2b2f)] shadow-[inset_0_1px_0_rgba(255,255,255,0.18),inset_0_-1px_0_rgba(0,0,0,0.5)] sm:block ${
                b.flush ? "w-[3.5px] right-[0.5px]" : "w-[4px]"
              }`}
              style={{ top: b.top, height: b.height }}
            />
          ))}

          {/* Titanium band */}
          <div className="relative h-full w-full sm:rounded-[70px] sm:bg-[linear-gradient(135deg,#6f7278_0%,#2f3136_18%,#4b4e54_48%,#26282c_78%,#65686e_100%)] sm:p-[4px] sm:shadow-[inset_0_0_0_1px_rgba(255,255,255,0.14),inset_0_0_3px_1px_rgba(0,0,0,0.55),0_40px_80px_-20px_rgba(0,0,0,0.9),0_18px_36px_-12px_rgba(0,0,0,0.7)]">
            {ANTENNA_LINES.map((pos) => (
              <div
                key={pos}
                aria-hidden="true"
                className={`absolute hidden h-[5px] w-[4px] bg-[#16171a]/80 sm:block ${pos}`}
              />
            ))}

            {/* Black glass bezel */}
            <div className="relative h-full w-full sm:rounded-[66px] sm:bg-black sm:p-[10px] sm:shadow-[inset_0_0_0_1px_rgba(255,255,255,0.07)]">
              {/* Screen */}
              <div
                className={`phone-screen relative flex min-h-screen w-full flex-col overflow-hidden sm:h-[874px] sm:min-h-0 sm:rounded-[56px] ${bg}`}
              >
                {/* Status bar + Dynamic Island (desktop only) */}
                <header
                  aria-hidden="true"
                  className="pointer-events-none absolute inset-x-0 top-0 z-40 hidden h-[59px] select-none items-center text-white sm:flex"
                >
                  <span className="flex flex-1 justify-center pr-[10px] text-[17px] font-semibold tracking-[-0.4px]">
                    9:41
                  </span>
                  <div className="w-[126px] shrink-0" />
                  <div className="flex flex-1 justify-center pr-[14px]">
                    <StatusIcons />
                  </div>
                </header>
                <div
                  aria-hidden="true"
                  className="pointer-events-none absolute left-1/2 top-[11px] z-50 hidden h-[37px] w-[126px] -translate-x-1/2 items-center justify-end rounded-full bg-black pr-[11px] sm:flex"
                >
                  {/* Front camera */}
                  <div className="size-[12px] rounded-full bg-[radial-gradient(circle_at_35%_35%,#2b3550_0%,#10141f_45%,#050608_100%)] shadow-[inset_0_0_0_1px_rgba(40,48,70,0.6)]" />
                </div>

                {/* Screen content (scrolls inside the phone on desktop) */}
                <div className="no-scrollbar relative flex-1 overflow-x-hidden sm:overflow-y-auto">
                  {children}
                </div>

                {/* Home indicator (desktop only) */}
                <div
                  aria-hidden="true"
                  className="pointer-events-none absolute bottom-[8px] left-1/2 z-40 hidden h-[5px] w-[139px] -translate-x-1/2 rounded-full bg-white/90 sm:block"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
