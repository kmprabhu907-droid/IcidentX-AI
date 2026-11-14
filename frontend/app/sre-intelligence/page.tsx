"use client";

import React, { useState, useEffect } from "react";
import {
  Activity,
  AlertTriangle,
  TrendingUp,
  Cpu,
  Layers,
  Shield,
  Zap,
  Clock,
  Sparkles,
  RefreshCw,
  Server,
  GitBranch,
  Flame,
} from "lucide-react";
import { sreIntelligenceApi } from "@/services/api";
import {
  MultiSignalAnomalyReport,
  PredictedIncidentRisk,
  ServiceHealthOverview,
  SLOTarget,
  DeploymentRiskAssessment,
  CascadingFailureRisk,
  PredictiveRecommendation,
  ModelEvaluationMetrics,
} from "@/types";

export default function SREIntelligencePage() {
  const [selectedService, setSelectedService] = useState("payment-service");
  const [loading, setLoading] = useState(false);

  const [anomalies, setAnomalies] = useState<MultiSignalAnomalyReport | null>(null);
  const [predictions, setPredictions] = useState<PredictedIncidentRisk[]>([]);
  const [health, setHealth] = useState<ServiceHealthOverview | null>(null);
  const [slos, setSlos] = useState<SLOTarget[]>([]);
  const [deployment, setDeployment] = useState<DeploymentRiskAssessment | null>(null);
  const [cascading, setCascading] = useState<CascadingFailureRisk | null>(null);
  const [recommendations, setRecommendations] = useState<PredictiveRecommendation[]>([]);
  const [evaluation, setEvaluation] = useState<ModelEvaluationMetrics | null>(null);

  useEffect(() => {
    loadData();
  }, [selectedService]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [a, p, h, s, d, c, r, e] = await Promise.all([
        sreIntelligenceApi.getAnomalies(selectedService).catch(() => null),
        sreIntelligenceApi.getPredictions(selectedService).catch(() => []),
        sreIntelligenceApi.getHealth(selectedService).catch(() => null),
        sreIntelligenceApi.getSlos(selectedService).catch(() => []),
        sreIntelligenceApi.getDeploymentCorrelation(selectedService).catch(() => null),
        sreIntelligenceApi.getCascadingRisk(selectedService).catch(() => null),
        sreIntelligenceApi.getRecommendations(selectedService).catch(() => []),
        sreIntelligenceApi.getEvaluation().catch(() => null),
      ]);

      setAnomalies(a);
      setPredictions(p);
      setHealth(h);
      setSlos(s);
      setDeployment(d);
      setCascading(c);
      setRecommendations(r);
      setEvaluation(e);
    } catch {
      // safe fallback
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl shadow-lg shadow-cyan-500/20">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              Predictive SRE Intelligence Center
              <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                PHASE 15
              </span>
            </h1>
            <p className="text-sm text-slate-400">
              Multi-signal anomaly detection, early incident prediction, SLO burn rates &amp; cascading blast radius
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <select
            value={selectedService}
            onChange={(e) => setSelectedService(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
          >
            <option value="payment-service">payment-service (Core Tier-1)</option>
            <option value="order-service">order-service (Tier-1)</option>
            <option value="auth-service">auth-service (Security)</option>
          </select>

          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-4">
          <div className="text-xs text-slate-400 font-semibold uppercase">Service Health</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1 font-mono">
            {health?.health_status || "HEALTHY"}
          </div>
          <div className="text-xs text-slate-400 mt-1">Avail: {health?.availability_percent || 99.98}%</div>
        </div>

        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-4">
          <div className="text-xs text-slate-400 font-semibold uppercase">SLO Burn Rate</div>
          <div className="text-2xl font-bold text-cyan-400 mt-1 font-mono">
            {slos[0]?.burn_rate || 1.0}x
          </div>
          <div className="text-xs text-slate-400 mt-1">Remaining Budget: {slos[0]?.error_budget_remaining_percent || 88.5}%</div>
        </div>

        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-4">
          <div className="text-xs text-slate-400 font-semibold uppercase">Prediction Accuracy</div>
          <div className="text-2xl font-bold text-indigo-400 mt-1 font-mono">
            {((evaluation?.prediction_accuracy || 0.892) * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-slate-400 mt-1">Lead Time: ~{evaluation?.mean_lead_time_minutes || 14.2}m</div>
        </div>

        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-4">
          <div className="text-xs text-slate-400 font-semibold uppercase">Cascading Blast Radius</div>
          <div className="text-2xl font-bold text-amber-400 mt-1 font-mono">
            {((cascading?.blast_radius_score || 0.70) * 100).toFixed(0)}%
          </div>
          <div className="text-xs text-slate-400 mt-1">Downstream: {cascading?.downstream_impacted_services?.length || 2} services</div>
        </div>
      </div>

      {/* Row 1: Anomalies & Incident Predictions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Anomalies Card */}
        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-cyan-400" />
              <span>Multi-Signal Telemetry Deviations (Z-Scores)</span>
            </h3>
            <span className="text-xs font-mono text-slate-400">
              Multivariate Score: {((anomalies?.multivariate_anomaly_score || 0.0) * 100).toFixed(0)}%
            </span>
          </div>

          <div className="space-y-2 font-mono text-xs">
            {(anomalies?.anomalous_signals || []).map((sig) => (
              <div key={sig.metric_name} className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800/80">
                <div>
                  <span className="font-bold text-slate-200">{sig.metric_name}</span>
                  <span className="text-[10px] text-slate-500 block">Baseline: {sig.baseline_mean}{sig.unit} (std: {sig.baseline_std})</span>
                </div>
                <div className="flex items-center space-x-3">
                  <span className="text-slate-300 font-bold">{sig.current_value}{sig.unit}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    sig.classification === "CONFIRMED_ANOMALY"
                      ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                      : sig.classification === "UNUSUAL"
                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      : "bg-emerald-500/10 text-emerald-400"
                  }`}>
                    z={sig.z_score > 0 ? `+${sig.z_score}` : sig.z_score}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Predictions Card */}
        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-400" />
              <span>Early Warning Incident Forecasts</span>
            </h3>
            <span className="text-xs font-mono text-slate-400">{predictions.length} Active Forecasts</span>
          </div>

          <div className="space-y-3">
            {predictions.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                Zero critical failure risks forecasted for {selectedService}.
              </div>
            ) : (
              predictions.map((p) => (
                <div key={p.prediction_id} className="p-4 rounded-xl bg-slate-900 border border-indigo-500/20 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-white flex items-center gap-1.5">
                      <Flame className="w-3.5 h-3.5 text-rose-400" />
                      {p.risk_type}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 font-mono">
                      Lead Time: ~{p.predicted_lead_time_minutes}m
                    </span>
                  </div>
                  <ul className="text-xs text-slate-300 space-y-1 list-disc pl-4">
                    {p.supporting_signals.map((s, idx) => (
                      <li key={idx}>{s}</li>
                    ))}
                  </ul>
                  <div className="text-[11px] bg-indigo-950/20 p-2 rounded text-indigo-300 border border-indigo-500/20">
                    <strong>Action: </strong>{p.recommended_proactive_investigation}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Row 2: Deployment Correlation & Cascading Impact */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-5 space-y-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-emerald-400" />
            <span>Deployment Health Correlation</span>
          </h3>
          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-400">Release Commit:</span>
              <span className="text-white font-mono">{deployment?.git_sha}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Correlation Risk:</span>
              <span className="text-emerald-400 font-bold">{deployment?.risk_category} ({((deployment?.risk_score || 0.15) * 100).toFixed(0)}%)</span>
            </div>
            <p className="text-slate-300 pt-1 border-t border-slate-800/80">{deployment?.explanation}</p>
          </div>
        </div>

        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-5 space-y-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-amber-400" />
            <span>Dependency Cascading Failure Risk</span>
          </h3>
          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-400">Downstream Impacted:</span>
              <span className="text-white font-mono">{cascading?.downstream_impacted_services?.join(", ")}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Bottleneck:</span>
              <span className="text-amber-400 font-bold font-mono">{cascading?.bottleneck_service}</span>
            </div>
            <p className="text-slate-300 pt-1 border-t border-slate-800/80">{cascading?.potential_impact}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
