"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { loadJSON, saveJSON, SESSION_KEYS } from "@/lib/session";
import Icon from "./Icon";

/** How many recent in-app routes to remember. Only the length matters, and only
 * whether it is greater than one, so this stays tiny. */
const TRAIL_LIMIT = 10;

/** Record this route as visited, and report whether anything preceded it.
 *
 * `router.back()` walks the browser's history, which is not the same thing as
 * the app's history: on a route someone deep-linked or opened in a new tab, the
 * previous entry belongs to whatever site they came from. Going back there would
 * leave the app, which Requirement 2.3 forbids. So the trail is recorded by the
 * Back control itself and `router.back()` is only used when the trail proves
 * there is somewhere inside the app to go back to.
 */
function useBackTrail(pathname: string): { canGoBack: boolean } {
  // Defaults to false, so a click landing before the effect runs pushes the
  // explicit fallback rather than gambling on the browser's history.
  const [canGoBack, setCanGoBack] = useState(false);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    const trail = loadJSON<string[]>(SESSION_KEYS.backTrail) ?? [];
    const alreadyRecorded = trail[trail.length - 1] === pathname;
    const next = alreadyRecorded ? trail : [...trail, pathname].slice(-TRAIL_LIMIT);
    if (!alreadyRecorded) saveJSON(SESSION_KEYS.backTrail, next);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCanGoBack(next.length > 1);
  }, [pathname]);

  return { canGoBack };
}

/**
 * The single Back control, on every screen except the landing page
 * (Requirements 2.1-2.3).
 *
 * Pass `href` whenever the screen knows where Back means — it is the only form
 * that cannot possibly leave the app, and it also survives someone arriving by
 * deep link with no history to walk. Without `href` this walks the in-app trail
 * and falls back to `fallbackHref` when there is nothing in-app behind us.
 */
export default function BackButton({
  href,
  fallbackHref = "/",
  label = "Back",
  className = "",
}: {
  /** Explicit in-app destination. Preferred: it can never escape the app. */
  href?: string;
  /** Where to land when there is no in-app history to walk. */
  fallbackHref?: string;
  /** Accessible name, for screens where "Back" is ambiguous. */
  label?: string;
  className?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { canGoBack } = useBackTrail(pathname);

  // Figma "back" pill: 75x28, light gradient, arrow + label.
  const shell = `inline-flex h-[28px] w-[75px] shrink-0 items-center justify-center gap-[5px] rounded-[60px] bg-gradient-to-b from-[#fcfcfc] to-[#f3f3f3] text-[12px] font-bold tracking-[0.04em] text-black shadow-sm transition-opacity hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#117d69] ${className}`;
  const content = (
    <>
      <Icon name="arrowLeft" size={16} />
      <span aria-hidden="true">Back</span>
    </>
  );

  if (href) {
    return (
      <Link href={href} aria-label={label} className={shell}>
        {content}
      </Link>
    );
  }

  return (
    <button
      type="button"
      aria-label={label}
      onClick={() => (canGoBack ? router.back() : router.push(fallbackHref))}
      className={shell}
    >
      {content}
    </button>
  );
}
