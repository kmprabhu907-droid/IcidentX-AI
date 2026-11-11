"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  BrainCircuit,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Play,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Clock,
  Layers,
  Settings,
  Flame,
  Radio,
  ExternalLink,
  RefreshCw,
  Sliders,
  Terminal,
  Zap,
  Info,
} from "lucide-react";
import { api } from "../../services/api";
import {
  ActionRegistryItem,
  ExecutionMode,
  RemediationPolicy,
} from "../../types";

export default function RemediationCommandCenterPage() {
  const [policy, setPolicy] = useState<RemediationPolicy | null>(null);
  const [registry, setRegistry] = useState<ActionRegistryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [updatingMode, setUpdatingMode] = useState(false);
  const [actionInProgress, setActionInProgress] = useState(false);
  const [selectedActionModal, setSelectedActionModal] = useState<ActionRegistryItem | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [polRes, regRes] = await Promise.all([
        api.getRemediationPolicy().catch(() => null),
        api.getRemediationRegistry().catch(() => []),
      ]);
      setPolicy(polRes);
      setRegistry(regRes);
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message || "Failed to load policy." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleModeChange = async (newMode: ExecutionMode) => {
    setUpdatingMode(true);
    setFeedbackMsg(null);
    try {
      const updated = await api.updateRemediationPolicy({ mode: newMode });
      setPolicy(updated);
      setFeedbackMsg({ type: "success", text: `Safety execution mode updated to ${newMode}.` });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message || "Failed to update safety mode." });
    } finally {
      setUpdatingMode(false);
    }
  };

  const handleEmergencyStop = async () => {
    if (!confirm("EMERGENCY STOP: Are you certain you want to lock down all remediation actions and trip the circuit breaker?")) {
      return;
    }
    setActionInProgress(true);
    try {
      const updated = await api.triggerEmergencyStop("Operator manual emergency stop from Command Center");
      setPolicy(updated);
      setFeedbackMsg({ type: "error", text: "EMERGENCY STOP ACTIVATED: Remediation locked down." });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message });
    } finally {
      setActionInProgress(false);
    }
  };

  const handleResetCircuitBreaker = async () => {
    setActionInProgress(true);
    try {
      const updated = await api.resetCircuitBreaker();
      setPolicy(updated);
      setFeedbackMsg({ type: "success", text: "Circuit breaker reset. Normal safety policy operational." });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message });
    } finally {
      setActionInProgress(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Banner Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <BrainCircuit className="w-5 h-5 text-indigo-400" />
              <span>Remediation Command Center</span>
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 font-bold">
              Phase 4: Self-Healing Engine
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Safe, auditable autonomous self-healing engine with empirical recovery verification and instant rollback.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/80 hover:bg-slate-800 text-xs font-mono text-slate-400 transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleEmergencyStop}
            disabled={actionInProgress}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-mono font-bold shadow-lg shadow-red-900/40 transition-all"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>EMERGENCY STOP</span>
          </button>
        </div>
      </div>

      {feedbackMsg && (
        <div
          className={`p-3 rounded-lg border text-xs font-mono flex items-center justify-between ${
            feedbackMsg.type === "success"
              ? "bg-emerald-950/20 border-emerald-500/30 text-emerald-300"
              : "bg-red-950/20 border-red-500/30 text-red-300"
          }`}
        >
          <span>{feedbackMsg.text}</span>
          <button onClick={() => setFeedbackMsg(null)} className="text-slate-400 hover:text-white">
            &times;
          </button>
        </div>
      )}

      {/* Safety Policy & Mode Controller */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-[#0e1424] shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-sm font-bold text-white font-mono flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Safety Governance &amp; Execution Mode</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              IncidentX operates under a strict safety hierarchy. Recommendation Only is the secure default.
            </p>
          </div>

          {policy?.circuit_breaker_tripped ? (
            <div className="flex items-center space-x-2">
              <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-red-500/20 text-red-400 border border-red-500/40 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
                <span>CIRCUIT BREAKER TRIPPED</span>
              </span>
              <button
                onClick={handleResetCircuitBreaker}
                disabled={actionInProgress}
                className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs font-mono text-white border border-slate-700"
              >
                Reset Breaker
              </button>
            </div>
          ) : (
            <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Circuit Breaker Armed (Healthy)</span>
            </span>
          )}
        </div>

        {/* 3 Execution Modes Selector */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Mode A: Recommendation Only */}
          <div
            onClick={() => handleModeChange("RECOMMENDATION_ONLY")}
            className={`p-4 rounded-xl border cursor-pointer transition-all space-y-2 ${
              policy?.mode === "RECOMMENDATION_ONLY"
                ? "border-blue-500 bg-blue-950/20 shadow-md shadow-blue-950/50"
                : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-blue-400">Mode A</span>
              {policy?.mode === "RECOMMENDATION_ONLY" && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500 text-white font-bold">
                  ACTIVE
                </span>
              )}
            </div>
            <h3 className="text-sm font-bold text-white font-mono">Recommendation Only</h3>
            <p className="text-xs text-slate-400 font-sans leading-relaxed">
              Safe advisory mode. Intelligence engine ranks recovery actions, but execution is blocked. <strong>Default safe state.</strong>
            </p>
          </div>

          {/* Mode B: Human Approval */}
          <div
            onClick={() => handleModeChange("HUMAN_APPROVAL")}
            className={`p-4 rounded-xl border cursor-pointer transition-all space-y-2 ${
              policy?.mode === "HUMAN_APPROVAL"
                ? "border-purple-500 bg-purple-950/20 shadow-md shadow-purple-950/50"
                : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-purple-400">Mode B</span>
              {policy?.mode === "HUMAN_APPROVAL" && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500 text-white font-bold">
                  ACTIVE
                </span>
              )}
            </div>
            <h3 className="text-sm font-bold text-white font-mono">Human Approval Required</h3>
            <p className="text-xs text-slate-400 font-sans leading-relaxed">
              Operators review expected impact, risk tiers, and telemetry before explicitly authorizing action execution.
            </p>
          </div>

          {/* Mode C: Controlled Autonomous */}
          <div
            onClick={() => handleModeChange("CONTROLLED_AUTONOMOUS")}
            className={`p-4 rounded-xl border cursor-pointer transition-all space-y-2 ${
              policy?.mode === "CONTROLLED_AUTONOMOUS"
                ? "border-emerald-500 bg-emerald-950/20 shadow-md shadow-emerald-950/50"
                : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-emerald-400">Mode C</span>
              {policy?.mode === "CONTROLLED_AUTONOMOUS" && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500 text-white font-bold">
                  ACTIVE
                </span>
              )}
            </div>
            <h3 className="text-sm font-bold text-white font-mono">Controlled Autonomous</h3>
            <p className="text-xs text-slate-400 font-sans leading-relaxed">
              Allows explicitly allowlisted, low-risk actions to run automatically. High/Medium risk actions <strong>always require human sign-off</strong>.
            </p>
          </div>
        </div>

        {/* Safety Invariants Specs */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs font-mono pt-2 border-t border-slate-800">
          <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800">
            <span className="text-[10px] text-slate-500 block uppercase">Execution Sandbox</span>
            <span className="text-slate-200 font-bold">Isolated Simulation</span>
          </div>
          <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800">
            <span className="text-[10px] text-slate-500 block uppercase">Max Actions / Incident</span>
            <span className="text-slate-200 font-bold">{policy?.max_actions_per_incident || 3} Attempts</span>
          </div>
          <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800">
            <span className="text-[10px] text-slate-500 block uppercase">LLM Code Generation</span>
            <span className="text-red-400 font-bold">STRICTLY PROHIBITED</span>
          </div>
          <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800">
            <span className="text-[10px] text-slate-500 block uppercase">Verification Policy</span>
            <span className="text-emerald-400 font-bold">Empirical Proof Req.</span>
          </div>
        </div>
      </div>

      {/* Controlled Action Registry Catalog */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white font-mono flex items-center gap-2">
            <Sliders className="w-4 h-4 text-purple-400" />
            <span>Controlled Action Registry (8 Safe Predefined Actions)</span>
          </h2>
          <span className="text-xs font-mono text-slate-400">
            {registry.length} Validated Actions
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {registry.map((act) => (
            <div
              key={act.action_id}
              className="p-5 rounded-xl border border-slate-800 bg-[#0e1424] hover:border-slate-700 transition-all space-y-3 flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-indigo-400">{act.action_id}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                        act.risk_level === "LOW"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                          : act.risk_level === "MEDIUM"
                          ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                          : "bg-red-500/10 text-red-400 border-red-500/30"
                      }`}
                    >
                      {act.risk_level} RISK
                    </span>
                  </div>
                  <span className="text-slate-400 text-[11px]">{act.timeout_seconds}s timeout</span>
                </div>

                <h3 className="text-sm font-bold text-white font-mono">{act.name}</h3>
                <p className="text-xs text-slate-300 font-sans leading-relaxed">{act.description}</p>

                <div className="pt-2 flex flex-wrap gap-1.5">
                  {act.supported_incident_types.map((st) => (
                    <span
                      key={st}
                      className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400"
                    >
                      {st}
                    </span>
                  ))}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
                <span>Cost: <strong className="text-slate-300">{act.estimated_cost}</strong></span>
                <button
                  onClick={() => setSelectedActionModal(act)}
                  className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 text-[11px]"
                >
                  <Terminal className="w-3 h-3" />
                  <span>Inspect Schema</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Schema Inspector Modal */}
      {selectedActionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-[#0c1220] p-6 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2 text-sm font-mono font-bold text-white">
                <Terminal className="w-4 h-4 text-indigo-400" />
                <span>{selectedActionModal.action_id} &bull; Parameter Contract</span>
              </div>
              <button
                onClick={() => setSelectedActionModal(null)}
                className="text-xs font-mono text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-900 border border-slate-800"
              >
                Close &times;
              </button>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="text-slate-300 font-bold">{selectedActionModal.name}</div>
              <div className="text-slate-400 font-sans">{selectedActionModal.description}</div>
            </div>

            <div className="flex-1 overflow-auto bg-[#060a12] p-4 rounded-xl border border-slate-900 font-mono text-xs text-emerald-400">
              <pre>
                <code>{JSON.stringify(selectedActionModal.parameter_schema, null, 2)}</code>
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
