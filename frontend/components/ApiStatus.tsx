"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/config";

type Status = "checking" | "online" | "unreachable";

const STATUS_CONFIG: Record<Status, { dotColor: string; label: string }> = {
  online: { dotColor: "bg-emerald-400", label: "Backend: online" },
  unreachable: { dotColor: "bg-red-400", label: "Backend: unreachable" },
  checking: { dotColor: "bg-zinc-400", label: "Backend: checking…" },
};

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

  const config = STATUS_CONFIG[status];

  return (
    <div className="inline-flex items-center gap-2 rounded-full bg-black/30 px-3 py-1 text-xs text-[#fcfcfc] backdrop-blur-sm">
      <span className={`size-1.5 rounded-full ${config.dotColor}`} />
      {config.label}
    </div>
  );
}
