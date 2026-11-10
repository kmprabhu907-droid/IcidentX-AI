"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { 
  ArrowLeft, 
  AlertTriangle, 
  Clock, 
  ShieldCheck, 
  FileText, 
  Brain, 
  Bot, 
  CheckCircle2, 
  Layers, 
  Activity,
  RefreshCw
} from "lucide-react";
import { api } from "../../../services/api";
import { 
  Incident, 
  Evidence, 
  RootCauseHypothesis, 
  AgentExecution 
} from "../../../types";

export default function IncidentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const incidentId = resolvedParams.id;

  const [incident, setIncident] = useState<Incident | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [hypotheses, setHypotheses] = useState<RootCauseHypothesis[]>([]);
  const [agentExecutions, setAgentExecutions] = useState<AgentExecution[]>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "courtroom" | "evidence" | "executions">("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadIncidentData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [inc, evRes, hypRes, agentRes] = await Promise.all([
        api.getIncident(incidentId),
        api.getIncidentEvidence(incidentId).catch(() => ({ items: [], total: 0 })),
        api.getIncidentHypotheses(incidentId).catch(() => ({ items: [], total: 0 })),
        api.getIncidentAgentExecutions(incidentId).catch(() => ({ items: [], total: 0 })),
      ]);
      setIncident(inc);
      setEvidence(evRes.items);
      setHypotheses(hypRes.items);
      setAgentExecutions(agentRes.items);
    } catch (err: any) {
      setError(err.message || "Failed to load incident details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidentData();
  }, [incidentId]);

  if (loading) {
    return (
      <div className="py-24 text-center text-xs font-mono text-slate-500">
        Loading incident #{incidentId} from database...
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="p-6 rounded-xl border border-red-500/30 bg-red-950/20 text-red-300 text-xs font-mono max-w-xl mx-auto space-y-3">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <span className="font-bold">Incident Not Found</span>
        </div>
        <p>{error || "The specified incident does not exist in PostgreSQL."}</p>
        <Link
          href="/incidents"
          className="inline-block px-3 py-1.5 rounded-lg bg-slate-800 text-white font-mono text-xs hover:bg-slate-700"
        >
          &larr; Back to Incident Register
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Navigation Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          href="/incidents"
          className="flex items-center space-x-2 text-xs font-mono text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Incident Register</span>
        </Link>

        <button
          onClick={loadIncidentData}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/80 hover:bg-slate-800 text-xs font-mono text-slate-400 transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Incident Hero Banner */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-[#0e1424] shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center space-x-3">
            <span className={`text-xs font-mono font-bold px-3 py-1 rounded-md border ${
              incident.severity === "SEV-1" 
                ? "bg-red-500/10 text-red-400 border-red-500/30" 
                : "bg-amber-500/10 text-amber-400 border-amber-500/30"
            }`}>
              {incident.severity}
            </span>
            <span className="text-xs font-mono font-bold px-3 py-1 rounded-md border border-slate-700 bg-slate-900 text-slate-300">
              {incident.status}
            </span>
            <span className="text-xs font-mono text-slate-400">
              UUID: <code className="text-slate-300">{incident.id}</code>
            </span>
          </div>

          <div className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            <span>Detected: {new Date(incident.detected_at).toLocaleString()}</span>
          </div>
        </div>

        <div>
          <h1 className="text-xl font-bold tracking-tight text-white">
            {incident.title}
          </h1>
          {incident.summary && (
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              {incident.summary}
            </p>
          )}
        </div>

        {incident.impact_scope && (
          <div className="text-xs font-mono text-slate-400 pt-2 border-t border-slate-800 flex items-center gap-2">
            <span className="text-slate-400">Impact Scope:</span>
            <span className="text-blue-400 font-semibold">{incident.impact_scope}</span>
          </div>
        )}
      </div>

      {/* Tab Controls */}
      <div className="flex border-b border-slate-800 space-x-2">
        <button
          onClick={() => setActiveTab("overview")}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all ${
            activeTab === "overview"
              ? "border-blue-500 text-blue-400 bg-blue-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Incident Overview</span>
        </button>

        <button
          onClick={() => setActiveTab("courtroom")}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all ${
            activeTab === "courtroom"
              ? "border-purple-500 text-purple-400 bg-purple-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Brain className="w-3.5 h-3.5" />
          <span>Root Cause Courtroom ({hypotheses.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("evidence")}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all ${
            activeTab === "evidence"
              ? "border-amber-500 text-amber-400 bg-amber-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Evidence Locker ({evidence.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("executions")}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all ${
            activeTab === "executions"
              ? "border-emerald-500 text-emerald-400 bg-emerald-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Bot className="w-3.5 h-3.5" />
          <span>Agent Executions ({agentExecutions.length})</span>
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-5 rounded-xl border border-slate-800 bg-[#0e1424] space-y-3">
            <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-300">
              Operational Status
            </h3>
            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between py-1.5 border-b border-slate-800/80">
                <span className="text-slate-400">Current Phase:</span>
                <span className="text-white font-bold">{incident.status}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800/80">
                <span className="text-slate-400">Detected At:</span>
                <span className="text-slate-200">{new Date(incident.detected_at).toUTCString()}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800/80">
                <span className="text-slate-400">Resolved At:</span>
                <span className="text-slate-200">
                  {incident.resolved_at ? new Date(incident.resolved_at).toUTCString() : "Active Incident (Unresolved)"}
                </span>
              </div>
            </div>
          </div>

          <div className="p-5 rounded-xl border border-slate-800 bg-[#0e1424] space-y-3">
            <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-300">
              Investigation Readiness
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              This incident is registered in the database. In Phase 2 &amp; Phase 4, the **Incident Time Machine** and **Root Cause Courtroom** will automatically attach telemetry streams and multi-agent debate threads to this incident record.
            </p>
          </div>
        </div>
      )}

      {activeTab === "courtroom" && (
        <div className="p-6 rounded-xl border border-slate-800 bg-[#0e1424]">
          {hypotheses.length === 0 ? (
            <div className="py-12 text-center text-xs font-mono text-slate-400 space-y-2">
              <Brain className="w-8 h-8 text-purple-400 mx-auto opacity-70" />
              <p className="font-bold text-slate-300">No Causal Hypotheses Generated Yet</p>
              <p className="text-slate-400 max-w-md mx-auto">
                Investigation agents have not yet evaluated this incident. Root cause courtroom debate triggers in Phase 4.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {hypotheses.map((hyp) => (
                <div key={hyp.id} className="p-4 rounded-lg border border-slate-800 bg-slate-900/50">
                  <div className="flex justify-between text-xs font-mono mb-2">
                    <span className="text-purple-400 font-bold">{hyp.status}</span>
                    <span className="text-slate-400">Probability: {(hyp.probability_score * 100).toFixed(1)}%</span>
                  </div>
                  <p className="text-sm font-semibold text-white">{hyp.hypothesis_text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "evidence" && (
        <div className="p-6 rounded-xl border border-slate-800 bg-[#0e1424]">
          {evidence.length === 0 ? (
            <div className="py-12 text-center text-xs font-mono text-slate-400 space-y-2">
              <FileText className="w-8 h-8 text-amber-400 mx-auto opacity-70" />
              <p className="font-bold text-slate-300">No Evidence Exhibits Filed</p>
              <p className="text-slate-400 max-w-md mx-auto">
                No telemetry anomalies, log stack traces, or trace waterfalls have been linked to this incident record yet.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {evidence.map((ev) => (
                <div key={ev.id} className="p-3.5 rounded-lg border border-slate-800 bg-slate-900/50 text-xs font-mono">
                  <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                    <span className="text-amber-400">{ev.evidence_type} ({ev.source_system})</span>
                    <span>Confidence: {(ev.confidence_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="text-slate-200">{ev.description}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "executions" && (
        <div className="p-6 rounded-xl border border-slate-800 bg-[#0e1424]">
          {agentExecutions.length === 0 ? (
            <div className="py-12 text-center text-xs font-mono text-slate-400 space-y-2">
              <Bot className="w-8 h-8 text-emerald-400 mx-auto opacity-70" />
              <p className="font-bold text-slate-300">No Agent Executions</p>
              <p className="text-slate-400 max-w-md mx-auto">
                No autonomous agents have run against this incident. In accordance with Rule #3, we never fabricate fake agent runs.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {agentExecutions.map((agent) => (
                <div key={agent.id} className="p-3.5 rounded-lg border border-slate-800 bg-slate-900/50 text-xs font-mono">
                  <div className="flex justify-between text-slate-400 mb-1">
                    <span className="text-emerald-400 font-bold">{agent.agent_role}</span>
                    <span>{agent.status}</span>
                  </div>
                  <div className="text-slate-300">{agent.observation}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

    </div>
  );
}
