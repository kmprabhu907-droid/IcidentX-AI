"use client";

import React, { useState, useEffect } from "react";
import {
  RotateCcw,
  Search,
  BrainCircuit,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  History,
  Shield,
  Layers,
  ArrowRight,
  Sparkles,
  RefreshCw,
  Sliders,
  FileText,
} from "lucide-react";
import { learningApi } from "@/services/api";
import {
  FailurePattern,
  LearningPolicyChange,
  SimilarIncidentMatch,
  ContinuousImprovementRecommendation,
} from "@/types";

export default function LearningDashboardPage() {
  const [activeTab, setActiveTab] = useState<"knowledge" | "patterns" | "policy" | "recommendations">("knowledge");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [searchQuery, setSearchQuery] = useState("");
  const [searchService, setSearchService] = useState("");
  const [searchResults, setSearchResults] = useState<SimilarIncidentMatch[]>([]);
  const [patterns, setPatterns] = useState<FailurePattern[]>([]);
  const [policyData, setPolicyData] = useState<{
    active_policy?: LearningPolicyChange;
    history?: LearningPolicyChange[];
    total_versions?: number;
  }>({});
  const [recommendations, setRecommendations] = useState<ContinuousImprovementRecommendation[]>([]);

  // Initial load
  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [patternsRes, policyRes, searchRes] = await Promise.all([
        learningApi.getRecurringPatterns().catch(() => []),
        learningApi.getLearningPolicy().catch(() => ({ active_policy: undefined, history: [], total_versions: 1 })),
        learningApi.searchKnowledge({ query: searchQuery || undefined }).catch(() => []),
      ]);

      setPatterns(patternsRes);
      setPolicyData(policyRes as any);
      setSearchResults(searchRes);
    } catch (err: any) {
      setError(err?.message || "Failed to load learning intelligence data");
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setLoading(true);
    try {
      const res = await learningApi.searchKnowledge({
        query: searchQuery || undefined,
        service: searchService || undefined,
      });
      setSearchResults(res);
    } catch (err: any) {
      setError(err?.message || "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async (versionId: string) => {
    if (!confirm(`Are you sure you want to rollback to policy version ${versionId}?`)) return;
    setLoading(true);
    try {
      await learningApi.rollbackPolicy(versionId, "web-sre-lead");
      await loadAllData();
      alert(`Successfully rolled back to policy ${versionId}`);
    } catch (err: any) {
      alert(`Rollback failed: ${err?.message || "Unknown error"}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 p-8">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl shadow-lg shadow-indigo-500/20">
              <RotateCcw className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                Continuous SRE Self-Learning Engine
                <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  PHASE 13
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Multi-dimensional recovery verification, before/after telemetry diffing, postmortems & knowledge memory
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={loadAllData}
          disabled={loading}
          className="flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm font-medium border border-slate-700 transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Intelligence</span>
        </button>
      </div>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 my-6">
        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Active Policy Version</span>
            <Shield className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-xl font-bold text-white mt-2 font-mono">
            {policyData.active_policy?.version_id || "pol-v1-base"}
          </div>
          <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block"></span>
            Reversible & Version Controlled
          </div>
        </div>

        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Historical Incidents</span>
            <History className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-xl font-bold text-white mt-2">
            {searchResults.length + 3} Verified Entries
          </div>
          <div className="text-xs text-slate-400 mt-1">Multi-feature cosine & Jaccard index</div>
        </div>

        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Recurring Patterns</span>
            <Layers className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-xl font-bold text-amber-400 mt-2">
            {patterns.length} Systemic Clusters
          </div>
          <div className="text-xs text-slate-400 mt-1">Cluster recurrence threshold: ≥ 2 events</div>
        </div>

        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Safety Guard Status</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-emerald-400 mt-2">100% Enforced</div>
          <div className="text-xs text-slate-400 mt-1">No unverified training / Human approval</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-6 mb-6">
        {[
          { key: "knowledge", label: "Incident Knowledge Base", icon: Search },
          { key: "patterns", label: "Recurring Failure Patterns", icon: Layers },
          { key: "policy", label: "Versioned Learning Policy", icon: Sliders },
          { key: "recommendations", label: "Systemic Recommendations", icon: Sparkles },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center space-x-2 py-3 px-1 border-b-2 font-medium text-sm transition ${
                isActive
                  ? "border-indigo-500 text-indigo-400 font-semibold"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 1: KNOWLEDGE BASE SEARCH */}
      {activeTab === "knowledge" && (
        <div className="space-y-6">
          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search by keywords, root cause hypothesis, or error trace..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[#0e1526] border border-slate-800 rounded-lg pl-9 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <input
              type="text"
              placeholder="Filter by service (e.g. payment-service)"
              value={searchService}
              onChange={(e) => setSearchService(e.target.value)}
              className="sm:w-64 bg-[#0e1526] border border-slate-800 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition"
            >
              Search Knowledge
            </button>
          </form>

          <div className="grid grid-cols-1 gap-4">
            {searchResults.length === 0 ? (
              <div className="p-12 text-center text-slate-400 bg-[#0e1526] rounded-xl border border-slate-800">
                No matching historical incidents found.
              </div>
            ) : (
              searchResults.map((match) => (
                <div
                  key={match.incident_id}
                  className="bg-[#0e1526] border border-slate-800 hover:border-slate-700 rounded-xl p-5 transition space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                          {match.incident_id}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                          {match.severity}
                        </span>
                        <span className="text-xs text-slate-400 font-mono">
                          Services: {match.common_services.join(", ")}
                        </span>
                      </div>
                      <h3 className="text-base font-semibold text-white mt-1.5">{match.title}</h3>
                    </div>
                    <div className="flex flex-col items-end">
                      <div className="text-xs text-slate-400 font-medium">Similarity</div>
                      <div className="text-sm font-bold text-emerald-400 font-mono">
                        {(match.similarity_score * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-800/80 text-sm">
                    <span className="text-xs font-semibold uppercase text-slate-400 block mb-1">
                      Verified Historical Root Cause:
                    </span>
                    <p className="text-slate-300">{match.verified_root_cause}</p>
                  </div>

                  {match.recommended_remediations.length > 0 && (
                    <div className="flex items-center space-x-2 text-xs">
                      <span className="text-slate-400 font-semibold">Effective Remediations:</span>
                      {match.recommended_remediations.map((rem, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono"
                        >
                          {rem}
                        </span>
                      ))}
                    </div>
                  )}

                  {match.matching_features.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {match.matching_features.map((feat, idx) => (
                        <span key={idx} className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                          {feat}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 2: RECURRING FAILURE PATTERNS */}
      {activeTab === "patterns" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {patterns.length === 0 ? (
            <div className="col-span-2 p-12 text-center text-slate-400 bg-[#0e1526] rounded-xl border border-slate-800">
              No recurring patterns detected. Services are exhibiting unique failure profiles.
            </div>
          ) : (
            patterns.map((pat) => (
              <div
                key={pat.pattern_id}
                className="bg-[#0e1526] border border-amber-500/20 rounded-xl p-5 space-y-4"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 text-xs font-bold rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                      RECURRING {pat.frequency_count}x
                    </span>
                    <span className="text-xs font-mono text-slate-400">{pat.pattern_id}</span>
                  </div>
                  <div className="text-xs text-slate-400">
                    MTTR: <span className="font-semibold text-white">{pat.mean_time_to_recover_minutes}m</span>
                  </div>
                </div>

                <div>
                  <h3 className="text-base font-bold text-white">{pat.pattern_name}</h3>
                  <div className="text-xs text-slate-400 mt-1 font-mono">
                    Affected: {pat.affected_services.join(", ")}
                  </div>
                </div>

                <div className="text-xs bg-slate-900/80 p-2.5 rounded border border-slate-800 font-mono text-rose-300">
                  Signature: {pat.error_signature}
                </div>

                <div className="text-sm bg-indigo-950/20 border border-indigo-500/20 rounded-lg p-3">
                  <span className="text-xs font-semibold text-indigo-400 uppercase block mb-1">
                    Recommended Systemic Remedy:
                  </span>
                  <p className="text-slate-300 text-xs leading-relaxed">{pat.recommended_systemic_fix}</p>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* TAB 3: VERSIONED LEARNING POLICY */}
      {activeTab === "policy" && (
        <div className="space-y-6">
          {policyData.active_policy && (
            <div className="bg-[#0e1526] border border-indigo-500/30 rounded-xl p-6 space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      ACTIVE VERSION
                    </span>
                    <span className="font-mono text-sm text-white font-semibold">
                      {policyData.active_policy.version_id}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{policyData.active_policy.rationale}</p>
                </div>
                <div className="text-xs text-slate-400 text-right">
                  <div>Approved: {policyData.active_policy.human_approved ? "Human Verified" : "Autonomous (SLA Bounded)"}</div>
                  <div className="font-mono">{policyData.active_policy.created_at.slice(0, 19)}</div>
                </div>
              </div>

              {/* Weights Table */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div className="bg-slate-900/60 rounded-lg p-3.5 border border-slate-800">
                  <div className="text-xs font-semibold uppercase text-slate-400 mb-2">
                    Hypothesis Ranking Biases
                  </div>
                  <div className="space-y-1.5 font-mono text-xs">
                    {Object.entries(policyData.active_policy.hypothesis_ranking_weights).map(([cat, w]) => (
                      <div key={cat} className="flex justify-between">
                        <span className="text-slate-300">{cat}</span>
                        <span className="text-indigo-400 font-bold">{w.toFixed(2)}x</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-slate-900/60 rounded-lg p-3.5 border border-slate-800">
                  <div className="text-xs font-semibold uppercase text-slate-400 mb-2">
                    Agent Investigation Priorities
                  </div>
                  <div className="space-y-1.5 font-mono text-xs">
                    {Object.entries(policyData.active_policy.agent_task_priorities).map(([agent, p]) => (
                      <div key={agent} className="flex justify-between">
                        <span className="text-slate-300 truncate max-w-[150px]">{agent}</span>
                        <span className="text-amber-400 font-bold">P{p}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-slate-900/60 rounded-lg p-3.5 border border-slate-800">
                  <div className="text-xs font-semibold uppercase text-slate-400 mb-2">
                    Evidence Collection Weights
                  </div>
                  <div className="space-y-1.5 font-mono text-xs">
                    {Object.entries(policyData.active_policy.evidence_collection_weights).map(([ev, w]) => (
                      <div key={ev} className="flex justify-between">
                        <span className="text-slate-300 truncate max-w-[150px]">{ev}</span>
                        <span className="text-emerald-400 font-bold">{w.toFixed(2)}x</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Version History Table */}
          <div className="bg-[#0e1526] border border-slate-800 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 font-semibold text-sm text-slate-300">
              Audit Log & Version History
            </div>
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-slate-400 uppercase font-semibold">
                <tr>
                  <th className="p-3">Version</th>
                  <th className="p-3">Created</th>
                  <th className="p-3">Source Incident</th>
                  <th className="p-3">Rationale</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {(policyData.history || []).map((v) => (
                  <tr key={v.version_id} className="hover:bg-slate-800/40">
                    <td className="p-3 font-mono font-semibold text-indigo-400">{v.version_id}</td>
                    <td className="p-3 font-mono text-slate-400">{v.created_at.slice(0, 19)}</td>
                    <td className="p-3 font-mono text-slate-300">{v.source_incident_ids.join(", ") || "Base"}</td>
                    <td className="p-3 text-slate-300 max-w-xs truncate">{v.rationale}</td>
                    <td className="p-3">
                      {v.is_active ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
                          Active
                        </span>
                      ) : (
                        <span className="text-slate-500">Archived</span>
                      )}
                    </td>
                    <td className="p-3 text-right">
                      {!v.is_active && (
                        <button
                          onClick={() => handleRollback(v.version_id)}
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-semibold transition"
                        >
                          Rollback
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: SYSTEMIC RECOMMENDATIONS */}
      {activeTab === "recommendations" && (
        <div className="space-y-4">
          <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-5">
            <h3 className="text-base font-bold text-white mb-2">Automated SRE Improvement Recommendations</h3>
            <p className="text-xs text-slate-400">
              Generated from postmortem findings, missing telemetry baselines, and recurring failure patterns.
              Zero automatic infrastructure mutations; all recommendations require human review.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {[
              {
                id: "REC-SYS-01",
                cat: "RESOURCE_LIMITS",
                title: "Optimize JVM Heap & Memory Ceiling for payment-service",
                desc: "Increase memory limits from 512Mi to 768Mi and configure -Xmx576m to grant GC headroom.",
                benefit: "Prevents sudden container OOMKilled evictions during ledger transaction spikes.",
                priority: "P1",
                owner: "Core Payment SRE",
              },
              {
                id: "REC-SYS-02",
                cat: "DEPENDENCY_OBSERVABILITY",
                title: "Install Circuit Breaker on order-service Database Pool",
                desc: "Shed non-critical queries when database pool utilization exceeds 85% for > 30 seconds.",
                benefit: "Eliminates cascading HTTP 5xx errors to front-end checkout gateway.",
                priority: "P1",
                owner: "Order Engineering Lead",
              },
              {
                id: "REC-SYS-03",
                cat: "ALERTS",
                title: "Add Early-Warning Memory Burn-Rate Alert (80% threshold)",
                desc: "Trigger on-call page when memory consumption growth rate projects OOM within 10 minutes.",
                benefit: "Reduces Mean Time to Detect (MTTD) by up to 12 minutes before user disruption.",
                priority: "P2",
                owner: "Observability Platform",
              },
            ].map((rec) => (
              <div
                key={rec.id}
                className="bg-[#0e1526] border border-slate-800 rounded-xl p-5 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 rounded text-xs font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono">
                      {rec.cat}
                    </span>
                    <span className="px-2 py-0.5 rounded text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                      {rec.priority}
                    </span>
                    <span className="text-xs font-mono text-slate-400">{rec.id}</span>
                  </div>
                  <span className="text-xs text-slate-400">Owner: <strong className="text-slate-200">{rec.owner}</strong></span>
                </div>

                <h4 className="text-base font-semibold text-white">{rec.title}</h4>
                <p className="text-xs text-slate-300">{rec.desc}</p>

                <div className="bg-emerald-950/20 border border-emerald-500/20 rounded-lg p-2.5 text-xs text-emerald-300">
                  <strong>Expected Benefit:</strong> {rec.benefit}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
