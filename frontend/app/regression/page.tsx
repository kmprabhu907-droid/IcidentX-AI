"use client";

import { useEffect, useState } from "react";
import {
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldAlert,
  Search,
  RefreshCw,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Layers,
  Sparkles,
  GitCompare,
  Activity,
  Check,
  XCircle,
  Database,
  History,
  Info
} from "lucide-react";
import { api } from "../../services/api";
import {
  RegressionRecordItem,
  FourStateComparisonData,
  RemediationEffectivenessOverview,
} from "../../types";

export default function RegressionLabPage() {
  const [regressions, setRegressions] = useState<RegressionRecordItem[]>([]);
  const [selectedRegression, setSelectedRegression] = useState<RegressionRecordItem | null>(null);
  const [comparisonData, setComparisonData] = useState<FourStateComparisonData | null>(null);
  const [historyData, setHistoryData] = useState<any | null>(null);
  const [effectivenessOverview, setEffectivenessOverview] = useState<RemediationEffectivenessOverview | null>(null);

  // Filters
  const [serviceFilter, setServiceFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [classificationFilter, setClassificationFilter] = useState<string>("");
  const [isTriggering, setIsTriggering] = useState<boolean>(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchRegressionData = async () => {
    try {
      const [regrRes, effRes] = await Promise.all([
        api.listRegressions({
          service_name: serviceFilter || undefined,
          status: statusFilter || undefined,
          classification: classificationFilter || undefined,
          page_size: 50,
        }).catch(() => ({ total: 0, page: 1, page_size: 50, total_pages: 0, items: [] })),
        api.getRemediationEffectiveness().catch(() => null),
      ]);

      const items = regrRes.items || [];
      setRegressions(items);
      if (effRes) setEffectivenessOverview(effRes);

      if (selectedRegression) {
        const updated = items.find((r) => r.id === selectedRegression.id);
        if (updated) setSelectedRegression(updated);
      } else if (items.length > 0) {
        setSelectedRegression(items[0]);
      }
    } catch (err) {
      console.error("Failed to load regression lab data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRegressionData();
    if (!autoRefresh) return;
    const interval = setInterval(fetchRegressionData, 3000);
    return () => clearInterval(interval);
  }, [serviceFilter, statusFilter, classificationFilter, autoRefresh]);

  // Load detailed comparison & historical provenance whenever selected regression changes
  useEffect(() => {
    if (!selectedRegression?.id) {
      setComparisonData(null);
      setHistoryData(null);
      return;
    }

    // Load four-state comparison matrix
    api.getRegressionComparison(selectedRegression.id)
      .then((data) => setComparisonData(data))
      .catch(() => setComparisonData(selectedRegression.comparison_windows || null));

    // Load historical provenance and previous remediations
    api.getRegressionHistory(selectedRegression.id)
      .then((hist) => setHistoryData(hist))
      .catch(() => setHistoryData(null));
  }, [selectedRegression?.id]);

  const handleUpdateStatus = async (regressionId: string, newStatus: string) => {
    try {
      setIsUpdatingStatus(true);
      const updated = await api.updateRegressionStatus(regressionId, newStatus);
      setRegressions((prev) => prev.map((r) => (r.id === regressionId ? updated : r)));
      if (selectedRegression?.id === regressionId) {
        setSelectedRegression(updated);
      }
    } catch (err) {
      console.error("Failed to update status:", err);
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handleTriggerEvaluation = async () => {
    try {
      setIsTriggering(true);
      await api.triggerRegressionDetection();
      await fetchRegressionData();
    } catch (err) {
      console.error("Failed to trigger regression evaluation:", err);
    } finally {
      setIsTriggering(false);
    }
  };

  const getClassificationBadge = (cls: string) => {
    switch (cls) {
      case "CONFIRMED_REGRESSION":
        return "bg-red-500/10 text-red-400 border-red-500/30";
      case "LIKELY_REGRESSION":
        return "bg-orange-500/10 text-orange-400 border-orange-500/30";
      case "POSSIBLE_REGRESSION":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/30";
    }
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case "ACTIVE":
        return "bg-red-500/10 text-red-400 border-red-500/30 animate-pulse";
      case "INVESTIGATING":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      case "CONFIRMED":
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
      case "RESOLVED":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "FALSE_POSITIVE":
        return "bg-slate-500/10 text-slate-400 border-slate-500/30";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  const activeCount = regressions.filter((r) => r.status === "ACTIVE" || r.status === "CONFIRMED").length;
  const confirmedCount = regressions.filter((r) => r.classification === "CONFIRMED_REGRESSION").length;

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">Regression Detection Lab</h1>
            <span className="px-2.5 py-1 rounded-full text-[11px] font-mono font-bold tracking-wider uppercase border bg-purple-500/10 text-purple-400 border-purple-500/30">
              HISTORICAL FAILURE INTELLIGENCE
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Continuous detection of recurring failure patterns, post-remediation degradation, and failed recovery strategies.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <label className="flex items-center space-x-2 text-xs font-mono text-slate-400 cursor-pointer bg-slate-900 px-3 py-2 rounded-xl border border-slate-800">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-blue-500 focus:ring-0"
            />
            <span>Auto Refresh (3s)</span>
          </label>

          <button
            onClick={fetchRegressionData}
            className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 px-3.5 py-2 rounded-xl text-xs font-medium transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleTriggerEvaluation}
            disabled={isTriggering}
            className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3.5 py-2 rounded-xl text-xs font-medium transition"
          >
            <Sparkles className={`w-3.5 h-3.5 ${isTriggering ? "animate-spin" : ""}`} />
            <span>{isTriggering ? "Evaluating..." : "Run Evaluation Cycle"}</span>
          </button>
        </div>
      </div>

      {/* Cluster KPI Overview Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#0f172a] border border-slate-800 p-4 rounded-xl">
          <div className="text-xs font-mono text-slate-400 uppercase">Tracked Regressions</div>
          <div className="text-2xl font-bold font-mono text-white mt-1">
            {regressions.length} <span className="text-xs text-slate-400 font-normal">records</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Deduplicated across 7 services</div>
        </div>

        <div className="bg-[#0f172a] border border-slate-800 p-4 rounded-xl">
          <div className="text-xs font-mono text-slate-400 uppercase">Active Recurrences</div>
          <div className="text-2xl font-bold font-mono mt-1">
            <span className={activeCount > 0 ? "text-amber-400" : "text-emerald-400"}>
              {activeCount}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Active or Investigating status</div>
        </div>

        <div className="bg-[#0f172a] border border-slate-800 p-4 rounded-xl">
          <div className="text-xs font-mono text-slate-400 uppercase">Confirmed Regressions</div>
          <div className="text-2xl font-bold font-mono mt-1">
            <span className={confirmedCount > 0 ? "text-red-400" : "text-emerald-400"}>
              {confirmedCount}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Score ≥ 0.80 + Deterministic proof</div>
        </div>

        <div className="bg-[#0f172a] border border-slate-800 p-4 rounded-xl">
          <div className="text-xs font-mono text-slate-400 uppercase">Remediation Stability Ratio</div>
          <div className="text-2xl font-bold font-mono text-white mt-1">
            <span className={(effectivenessOverview?.remediation_stability_ratio || 1.0) < 0.7 ? "text-amber-400" : "text-emerald-400"}>
              {((effectivenessOverview?.remediation_stability_ratio ?? 1.0) * 100).toFixed(0)}%
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {effectivenessOverview?.verified_immediately ?? 0} verified actions analyzed
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-[#0f172a] border border-slate-800 p-4 rounded-xl">
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={serviceFilter}
            onChange={(e) => setServiceFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-xl px-3 py-1.5 font-mono"
          >
            <option value="">All Services</option>
            <option value="api-gateway">api-gateway</option>
            <option value="order-service">order-service</option>
            <option value="payment-service">payment-service</option>
            <option value="auth-service">auth-service</option>
            <option value="inventory-service">inventory-service</option>
            <option value="postgres-db">postgres-db</option>
            <option value="redis-cache">redis-cache</option>
          </select>

          <select
            value={classificationFilter}
            onChange={(e) => setClassificationFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-xl px-3 py-1.5 font-mono"
          >
            <option value="">All Classifications</option>
            <option value="CONFIRMED_REGRESSION">CONFIRMED_REGRESSION</option>
            <option value="LIKELY_REGRESSION">LIKELY_REGRESSION</option>
            <option value="POSSIBLE_REGRESSION">POSSIBLE_REGRESSION</option>
            <option value="LOW_SIMILARITY">LOW_SIMILARITY</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-xl px-3 py-1.5 font-mono"
          >
            <option value="">All Statuses</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="INVESTIGATING">INVESTIGATING</option>
            <option value="CONFIRMED">CONFIRMED</option>
            <option value="RESOLVED">RESOLVED</option>
            <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
          </select>
        </div>

        <div className="text-xs font-mono text-slate-400">
          Showing {regressions.length} regression events
        </div>
      </div>

      {/* Main Split Layout: Left Feed, Right Deep Inspection */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Regression Feed */}
        <div className="lg:col-span-5 space-y-3 max-h-[780px] overflow-y-auto pr-1">
          {regressions.length === 0 ? (
            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-8 text-center space-y-3">
              <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
              <div className="text-sm font-semibold text-slate-200">
                No Regressions Detected
              </div>
              <div className="text-xs text-slate-400 leading-relaxed">
                Four-state comparisons confirm all recovered services maintain sustained post-remediation stability.
              </div>
            </div>
          ) : (
            regressions.map((item) => {
              const isSelected = selectedRegression?.id === item.id;
              const regrScorePct = Math.round((item.regression_score || 0) * 100);
              const simScorePct = Math.round((item.similarity_score || 0) * 100);

              return (
                <div
                  key={item.id}
                  onClick={() => setSelectedRegression(item)}
                  className={`p-4 rounded-xl border transition cursor-pointer space-y-3 ${
                    isSelected
                      ? "bg-slate-800/90 border-blue-500/80 shadow-lg"
                      : "bg-[#0f172a] border-slate-800 hover:border-slate-700"
                  }`}
                >
                  {/* Top Badges */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${getClassificationBadge(item.classification)}`}>
                        {item.classification.replace(/_/g, " ")}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${getStatusBadge(item.status)}`}>
                        {item.status}
                      </span>
                    </div>

                    <span className="text-[10px] font-mono text-slate-400">
                      {item.last_observed_at ? new Date(item.last_observed_at).toLocaleTimeString() : "--:--:--"}
                    </span>
                  </div>

                  {/* Service & Metric Name */}
                  <div>
                    <div className="text-sm font-bold text-white font-mono flex items-center gap-1.5">
                      <span className="text-purple-400">[{item.service_name}]</span>
                      <span>{item.metric_name}</span>
                    </div>
                    {item.evidence?.detected_pattern && (
                      <div className="text-[11px] font-mono text-amber-300 mt-0.5">
                        Pattern: {item.evidence.detected_pattern.replace(/_/g, " ")}
                      </div>
                    )}
                  </div>

                  {/* Four-State Values Summary Grid */}
                  <div className="grid grid-cols-3 gap-2 text-xs font-mono bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
                    <div>
                      <div className="text-slate-400 text-[10px]">Baseline (A)</div>
                      <div className="text-slate-200 font-bold mt-0.5">
                        {item.baseline_value.toFixed(1)}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-400 text-[10px]">Recovered (C)</div>
                      <div className="text-emerald-400 font-bold mt-0.5">
                        {item.post_remediation_value.toFixed(1)}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-400 text-[10px]">Current (D)</div>
                      <div className="text-red-400 font-bold mt-0.5">
                        {item.current_value.toFixed(1)}
                      </div>
                    </div>
                  </div>

                  {/* Dual Score Bars */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                        <span>Regression Score</span>
                        <span className="text-red-400 font-bold">{regrScorePct}%</span>
                      </div>
                      <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            regrScorePct >= 80 ? "bg-red-500" : regrScorePct >= 65 ? "bg-orange-500" : "bg-amber-500"
                          }`}
                          style={{ width: `${regrScorePct}%` }}
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                        <span>Fingerprint Sim</span>
                        <span className="text-blue-300 font-bold">{simScorePct}%</span>
                      </div>
                      <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-blue-500"
                          style={{ width: `${simScorePct}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-1 border-t border-slate-800/60">
                    <span>Matches: {item.incident_id ? item.incident_id.slice(0, 8) : "HIST-0"}</span>
                    <span className="text-blue-400 flex items-center gap-0.5 hover:underline">
                      <span>Inspect Lab</span>
                      <ChevronRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Column: Deep SRE Diagnostic Inspection */}
        <div className="lg:col-span-7">
          {selectedRegression ? (
            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-6">
              {/* Header & Status Actions */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${getClassificationBadge(selectedRegression.classification)}`}>
                      {selectedRegression.classification.replace(/_/g, " ")}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${getStatusBadge(selectedRegression.status)}`}>
                      {selectedRegression.status}
                    </span>
                    <span className="text-xs font-mono text-slate-400">
                      ID: {selectedRegression.id.slice(0, 16)}...
                    </span>
                  </div>
                  <h2 className="text-base font-bold text-white font-mono mt-1">
                    [{selectedRegression.service_name}] {selectedRegression.metric_name}
                  </h2>
                </div>

                {/* Status Transition Action Buttons */}
                <div className="flex items-center space-x-2">
                  {selectedRegression.status !== "INVESTIGATING" && (
                    <button
                      onClick={() => handleUpdateStatus(selectedRegression.id, "INVESTIGATING")}
                      disabled={isUpdatingStatus}
                      className="px-2.5 py-1.5 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border border-blue-500/30 text-xs font-mono transition"
                    >
                      Investigate
                    </button>
                  )}

                  {selectedRegression.status !== "CONFIRMED" && (
                    <button
                      onClick={() => handleUpdateStatus(selectedRegression.id, "CONFIRMED")}
                      disabled={isUpdatingStatus}
                      className="px-2.5 py-1.5 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/30 text-xs font-mono transition"
                    >
                      Confirm
                    </button>
                  )}

                  {selectedRegression.status !== "RESOLVED" && (
                    <button
                      onClick={() => handleUpdateStatus(selectedRegression.id, "RESOLVED")}
                      disabled={isUpdatingStatus}
                      className="px-2.5 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 text-xs font-mono transition"
                    >
                      Resolve
                    </button>
                  )}

                  {selectedRegression.status !== "FALSE_POSITIVE" && (
                    <button
                      onClick={() => handleUpdateStatus(selectedRegression.id, "FALSE_POSITIVE")}
                      disabled={isUpdatingStatus}
                      className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-mono transition"
                    >
                      False Positive
                    </button>
                  )}
                </div>
              </div>

              {/* 10 SRE Diagnostic Questions & Answers */}
              <div className="space-y-4">
                <div className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider text-slate-400">
                  <ShieldAlert className="w-4 h-4 text-purple-400" />
                  <span>SRE Regression Assessment (10 Standard Questions)</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                  {/* 1. Which Previous Incident */}
                  <div className="col-span-full bg-slate-900/80 p-3 rounded-xl border border-slate-800 space-y-1">
                    <div className="text-[10px] text-purple-400 uppercase font-semibold">1. Which previous incident does this resemble?</div>
                    <div className="text-white font-bold text-xs">
                      {selectedRegression.explanation?.which_previous_incident || `Historical failure (ID: ${selectedRegression.incident_id || "HIST-0"})`}
                    </div>
                  </div>

                  {/* 2. Affected Services */}
                  <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                    <div className="text-[10px] text-slate-400 uppercase">2. Affected Services</div>
                    <div className="text-slate-200">
                      {selectedRegression.explanation?.affected_services || selectedRegression.service_name}
                    </div>
                  </div>

                  {/* 3. Metrics Returning Abnormal */}
                  <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                    <div className="text-[10px] text-slate-400 uppercase">3. Metric Returning Abnormal</div>
                    <div className="text-amber-400 font-bold">
                      {selectedRegression.explanation?.metrics_returning_abnormal || `${selectedRegression.metric_name}: observed ${selectedRegression.current_value}`}
                    </div>
                  </div>

                  {/* 4. Original Root Cause */}
                  <div className="col-span-full bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                    <div className="text-[10px] text-slate-400 uppercase">4. Original Root Cause Hypothesis</div>
                    <div className="text-slate-300 leading-relaxed font-sans text-xs">
                      {selectedRegression.explanation?.original_root_cause_hypothesis || "Historical failure hypothesis"}
                    </div>
                  </div>

                  {/* 5. Previous Remediation */}
                  <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                    <div className="text-[10px] text-slate-400 uppercase">5. Previous Remediation Performed</div>
                    <div className="text-slate-200">
                      {selectedRegression.explanation?.previous_remediation_performed || "Automated service recovery action"}
                    </div>
                  </div>

                  {/* 6. Did Remediation Provide Sustained Improvement? */}
                  <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                    <div className="text-[10px] text-slate-400 uppercase">6. Sustained Improvement?</div>
                    <div className="text-amber-300">
                      {selectedRegression.explanation?.did_remediation_provide_sustained_improvement || "Temporary relief followed by re-degradation"}
                    </div>
                  </div>

                  {/* 7. Evidence Supporting Recurrence */}
                  <div className="col-span-full bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                    <div className="text-[10px] text-emerald-400 uppercase font-semibold">7. Evidence Supporting Recurrence</div>
                    <div className="text-slate-200 text-xs leading-relaxed font-sans">
                      {selectedRegression.explanation?.evidence_supporting_recurrence || "Concordant anomaly vectors and identical culprit service"}
                    </div>
                  </div>

                  {/* 8. Evidence Contradicting Recurrence */}
                  <div className="col-span-full bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">8. Evidence Contradicting Recurrence</div>
                    <div className="text-slate-400 text-xs leading-relaxed font-sans">
                      {selectedRegression.explanation?.evidence_contradicting_recurrence || "No significant contradictory evidence observed"}
                    </div>
                  </div>

                  {/* 9. Similarity Strength */}
                  <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                    <div className="text-[10px] text-slate-400 uppercase">9. Similarity Strength</div>
                    <div className="text-blue-400 font-bold">
                      {selectedRegression.explanation?.similarity_strength || `${(selectedRegression.similarity_score * 100).toFixed(1)}% Similarity`}
                    </div>
                  </div>

                  {/* 10. Next Recommended SRE Action */}
                  <div className="col-span-full bg-blue-950/20 p-3.5 rounded-xl border border-blue-500/30 space-y-1">
                    <div className="text-[10px] text-blue-400 uppercase font-semibold">10. Next Recommended SRE Investigation Step</div>
                    <div className="text-blue-200 text-xs leading-relaxed font-sans">
                      {selectedRegression.explanation?.next_investigation_step || "Inspect root cause parameters and verify thread pool allocation."}
                    </div>
                  </div>
                </div>
              </div>

              {/* Four-State Comparative Matrix Table */}
              {comparisonData && comparisonData.metrics && (
                <div className="bg-[#0b101b] border border-slate-800 rounded-xl overflow-hidden space-y-2">
                  <div className="p-3.5 border-b border-slate-800 flex items-center justify-between">
                    <div className="text-xs font-mono font-bold text-white flex items-center gap-1.5">
                      <GitCompare className="w-3.5 h-3.5 text-blue-400" />
                      <span>Four-State Telemetry Matrix (Baseline ➔ Pre-Incident ➔ Post-Remediation ➔ Current)</span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-400">
                      Window: {comparisonData.comparison_window_minutes}m
                    </span>
                  </div>

                  <div className="overflow-x-auto p-2">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="bg-slate-900/80 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                        <tr>
                          <th className="py-2 px-3">Metric</th>
                          <th className="py-2 px-3">Baseline (A)</th>
                          <th className="py-2 px-3">Pre-Incident (B)</th>
                          <th className="py-2 px-3">Post-Remediation (C)</th>
                          <th className="py-2 px-3">Current (D)</th>
                          <th className="py-2 px-3">Retention</th>
                          <th className="py-2 px-3">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {Object.entries(comparisonData.metrics).map(([mName, mVal]) => (
                          <tr key={mName} className="hover:bg-slate-900/40">
                            <td className="py-2.5 px-3 font-semibold text-white">
                              {mName}
                            </td>
                            <td className="py-2.5 px-3 text-slate-300">
                              {mVal.healthy_baseline.toFixed(1)} {mVal.unit}
                            </td>
                            <td className="py-2.5 px-3 text-amber-300">
                              {mVal.pre_incident.toFixed(1)} {mVal.unit}
                            </td>
                            <td className="py-2.5 px-3 text-emerald-400">
                              {mVal.post_remediation.toFixed(1)} {mVal.unit}
                            </td>
                            <td className={`py-2.5 px-3 font-bold ${mVal.is_regressing ? "text-red-400" : "text-slate-200"}`}>
                              {mVal.current_state.toFixed(1)} {mVal.unit}
                            </td>
                            <td className="py-2.5 px-3">
                              {Math.round(mVal.recovery_retained_ratio * 100)}%
                            </td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`px-1.5 py-0.5 rounded text-[10px] ${
                                  mVal.status_summary === "REGRESSING" || mVal.status_summary === "WORSENED_BEYOND_FAILURE"
                                    ? "bg-red-500/20 text-red-300 border border-red-500/30 font-bold"
                                    : "bg-emerald-500/10 text-emerald-400"
                                }`}
                              >
                                {mVal.status_summary}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Historical Provenance & Previous Remediations */}
              {historyData && (
                <div className="bg-[#0b101b] border border-slate-800 rounded-xl p-4 space-y-3">
                  <div className="text-xs font-mono font-bold text-white flex items-center gap-1.5">
                    <History className="w-3.5 h-3.5 text-purple-400" />
                    <span>Historical Incident Provenance & Remediation Audit</span>
                  </div>

                  {historyData.original_incident && (
                    <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800/80 text-xs font-mono space-y-1">
                      <div className="text-purple-300 font-bold">
                        Incident: {historyData.original_incident.title}
                      </div>
                      <div className="text-slate-400 text-[11px]">
                        ID: {historyData.original_incident.id} | Severity: {historyData.original_incident.severity} | Status: {historyData.original_incident.status}
                      </div>
                    </div>
                  )}

                  {historyData.previous_remediations && historyData.previous_remediations.length > 0 ? (
                    <div className="space-y-2">
                      <div className="text-[11px] font-mono text-slate-400">Previous Remediation Interventions:</div>
                      {historyData.previous_remediations.map((a: any) => (
                        <div key={a.id} className="p-2.5 bg-slate-900/40 border border-slate-800/80 rounded-lg text-xs font-mono flex items-center justify-between">
                          <div>
                            <span className="font-semibold text-slate-200">{a.name}</span>
                            <span className="text-slate-400 text-[10px] ml-2">({a.action_id})</span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] ${a.verification_status === "VERIFIED" ? "bg-emerald-500/20 text-emerald-300" : "bg-red-500/20 text-red-300"}`}>
                              {a.verification_status}
                            </span>
                            <span className="text-[10px] text-slate-400">
                              {a.executed_at ? new Date(a.executed_at).toLocaleDateString() : ""}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs font-mono text-slate-400">
                      No previous remediation actions registered for this historical incident.
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-12 text-center text-slate-400 space-y-2">
              <Info className="w-8 h-8 text-slate-500 mx-auto" />
              <div className="text-sm font-semibold text-slate-300">No Regression Selected</div>
              <div className="text-xs">
                Select a regression event from the feed to inspect the four-state matrix, multi-feature fingerprint similarity, and SRE recurrence answers.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
