"use client";

import React, { useState, useEffect } from "react";
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  Clock,
  Compass,
  Database,
  Flame,
  GitBranch,
  Gauge,
  History,
  Layers,
  LineChart,
  Play,
  RefreshCw,
  Search,
  Server,
  ShieldAlert,
  Zap,
} from "lucide-react";
import { reliabilityApi } from "../../services/api";

export default function ReliabilityCommandCenter() {
  const [activeTab, setActiveTab] = useState<"overview" | "predictive" | "slo" | "memory" | "timemachine" | "agent">("overview");
  const [loading, setLoading] = useState(false);

  // Data states
  const [overview, setOverview] = useState<any>(null);
  const [capacityRisks, setCapacityRisks] = useState<any[]>([]);
  const [predictions, setPredictions] = useState<any[]>([]);
  const [slos, setSlos] = useState<any[]>([]);
  const [burnRates, setBurnRates] = useState<any[]>([]);
  const [memories, setMemories] = useState<any[]>([]);
  const [memorySearch, setMemorySearch] = useState("");
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>("");
  const [timeMachineData, setTimeMachineData] = useState<any>(null);
  const [agentData, setAgentData] = useState<any>(null);
  const [agentAssessing, setAgentAssessing] = useState(false);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [ovRes, riskRes, predRes, sloRes, burnRes, memRes, agentRes] = await Promise.allSettled([
        reliabilityApi.getOverview(),
        reliabilityApi.getCapacityRisks(),
        reliabilityApi.getPredictions(),
        reliabilityApi.getSLOs(),
        reliabilityApi.getBurnRates(),
        reliabilityApi.getIncidentMemories({ limit: 10 }),
        reliabilityApi.getAgentLastRun(),
      ]);

      if (ovRes.status === "fulfilled") setOverview(ovRes.value);
      if (riskRes.status === "fulfilled") setCapacityRisks(riskRes.value.risks || []);
      if (predRes.status === "fulfilled") setPredictions(predRes.value.predictions || []);
      if (sloRes.status === "fulfilled") setSlos(sloRes.value.slos || []);
      if (burnRes.status === "fulfilled") setBurnRates(burnRes.value.burn_rates || []);
      if (memRes.status === "fulfilled") {
        setMemories(memRes.value.items || []);
        if (memRes.value.items?.length > 0 && !selectedIncidentId) {
          setSelectedIncidentId(memRes.value.items[0].incident_id);
        }
      }
      if (agentRes.status === "fulfilled") setAgentData(agentRes.value);
    } catch (err) {
      console.error("Failed to load reliability dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  useEffect(() => {
    if (selectedIncidentId && activeTab === "timemachine") {
      reliabilityApi.getTimeMachine(selectedIncidentId)
        .then(data => setTimeMachineData(data))
        .catch(err => console.error("Failed to load time machine:", err));
    }
  }, [selectedIncidentId, activeTab]);

  const handleRunAgent = async () => {
    setAgentAssessing(true);
    try {
      const res = await reliabilityApi.runAgentAssessment({ service_name: "order-service" });
      setAgentData(res);
    } catch (err) {
      console.error("Agent assessment failed:", err);
    } finally {
      setAgentAssessing(false);
    }
  };

  const handleSearchMemory = async () => {
    if (!memorySearch) {
      const res = await reliabilityApi.getIncidentMemories({ limit: 10 });
      setMemories(res.items || []);
      return;
    }
    const res = await reliabilityApi.searchMemory({ query_text: memorySearch });
    setMemories(res.matches || []);
  };

  return (
    <div className="flex-1 bg-[#070b14] text-slate-100 flex flex-col min-h-screen">
      {/* Header Bar */}
      <div className="border-b border-slate-800 bg-[#0c1222]/80 backdrop-blur px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/30 text-blue-400">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                Continuous Reliability Command Center
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                  Phase 5 Intelligence
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Proactive time-series forecasting, multi-window SLO burn rates, reliability memory, and LangGraph agent reasoning.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={fetchDashboardData}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 border border-slate-700 flex items-center space-x-1.5 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh All</span>
          </button>
          <button
            onClick={handleRunAgent}
            disabled={agentAssessing}
            className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-xs font-semibold text-white shadow-lg shadow-blue-500/20 flex items-center space-x-1.5 transition"
          >
            <Zap className={`w-3.5 h-3.5 ${agentAssessing ? "animate-spin text-amber-300" : ""}`} />
            <span>{agentAssessing ? "Agent Evaluating..." : "Run LangGraph Agent"}</span>
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="border-b border-slate-800 bg-[#0a0f1d] px-6 flex space-x-2 overflow-x-auto select-none">
        {[
          { id: "overview", label: "Cluster Topology & Health", icon: Layers },
          { id: "predictive", label: "Predictive Warnings & TTE", icon: LineChart },
          { id: "slo", label: "SLOs & Error Budget", icon: Gauge },
          { id: "memory", label: "Reliability Memory", icon: History },
          { id: "timemachine", label: "Incident Time Machine", icon: Compass },
          { id: "agent", label: "Autonomous Agent", icon: BrainCircuit },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-3 px-3.5 text-xs font-medium border-b-2 flex items-center space-x-2 transition ${
                isActive
                  ? "border-blue-500 text-blue-400 bg-blue-500/5 font-semibold"
                  : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Main Tab Content */}
      <div className="flex-1 p-6 overflow-y-auto">
        {/* ==================================================================== */}
        {/* TAB 1: OVERVIEW */}
        {/* ==================================================================== */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Top Stat Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center space-x-3">
                <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-400">
                  <Server className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-xs text-slate-400">Monitored Services</div>
                  <div className="text-xl font-bold text-white mt-0.5">{overview?.total_services || 7} Nodes</div>
                </div>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center space-x-3">
                <div className="p-2.5 rounded-lg bg-blue-500/10 text-blue-400">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-xs text-slate-400">Cluster Throughput</div>
                  <div className="text-xl font-bold text-white mt-0.5">{overview?.cluster_throughput_mbps?.toFixed(1) || "12.4"} MB/s</div>
                </div>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center space-x-3">
                <div className="p-2.5 rounded-lg bg-amber-500/10 text-amber-400">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-xs text-slate-400">Active Anomalies</div>
                  <div className="text-xl font-bold text-amber-400 mt-0.5">{overview?.active_anomaly_count || 0} Alerting</div>
                </div>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center space-x-3">
                <div className="p-2.5 rounded-lg bg-purple-500/10 text-purple-400">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-xs text-slate-400">Error Budget Burn Status</div>
                  <div className="text-xl font-bold text-emerald-400 mt-0.5">Healthy (0.8x)</div>
                </div>
              </div>
            </div>

            {/* Capacity Risk Matrix */}
            <div className="rounded-xl bg-slate-900/50 border border-slate-800 p-5">
              <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <Gauge className="w-4 h-4 text-blue-400" />
                Service Capacity Risk Matrix & Impending Exhaustion
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-800/50 text-slate-400 font-mono text-[11px] uppercase">
                    <tr>
                      <th className="py-2.5 px-3">Service Name</th>
                      <th className="py-2.5 px-3">Highest Risk Metric</th>
                      <th className="py-2.5 px-3">Current Value</th>
                      <th className="py-2.5 px-3">Shortest TTE</th>
                      <th className="py-2.5 px-3">Risk Tier</th>
                      <th className="py-2.5 px-3">Prescriptive SRE Advice</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {capacityRisks.map((risk, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/30 transition">
                        <td className="py-3 px-3 font-semibold text-slate-200 flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                          {risk.service_name}
                        </td>
                        <td className="py-3 px-3 font-mono text-slate-300">{risk.highest_risk_metric}</td>
                        <td className="py-3 px-3 font-mono font-bold text-white">{risk.current_metric_value.toFixed(1)}%</td>
                        <td className="py-3 px-3">
                          {risk.shortest_tte_minutes ? (
                            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">
                              {risk.shortest_tte_minutes.toFixed(1)}m to threshold
                            </span>
                          ) : (
                            <span className="text-slate-400 font-mono">Stable / ∞</span>
                          )}
                        </td>
                        <td className="py-3 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            risk.risk_tier === "CRITICAL" ? "bg-rose-500/20 text-rose-400" :
                            risk.risk_tier === "HIGH" ? "bg-amber-500/20 text-amber-400" :
                            risk.risk_tier === "MODERATE" ? "bg-blue-500/20 text-blue-400" :
                            "bg-emerald-500/20 text-emerald-400"
                          }`}>
                            {risk.risk_tier}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-slate-300 text-[11px]">
                          {risk.recommendations?.[0] || "Maintain standard telemetry polling."}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ==================================================================== */}
        {/* TAB 2: PREDICTIVE WARNINGS */}
        {/* ==================================================================== */}
        {activeTab === "predictive" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <LineChart className="w-4 h-4 text-blue-400" />
                Resource Creep & Time-to-Exhaustion (TTE = (Threshold - Current) / Growth Rate)
              </h2>
              <span className="text-xs text-slate-400 font-mono">Models: Linear OLS & EWMA Momentum</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {predictions.map((p, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-sm">{p.service_name}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      p.warning_level === "CRITICAL" ? "bg-rose-500/20 text-rose-400" :
                      p.warning_level === "WARNING" ? "bg-amber-500/20 text-amber-400" :
                      p.warning_level === "ADVISORY" ? "bg-blue-500/20 text-blue-400" :
                      "bg-emerald-500/20 text-emerald-400"
                    }`}>
                      {p.warning_level}
                    </span>
                  </div>

                  <div className="text-xs text-slate-400 font-mono">Metric: {p.metric_name}</div>

                  <div className="flex items-end justify-between border-t border-slate-800/80 pt-2">
                    <div>
                      <div className="text-[10px] text-slate-400">Current / Threshold</div>
                      <div className="text-base font-bold text-white font-mono">
                        {p.current_value.toFixed(1)} / {p.exhaustion_threshold.toFixed(0)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] text-slate-400">Growth Rate</div>
                      <div className="text-xs font-mono text-blue-400">
                        {p.growth_rate_per_min >= 0 ? "+" : ""}{p.growth_rate_per_min.toFixed(2)}/min
                      </div>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 text-xs font-mono flex items-center justify-between">
                    <span className="text-slate-400">Time-to-Exhaustion:</span>
                    <span className="font-bold text-amber-400">
                      {p.time_to_exhaustion_minutes ? `${p.time_to_exhaustion_minutes.toFixed(1)} mins` : "Stable"}
                    </span>
                  </div>

                  {/* Forward Projections */}
                  {p.forecast_points?.length > 0 && (
                    <div className="border-t border-slate-800/80 pt-2 space-y-1">
                      <div className="text-[10px] text-slate-400 uppercase font-mono">Forward 30m Projections</div>
                      <div className="flex justify-between text-[11px] font-mono text-slate-300">
                        {p.forecast_points.slice(1, 4).map((fp: any, fidx: number) => (
                          <div key={fidx} className="text-center">
                            <span className="text-[10px] text-slate-400 block">+{fp.minutes_ahead}m</span>
                            <span className="font-semibold text-slate-200">{fp.predicted_value.toFixed(1)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ==================================================================== */}
        {/* TAB 3: SLOS & ERROR BUDGETS */}
        {/* ==================================================================== */}
        {activeTab === "slo" && (
          <div className="space-y-6">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <Gauge className="w-4 h-4 text-blue-400" />
              Service Level Objectives (SLOs) & Multi-Window Burn Rates
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {slos.map((slo, idx) => (
                <div key={idx} className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-white">{slo.name}</h3>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">{slo.service_name} • {slo.slo_type}</p>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      slo.status === "HEALTHY" ? "bg-emerald-500/20 text-emerald-400" :
                      slo.status === "AT_RISK" ? "bg-amber-500/20 text-amber-400" :
                      "bg-rose-500/20 text-rose-400"
                    }`}>
                      {slo.status}
                    </span>
                  </div>

                  {/* Target vs SLI Progress */}
                  <div>
                    <div className="flex justify-between text-xs mb-1 font-mono">
                      <span className="text-slate-400">Current SLI: <strong className="text-white">{slo.current_sli.toFixed(2)}%</strong></span>
                      <span className="text-slate-400">Target: <strong className="text-blue-400">{slo.target_percentage.toFixed(2)}%</strong></span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-emerald-500 h-2 rounded-full transition-all"
                        style={{ width: `${Math.min(100, slo.current_sli)}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* Error Budget Bar */}
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80">
                    <div className="flex justify-between text-xs font-mono mb-1">
                      <span className="text-slate-400">Error Budget Remaining:</span>
                      <span className="font-bold text-white">{slo.error_budget_remaining_pct.toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-1.5 rounded-full transition-all ${
                          slo.error_budget_remaining_pct > 70 ? "bg-emerald-400" :
                          slo.error_budget_remaining_pct > 30 ? "bg-amber-400" : "bg-rose-500"
                        }`}
                        style={{ width: `${slo.error_budget_remaining_pct}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Burn Rate Reports */}
            <div className="rounded-xl bg-slate-900/50 border border-slate-800 p-5 space-y-3">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
                Google SRE Multi-Window Burn Rate Intelligence (1h, 6h, 24h, 3d, 14d, 30d)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {burnRates.map((br, bidx) => (
                  <div key={bidx} className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold text-white">{br.service_name}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                        br.alert_status === "CRITICAL" ? "bg-rose-500/20 text-rose-400" :
                        br.alert_status === "WARNING" ? "bg-amber-500/20 text-amber-400" :
                        "bg-emerald-500/20 text-emerald-400"
                      }`}>
                        {br.alert_status}
                      </span>
                    </div>
                    <div className="text-[11px] font-mono text-slate-400">
                      Burn Rate: <strong className="text-white">{br.current_burn_rate.toFixed(2)}x</strong>
                    </div>
                    <div className="flex justify-between text-[10px] text-slate-400 font-mono border-t border-slate-800 pt-1.5">
                      <span>1h: {br.windows?.[0]?.burn_rate.toFixed(1)}x</span>
                      <span>6h: {br.windows?.[1]?.burn_rate.toFixed(1)}x</span>
                      <span>24h: {br.windows?.[2]?.burn_rate.toFixed(1)}x</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ==================================================================== */}
        {/* TAB 4: RELIABILITY MEMORY */}
        {/* ==================================================================== */}
        {activeTab === "memory" && (
          <div className="space-y-6">
            <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <History className="w-4 h-4 text-blue-400" />
                Reliability Memory Engine (20-Dimension Historical Index)
              </h2>
              <div className="flex gap-2 w-full md:w-80">
                <input
                  type="text"
                  placeholder="Search memory (e.g. Postgres pool)..."
                  value={memorySearch}
                  onChange={(e) => setMemorySearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearchMemory()}
                  className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
                />
                <button
                  onClick={handleSearchMemory}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold text-white transition flex items-center gap-1"
                >
                  <Search className="w-3.5 h-3.5" />
                  <span>Search</span>
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {memories.map((m, idx) => (
                <div key={idx} className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                        {m.severity || "SEV-1"}
                      </span>
                      <h3 className="text-sm font-bold text-white mt-1.5">{m.title}</h3>
                    </div>
                    <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                      {m.remediation_outcome || "SUSTAINED_SUCCESS"}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300">{m.summary}</p>

                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-xs space-y-1.5">
                    <div className="text-[11px] font-semibold text-slate-400 uppercase font-mono">Confirmed Root Cause:</div>
                    <div className="text-slate-200 font-mono text-[11px]">{m.confirmed_root_cause || "Database connection pool leak in session handler."}</div>
                  </div>

                  {m.learned_lessons?.length > 0 && (
                    <div className="text-xs text-slate-400 space-y-1 border-t border-slate-800/80 pt-2">
                      <div className="text-[10px] font-semibold text-slate-400 uppercase font-mono">Learned Lessons:</div>
                      {m.learned_lessons.map((lesson: string, lidx: number) => (
                        <div key={lidx} className="flex items-center gap-1.5 text-slate-300 text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span>{lesson}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ==================================================================== */}
        {/* TAB 5: INCIDENT TIME MACHINE */}
        {/* ==================================================================== */}
        {activeTab === "timemachine" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <Compass className="w-4 h-4 text-blue-400" />
                Incident Time Machine & NetworkX Causal Graph Replay
              </h2>
              <div className="text-xs font-mono text-slate-400">
                Viewing: {timeMachineData?.title || "Historical Incident Replay"}
              </div>
            </div>

            {/* Causal Graph Visualization Panel */}
            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
              <div className="flex justify-between items-center">
                <h3 className="text-xs font-bold text-white uppercase font-mono flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-blue-400" />
                  NetworkX Dependency Topology & Failure Propagation Path
                </h3>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  Blast Radius: {timeMachineData?.causal_graph?.blast_radius_score?.toFixed(0) || "62"}%
                </span>
              </div>

              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-wrap gap-3 items-center justify-center min-h-[140px]">
                {timeMachineData?.causal_graph?.nodes?.map((node: any, nidx: number) => (
                  <div
                    key={nidx}
                    className={`px-3.5 py-2 rounded-lg border text-xs font-mono flex items-center gap-2 shadow-sm ${
                      node.is_root_cause_candidate
                        ? "bg-rose-950/40 border-rose-500/80 text-rose-300 font-bold"
                        : node.health_status === "DEGRADED"
                        ? "bg-amber-950/30 border-amber-500/50 text-amber-300"
                        : "bg-slate-900 border-slate-700 text-slate-300"
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full ${
                      node.is_root_cause_candidate ? "bg-rose-400 animate-pulse" :
                      node.health_status === "DEGRADED" ? "bg-amber-400" : "bg-emerald-400"
                    }`}></span>
                    <span>{node.label}</span>
                  </div>
                ))}
              </div>

              {/* Impact Path Bar */}
              <div className="p-3 rounded-lg bg-slate-950 text-xs font-mono text-slate-400 flex items-center gap-2">
                <span className="text-slate-400">Propagation Path:</span>
                <span className="text-blue-400 font-semibold">
                  {timeMachineData?.causal_graph?.impacted_path?.join(" ➔ ") || "api-gateway ➔ order-service ➔ postgres-db"}
                </span>
              </div>
            </div>

            {/* Chronological Timeline */}
            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
              <h3 className="text-xs font-bold text-white uppercase font-mono flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-400" />
                Correlated Event Sequence
              </h3>
              <div className="space-y-2.5 max-h-96 overflow-y-auto pr-2">
                {timeMachineData?.timeline_events?.map((ev: any, eidx: number) => (
                  <div key={eidx} className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs flex items-start gap-3">
                    <span className="font-mono text-[10px] text-slate-400 shrink-0 mt-0.5">
                      {new Date(ev.timestamp).toLocaleTimeString()}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase shrink-0 ${
                      ev.phase === "DETECTION" ? "bg-rose-500/20 text-rose-400" :
                      ev.phase === "REMEDIATION" ? "bg-blue-500/20 text-blue-400" :
                      ev.phase === "VERIFICATION" ? "bg-emerald-500/20 text-emerald-400" :
                      ev.phase === "REGRESSION" ? "bg-rose-600/30 text-rose-300" :
                      "bg-slate-800 text-slate-300"
                    }`}>
                      {ev.phase}
                    </span>
                    <div className="flex-1">
                      <span className="font-semibold text-slate-200 mr-2">[{ev.source_service}]</span>
                      <span className="text-slate-300">{ev.summary}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ==================================================================== */}
        {/* TAB 6: AUTONOMOUS AGENT */}
        {/* ==================================================================== */}
        {activeTab === "agent" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <BrainCircuit className="w-4 h-4 text-blue-400" />
                LangGraph Autonomous Reliability Intelligence Agent
              </h2>
              <button
                onClick={handleRunAgent}
                disabled={agentAssessing}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold text-white transition flex items-center gap-1.5"
              >
                <Play className={`w-3.5 h-3.5 ${agentAssessing ? "animate-spin text-amber-300" : ""}`} />
                <span>{agentAssessing ? "Executing 8-Node Loop..." : "Execute Agent Loop"}</span>
              </button>
            </div>

            {agentData?.decision && (
              <div className="p-5 rounded-xl bg-gradient-to-r from-blue-950/40 to-indigo-950/40 border border-blue-500/30 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-amber-400" />
                    <span className="font-bold text-white text-sm">Agent Decision Recommendation</span>
                  </div>
                  <span className={`px-2.5 py-0.5 rounded text-xs font-bold ${
                    agentData.decision.risk_level === "CRITICAL" ? "bg-rose-500/20 text-rose-400" :
                    agentData.decision.risk_level === "HIGH" ? "bg-amber-500/20 text-amber-400" :
                    "bg-emerald-500/20 text-emerald-400"
                  }`}>
                    Mode: {agentData.decision.execution_mode}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200">
                  <strong className="text-blue-400 font-bold">Action ID: </strong> {agentData.decision.action_id}
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">
                  <strong className="text-slate-400">Rationale: </strong> {agentData.decision.rationale}
                </p>
              </div>
            )}

            {/* 8-Node Reasoning Trace */}
            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
              <h3 className="text-xs font-bold text-white uppercase font-mono flex items-center gap-2">
                <Layers className="w-4 h-4 text-blue-400" />
                LangGraph 8-Node Execution Trace
              </h3>
              <div className="space-y-2 font-mono text-xs max-h-96 overflow-y-auto pr-2">
                {agentData?.reasoning_trace?.map((trace: string, tidx: number) => (
                  <div key={tidx} className="p-2.5 rounded bg-slate-950 border border-slate-800/80 text-slate-300 flex items-start gap-2.5">
                    <span className="text-blue-400 font-bold">[{tidx + 1}]</span>
                    <span>{trace}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
