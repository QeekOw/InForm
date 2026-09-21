import React from "react";

/**
 * Shared phone-width column and desktop iPhone emulator frame that wraps every screen.
 *
 * On desktop (>= 640px):
 *   Renders an authentic iPhone 16 Pro / 15 Pro titanium emulator frame with physical
 *   side buttons, Dynamic Island, iOS status indicators (time, wifi, cellular, battery),
 *   and home indicator bar, with smooth internal scrolling.
 *
 * On mobile (< 640px):
 *   Renders seamlessly as an edge-to-edge native full-screen view without double bezels.
 */
export default function PhoneFrame({
  children,
  bg = "bg-[#3e3e3e]",
}: {
  children: React.ReactNode;
  bg?: string;
}) {
  return (
    <div className="relative flex min-h-screen w-full flex-col items-center justify-center bg-[#0c0e12] sm:py-8 sm:px-4 selection:bg-[#117d69] selection:text-white">
      {/* Subtle ambient spotlight behind device on desktop */}
      <div
        className="pointer-events-none fixed inset-0 z-0 opacity-40"
        style={{
          background:
            "radial-gradient(circle at 50% 35%, rgba(17, 125, 105, 0.22) 0%, rgba(12, 14, 18, 0.7) 60%, #0c0e12 100%)",
        }}
      />

      {/* Phone Emulator Outer Chassis */}
      <div className="relative z-10 w-full sm:w-[426px] sm:my-auto">
        {/* Physical Side Buttons (Left side: Action + Volume Rockers) */}
        <div
          aria-hidden="true"
          className="hidden sm:block absolute -left-[3px] top-[115px] w-[3px] h-[26px] bg-[#3a3b41] rounded-l-[2px] shadow-[inset_1px_1px_1px_rgba(255,255,255,0.25)]"
        />
        <div
          aria-hidden="true"
          className="hidden sm:block absolute -left-[3px] top-[156px] w-[3px] h-[52px] bg-[#3a3b41] rounded-l-[2px] shadow-[inset_1px_1px_1px_rgba(255,255,255,0.25)]"
        />
        <div
          aria-hidden="true"
          className="hidden sm:block absolute -left-[3px] top-[220px] w-[3px] h-[52px] bg-[#3a3b41] rounded-l-[2px] shadow-[inset_1px_1px_1px_rgba(255,255,255,0.25)]"
        />

        {/* Physical Side Buttons (Right side: Power / Siri Button) */}
        <div
          aria-hidden="true"
          className="hidden sm:block absolute -right-[3px] top-[175px] w-[3px] h-[76px] bg-[#3a3b41] rounded-r-[2px] shadow-[inset_-1px_1px_1px_rgba(255,255,255,0.25)]"
        />

        {/* iPhone Titanium Frame Body */}
        <div className="relative w-full sm:rounded-[55px] bg-gradient-to-b from-[#2e3036] via-[#1a1b1e] to-[#121316] sm:p-[11px] sm:shadow-[0_0_0_1px_rgba(255,255,255,0.12),0_25px_65px_-10px_rgba(0,0,0,0.85),0_15px_30px_rgba(0,0,0,0.7)] sm:ring-1 sm:ring-black/60">
          
          {/* Inner Screen Display Viewport */}
          <div
            className={`relative w-full min-h-screen sm:min-h-0 sm:h-[874px] sm:max-h-[874px] sm:rounded-[44px] overflow-hidden flex flex-col ${bg}`}
          >
            {/* iOS Status Bar + Dynamic Island (Desktop only) */}
            <header className="hidden sm:flex absolute top-0 inset-x-0 h-[48px] px-7 items-center justify-between z-40 pointer-events-none select-none text-white">
              {/* iOS Clock */}
              <span className="text-[13px] font-semibold tracking-tight text-white/90">
                9:41
              </span>

              {/* Dynamic Island (Mathematically centered) */}
              <div className="absolute left-1/2 top-2.5 -translate-x-1/2 w-[110px] h-[30px] bg-black rounded-full flex items-center justify-between px-3 shadow-[0_2px_8px_rgba(0,0,0,0.6)]">
                {/* Camera lens */}
                <div className="size-2.5 rounded-full bg-[#0d121d] ring-1 ring-[#1f293d]/60 flex items-center justify-center">
                  <div className="size-1 rounded-full bg-[#2563eb]/50" />
                </div>
                {/* Sensor dot */}
                <div className="size-1.5 rounded-full bg-[#080808]" />
              </div>

              {/* Status Icons: Cellular, Wi-Fi, Battery */}
              <div className="flex items-center gap-1.5 text-white/90">
                {/* Cellular bars */}
                <svg className="w-4 h-3 fill-current" viewBox="0 0 18 12">
                  <rect x="0.5" y="8.5" width="2.5" height="3.5" rx="0.6" />
                  <rect x="5" y="6" width="2.5" height="6" rx="0.6" />
                  <rect x="9.5" y="3.5" width="2.5" height="8.5" rx="0.6" />
                  <rect x="14" y="0.5" width="2.5" height="11.5" rx="0.6" />
                </svg>

                {/* Wi-Fi */}
                <svg className="w-3.5 h-3 fill-current" viewBox="0 0 16 12">
                  <path d="M8 9.5C8.83 9.5 9.5 10.17 9.5 11C9.5 11.83 8.83 12.5 8 12.5C7.17 12.5 6.5 11.83 6.5 11C6.5 10.17 7.17 9.5 8 9.5Z" />
                  <path
                    fillRule="evenodd"
                    clipRule="evenodd"
                    d="M3.76 6.76C6.1 4.41 9.9 4.41 12.24 6.76C12.63 7.15 13.27 7.15 13.66 6.76C14.05 6.37 14.05 5.73 13.66 5.34C10.53 2.22 5.47 2.22 2.34 5.34C1.95 5.73 1.95 6.37 2.34 6.76C2.73 7.15 3.37 7.15 3.76 6.76Z"
                  />
                  <path
                    fillRule="evenodd"
                    clipRule="evenodd"
                    d="M1.29 3.29C5 -0.42 11 -0.42 14.71 3.29C15.1 3.68 15.1 4.31 14.71 4.7C14.32 5.09 13.69 5.09 13.3 4.7C10.37 1.77 5.63 1.77 2.7 4.7C2.31 5.09 1.68 5.09 1.29 4.7C0.9 4.31 0.9 3.68 1.29 3.29Z"
                  />
                </svg>

                {/* Battery */}
                <div className="flex items-center gap-[1px]">
                  <div className="w-[19px] h-[10px] rounded-[3px] border border-white/80 p-[1px] flex items-center">
                    <div className="h-full w-full bg-white rounded-[1.5px]" />
                  </div>
                  <div className="w-[1.5px] h-[3.5px] bg-white/80 rounded-r-[1px]" />
                </div>
              </div>
            </header>

            {/* Screen Content (Scrollable with hidden scrollbar) */}
            <div className="relative flex-1 h-full overflow-y-auto overflow-x-hidden no-scrollbar">
              {children}
            </div>

            {/* iOS Home Indicator Bar (Desktop only) */}
            <footer className="hidden sm:flex justify-center pb-2.5 pt-1.5 pointer-events-none select-none z-40">
              <div className="w-32 h-1 bg-white/40 rounded-full" />
            </footer>
          </div>
        </div>
      </div>
    </div>
  );
}
