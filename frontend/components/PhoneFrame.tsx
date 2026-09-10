/**
 * Shared phone-width column that wraps every screen. The Figma file also
 * draws an OS status bar and home-indicator bar on every frame, but those
 * are the design tool's device-preview chrome, not real product UI — this
 * deliberately does not reproduce them. `bg` sets the screen's own
 * background (each design screen uses a different one).
 */
export default function PhoneFrame({
  children,
  bg = "bg-white",
}: {
  children: React.ReactNode;
  bg?: string;
}) {
  return (
    <div className="flex flex-1 justify-center bg-[#0a0a0a]">
      <div className={`relative min-h-[874px] w-full max-w-[402px] overflow-hidden ${bg}`}>
        {children}
      </div>
    </div>
  );
}
