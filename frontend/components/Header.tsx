"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, Bell, Building, RefreshCw, Server, ShieldCheck } from "lucide-react";
import { api } from "../services/api";
import { SystemHealth } from "../types";

export function Header() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  const fetchHealth = async () => {
    setIsChecking(true);
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch (_) {
      setHealth(null);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 border-b border-slate-800 bg-[#0d1322]/80 backdrop-blur-md px-6 flex items-center justify-between z-20">
      <div className="flex items-center space-x-4">
        <h2 className="text-sm font-semibold text-slate-200 tracking-tight font-mono">
          CLUSTER: <span className="text-blue-400 font-bold">us-east-prod-k8s</span>
        </h2>
        <div className="hidden md:flex items-center space-x-1.5 px-2.5 py-1 rounded-md border border-slate-800 bg-slate-900/40 text-xs font-mono text-slate-400">
          <Building className="w-3.5 h-3.5 text-blue-400" />
          <span>TENANT:</span>
          <span className="text-slate-200 font-semibold">default-org</span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* Live Backend Telemetry Indicator */}
        <div className="hidden sm:flex items-center space-x-2.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 text-xs font-mono">
          <span className="text-slate-400">Backend API:</span>
          {health ? (
            <span className="text-emerald-400 font-bold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              CONNECTED ({health.components.database})
            </span>
          ) : (
            <span className="text-red-400 font-bold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
              DISCONNECTED
            </span>
          )}
        </div>

        <button
          onClick={fetchHealth}
          disabled={isChecking}
          title="Refresh Backend Connectivity"
          className="p-2 rounded-lg border border-slate-800 bg-slate-900/80 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isChecking ? "animate-spin text-blue-400" : ""}`} />
        </button>

        <Link
          href="/login"
          title="Manage Enterprise Access & RBAC Profile"
          className="flex items-center space-x-2 pl-2 border-l border-slate-800 hover:opacity-80 transition-opacity"
        >
          <div className="px-2.5 py-1 rounded-lg bg-blue-600/20 border border-blue-500/30 text-blue-400 font-mono text-xs flex items-center justify-center font-bold">
            SRE • AUTH
          </div>
        </Link>
      </div>
    </header>
  );
}
