"use client";

import { useEffect, useState } from "react";
import { 
  Settings, 
  ShieldCheck, 
  Database, 
  Server, 
  Lock, 
  Terminal,
  Activity,
  CheckCircle2,
  RefreshCw
} from "lucide-react";
import { api } from "../../services/api";
import { SystemHealth } from "../../types";

export default function SettingsPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch (_) {
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            System Settings &amp; Governance
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-medium">
            Runtime configurations, safety policy guardrails, and cluster interconnects.
          </p>
        </div>

        <button
          onClick={fetchHealth}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900 text-xs font-mono text-slate-400 hover:text-white"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Test Connectivity</span>
        </button>
      </div>

      {/* Backend Status Card */}
      <div className="p-5 rounded-xl border border-slate-800 bg-[#0e1424] space-y-4 shadow-sm">
        <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
          <Activity className="w-4 h-4 text-emerald-400" />
          <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-200">
            Backend Diagnostics
          </h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3 rounded-lg border border-slate-800/80 bg-slate-900/40">
            <span className="text-slate-400 block text-[10px] uppercase">Service Name</span>
            <span className="text-white font-bold text-sm">{health?.service || "INCIDENTX AI"}</span>
          </div>

          <div className="p-3 rounded-lg border border-slate-800/80 bg-slate-900/40">
            <span className="text-slate-400 block text-[10px] uppercase">Runtime Version</span>
            <span className="text-blue-400 font-bold text-sm">v{health?.version || "0.1.0"}</span>
          </div>

          <div className="p-3 rounded-lg border border-slate-800/80 bg-slate-900/40">
            <span className="text-slate-400 block text-[10px] uppercase">PostgreSQL Connectivity</span>
            <span className={`font-bold text-sm ${health?.components.database === "connected" ? "text-emerald-400" : "text-red-400"}`}>
              {health?.components.database === "connected" ? "ONLINE & OPERATIONAL" : "DISCONNECTED"}
            </span>
          </div>

          <div className="p-3 rounded-lg border border-slate-800/80 bg-slate-900/40">
            <span className="text-slate-400 block text-[10px] uppercase">API Target URL</span>
            <span className="text-slate-300 font-mono text-xs truncate block">
              {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}
            </span>
          </div>
        </div>
      </div>

      {/* Governance & Guardrails Card */}
      <div className="p-5 rounded-xl border border-slate-800 bg-[#0e1424] space-y-4 shadow-sm">
        <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
          <ShieldCheck className="w-4 h-4 text-purple-400" />
          <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-200">
            Execution Safety Guardrails
          </h3>
        </div>

        <div className="space-y-3 text-xs font-sans">
          <div className="p-3.5 rounded-lg border border-emerald-500/20 bg-emerald-950/10 flex items-start space-x-3">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <strong className="text-emerald-300 block font-mono text-xs">Rule #5: Zero Unrestricted Execution</strong>
              <p className="text-slate-400 text-xs mt-0.5 leading-relaxed">
                Autonomous agents are strictly blocked from raw terminal or unconstrained shell execution. All mutating commands map to typed, bounded Python API calls.
              </p>
            </div>
          </div>

          <div className="p-3.5 rounded-lg border border-purple-500/20 bg-purple-950/10 flex items-start space-x-3">
            <CheckCircle2 className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
            <div>
              <strong className="text-purple-300 block font-mono text-xs">Rule #7: Human-in-the-Loop Requirement</strong>
              <p className="text-slate-400 text-xs mt-0.5 leading-relaxed">
                State-changing infrastructure operations require mandatory 1-click operator confirmation via Slack Block Kit or the IncidentX web console.
              </p>
            </div>
          </div>

          <div className="p-3.5 rounded-lg border border-blue-500/20 bg-blue-950/10 flex items-start space-x-3">
            <CheckCircle2 className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
            <div>
              <strong className="text-blue-300 block font-mono text-xs">Rule #6: Isolated Simulation Environs</strong>
              <p className="text-slate-400 text-xs mt-0.5 leading-relaxed">
                What-If Laboratory counterfactual replays execute in isolated containerized namespaces with synthetic state buffers.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
