"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Bot,
  BrainCircuit,
  Scale,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Activity,
  Server,
  Zap,
  Clock,
  DollarSign,
  Cpu,
  RefreshCw,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Layers,
  ChevronRight,
  Database,
  ArrowRight,
  Play,
  RotateCcw,
  Sliders,
  Radio,
  BarChart3,
  ExternalLink,
} from "lucide-react";
import { aiApi, api } from "../../services/api";
import {
  AIIncidentReasoningReport,
  AIUsageSummary,
  CourtroomHypothesis,
  ProviderHealth,
  ProviderInfo,
  Incident,
} from "../../types";

export default function AIReasoningPage() {
  const [loading, setLoading] = useState(true);
  const [runningReasoning, setRunningReasoning] = useState(false);
  const [resettingCb, setResettingCb] = useState(false);
  const [activeTab, setActiveTab] = useState<"courtroom" | "providers" | "usage" | "evidence">("courtroom");

  // State data
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [providerHealth, setProviderHealth] = useState<Record<string, ProviderHealth>>({});
  const [usageSummary, setUsageSummary] = useState<AIUsageSummary | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>("");
  const [reasoningReport, setReasoningReport] = useState<AIIncidentReasoningReport | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string>("openai");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Load initial dashboard data
  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [provRes, healthRes, usageRes, incRes] = await Promise.all([
        aiApi.getProviders(),
        aiApi.getProvidersHealth(),
        aiApi.getUsage(),
        api.listIncidents(1, 10),
      ]);

      setProviders(provRes.providers || []);
      setProviderHealth(healthRes.providers || {});
      setUsageSummary(usageRes);
      
      const incList = incRes.items || [];
      setIncidents(incList);
      if (incList.length > 0 && !selectedIncidentId) {
        setSelectedIncidentId(incList[0].id);
        loadReasoningForIncident(incList[0].id);
      }
    } catch (err: any) {
      console.error("Failed to load AI Reasoning dashboard:", err);
      setErrorMsg("Failed to connect to AI engine API. Please check backend connectivity.");
    } finally {
      setLoading(false);
    }
  };

  const loadReasoningForIncident = async (incidentId: string) => {
    try {
      const report = await aiApi.getReasoning(incidentId);
      setReasoningReport(report);
    } catch (err) {
      // If 404, not run yet
      setReasoningReport(null);
    }
  };

  const handleSelectIncident = (id: string) => {
    setSelectedIncidentId(id);
    loadReasoningForIncident(id);
  };

  const handleRunReasoning = async () => {
    if (!selectedIncidentId) return;
    setRunningReasoning(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const report = await aiApi.runReasoning(selectedIncidentId, {
        preferred_provider: selectedProvider,
      });
      setReasoningReport(report);
      setSuccessMsg(`AI Reasoning completed successfully via ${report.model_attribution.provider_name} (${report.model_attribution.model_name}) in ${report.model_attribution.execution_time_ms}ms!`);
      // Refresh usage stats
      const updatedUsage = await aiApi.getUsage();
      setUsageSummary(updatedUsage);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to execute AI reasoning.");
    } finally {
      setRunningReasoning(false);
    }
  };

  const handleResetCircuitBreaker = async (provName?: string) => {
    setResettingCb(true);
    try {
      await aiApi.resetCircuitBreaker(provName);
      setSuccessMsg(`Circuit breaker for ${provName || "all providers"} reset successfully.`);
      const healthRes = await aiApi.getProvidersHealth();
      setProviderHealth(healthRes.providers || {});
      const provRes = await aiApi.getProviders();
      setProviders(provRes.providers || []);
    } catch (err: any) {
      setErrorMsg("Failed to reset circuit breaker.");
    } finally {
      setResettingCb(false);
    }
  };

  const handleUpdateLifecycle = async (hypothesisId: string, newStatus: string) => {
    if (!selectedIncidentId) return;
    try {
      await aiApi.updateHypothesisLifecycle(selectedIncidentId, {
        hypothesis_id: hypothesisId,
        new_status: newStatus,
        reason: `Manual operator update in AI Intelligence Center.`,
      });
      // Refresh reasoning
      await loadReasoningForIncident(selectedIncidentId);
      setSuccessMsg(`Hypothesis transitioned to ${newStatus}.`);
    } catch (err: any) {
      setErrorMsg("Failed to update hypothesis lifecycle.");
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-[#070b14] text-slate-100 p-8">
      {/* Top Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-2xl font-bold tracking-tight text-white">AI Intelligence Center</h1>
                <span className="px-2 py-0.5 text-[10px] font-mono bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-full font-semibold">
                  PHASE 8.4
                </span>
                <span className="px-2 py-0.5 text-[10px] font-mono bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded-full">
                  MULTI-PROVIDER
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Multi-Provider LLM Abstraction, Root Cause Courtroom 2.0 & Transparent AI Attribution
              </p>
            </div>
          </div>
        </div>

        {/* Global Provider Health Pills */}
        <div className="flex items-center space-x-2 flex-wrap">
          {providers.map((p) => {
            const h = providerHealth[p.provider_name];
            const isAvail = h?.status === "AVAILABLE";
            const isDegraded = h?.status === "DEGRADED";
            const isNotConfig = h?.status === "NOT_CONFIGURED";
            return (
              <div
                key={p.provider_name}
                className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-xs font-mono transition-all ${
                  isAvail
                    ? "bg-emerald-950/40 border-emerald-500/30 text-emerald-300"
                    : isDegraded
                    ? "bg-amber-950/40 border-amber-500/30 text-amber-300"
                    : isNotConfig
                    ? "bg-slate-900 border-slate-800 text-slate-400"
                    : "bg-red-950/40 border-red-500/30 text-red-300"
                }`}
              >
                <div
                  className={`w-2 h-2 rounded-full ${
                    isAvail
                      ? "bg-emerald-400 animate-pulse"
                      : isDegraded
                      ? "bg-amber-400"
                      : isNotConfig
                      ? "bg-slate-500"
                      : "bg-red-500"
                  }`}
                />
                <span className="font-semibold uppercase">{p.provider_name}</span>
                <span className="text-[10px] opacity-75">
                  {h?.latency_ms ? `${h.latency_ms.toFixed(0)}ms` : isNotConfig ? "NO KEY" : "OFFLINE"}
                </span>
              </div>
            );
          })}

          <button
            onClick={() => handleResetCircuitBreaker()}
            disabled={resettingCb}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/60 hover:bg-slate-700/60 text-slate-300 text-xs transition"
            title="Reset Circuit Breakers"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${resettingCb ? "animate-spin" : ""}`} />
            <span>Reset CB</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {errorMsg && (
        <div className="mt-4 p-3 bg-red-950/50 border border-red-500/30 rounded-xl text-xs text-red-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-red-400 hover:text-red-200 text-sm">
            ✕
          </button>
        </div>
      )}
      {successMsg && (
        <div className="mt-4 p-3 bg-emerald-950/50 border border-emerald-500/30 rounded-xl text-xs text-emerald-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-emerald-200 text-sm">
            ✕
          </button>
        </div>
      )}

      {/* Analytics KPI Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-6">
        <div className="p-4 bg-[#0d1424] border border-slate-800/80 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Total LLM Calls</span>
            <Bot className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white mt-2">
            {usageSummary?.total_requests || 0}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Multi-agent orchestrations</div>
        </div>

        <div className="p-4 bg-[#0d1424] border border-slate-800/80 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Tokens Consumed</span>
            <Cpu className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white mt-2">
            {(usageSummary?.total_tokens || 0).toLocaleString()}
          </div>
          <div className="text-[10px] text-blue-400 mt-1">
            Budget: {usageSummary?.budget_consumed_percent || 0}% of {(usageSummary?.daily_token_budget || 500000).toLocaleString()}
          </div>
        </div>

        <div className="p-4 bg-[#0d1424] border border-slate-800/80 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Estimated Spend</span>
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white mt-2">
            ${(usageSummary?.total_estimated_cost_usd || 0).toFixed(4)}
          </div>
          <div className="text-[10px] text-emerald-400 mt-1">Local & Deterministic = $0.00</div>
        </div>

        <div className="p-4 bg-[#0d1424] border border-slate-800/80 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Avg Reasoning Time</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white mt-2">
            {usageSummary?.average_latency_ms || 0} ms
          </div>
          <div className="text-[10px] text-slate-500 mt-1">End-to-end telemetry evaluation</div>
        </div>

        <div className="p-4 bg-[#0d1424] border border-slate-800/80 rounded-xl col-span-2 md:col-span-1">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Fallback Activations</span>
            <RotateCcw className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white mt-2">
            {usageSummary?.fallback_count || 0}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Safe deterministic fallback</div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 mt-8 space-x-6">
        <button
          onClick={() => setActiveTab("courtroom")}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition ${
            activeTab === "courtroom"
              ? "border-purple-500 text-purple-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Scale className="w-4 h-4" />
          <span>Root Cause Courtroom 2.0</span>
        </button>

        <button
          onClick={() => setActiveTab("providers")}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition ${
            activeTab === "providers"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Cpu className="w-4 h-4" />
          <span>Multi-Provider Hub & Routing</span>
        </button>

        <button
          onClick={() => setActiveTab("usage")}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition ${
            activeTab === "usage"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          <span>Cost & Token Observability</span>
        </button>

        <button
          onClick={() => setActiveTab("evidence")}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition ${
            activeTab === "evidence"
              ? "border-amber-500 text-amber-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Evidence Exhibits ({reasoningReport?.evidence_items?.length || 0})</span>
        </button>
      </div>

      {/* TAB 1: Root Cause Courtroom 2.0 */}
      {activeTab === "courtroom" && (
        <div className="mt-6 space-y-6">
          {/* Incident Selector & Trigger Bar */}
          <div className="p-4 bg-[#0d1424] border border-slate-800 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center space-x-3 flex-1">
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono">
                Active Incident:
              </label>
              <select
                value={selectedIncidentId}
                onChange={(e) => handleSelectIncident(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs text-white rounded-lg px-3 py-2 focus:outline-none focus:border-purple-500 flex-1 max-w-md font-mono"
              >
                {incidents.map((inc) => (
                  <option key={inc.id} value={inc.id}>
                    [{inc.severity}] {inc.id.substring(0, 12)} - {inc.title.substring(0, 45)}
                  </option>
                ))}
              </select>

              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono ml-2">
                Provider:
              </label>
              <select
                value={selectedProvider}
                onChange={(e) => setSelectedProvider(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs text-white rounded-lg px-3 py-2 focus:outline-none focus:border-purple-500 font-mono"
              >
                <option value="openai">OpenAI / OpenRouter (Qwen 72B • Active)</option>
                <option value="deterministic">Deterministic Engine (Offline Safe)</option>
                <option value="gemini">Google Gemini</option>
                <option value="ollama">Ollama (Local Daemon)</option>
                <option value="vllm">vLLM (Self-Hosted)</option>
              </select>
            </div>

            <button
              onClick={handleRunReasoning}
              disabled={runningReasoning || !selectedIncidentId}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs shadow-lg shadow-purple-600/20 transition disabled:opacity-50"
            >
              {runningReasoning ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4 fill-current" />
              )}
              <span>{runningReasoning ? "Investigating Telemetry..." : "Run AI Reasoning"}</span>
            </button>
          </div>

          {/* Model Attribution Badge */}
          {reasoningReport?.model_attribution && (
            <div className="p-3 bg-purple-950/30 border border-purple-500/20 rounded-xl flex items-center justify-between text-xs font-mono">
              <div className="flex items-center space-x-3">
                <span className="text-purple-400 font-semibold">ATTRIBUTION:</span>
                <span className="px-2 py-0.5 bg-purple-900/60 rounded text-purple-200">
                  Provider: {reasoningReport.model_attribution.provider_name.toUpperCase()}
                </span>
                <span className="px-2 py-0.5 bg-slate-800 rounded text-slate-300">
                  Model: {reasoningReport.model_attribution.model_name}
                </span>
                {reasoningReport.model_attribution.is_fallback && (
                  <span className="px-2 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded">
                    FALLBACK ACTIVE
                  </span>
                )}
              </div>
              <div className="text-slate-400">
                Latency: {reasoningReport.model_attribution.execution_time_ms}ms | Cost: $
                {reasoningReport.model_attribution.token_usage?.estimated_cost_usd?.toFixed(6) || "0.000000"}
              </div>
            </div>
          )}

          {/* Courtroom Verdict Leading Card */}
          {reasoningReport?.courtroom_verdict ? (
            <div className="p-6 bg-[#0b101b] border-2 border-purple-500/30 rounded-2xl shadow-xl space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-purple-400 text-xs font-mono uppercase tracking-wider font-semibold">
                  <Scale className="w-4 h-4" />
                  <span>Judicial Verdict & Grounded Consensus</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-slate-400 font-mono">Calibrated Confidence:</span>
                  <div className="flex items-center space-x-1.5 px-3 py-1 bg-purple-950/60 border border-purple-500/40 rounded-lg text-purple-300 font-mono font-bold text-sm">
                    <span>
                      {(reasoningReport.courtroom_verdict.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>

              <h2 className="text-xl font-bold text-white tracking-tight">
                {reasoningReport.courtroom_verdict.verdict_summary}
              </h2>

              <p className="text-sm text-slate-300 leading-relaxed bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <span className="font-semibold text-slate-200">Evidentiary Justification: </span>
                {reasoningReport.courtroom_verdict.evidentiary_justification}
              </p>

              {/* Competing Hypotheses Grid */}
              <div className="pt-4">
                <h3 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-bold mb-3">
                  Courtroom Competing Hypotheses ({reasoningReport.courtroom_verdict.competing_hypotheses.length})
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {reasoningReport.courtroom_verdict.competing_hypotheses.map((hyp) => (
                    <div
                      key={hyp.hypothesis_id}
                      className={`p-5 rounded-xl border transition-all ${
                        hyp.is_leading
                          ? "bg-purple-950/20 border-purple-500/50 shadow-md shadow-purple-950/30"
                          : "bg-[#0d1424] border-slate-800"
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center space-x-2">
                            {hyp.is_leading && (
                              <span className="px-2 py-0.5 text-[10px] font-mono bg-purple-500/30 text-purple-300 border border-purple-500/40 rounded font-bold">
                                LEADING ROOT CAUSE
                              </span>
                            )}
                            <span className="px-2 py-0.5 text-[10px] font-mono bg-slate-800 text-slate-300 rounded">
                              Service: {hyp.culprit_service || "cluster"}
                            </span>
                          </div>
                          <h4 className="text-base font-semibold text-white mt-1.5">{hyp.title}</h4>
                        </div>

                        {/* Lifecycle Selector */}
                        <select
                          value={hyp.verification_status}
                          onChange={(e) => handleUpdateLifecycle(hyp.hypothesis_id, e.target.value)}
                          className={`text-[10px] font-mono font-bold uppercase rounded px-2 py-1 border focus:outline-none ${
                            hyp.verification_status === "VERIFIED"
                              ? "bg-emerald-950 text-emerald-300 border-emerald-500/40"
                              : hyp.verification_status === "REJECTED"
                              ? "bg-red-950 text-red-300 border-red-500/40"
                              : hyp.verification_status === "SUPERSEDED"
                              ? "bg-slate-800 text-slate-400 border-slate-700"
                              : "bg-blue-950 text-blue-300 border-blue-500/40"
                          }`}
                        >
                          <option value="PROPOSED">PROPOSED</option>
                          <option value="INVESTIGATED">INVESTIGATED</option>
                          <option value="VERIFIED">VERIFIED</option>
                          <option value="REJECTED">REJECTED</option>
                          <option value="SUPERSEDED">SUPERSEDED</option>
                        </select>
                      </div>

                      <p className="text-xs text-slate-400 mt-2.5 leading-relaxed">{hyp.explanation}</p>

                      {/* Evidence Linkage Section */}
                      <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-2 text-xs">
                        <div className="flex items-center space-x-2 text-emerald-400">
                          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                          <span className="font-semibold text-[11px]">Supporting Evidence:</span>
                          <span className="font-mono text-[11px] text-slate-300">
                            {hyp.supporting_evidence_ids.length > 0
                              ? hyp.supporting_evidence_ids.join(", ")
                              : "None verified"}
                          </span>
                        </div>

                        {hyp.contradicting_evidence_ids.length > 0 && (
                          <div className="flex items-center space-x-2 text-red-400">
                            <XCircle className="w-3.5 h-3.5 shrink-0" />
                            <span className="font-semibold text-[11px]">Contradicting Evidence:</span>
                            <span className="font-mono text-[11px] text-slate-300">
                              {hyp.contradicting_evidence_ids.join(", ")}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center bg-[#0d1424] border border-slate-800 rounded-2xl">
              <Scale className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-300">No AI Reasoning Report Loaded</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4">
                Select an incident above and click &quot;Run AI Reasoning&quot; to formulate multi-agent Courtroom 2.0 hypotheses and evaluate telemetry contracts.
              </p>
              <button
                onClick={handleRunReasoning}
                disabled={runningReasoning || !selectedIncidentId}
                className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs transition"
              >
                Execute Investigation
              </button>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Multi-Provider Hub */}
      {activeTab === "providers" && (
        <div className="mt-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {providers.map((prov) => {
              const h = providerHealth[prov.provider_name];
              const isTripped = prov.circuit_breaker_tripped;
              return (
                <div
                  key={prov.provider_name}
                  className="p-5 bg-[#0d1424] border border-slate-800 rounded-2xl flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Cpu className="w-5 h-5 text-blue-400" />
                        <h4 className="text-base font-bold text-white capitalize">{prov.provider_name}</h4>
                      </div>
                      <span
                        className={`px-2 py-0.5 text-[10px] font-mono rounded-full font-bold uppercase ${
                          h?.status === "AVAILABLE"
                            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                            : h?.status === "NOT_CONFIGURED"
                            ? "bg-slate-800 text-slate-400"
                            : "bg-red-500/20 text-red-300 border border-red-500/30"
                        }`}
                      >
                        {h?.status || "UNKNOWN"}
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 mt-2">
                      {prov.provider_name === "gemini" && "Google Gemini Multimodal API with native structured JSON schema enforcement."}
                      {prov.provider_name === "openai" && "OpenAI GPT-4o Flagship engine with cascading fallback."}
                      {prov.provider_name === "ollama" && "Local daemon inference on host machine with zero API cost."}
                      {prov.provider_name === "vllm" && "Self-hosted high-throughput GPU inference cluster."}
                      {prov.provider_name === "deterministic" && "Zero-dependency, rule-grounded SRE analytical reasoning engine."}
                    </p>

                    <div className="mt-4 space-y-2 text-xs font-mono">
                      <div className="flex justify-between text-slate-400">
                        <span>Default Model:</span>
                        <span className="text-slate-200">{prov.default_model}</span>
                      </div>
                      <div className="flex justify-between text-slate-400">
                        <span>Configured:</span>
                        <span className={prov.configured ? "text-emerald-400" : "text-amber-400"}>
                          {prov.configured ? "YES" : "MISSING KEY"}
                        </span>
                      </div>
                      <div className="flex justify-between text-slate-400">
                        <span>Latency:</span>
                        <span className="text-slate-200">{h?.latency_ms ? `${h.latency_ms.toFixed(1)} ms` : "N/A"}</span>
                      </div>
                      <div className="flex justify-between text-slate-400">
                        <span>Circuit Breaker:</span>
                        <span className={isTripped ? "text-red-400 font-bold" : "text-emerald-400"}>
                          {isTripped ? "TRIPPED" : "CLOSED (HEALTHY)"}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                    <span className="text-[10px] text-slate-500 font-mono">
                      {prov.is_primary ? "PRIMARY" : prov.is_secondary ? "SECONDARY" : prov.is_fallback ? "GUARANTEED FALLBACK" : "STANDBY"}
                    </span>
                    {isTripped && (
                      <button
                        onClick={() => handleResetCircuitBreaker(prov.provider_name)}
                        className="px-2.5 py-1 text-[11px] bg-red-950 text-red-200 border border-red-500/40 rounded hover:bg-red-900 transition"
                      >
                        Reset Breaker
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 3: Cost & Token Observability */}
      {activeTab === "usage" && (
        <div className="mt-6 space-y-6">
          <div className="p-6 bg-[#0d1424] border border-slate-800 rounded-2xl space-y-5">
            <h3 className="text-base font-bold text-white">Daily Token Budget Consumption</h3>

            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-400">
                  Consumed: {(usageSummary?.total_tokens || 0).toLocaleString()} / {(usageSummary?.daily_token_budget || 500000).toLocaleString()} tokens
                </span>
                <span className="text-purple-400 font-bold">{usageSummary?.budget_consumed_percent || 0}%</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-purple-600 h-full rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(100, usageSummary?.budget_consumed_percent || 0)}%` }}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
              {/* Usage by Provider */}
              <div>
                <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold mb-3">
                  Expenditure by Provider
                </h4>
                <div className="space-y-2">
                  {Object.entries(usageSummary?.usage_by_provider || {}).map(([pName, stats]) => (
                    <div
                      key={pName}
                      className="p-3 bg-slate-900/60 border border-slate-800 rounded-lg flex items-center justify-between text-xs font-mono"
                    >
                      <span className="text-white font-semibold uppercase">{pName}</span>
                      <div className="text-right">
                        <div className="text-slate-300">{stats.tokens.toLocaleString()} tokens</div>
                        <div className="text-emerald-400 text-[10px]">${stats.cost_usd.toFixed(4)}</div>
                      </div>
                    </div>
                  ))}
                  {Object.keys(usageSummary?.usage_by_provider || {}).length === 0 && (
                    <div className="text-xs text-slate-500 py-3">No provider usage recorded in active session.</div>
                  )}
                </div>
              </div>

              {/* Usage by Model */}
              <div>
                <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold mb-3">
                  Expenditure by Model
                </h4>
                <div className="space-y-2">
                  {Object.entries(usageSummary?.usage_by_model || {}).map(([mName, stats]) => (
                    <div
                      key={mName}
                      className="p-3 bg-slate-900/60 border border-slate-800 rounded-lg flex items-center justify-between text-xs font-mono"
                    >
                      <span className="text-white font-semibold">{mName}</span>
                      <div className="text-right">
                        <div className="text-slate-300">{stats.requests} requests</div>
                        <div className="text-emerald-400 text-[10px]">${stats.cost_usd.toFixed(4)}</div>
                      </div>
                    </div>
                  ))}
                  {Object.keys(usageSummary?.usage_by_model || {}).length === 0 && (
                    <div className="text-xs text-slate-500 py-3">No model usage recorded in active session.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: Evidence Exhibits */}
      {activeTab === "evidence" && (
        <div className="mt-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Ingested Telemetry Contracts</h3>
            <span className="text-xs text-slate-400 font-mono">
              Strict Environment Isolation: DemoMesh (SIMULATED) vs Kubernetes (LIVE_K8S)
            </span>
          </div>

          <div className="overflow-x-auto border border-slate-800 rounded-xl">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#0b101b] border-b border-slate-800 text-slate-400 uppercase">
                <tr>
                  <th className="p-3">Evidence ID</th>
                  <th className="p-3">Source</th>
                  <th className="p-3">Classification</th>
                  <th className="p-3">Resource</th>
                  <th className="p-3">Environment</th>
                  <th className="p-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 bg-[#0d1424]">
                {reasoningReport?.evidence_items?.map((item) => (
                  <tr key={item.evidence_id} className="hover:bg-slate-800/40">
                    <td className="p-3 text-purple-400 font-semibold">{item.evidence_id}</td>
                    <td className="p-3 text-slate-300">{item.source_type}</td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] ${
                          item.statement_classification === "OBSERVED_FACT"
                            ? "bg-blue-500/20 text-blue-300"
                            : "bg-amber-500/20 text-amber-300"
                        }`}
                      >
                        {item.statement_classification}
                      </span>
                    </td>
                    <td className="p-3 text-white">{item.resource_name}</td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] ${
                          item.data_source === "LIVE_K8S"
                            ? "bg-emerald-500/20 text-emerald-300"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {item.data_source}
                      </span>
                    </td>
                    <td className="p-3 text-slate-400">{item.timestamp}</td>
                  </tr>
                ))}
                {(!reasoningReport?.evidence_items || reasoningReport.evidence_items.length === 0) && (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-slate-500">
                      No evidence ingested yet for this incident. Run AI Reasoning to populate.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
