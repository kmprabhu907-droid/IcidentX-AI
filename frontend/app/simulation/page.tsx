"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Flame, 
  AlertTriangle, 
  ShieldAlert, 
  Square, 
  Play, 
  RotateCcw, 
  Sliders, 
  ExternalLink,
  Layers,
  Clock,
  Radio,
  CheckCircle2,
  Info
} from "lucide-react";
import { api } from "../../services/api";
import { ChaosScenario, SimulationStatus } from "../../types";

export default function SimulationLabPage() {
  const [scenarios, setScenarios] = useState<ChaosScenario[]>([]);
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [selectedDuration, setSelectedDuration] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [injectingId, setInjectingId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [scenList, simStatus] = await Promise.all([
        api.listChaosScenarios().catch(() => []),
        api.getSimulationStatus().catch(() => null),
      ]);
      setScenarios(scenList);
      setStatus(simStatus);

      // Initialize default duration map
      const initialDur: Record<string, number> = {};
      scenList.forEach((s) => {
        initialDur[s.id] = s.default_duration_seconds;
      });
      setSelectedDuration((prev) => ({ ...initialDur, ...prev }));
    } catch (err) {
      console.error("Failed to load simulation data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleInject = async (scenarioId: string, defaultTarget: string) => {
    setInjectingId(scenarioId);
    setActionMessage(null);
    try {
      const dur = selectedDuration[scenarioId] || 60;
      const res = await api.injectChaos(scenarioId, defaultTarget, dur);
      setActionMessage(`Injected: ${res.message}`);
      await loadData();
    } catch (err: any) {
      setActionMessage(`Failed to inject: ${err.message}`);
    } finally {
      setInjectingId(null);
    }
  };

  const handleStop = async (scenarioId: string) => {
    try {
      await api.stopChaos(scenarioId);
      setActionMessage(`Stopped scenario: ${scenarioId}`);
      await loadData();
    } catch (err: any) {
      setActionMessage(`Failed to stop: ${err.message}`);
    }
  };

  const handleStopAll = async () => {
    try {
      await api.stopAllChaos();
      setActionMessage("Emergency stop executed. All chaos faults terminated.");
      await loadData();
    } catch (err: any) {
      setActionMessage(`Emergency stop failed: ${err.message}`);
    }
  };

  const isSimulatedActive = status?.is_active || false;

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <Flame className="w-6 h-6 text-red-500" />
              Failure Injection Lab
            </h1>
            <span className="px-2.5 py-1 rounded-full text-[11px] font-mono font-bold tracking-wider uppercase border bg-red-500/10 text-red-400 border-red-500/30">
              CHAOS EXPERIMENTATION
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Controlled fault injection across 9 production failure patterns. Verifies autonomous detection and correlation.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {isSimulatedActive && (
            <button
              onClick={handleStopAll}
              className="flex items-center space-x-2 bg-red-600 hover:bg-red-500 text-white font-mono text-xs px-4 py-2.5 rounded-xl font-bold shadow-lg shadow-red-600/20 transition animate-pulse"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>EMERGENCY STOP ALL</span>
            </button>
          )}

          <Link
            href="/telemetry"
            className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs px-3.5 py-2.5 rounded-xl font-mono transition"
          >
            <Radio className="w-3.5 h-3.5 text-blue-400" />
            <span>Telemetry Explorer</span>
          </Link>
        </div>
      </div>

      {/* Action Notification */}
      {actionMessage && (
        <div className="p-3 bg-blue-950/40 border border-blue-500/30 rounded-xl text-xs font-mono text-blue-300 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Info className="w-4 h-4 text-blue-400" />
            <span>{actionMessage}</span>
          </div>
          <button onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Active Simulation Status Banner */}
      {isSimulatedActive && (
        <div className="p-5 bg-amber-950/20 border border-amber-500/40 rounded-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <span className="w-3 h-3 rounded-full bg-amber-400 animate-ping" />
              <h2 className="text-sm font-bold text-amber-300 font-mono uppercase tracking-wider">
                Active Fault Injection ({status?.active_fault_count} running)
              </h2>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
              DATA SOURCE: SIMULATED
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {status?.active_faults.map((fault) => (
              <div
                key={fault.fault_id}
                className="p-3.5 bg-slate-900/90 rounded-xl border border-slate-800 text-xs font-mono flex items-center justify-between"
              >
                <div>
                  <div className="text-white font-bold">{fault.scenario_id}</div>
                  <div className="text-slate-400 text-[11px] mt-0.5">
                    Target: <span className="text-blue-400">{fault.target_service}</span> | Remaining:{" "}
                    <span className="text-amber-400">{fault.remaining_seconds}s</span>
                  </div>
                </div>
                <button
                  onClick={() => handleStop(fault.scenario_id)}
                  className="bg-red-600/20 hover:bg-red-600/40 text-red-400 border border-red-500/30 px-3 py-1.5 rounded-lg text-xs transition"
                >
                  Stop
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 9 Chaos Scenario Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {scenarios.map((scen) => {
          const isActive = status?.active_faults.some((f) => f.scenario_id === scen.id);
          const duration = selectedDuration[scen.id] || scen.default_duration_seconds;

          return (
            <div
              key={scen.id}
              className={`p-5 rounded-xl border flex flex-col justify-between transition-all ${
                isActive
                  ? "bg-amber-950/10 border-amber-500/40 shadow-lg shadow-amber-500/5"
                  : "bg-[#0f172a] border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="space-y-3">
                {/* Header tags */}
                <div className="flex items-center justify-between text-[10px] font-mono">
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    {scen.category}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded font-bold ${
                      scen.severity_potential === "SEV-1"
                        ? "bg-red-500/10 text-red-400 border border-red-500/20"
                        : scen.severity_potential === "SEV-2"
                        ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                    }`}
                  >
                    {scen.severity_potential}
                  </span>
                </div>

                {/* Title & Description */}
                <div>
                  <h3 className="text-base font-bold text-white tracking-tight">{scen.name}</h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">{scen.description}</p>
                </div>

                {/* Impact Preview */}
                <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80 text-[11px] font-mono text-slate-300">
                  <span className="text-slate-400">Impact: </span>
                  {scen.impact_summary}
                </div>

                {/* Duration Slider Control */}
                <div className="space-y-1.5 pt-1">
                  <div className="flex justify-between text-[11px] font-mono text-slate-400">
                    <span>Duration</span>
                    <span className="text-blue-400 font-semibold">{duration}s</span>
                  </div>
                  <input
                    type="range"
                    min="15"
                    max="180"
                    step="15"
                    value={duration}
                    disabled={isActive}
                    onChange={(e) =>
                      setSelectedDuration({ ...selectedDuration, [scen.id]: Number(e.target.value) })
                    }
                    className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
                  />
                </div>
              </div>

              {/* Action Button */}
              <div className="pt-5 mt-4 border-t border-slate-800/80">
                {isActive ? (
                  <button
                    onClick={() => handleStop(scen.id)}
                    className="w-full flex items-center justify-center space-x-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30 py-2.5 rounded-xl font-mono text-xs font-bold transition"
                  >
                    <Square className="w-3.5 h-3.5 fill-current" />
                    <span>Stop Simulation</span>
                  </button>
                ) : (
                  <button
                    onClick={() => handleInject(scen.id, scen.target_service)}
                    disabled={injectingId === scen.id}
                    className="w-full flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-500 text-white py-2.5 rounded-xl font-mono text-xs font-bold transition shadow-sm shadow-blue-500/20 disabled:opacity-50"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>{injectingId === scen.id ? "Injecting..." : "Inject Chaos"}</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
