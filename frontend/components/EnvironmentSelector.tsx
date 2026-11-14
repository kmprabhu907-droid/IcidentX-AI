"use client";

import { useEffect, useState } from "react";
import {
  Layers,
  Server,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  ChevronDown,
  Shield,
  Info,
  X,
  Lock,
  Cpu,
  ArrowLeft,
} from "lucide-react";
import { api } from "../services/api";
import { EnvironmentMetadata, EnvironmentMode, EnvironmentHealth } from "../types";

export function EnvironmentSelector() {
  const [activeEnv, setActiveEnv] = useState<EnvironmentMetadata | null>(null);
  const [environments, setEnvironments] = useState<EnvironmentMetadata[]>([]);
  const [health, setHealth] = useState<EnvironmentHealth | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSwitching, setIsSwitching] = useState<boolean>(false);
  const [showModal, setShowModal] = useState<boolean>(false);
  const [targetMode, setTargetMode] = useState<EnvironmentMode | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchEnvironmentState = async () => {
    try {
      setIsLoading(true);
      const [active, allEnvs, envHealth] = await Promise.allSettled([
        api.getActiveEnvironment(),
        api.getEnvironments(),
        api.getEnvironmentHealth(),
      ]);

      if (active.status === "fulfilled") {
        setActiveEnv(active.value);
      }
      if (allEnvs.status === "fulfilled") {
        setEnvironments(allEnvs.value);
      }
      if (envHealth.status === "fulfilled") {
        setHealth(envHealth.value);
      }
    } catch (err: any) {
      console.error("Failed to load environment state:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEnvironmentState();
    const interval = setInterval(fetchEnvironmentState, 20000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && showModal) {
        setShowModal(false);
        setTargetMode(null);
        setErrorMsg(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showModal]);

  const initiateSwitch = (mode: EnvironmentMode) => {
    if (activeEnv?.mode === mode) return;
    setTargetMode(mode);
    setErrorMsg(null);
    setShowModal(true);
  };

  const confirmSwitch = async () => {
    if (!targetMode) return;
    setIsSwitching(true);
    setErrorMsg(null);
    try {
      const res = await api.selectEnvironment(targetMode);
      setActiveEnv(res.environment);
      setShowModal(false);
      setTargetMode(null);
      await fetchEnvironmentState();
    } catch (err: any) {
      setErrorMsg(
        err.message ||
          `Failed to connect to ${targetMode}. Explicit error raised; no silent fallback occurred.`
      );
    } finally {
      setIsSwitching(false);
    }
  };

  const isDemoMesh = activeEnv?.mode === "DEMOMESH";

  return (
    <>
      {/* Header Selector Button / Badge */}
      <div className="flex items-center space-x-2">
        <button
          onClick={() => {
            setErrorMsg(null);
            setShowModal(true);
          }}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border transition-all text-xs font-mono shadow-sm ${
            isDemoMesh
              ? "bg-purple-950/40 border-purple-800/60 hover:bg-purple-900/50 text-purple-200"
              : "bg-emerald-950/40 border-emerald-700/60 hover:bg-emerald-900/50 text-emerald-200"
          }`}
          title="Click to inspect or switch Infrastructure Environment"
        >
          {isDemoMesh ? (
            <div className="flex items-center space-x-1.5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-500"></span>
              </span>
              <Cpu className="w-3.5 h-3.5 text-purple-400" />
              <span className="font-bold tracking-tight text-purple-300">DEMOMESH</span>
              <span className="hidden lg:inline text-[10px] px-1.5 py-0.2 rounded bg-purple-900/80 text-purple-300 border border-purple-700/40">
                SIMULATION
              </span>
            </div>
          ) : (
            <div className="flex items-center space-x-1.5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <Server className="w-3.5 h-3.5 text-emerald-400" />
              <span className="font-bold tracking-tight text-emerald-300">
                {activeEnv?.cluster_name || "K8S CLUSTER"}
              </span>
              <span className="hidden lg:inline text-[10px] px-1.5 py-0.2 rounded bg-emerald-900/80 text-emerald-300 border border-emerald-700/40">
                LIVE (READ-ONLY)
              </span>
            </div>
          )}
          <ChevronDown className="w-3 h-3 text-slate-400 ml-1" />
        </button>
      </div>

      {/* Environment Management Modal */}
      {showModal && (
        <div
          onClick={() => {
            setShowModal(false);
            setTargetMode(null);
            setErrorMsg(null);
          }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-[#0f172a] border border-slate-700 rounded-xl w-full max-w-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150"
          >
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
              <div className="flex items-center space-x-2.5">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    setTargetMode(null);
                    setErrorMsg(null);
                  }}
                  className="flex items-center space-x-1.5 px-2.5 py-1 text-xs font-mono font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition"
                  title="Back to Dashboard"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back</span>
                </button>
                <div className="h-4 w-px bg-slate-700 mx-1" />
                <Layers className="w-5 h-5 text-blue-400" />
                <div>
                  <h3 className="text-sm font-bold text-slate-100 font-mono">
                    Infrastructure Environment Selector
                  </h3>
                  <p className="text-xs text-slate-400">
                    IncidentX AI Dual-Environment Abstraction Engine (Phase 8.1)
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowModal(false);
                  setTargetMode(null);
                  setErrorMsg(null);
                }}
                className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-6">
              {/* Active Environment Diagnostics Banner */}
              <div
                className={`p-4 rounded-lg border text-xs font-mono space-y-2 ${
                  isDemoMesh
                    ? "bg-purple-950/30 border-purple-800/50 text-purple-200"
                    : "bg-emerald-950/30 border-emerald-800/50 text-emerald-200"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold flex items-center gap-1.5">
                    {isDemoMesh ? (
                      <Cpu className="w-4 h-4 text-purple-400" />
                    ) : (
                      <Server className="w-4 h-4 text-emerald-400" />
                    )}
                    ACTIVE: {activeEnv?.name || activeEnv?.mode}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${
                      health?.is_healthy
                        ? "bg-emerald-900/60 text-emerald-300 border-emerald-700/50"
                        : "bg-amber-900/60 text-amber-300 border-amber-700/50"
                    }`}
                  >
                    STATUS: {health?.status || "CONNECTED"}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-300 pt-1">
                  <div>
                    <span className="text-slate-400">Data Source Tag:</span>{" "}
                    <code className="text-blue-300 bg-slate-900 px-1 rounded">
                      {activeEnv?.data_source}
                    </code>
                  </div>
                  <div>
                    <span className="text-slate-400">Access Mode:</span>{" "}
                    <span className="text-amber-300 font-semibold">
                      {activeEnv?.is_read_only ? "READ-ONLY OBSERVABILITY" : "READ-WRITE"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400">Discovered Workloads:</span>{" "}
                    <span className="text-white font-bold">{activeEnv?.total_workloads ?? 0}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Discovered Services:</span>{" "}
                    <span className="text-white font-bold">{activeEnv?.total_services ?? 0}</span>
                  </div>
                </div>

                {isDemoMesh && (
                  <div className="flex items-center gap-1.5 text-amber-400 text-[11px] pt-1">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                    <span>
                      DemoMesh runs controlled chaos simulations, benchmark drills, and synthetic
                      faults. All telemetry is tagged as SIMULATED.
                    </span>
                  </div>
                )}
              </div>

              {/* Environment Choice Cards */}
              <div className="space-y-3">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block font-mono">
                  Switch Infrastructure Runtime Mode
                </label>

                {/* Card 1: DemoMesh Simulation */}
                <div
                  onClick={() => initiateSwitch("DEMOMESH")}
                  className={`p-4 rounded-lg border transition-all cursor-pointer flex items-start justify-between ${
                    activeEnv?.mode === "DEMOMESH"
                      ? "bg-purple-950/40 border-purple-600 ring-1 ring-purple-500"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <Cpu className="w-4 h-4 text-purple-400" />
                      <span className="text-sm font-bold text-slate-100 font-mono">
                        MODE A: DemoMesh Simulation Engine
                      </span>
                      {activeEnv?.mode === "DEMOMESH" && (
                        <span className="text-[10px] bg-purple-900/80 text-purple-200 px-2 py-0.5 rounded-full font-mono">
                          ACTIVE
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400">
                      High-fidelity synthetic microservices (12 services), chaos scenarios, and
                      automated benchmarks.
                    </p>
                    <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 pt-1">
                      <span className="bg-slate-800 px-1.5 py-0.5 rounded">Tag: SIMULATED</span>
                      <span className="bg-slate-800 px-1.5 py-0.5 rounded">Phase 0–7 Ready</span>
                    </div>
                  </div>
                  {activeEnv?.mode === "DEMOMESH" ? (
                    <CheckCircle2 className="w-5 h-5 text-purple-400 shrink-0" />
                  ) : (
                    <div className="w-5 h-5 rounded-full border border-slate-700 shrink-0" />
                  )}
                </div>

                {/* Card 2: Kubernetes Live Cluster */}
                <div
                  onClick={() => initiateSwitch("KUBERNETES")}
                  className={`p-4 rounded-lg border transition-all cursor-pointer flex items-start justify-between ${
                    activeEnv?.mode === "KUBERNETES"
                      ? "bg-emerald-950/40 border-emerald-600 ring-1 ring-emerald-500"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <Server className="w-4 h-4 text-emerald-400" />
                      <span className="text-sm font-bold text-slate-100 font-mono">
                        MODE B: Kubernetes Live Cluster Engine
                      </span>
                      {activeEnv?.mode === "KUBERNETES" && (
                        <span className="text-[10px] bg-emerald-900/80 text-emerald-200 px-2 py-0.5 rounded-full font-mono">
                          ACTIVE
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400">
                      Real Kubernetes API inspection. Discovers real namespaces, pods, deployments,
                      restart counts, and events.
                    </p>
                    <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 pt-1">
                      <span className="bg-slate-800 px-1.5 py-0.5 rounded">Tag: LIVE_K8S</span>
                      <span className="bg-amber-950 text-amber-300 border border-amber-800 px-1.5 py-0.5 rounded flex items-center gap-1">
                        <Lock className="w-2.5 h-2.5" /> Read-Only RBAC
                      </span>
                    </div>
                  </div>
                  {activeEnv?.mode === "KUBERNETES" ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                  ) : (
                    <div className="w-5 h-5 rounded-full border border-slate-700 shrink-0" />
                  )}
                </div>
              </div>

              {/* Error Alert Display */}
              {errorMsg && (
                <div className="p-3 bg-red-950/60 border border-red-700/80 rounded-lg text-xs text-red-200 flex items-start space-x-2 font-mono">
                  <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="block font-bold">Explicit Connection Error:</strong>
                    <span>{errorMsg}</span>
                  </div>
                </div>
              )}

              {/* Confirmation Action Area */}
              {targetMode && targetMode !== activeEnv?.mode && (
                <div className="p-4 bg-blue-950/40 border border-blue-800/60 rounded-lg space-y-3">
                  <div className="flex items-center space-x-2 text-blue-300 text-xs font-mono">
                    <Info className="w-4 h-4 shrink-0" />
                    <span>
                      Switching to <strong className="text-white">{targetMode}</strong> requires SRE
                      privileges. Telemetry stream will switch cleanly with zero cross-environment
                      contamination.
                    </span>
                  </div>
                  <div className="flex justify-end space-x-3">
                    <button
                      onClick={() => setTargetMode(null)}
                      className="px-3 py-1.5 text-xs text-slate-400 hover:text-white rounded border border-slate-700 hover:bg-slate-800"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={confirmSwitch}
                      disabled={isSwitching}
                      className="px-4 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 rounded transition-colors flex items-center space-x-1.5"
                    >
                      {isSwitching ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          <span>Connecting...</span>
                        </>
                      ) : (
                        <span>Confirm Switch to {targetMode}</span>
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between text-xs text-slate-500 font-mono">
              <span className="flex items-center gap-1">
                <Shield className="w-3.5 h-3.5 text-blue-400" /> Strict Data Isolation Enforced
              </span>
              <div className="flex items-center space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    setTargetMode(null);
                    setErrorMsg(null);
                  }}
                  className="flex items-center space-x-1.5 px-3 py-1 text-xs font-mono font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition"
                >
                  <ArrowLeft className="w-3 h-3" />
                  <span>Back / Close</span>
                </button>
                <span>IncidentX AI v0.8.1</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
