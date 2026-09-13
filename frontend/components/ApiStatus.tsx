"use client";

import { useEffect, useState } from "react";

type Status = "checking" | "online" | "unreachable";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ApiStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let cancelled = false;

    fetch(`${API_URL}/health`)
      .then((res) => {
        if (!cancelled) setStatus(res.ok ? "online" : "unreachable");
      })
      .catch(() => {
        if (!cancelled) setStatus("unreachable");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const dotColor =
    status === "online"
      ? "bg-emerald-400"
      : status === "unreachable"
        ? "bg-red-400"
        : "bg-zinc-400";

  const label =
    status === "online"
      ? "Backend: online"
      : status === "unreachable"
        ? "Backend: unreachable"
        : "Backend: checking…";

  return (
    <div className="inline-flex items-center gap-2 rounded-full bg-black/30 px-3 py-1 text-xs text-[#fcfcfc] backdrop-blur-sm">
      <span className={`size-1.5 rounded-full ${dotColor}`} />
      {label}
    </div>
  );
}
