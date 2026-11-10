"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  ShieldAlert, 
  LayoutDashboard, 
  AlertTriangle, 
  Server, 
  Settings, 
  Activity, 
  Flame,
  Radio,
  Clock,
  Scale,
  BrainCircuit,
  TestTube
} from "lucide-react";

const NAV_ITEMS = [
  { label: "Overview", href: "/", icon: LayoutDashboard },
  { label: "Incidents", href: "/incidents", icon: AlertTriangle },
  { label: "Telemetry Explorer", href: "/telemetry", icon: Radio },
  { label: "Failure Injection Lab", href: "/simulation", icon: Flame },
  { label: "Services & Topology", href: "/services", icon: Server },
  { label: "System Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-slate-800 bg-[#0b101b] flex flex-col justify-between shrink-0 select-none">
      <div>
        {/* Brand Header */}
        <div className="h-16 border-b border-slate-800 px-5 flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
            <ShieldAlert className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="font-bold text-white tracking-tight text-base">INCIDENTX</span>
              <span className="text-blue-500 font-mono font-semibold text-xs">AI</span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium tracking-tight">Reliability Intelligence</p>
          </div>
        </div>

        {/* Navigation Section */}
        <div className="p-3 space-y-1">
          <div className="px-3 py-2 text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold">
            Operations Console
          </div>
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center space-x-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                  isActive
                    ? "bg-blue-600/15 text-blue-400 border border-blue-500/30 font-semibold shadow-sm shadow-blue-500/10"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-blue-400" : "text-slate-400"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>

        {/* Innovation Pillars Indicator */}
        <div className="px-5 py-4 border-t border-slate-800/80 mt-2">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold mb-2.5">
            Core Differentiators
          </div>
          <div className="space-y-2 text-[11px] font-mono text-slate-400">
            <div className="flex items-center space-x-2">
              <Clock className="w-3.5 h-3.5 text-blue-400" />
              <span>Incident Time Machine</span>
            </div>
            <div className="flex items-center space-x-2">
              <Scale className="w-3.5 h-3.5 text-purple-400" />
              <span>Root Cause Courtroom</span>
            </div>
            <div className="flex items-center space-x-2">
              <BrainCircuit className="w-3.5 h-3.5 text-amber-400" />
              <span>Active Planner</span>
            </div>
            <div className="flex items-center space-x-2">
              <TestTube className="w-3.5 h-3.5 text-emerald-400" />
              <span>What-If Lab</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer System Status */}
      <div className="p-4 border-t border-slate-800 bg-[#080d17]">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="text-slate-400">Observability Loop</span>
          <span className="text-emerald-400 font-bold flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            ACTIVE
          </span>
        </div>
        <div className="text-[10px] text-slate-400 font-mono mt-1">
          OpenTelemetry + Prometheus
        </div>
      </div>
    </aside>
  );
}
