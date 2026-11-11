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
  RefreshCw,
  Play,
  Gavel,
  History,
  Compass,
  Code2,
  Scale,
  Search,
  ChevronRight,
  ChevronDown,
  Database,
  Cpu,
  Network,
  Terminal,
  Sliders,
  Sparkles,
  Info,
  XCircle,
  ShieldAlert,
  ListChecks,
  BrainCircuit,
  RotateCcw,
  UserCheck,
} from "lucide-react";
import { api } from "../../../services/api";
import {
  Incident,
  Evidence,
  RootCauseHypothesis,
  AgentExecution,
  TimelineEvent,
  CourtroomItem,
  CourtroomView,
  InvestigationPlanView,
  DiagnosticAction,
  InvestigationStatus,
  RemediationAction,
  RemediationPolicy,
} from "../../../types";

const INVESTIGATION_AGENTS = [
  { id: "IncidentIntakeAgent", label: "Intake", icon: FileText },
  { id: "ContextGatheringAgent", label: "Context", icon: Network },
  { id: "TelemetryAnalysisAgent", label: "Telemetry", icon: Activity },
  { id: "LogAnalysisAgent", label: "Logs", icon: Terminal },
  { id: "TraceAnalysisAgent", label: "Traces", icon: Sliders },
  { id: "ServiceDependencyAnalysisAgent", label: "Topology", icon: Layers },
  { id: "DeploymentChangeAgent", label: "Deployments", icon: History },
  { id: "RootCauseHypothesisAgent", label: "Hypotheses", icon: Brain },
  { id: "EvidenceVerificationAgent", label: "Verification", icon: Scale },
  { id: "InvestigationSummaryAgent", label: "Summary", icon: ShieldCheck },
];

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
  const [courtroom, setCourtroom] = useState<CourtroomView | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [planner, setPlanner] = useState<InvestigationPlanView | null>(null);
  const [investigationStatus, setInvestigationStatus] = useState<InvestigationStatus | null>(null);

  // Phase 4 Remediation State
  const [remediationActions, setRemediationActions] = useState<RemediationAction[]>([]);
  const [remediationPolicy, setRemediationPolicy] = useState<RemediationPolicy | null>(null);
  const [actionOperating, setActionOperating] = useState(false);
  const [approvalModalAction, setApprovalModalAction] = useState<RemediationAction | null>(null);
  const [approvalOperatorName, setApprovalOperatorName] = useState("alice@incidentx.ai");
  const [approvalComment, setApprovalComment] = useState("");
  const [verificationModalAction, setVerificationModalAction] = useState<RemediationAction | null>(null);

  const [activeTab, setActiveTab] = useState<
    "overview" | "courtroom" | "timeline" | "evidence" | "planner" | "agents" | "remediation"
  >("overview");
  const [loading, setLoading] = useState(true);
  const [investigating, setInvestigating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Inspector Modals
  const [selectedRawPayload, setSelectedRawPayload] = useState<{ title: string; json: string } | null>(null);
  const [evidenceFilter, setEvidenceFilter] = useState<string>("ALL");
  const [timelineServiceFilter, setTimelineServiceFilter] = useState<string>("ALL");

  const loadIncidentData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        inc,
        evRes,
        hypRes,
        agentRes,
        courtroomRes,
        timelineRes,
        plannerRes,
        statusRes,
        remRes,
        polRes,
      ] = await Promise.all([
        api.getIncident(incidentId),
        api.getIncidentEvidence(incidentId).catch(() => ({ items: [], total: 0 })),
        api.getIncidentHypotheses(incidentId).catch(() => ({ items: [], total: 0 })),
        api.getIncidentAgentExecutions(incidentId).catch(() => ({ items: [], total: 0 })),
        api.getCourtroom(incidentId).catch(() => null),
        api.getTimeline(incidentId).catch(() => ({ incident_id: incidentId, total_events: 0, events: [] })),
        api.getPlanner(incidentId).catch(() => null),
        api.getInvestigationStatus(incidentId).catch(() => null),
        api.listIncidentRemediationActions(incidentId).catch(() => []),
        api.getRemediationPolicy().catch(() => null),
      ]);

      setIncident(inc);
      setEvidence(evRes.items);
      setHypotheses(hypRes.items);
      setAgentExecutions(agentRes.items);
      setCourtroom(courtroomRes);
      setTimelineEvents(timelineRes?.events || []);
      setPlanner(plannerRes);
      setInvestigationStatus(statusRes);
      setRemediationActions(remRes);
      setRemediationPolicy(polRes);
    } catch (err: any) {
      setError(err.message || "Failed to load incident investigation details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidentData();
  }, [incidentId]);

  const handleTriggerInvestigation = async () => {
    setInvestigating(true);
    try {
      await api.triggerInvestigation(incidentId);
      await loadIncidentData();
      setActiveTab("courtroom");
    } catch (err: any) {
      alert(`Investigation failed: ${err.message}`);
    } finally {
      setInvestigating(false);
    }
  };

  const handleGenerateRecommendations = async () => {
    setActionOperating(true);
    try {
      await api.triggerRemediationRecommendations(incidentId);
      const updated = await api.listIncidentRemediationActions(incidentId);
      setRemediationActions(updated);
    } catch (err: any) {
      alert(`Failed to formulate remediation recommendations: ${err.message}`);
    } finally {
      setActionOperating(false);
    }
  };

  const handleApproveAction = async () => {
    if (!approvalModalAction) return;
    setActionOperating(true);
    try {
      await api.approveRemediationAction(incidentId, approvalModalAction.id, {
        approved_by: approvalOperatorName,
        comment: approvalComment || undefined,
      });
      setApprovalModalAction(null);
      const updated = await api.listIncidentRemediationActions(incidentId);
      setRemediationActions(updated);
    } catch (err: any) {
      alert(`Approval failed: ${err.message}`);
    } finally {
      setActionOperating(false);
    }
  };

  const handleRejectAction = async (action: RemediationAction) => {
    const reason = prompt("Enter justification for rejecting this recovery action:");
    if (!reason) return;
    setActionOperating(true);
    try {
      await api.rejectRemediationAction(incidentId, action.id, {
        rejected_by: approvalOperatorName,
        reason: reason,
      });
      const updated = await api.listIncidentRemediationActions(incidentId);
      setRemediationActions(updated);
    } catch (err: any) {
      alert(`Rejection failed: ${err.message}`);
    } finally {
      setActionOperating(false);
    }
  };

  const handleExecuteAction = async (action: RemediationAction) => {
    setActionOperating(true);
    try {
      await api.executeRemediationAction(incidentId, action.id);
      const updated = await api.listIncidentRemediationActions(incidentId);
      setRemediationActions(updated);
      const executed = updated.find((a) => a.id === action.id);
      if (executed) {
        setVerificationModalAction(executed);
      }
    } catch (err: any) {
      alert(`Remediation execution failed: ${err.message}`);
      await loadIncidentData();
    } finally {
      setActionOperating(false);
    }
  };

  const handleRollbackAction = async (action: RemediationAction) => {
    if (!confirm(`Are you sure you want to rollback ${action.name}?`)) return;
    setActionOperating(true);
    try {
      await api.rollbackRemediationAction(incidentId, action.id, approvalOperatorName);
      const updated = await api.listIncidentRemediationActions(incidentId);
      setRemediationActions(updated);
      alert(`Action ${action.name} successfully rolled back.`);
    } catch (err: any) {
      alert(`Rollback failed: ${err.message}`);
    } finally {
      setActionOperating(false);
    }
  };

  if (loading && !incident) {
    return (
      <div className="py-24 text-center text-xs font-mono text-slate-500">
        Loading IncidentX Investigation Workspace for #{incidentId}...
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="p-6 rounded-xl border border-red-500/30 bg-red-950/20 text-red-300 text-xs font-mono max-w-xl mx-auto space-y-3">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <span className="font-bold">Incident Record Missing</span>
        </div>
        <p>{error || "The specified incident does not exist in the database."}</p>
        <Link
          href="/incidents"
          className="inline-block px-3 py-1.5 rounded-lg bg-slate-800 text-white font-mono text-xs hover:bg-slate-700"
        >
          &larr; Back to Incident Register
        </Link>
      </div>
    );
  }

  const completedAgentSet = new Set(
    agentExecutions.filter((a) => a.status === "COMPLETED").map((a) => a.agent_role)
  );

  const topHypothesis = hypotheses.length > 0 ? hypotheses[0] : null;

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

        <div className="flex items-center space-x-2">
          <button
            onClick={loadIncidentData}
            disabled={loading || investigating}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/80 hover:bg-slate-800 text-xs font-mono text-slate-400 transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleTriggerInvestigation}
            disabled={investigating}
            className="flex items-center space-x-2 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-mono font-bold shadow-md shadow-purple-900/30 transition-all disabled:opacity-50"
          >
            <Sparkles className={`w-3.5 h-3.5 ${investigating ? "animate-spin text-amber-300" : ""}`} />
            <span>{investigating ? "Investigating..." : hypotheses.length > 0 ? "Re-Run Investigation" : "Run Investigation"}</span>
          </button>
        </div>
      </div>

      {/* Incident Hero Banner */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-[#0e1424] shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center space-x-3">
            <span
              className={`text-xs font-mono font-bold px-3 py-1 rounded-md border ${
                incident.severity === "SEV-1"
                  ? "bg-red-500/10 text-red-400 border-red-500/30"
                  : incident.severity === "SEV-2"
                  ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                  : "bg-blue-500/10 text-blue-400 border-blue-500/30"
              }`}
            >
              {incident.severity}
            </span>
            <span className="text-xs font-mono font-bold px-3 py-1 rounded-md border border-slate-700 bg-slate-900 text-slate-300">
              {incident.status}
            </span>
            <span className="text-xs font-mono text-slate-400 hidden sm:inline">
              ID: <code className="text-slate-300">{incident.id.slice(0, 8)}...</code>
            </span>
          </div>

          <div className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-blue-400" />
            <span>Detected: {new Date(incident.detected_at).toLocaleString()}</span>
          </div>
        </div>

        <div>
          <h1 className="text-xl font-bold tracking-tight text-white">{incident.title}</h1>
          {incident.summary && (
            <p className="text-xs text-slate-400 mt-2 leading-relaxed font-sans">{incident.summary}</p>
          )}
        </div>

        {incident.impact_scope && (
          <div className="text-xs font-mono text-slate-400 pt-2 border-t border-slate-800 flex items-center gap-2">
            <span className="text-slate-400">Impact Scope:</span>
            <span className="text-blue-400 font-semibold">{incident.impact_scope}</span>
          </div>
        )}
      </div>

      {/* 10-Agent Investigation Pipeline State Machine Tracker */}
      <div className="p-4 rounded-xl border border-slate-800 bg-[#0b101e] space-y-3">
        <div className="flex items-center justify-between text-xs font-mono">
          <div className="flex items-center space-x-2">
            <Bot className="w-4 h-4 text-purple-400" />
            <span className="font-bold text-slate-200">10-Agent Autonomous Investigation Pipeline</span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30">
              v3.0.0
            </span>
          </div>
          <span className="text-slate-400">
            {completedAgentSet.size} / 10 Agents Completed
          </span>
        </div>

        {/* Pipeline Stepper */}
        <div className="grid grid-cols-2 sm:grid-cols-5 lg:grid-cols-10 gap-2">
          {INVESTIGATION_AGENTS.map((agent, idx) => {
            const Icon = agent.icon;
            const isCompleted = completedAgentSet.has(agent.id);
            const isRunning = investigating && !isCompleted;
            return (
              <div
                key={agent.id}
                className={`p-2 rounded-lg border text-center transition-all ${
                  isCompleted
                    ? "border-emerald-500/40 bg-emerald-500/5 text-emerald-300"
                    : isRunning
                    ? "border-purple-500/40 bg-purple-500/10 text-purple-300 animate-pulse"
                    : "border-slate-800 bg-slate-900/40 text-slate-500"
                }`}
              >
                <div className="flex items-center justify-center mb-1">
                  {isCompleted ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <Icon className="w-4 h-4" />
                  )}
                </div>
                <div className="text-[10px] font-mono font-bold truncate">{agent.label}</div>
                <div className="text-[9px] font-mono text-slate-400">Step {idx + 1}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Primary Tab Navigation */}
      <div className="flex border-b border-slate-800 space-x-1 overflow-x-auto">
        <button
          onClick={() => setActiveTab("overview")}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === "overview"
              ? "border-blue-500 text-blue-400 bg-blue-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Executive Summary</span>
        </button>

        <button
          onClick={() => setActiveTab("courtroom")}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === "courtroom"
              ? "border-purple-500 text-purple-400 bg-purple-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Scale className="w-3.5 h-3.5" />
          <span>Root Cause Courtroom ({hypotheses.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("timeline")}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === "timeline"
              ? "border-cyan-500 text-cyan-400 bg-cyan-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>Incident Time Machine ({timelineEvents.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("evidence")}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === "evidence"
              ? "border-amber-500 text-amber-400 bg-amber-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Evidence Locker ({evidence.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("planner")}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === "planner"
              ? "border-indigo-500 text-indigo-400 bg-indigo-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Compass className="w-3.5 h-3.5" />
          <span>Diagnostic Planner ({planner?.total_actions || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab("agents")}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === "agents"
              ? "border-emerald-500 text-emerald-400 bg-emerald-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Bot className="w-3.5 h-3.5" />
          <span>Agent Activity ({agentExecutions.length})</span>
        </button>

        {/* Phase 4 Tab */}
        <button
          onClick={() => setActiveTab("remediation")}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === "remediation"
              ? "border-rose-500 text-rose-400 bg-rose-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <BrainCircuit className="w-3.5 h-3.5 text-rose-400" />
          <span>Self-Healing &amp; Remediation ({remediationActions.length})</span>
        </button>
      </div>

      {/* Tab 1: Executive Summary & Postmortem */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Culprit Verdict Card */}
            <div className="p-5 rounded-xl border border-slate-800 bg-[#0e1424] space-y-3 md:col-span-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-300 flex items-center gap-2">
                  <Gavel className="w-4 h-4 text-purple-400" />
                  <span>Autonomous Judicial Ruling</span>
                </h3>
                {topHypothesis && (
                  <span
                    className={`text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full border ${
                      topHypothesis.status === "VALIDATED"
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                        : topHypothesis.status === "INSUFFICIENT_EVIDENCE"
                        ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                        : "bg-purple-500/10 text-purple-400 border-purple-500/30"
                    }`}
                  >
                    {topHypothesis.status}
                  </span>
                )}
              </div>

              {topHypothesis ? (
                <div className="space-y-3">
                  <div className="p-3.5 rounded-lg border border-purple-500/20 bg-purple-950/10 space-y-2">
                    <div className="text-xs font-mono text-purple-300 font-bold">
                      Leading Hypothesis:
                    </div>
                    <div className="text-sm font-semibold text-white">
                      {topHypothesis.hypothesis_text}
                    </div>
                    <div className="flex items-center gap-4 text-xs font-mono text-slate-400 pt-1">
                      <span>
                        Confidence:{" "}
                        <strong className="text-white">
                          {(topHypothesis.probability_score * 100).toFixed(1)}%
                        </strong>
                      </span>
                      <span>
                        Exhibits:{" "}
                        <strong className="text-emerald-400">
                          {topHypothesis.evidence_count || 0} supporting
                        </strong>
                        {" / "}
                        <strong className="text-red-400">
                          {topHypothesis.contradiction_count || 0} contradicting
                        </strong>
                      </span>
                    </div>
                  </div>

                  {topHypothesis.judicial_ruling && (
                    <div className="text-xs font-sans text-slate-300 bg-slate-900/60 p-3 rounded-lg border border-slate-800 leading-relaxed">
                      <strong className="text-slate-200 font-mono text-[11px] block mb-1">
                        JUDICIAL OPINION &amp; EVIDENCE EVALUATION:
                      </strong>
                      {topHypothesis.judicial_ruling}
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-8 text-center text-xs font-mono text-slate-500 space-y-2">
                  <AlertTriangle className="w-6 h-6 text-slate-600 mx-auto" />
                  <div>No investigation has been executed for this incident yet.</div>
                  <button
                    onClick={handleTriggerInvestigation}
                    disabled={investigating}
                    className="px-3 py-1 rounded bg-purple-600 text-white text-xs hover:bg-purple-500 font-mono"
                  >
                    Trigger 10-Agent Investigation
                  </button>
                </div>
              )}
            </div>

            {/* Quick Metrics */}
            <div className="p-5 rounded-xl border border-slate-800 bg-[#0e1424] space-y-4">
              <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-300">
                Incident Telemetry Scope
              </h3>
              <div className="space-y-3 text-xs font-mono">
                <div className="flex justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-400">Identified Impact:</span>
                  <span className="text-blue-400 font-bold">{incident.impact_scope || "Distributed"}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-400">Reconstructed Events:</span>
                  <span className="text-cyan-400 font-bold">{timelineEvents.length}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-400">Evidence Exhibits:</span>
                  <span className="text-amber-400 font-bold">{evidence.length}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-400">Remediation Actions:</span>
                  <span className="text-rose-400 font-bold">{remediationActions.length} Formulated</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-800">
                  <span className="text-slate-400">Autonomous Agents:</span>
                  <span className="text-purple-400 font-bold">{agentExecutions.length} ran</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Root Cause Courtroom */}
      {activeTab === "courtroom" && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl border border-purple-500/20 bg-purple-950/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <Scale className="w-4 h-4 text-purple-400" />
                Root Cause Courtroom: Adversarial Evidence Evaluation
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Hypotheses are subjected to prosecution and defense cross-examination. Hypotheses with insufficient evidence receive a formal non liquet ruling.
              </p>
            </div>
            <div className="text-xs font-mono text-purple-300 font-bold bg-purple-900/30 px-3 py-1.5 rounded-lg border border-purple-500/30 whitespace-nowrap">
              Testable Confidence: W_supp / (W_supp + W_contra + gap_pen)
            </div>
          </div>

          {hypotheses.length === 0 ? (
            <div className="p-12 text-center text-xs font-mono text-slate-400 border border-slate-800 rounded-xl bg-[#0e1424] space-y-3">
              <Brain className="w-10 h-10 text-purple-400 mx-auto opacity-70" />
              <p className="font-bold text-slate-200">No Causal Hypotheses Filed Yet</p>
              <p className="max-w-md mx-auto text-slate-400">
                Run the autonomous investigation to analyze telemetry, logs, traces, and dependency topology to construct adversarial hypotheses.
              </p>
              <button
                onClick={handleTriggerInvestigation}
                disabled={investigating}
                className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-mono text-xs font-bold"
              >
                {investigating ? "Evaluating Exhibits..." : "Launch Courtroom Investigation"}
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {hypotheses.map((hyp, index) => {
                const supporting = evidence.filter(
                  (e) => !e.is_contradictory && (e.hypothesis_id === hyp.id || hyp.culprit_service_id)
                );
                const contradictory = evidence.filter((e) => e.is_contradictory);

                return (
                  <div
                    key={hyp.id}
                    className="p-6 rounded-2xl border border-slate-800 bg-[#0e1424] shadow-sm space-y-5"
                  >
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-4">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-mono font-bold text-slate-400">
                            Hypothesis #{index + 1}
                          </span>
                          <span
                            className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded-md border ${
                              hyp.status === "VALIDATED"
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                                : hyp.status === "INSUFFICIENT_EVIDENCE"
                                ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                                : hyp.status === "DISPROVEN"
                                ? "bg-red-500/10 text-red-400 border-red-500/30"
                                : "bg-purple-500/10 text-purple-400 border-purple-500/30"
                            }`}
                          >
                            {hyp.status}
                          </span>
                          {hyp.is_confirmed_root_cause && (
                            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                              PROBABLE ROOT CAUSE
                            </span>
                          )}
                        </div>
                        <h3 className="text-base font-bold text-white">{hyp.hypothesis_text}</h3>
                      </div>

                      {/* Confidence Score Gauge */}
                      <div className="flex items-center space-x-3 bg-slate-900 p-2.5 rounded-xl border border-slate-800">
                        <div className="text-right">
                          <div className="text-[10px] font-mono text-slate-400">Confidence Score</div>
                          <div className="text-base font-mono font-extrabold text-white">
                            {(hyp.probability_score * 100).toFixed(1)}%
                          </div>
                        </div>
                        <div className="w-12 h-12 rounded-full border-2 border-purple-500/30 flex items-center justify-center font-mono text-xs font-bold text-purple-300">
                          {Math.round(hyp.probability_score * 100)}
                        </div>
                      </div>
                    </div>

                    {/* Causal Chain Visualization */}
                    {hyp.causal_chain && (
                      <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/60 space-y-1.5">
                        <div className="text-[10px] font-mono font-bold uppercase text-slate-400 flex items-center gap-1.5">
                          <Network className="w-3.5 h-3.5 text-blue-400" />
                          <span>Reconstructed Causal Chain (Correlation &ne; Causation)</span>
                        </div>
                        <div className="text-xs font-mono text-blue-300 bg-[#080d1a] p-2 rounded border border-blue-950 overflow-x-auto whitespace-pre-wrap">
                          {hyp.causal_chain}
                        </div>
                      </div>
                    )}

                    {/* Prosecutor vs Defense Arguments */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Prosecutor Argument */}
                      <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-950/10 space-y-2">
                        <div className="flex items-center space-x-2 text-xs font-mono font-bold text-emerald-400">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Prosecution Argument (Why this is guilty)</span>
                        </div>
                        <p className="text-xs text-slate-300 font-sans leading-relaxed">
                          {hyp.prosecutor_argument || "Direct telemetry and traces correlate with observed fault patterns."}
                        </p>
                      </div>

                      {/* Defense Argument */}
                      <div className="p-4 rounded-xl border border-red-500/20 bg-red-950/10 space-y-2">
                        <div className="flex items-center space-x-2 text-xs font-mono font-bold text-red-400">
                          <ShieldAlert className="w-4 h-4" />
                          <span>Defense Argument (Alternative explanations &amp; Mitigations)</span>
                        </div>
                        <p className="text-xs text-slate-300 font-sans leading-relaxed">
                          {hyp.defense_argument || "Telemetry could be a secondary cascade symptom rather than primary root cause."}
                        </p>
                      </div>
                    </div>

                    {/* Exhibits: Supporting vs Contradictory Evidence */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Supporting Exhibits */}
                      <div className="space-y-2">
                        <div className="text-xs font-mono font-bold text-slate-300 flex items-center gap-1.5">
                          <FileText className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Supporting Exhibits ({supporting.length})</span>
                        </div>
                        {supporting.length === 0 ? (
                          <div className="text-xs font-mono text-slate-500 p-3 rounded border border-slate-800 bg-slate-900/30">
                            No verified supporting exhibits linked.
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {supporting.slice(0, 3).map((e) => (
                              <div
                                key={e.id}
                                className="p-2.5 rounded-lg border border-slate-800 bg-slate-900/40 text-xs font-mono space-y-1"
                              >
                                <div className="flex justify-between text-[10px] text-slate-400">
                                  <span className="text-emerald-400 font-bold">{e.evidence_type}</span>
                                  <span>{e.source_system} &bull; {(e.confidence_score * 100).toFixed(0)}% conf</span>
                                </div>
                                <div className="text-slate-200">{e.description}</div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Contradictory Exhibits */}
                      <div className="space-y-2">
                        <div className="text-xs font-mono font-bold text-slate-300 flex items-center gap-1.5">
                          <XCircle className="w-3.5 h-3.5 text-red-400" />
                          <span>Contradictory / Exonerating Exhibits ({contradictory.length})</span>
                        </div>
                        {contradictory.length === 0 ? (
                          <div className="text-xs font-mono text-slate-500 p-3 rounded border border-slate-800 bg-slate-900/30">
                            No contradicting telemetry observed.
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {contradictory.slice(0, 3).map((e) => (
                              <div
                                key={e.id}
                                className="p-2.5 rounded-lg border border-red-950/40 bg-red-950/10 text-xs font-mono space-y-1"
                              >
                                <div className="flex justify-between text-[10px] text-slate-400">
                                  <span className="text-red-400 font-bold">{e.evidence_type}</span>
                                  <span>{e.source_system} &bull; Contradicts</span>
                                </div>
                                <div className="text-slate-300">{e.description}</div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Missing Evidence / Information Gaps */}
                    {hyp.missing_evidence && (
                      <div className="p-3 rounded-lg border border-amber-500/20 bg-amber-950/10 text-xs space-y-1">
                        <div className="font-mono font-bold text-amber-300 flex items-center gap-1.5 text-[11px]">
                          <Info className="w-3.5 h-3.5" />
                          <span>Information Gaps (Missing Evidence to Reach Conclusive Proof):</span>
                        </div>
                        <div className="font-sans text-slate-300 leading-relaxed">
                          {hyp.missing_evidence}
                        </div>
                      </div>
                    )}

                    {/* Judicial Ruling */}
                    {hyp.judicial_ruling && (
                      <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/80 text-xs font-mono space-y-1">
                        <div className="text-purple-300 font-bold text-[10px] uppercase">
                          Courtroom Verdict &amp; Rationale:
                        </div>
                        <div className="text-slate-300 font-sans leading-relaxed">
                          {hyp.judicial_ruling}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Incident Time Machine */}
      {activeTab === "timeline" && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 rounded-xl border border-cyan-500/20 bg-cyan-950/10">
            <div>
              <h2 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <History className="w-4 h-4 text-cyan-400" />
                Incident Time Machine: Chronological Telemetry Scrubber
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Reconstructs the full sequence of anomalies, stack traces, spans, and topology shifts.
              </p>
            </div>

            {/* Filter by Service */}
            <div className="flex items-center space-x-2 text-xs font-mono">
              <span className="text-slate-400">Service:</span>
              <select
                value={timelineServiceFilter}
                onChange={(e) => setTimelineServiceFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-slate-200 text-xs font-mono"
              >
                <option value="ALL">All Services ({timelineEvents.length})</option>
                {Array.from(new Set(timelineEvents.map((e) => e.service_name))).map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {timelineEvents.length === 0 ? (
            <div className="p-12 text-center text-xs font-mono text-slate-400 border border-slate-800 rounded-xl bg-[#0e1424] space-y-3">
              <History className="w-10 h-10 text-cyan-400 mx-auto opacity-70" />
              <p className="font-bold text-slate-200">No Timeline Events Reconstructed</p>
              <p className="max-w-md mx-auto text-slate-400">
                Trigger autonomous investigation to assemble chronological telemetry and log records.
              </p>
            </div>
          ) : (
            <div className="relative border-l border-slate-800 ml-4 pl-6 space-y-6">
              {timelineEvents
                .filter(
                  (e) => timelineServiceFilter === "ALL" || e.service_name === timelineServiceFilter
                )
                .map((event, idx) => (
                  <div key={event.id || idx} className="relative group">
                    {/* Circle Node on Timeline */}
                    <div
                      className={`absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full border-2 bg-slate-950 ${
                        event.severity === "CRITICAL" || event.event_type === "INCIDENT_DETECTED"
                          ? "border-red-500 bg-red-500/20"
                          : event.severity === "WARN"
                          ? "border-amber-500 bg-amber-500/20"
                          : "border-cyan-500 bg-cyan-500/20"
                      }`}
                    />

                    {/* Event Card */}
                    <div className="p-4 rounded-xl border border-slate-800 bg-[#0e1424] hover:border-slate-700 transition-all space-y-2">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 text-xs font-mono">
                        <div className="flex items-center space-x-2">
                          <span className="text-cyan-400 font-bold px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20">
                            {event.event_type}
                          </span>
                          <span className="text-slate-300 font-semibold">{event.service_name}</span>
                          <span
                            className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                              event.severity === "CRITICAL"
                                ? "text-red-400"
                                : event.severity === "WARN"
                                ? "text-amber-400"
                                : "text-blue-400"
                            }`}
                          >
                            {event.severity}
                          </span>
                        </div>
                        <div className="text-slate-400 text-[11px]">
                          {new Date(event.timestamp).toLocaleTimeString()} ({new Date(event.timestamp).toLocaleDateString()})
                        </div>
                      </div>

                      <div className="text-sm font-semibold text-white">{event.title}</div>
                      <div className="text-xs text-slate-300 font-sans leading-relaxed">
                        {event.description}
                      </div>

                      {event.raw_data && (
                        <div className="pt-2">
                          <button
                            onClick={() =>
                              setSelectedRawPayload({
                                title: `${event.event_type} - ${event.service_name}`,
                                json: event.raw_data || "{}",
                              })
                            }
                            className="text-[11px] font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
                          >
                            <Code2 className="w-3 h-3" />
                            <span>Inspect Raw Telemetry Payload</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Evidence Locker */}
      {activeTab === "evidence" && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 rounded-xl border border-amber-500/20 bg-amber-950/10">
            <div>
              <h2 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <FileText className="w-4 h-4 text-amber-400" />
                Evidence Locker &amp; Provenance Chain
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Every exhibit tracks source system, affected service, raw reference, and verification status.
              </p>
            </div>

            <div className="flex items-center space-x-2 text-xs font-mono">
              <span className="text-slate-400">Filter:</span>
              <select
                value={evidenceFilter}
                onChange={(e) => setEvidenceFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-slate-200 text-xs font-mono"
              >
                <option value="ALL">All Exhibits ({evidence.length})</option>
                <option value="METRIC">Metrics</option>
                <option value="LOG">Logs</option>
                <option value="TRACE">Traces</option>
                <option value="DEPENDENCY">Dependencies</option>
                <option value="CONFIG">Deployments / Config</option>
                <option value="CONTRADICTION">Contradictory Only</option>
              </select>
            </div>
          </div>

          {evidence.length === 0 ? (
            <div className="p-12 text-center text-xs font-mono text-slate-400 border border-slate-800 rounded-xl bg-[#0e1424] space-y-3">
              <FileText className="w-10 h-10 text-amber-400 mx-auto opacity-70" />
              <p className="font-bold text-slate-200">No Evidence Filed</p>
              <p className="max-w-md mx-auto text-slate-400">
                Run autonomous investigation to collect and verify exhibits.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {evidence
                .filter((e) => {
                  if (evidenceFilter === "ALL") return true;
                  if (evidenceFilter === "CONTRADICTION") return e.is_contradictory;
                  return e.evidence_type.toUpperCase().includes(evidenceFilter);
                })
                .map((item) => (
                  <div
                    key={item.id}
                    className="p-4 rounded-xl border border-slate-800 bg-[#0e1424] space-y-3 flex flex-col justify-between"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-[11px] font-mono">
                        <span
                          className={`font-bold px-2 py-0.5 rounded border ${
                            item.is_contradictory
                              ? "bg-red-500/10 text-red-400 border-red-500/30"
                              : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                          }`}
                        >
                          {item.evidence_type}
                        </span>
                        <span className="text-slate-400">{item.source_system}</span>
                      </div>

                      <div className="text-xs text-slate-200 font-sans leading-relaxed">
                        {item.description}
                      </div>

                      {item.relevant_observation && (
                        <div className="text-[11px] font-mono text-slate-400 bg-slate-900/80 p-2 rounded border border-slate-800">
                          {item.relevant_observation}
                        </div>
                      )}
                    </div>

                    <div className="pt-2 border-t border-slate-800/80 text-[10px] font-mono text-slate-400 flex items-center justify-between">
                      <div>
                        Provenance:{" "}
                        <code className="text-blue-400">
                          {item.raw_source_ref || item.affected_service_name || "cluster-telemetry"}
                        </code>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-emerald-400 font-bold">
                          {(item.confidence_score * 100).toFixed(0)}% Conf
                        </span>
                        {item.raw_data && (
                          <button
                            onClick={() =>
                              setSelectedRawPayload({
                                title: `Exhibit: ${item.evidence_type} (${item.source_system})`,
                                json: item.raw_data || "{}",
                              })
                            }
                            className="text-amber-400 hover:text-amber-300"
                          >
                            Raw Data
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Active Investigation Planner */}
      {activeTab === "planner" && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl border border-indigo-500/20 bg-indigo-950/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <Compass className="w-4 h-4 text-indigo-400" />
                Active Investigation Planner (Diagnostic Action Prioritizer)
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Generates safe, high-value diagnostic actions. Destructive operations are strictly prohibited.
              </p>
            </div>
            <div className="text-xs font-mono text-indigo-300 font-bold bg-indigo-900/30 px-3 py-1.5 rounded-lg border border-indigo-500/30">
              Safety Constraint: ZERO DESTRUCTIVE COMMANDS
            </div>
          </div>

          {!planner || planner.recommended_actions.length === 0 ? (
            <div className="p-12 text-center text-xs font-mono text-slate-400 border border-slate-800 rounded-xl bg-[#0e1424] space-y-3">
              <Compass className="w-10 h-10 text-indigo-400 mx-auto opacity-70" />
              <p className="font-bold text-slate-200">No Diagnostic Actions Formulated</p>
              <p className="max-w-md mx-auto text-slate-400">
                Run the autonomous investigation pipeline to synthesize safe diagnostic probes.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {planner.recommended_actions.map((act, idx) => (
                <div
                  key={act.action_id || idx}
                  className="p-5 rounded-xl border border-slate-800 bg-[#0e1424] space-y-4"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-800 pb-3">
                    <div className="flex items-center space-x-3">
                      <span className="text-xs font-mono font-bold text-indigo-400">
                        Action #{idx + 1}
                      </span>
                      <h3 className="text-sm font-bold text-white font-mono">{act.name}</h3>
                      <span className="text-xs font-mono text-slate-400">
                        &bull; Target: <strong className="text-slate-200">{act.target_service}</strong>
                      </span>
                    </div>

                    <div className="flex items-center space-x-2 text-xs font-mono">
                      <span
                        className={`px-2.5 py-0.5 rounded-full font-bold border ${
                          (act.safety_rating === "SAFE" || act.operational_risk === "LOW")
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                            : act.safety_rating === "RESTRICTED"
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                            : "bg-red-500/10 text-red-400 border-red-500/30"
                        }`}
                      >
                        {act.safety_rating || (act.operational_risk === "LOW" ? "SAFE" : act.operational_risk) || "SAFE"}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                        {act.category || act.command_type || "READ_ONLY"}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 space-y-1">
                      <span className="text-[10px] text-slate-400 uppercase font-bold">Diagnostic Value:</span>
                      <p className="text-indigo-300 font-semibold">
                        {act.value_estimate || (act.diagnostic_value ? `${(act.diagnostic_value * 100).toFixed(0)}% Information Gain` : "HIGH")}
                      </p>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 space-y-1">
                      <span className="text-[10px] text-slate-400 uppercase font-bold">Cost / Overhead:</span>
                      <p className="text-slate-300">{act.estimated_cost}</p>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 space-y-1">
                      <span className="text-[10px] text-slate-400 uppercase font-bold">Safety Assessment:</span>
                      <p className="text-slate-300">
                        {act.risk_explanation || act.rationale || "Zero destructive commands permitted. Verified non-invasive read probe."}
                      </p>
                    </div>
                  </div>

                  <div className="space-y-1 text-xs font-mono">
                    <div className="text-[10px] text-slate-400 uppercase font-bold flex items-center gap-1.5">
                      <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Recommended Non-Destructive Inspection Command:</span>
                    </div>
                    <pre className="p-3 rounded-lg bg-[#080d1a] border border-slate-800 text-emerald-400 overflow-x-auto text-xs">
                      <code>
                        {act.command_template ||
                          (act.target_service === "postgres-db"
                            ? `psql -h postgres-db -U postgres -d incidentx_demo -c "SELECT pid, query, state, age(clock_timestamp(), query_start) FROM pg_stat_activity WHERE state != 'idle';"`
                            : act.target_service === "payment-service"
                            ? `curl -s -w "\\nTime Total: %{time_total}s\\n" http://payment-service:8080/health`
                            : `curl -s http://${act.target_service}:8080/metrics | grep -E "requests_total|latency"`)}
                      </code>
                    </pre>
                  </div>

                  {(act.justification || act.rationale) && (
                    <div className="text-xs text-slate-400 font-sans leading-relaxed">
                      <strong className="font-mono text-slate-300">Justification: </strong>
                      {act.justification || act.rationale}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 6: Agent Activity */}
      {activeTab === "agents" && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-950/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <Bot className="w-4 h-4 text-emerald-400" />
                Autonomous Agent Execution Ledger
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Full transparency into each agent’s execution latency, model version, and reasoning artifacts.
              </p>
            </div>
            <div className="text-xs font-mono text-emerald-300 font-bold bg-emerald-900/30 px-3 py-1.5 rounded-lg border border-emerald-500/30">
              Deterministic Mode Transparency Enabled
            </div>
          </div>

          {agentExecutions.length === 0 ? (
            <div className="p-12 text-center text-xs font-mono text-slate-400 border border-slate-800 rounded-xl bg-[#0e1424] space-y-3">
              <Bot className="w-10 h-10 text-emerald-400 mx-auto opacity-70" />
              <p className="font-bold text-slate-200">No Agent Executions Recorded</p>
              <p className="max-w-md mx-auto text-slate-400">
                Trigger investigation to dispatch the 10-agent orchestration sequence.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {agentExecutions.map((agent) => (
                <div
                  key={agent.id}
                  className="p-5 rounded-xl border border-slate-800 bg-[#0e1424] space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-800 pb-3">
                    <div className="flex items-center space-x-2">
                      <Bot className="w-4 h-4 text-purple-400" />
                      <span className="text-sm font-bold font-mono text-white">
                        {agent.agent_role}
                      </span>
                      <span className="text-xs font-mono text-slate-400">
                        ({agent.execution_phase})
                      </span>
                    </div>

                    <div className="flex items-center space-x-3 text-xs font-mono">
                      <span className="text-slate-400">
                        Duration:{" "}
                        <strong className="text-slate-200">{agent.duration_ms || 0}ms</strong>
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          agent.status === "COMPLETED"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                            : "bg-red-500/10 text-red-400 border-red-500/30"
                        }`}
                      >
                        {agent.status}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono text-slate-400">
                    <div>
                      Engine:{" "}
                      <code className="text-indigo-300">
                        {agent.model_version || "incidentx-deterministic-v1"}
                      </code>
                    </div>
                    <div>
                      Prompt Version:{" "}
                      <code className="text-indigo-300">{agent.prompt_version || "v3.0.0"}</code>
                    </div>
                  </div>

                  {agent.thought_process && (
                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs font-mono text-slate-300 space-y-1">
                      <div className="text-[10px] font-bold uppercase text-purple-300">
                        Reasoning Strategy / Plan:
                      </div>
                      <p className="leading-relaxed whitespace-pre-wrap">{agent.thought_process}</p>
                    </div>
                  )}

                  {agent.observation && (
                    <div className="p-3 rounded-lg bg-[#080d1a] border border-slate-800/80 text-xs font-mono text-emerald-300 space-y-1">
                      <div className="text-[10px] font-bold uppercase text-emerald-400">
                        Agent Observation / Conclusion:
                      </div>
                      <p className="leading-relaxed whitespace-pre-wrap">{agent.observation}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 7: Self-Healing & Remediation (Phase 4) */}
      {activeTab === "remediation" && (
        <div className="space-y-6">
          {/* Remediation Safety Status Banner */}
          <div className="p-5 rounded-2xl border border-slate-800 bg-[#0e1424] space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-3">
                <BrainCircuit className="w-5 h-5 text-rose-400" />
                <div>
                  <h2 className="text-sm font-bold text-white font-mono">
                    Autonomous Self-Healing &amp; Remediation Center
                  </h2>
                  <p className="text-xs text-slate-400">
                    Evidence-grounded action recommendations. No action executes without safety validation.
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2 text-xs font-mono">
                <span className="text-slate-400">Safety Policy:</span>
                <span className="px-2.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-bold">
                  {remediationPolicy?.mode || "RECOMMENDATION_ONLY"}
                </span>
                <button
                  onClick={handleGenerateRecommendations}
                  disabled={actionOperating}
                  className="px-3 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold transition-colors disabled:opacity-50"
                >
                  {remediationActions.length === 0 ? "Formulate Actions" : "Re-Formulate Actions"}
                </button>
              </div>
            </div>

            <div className="text-[11px] font-mono text-slate-400 flex items-center gap-2">
              <Info className="w-4 h-4 text-blue-400 shrink-0" />
              <span>
                <strong>Zero-Hallucination Policy:</strong> A recommendation is never treated as proof that the root cause is correct. Execution is restricted to pre-validated registry actions in the isolated simulation sandbox.
              </span>
            </div>
          </div>

          {/* Remediation Actions List */}
          {remediationActions.length === 0 ? (
            <div className="p-12 text-center text-xs font-mono text-slate-400 border border-slate-800 rounded-xl bg-[#0e1424] space-y-3">
              <BrainCircuit className="w-10 h-10 text-rose-400 mx-auto opacity-70" />
              <p className="font-bold text-slate-200">No Remediation Actions Formulated Yet</p>
              <p className="max-w-md mx-auto text-slate-400">
                Click below to synthesize evidence-backed recovery recommendations for this incident.
              </p>
              <button
                onClick={handleGenerateRecommendations}
                disabled={actionOperating}
                className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-mono text-xs font-bold"
              >
                {actionOperating ? "Synthesizing Actions..." : "Synthesize Remediation Actions"}
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {remediationActions.map((act, idx) => {
                const contraList = (() => {
                  try {
                    return JSON.parse(act.contraindications || "[]");
                  } catch {
                    return [];
                  }
                })();

                return (
                  <div
                    key={act.id}
                    className="p-6 rounded-2xl border border-slate-800 bg-[#0e1424] shadow-sm space-y-5"
                  >
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-3">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-mono font-bold text-slate-400">
                            Rank #{idx + 1} &bull; <code className="text-indigo-400">{act.action_id}</code>
                          </span>
                          <span
                            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                              act.risk_level === "LOW"
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                                : act.risk_level === "MEDIUM"
                                ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                                : "bg-red-500/10 text-red-400 border-red-500/30"
                            }`}
                          >
                            {act.risk_level} RISK
                          </span>
                          <span
                            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                              act.status === "EXECUTED"
                                ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                                : act.status === "APPROVED"
                                ? "bg-blue-500/20 text-blue-300 border-blue-500/40"
                                : act.status === "FAILED"
                                ? "bg-red-500/20 text-red-300 border-red-500/40"
                                : "bg-slate-800 text-slate-400 border-slate-700"
                            }`}
                          >
                            STATUS: {act.status}
                          </span>
                        </div>
                        <h3 className="text-base font-bold text-white font-mono">{act.name}</h3>
                        <div className="text-xs font-mono text-slate-400">
                          Target Service: <strong className="text-slate-200">{act.target_service_name}</strong> &bull; Timeout: {act.timeout_seconds}s
                        </div>
                      </div>

                      {/* Benefit Score Gauge */}
                      <div className="flex items-center space-x-3 bg-slate-900 p-2.5 rounded-xl border border-slate-800">
                        <div className="text-right">
                          <div className="text-[10px] font-mono text-slate-400">Expected Benefit</div>
                          <div className="text-base font-mono font-extrabold text-rose-300">
                            {Math.round(act.expected_benefit * 100)}%
                          </div>
                        </div>
                        <div className="w-12 h-12 rounded-full border-2 border-rose-500/30 flex items-center justify-center font-mono text-xs font-bold text-rose-300">
                          {Math.round(act.expected_benefit * 100)}
                        </div>
                      </div>
                    </div>

                    {/* Recommendation Reason (Evidence Grounded) */}
                    <div className="p-3 rounded-lg border border-indigo-500/20 bg-indigo-950/10 space-y-1 text-xs">
                      <div className="font-mono font-bold text-indigo-300 flex items-center gap-1.5 text-[11px]">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Why This Action Is Recommended (Empirical Telemetry Grounding):</span>
                      </div>
                      <p className="text-slate-300 font-sans leading-relaxed">
                        {act.recommendation_reason}
                      </p>
                    </div>

                    {/* Contraindications Callout */}
                    {contraList.length > 0 && (
                      <div className="p-3 rounded-lg border border-red-500/20 bg-red-950/10 space-y-1.5 text-xs">
                        <div className="font-mono font-bold text-red-400 flex items-center gap-1.5 text-[11px]">
                          <XCircle className="w-3.5 h-3.5" />
                          <span>Contraindications (Actions that MUST NOT be attempted for this incident):</span>
                        </div>
                        <ul className="list-disc pl-5 text-slate-300 space-y-1 font-sans text-xs">
                          {contraList.map((c: string, i: number) => (
                            <li key={i}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Verification Result Pill (If Executed) */}
                    {act.verification_status !== "PENDING" && (
                      <div
                        className={`p-3.5 rounded-lg border flex items-center justify-between text-xs font-mono ${
                          act.verification_status === "VERIFIED"
                            ? "bg-emerald-950/20 border-emerald-500/40 text-emerald-300"
                            : act.verification_status === "PARTIALLY_VERIFIED"
                            ? "bg-amber-950/20 border-amber-500/40 text-amber-300"
                            : "bg-red-950/20 border-red-500/40 text-red-300"
                        }`}
                      >
                        <div className="flex items-center space-x-2">
                          {act.verification_status === "VERIFIED" ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          ) : (
                            <AlertTriangle className="w-4 h-4 text-amber-400" />
                          )}
                          <div>
                            <span className="font-bold">Recovery Verification: {act.verification_status}</span>
                            <span className="text-[11px] block opacity-80">
                              Duration: {act.execution_duration_ms || 0}ms &bull; Rollback Status: {act.rollback_status}
                            </span>
                          </div>
                        </div>

                        <button
                          onClick={() => setVerificationModalAction(act)}
                          className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-white text-[11px] hover:bg-slate-800"
                        >
                          View Delta Telemetry
                        </button>
                      </div>
                    )}

                    {/* Action Controls & Approval Workflow */}
                    <div className="pt-2 border-t border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs font-mono">
                      <div className="text-slate-400">
                        {act.approval_status === "APPROVED" ? (
                          <span className="text-emerald-400 flex items-center gap-1">
                            <UserCheck className="w-3.5 h-3.5" />
                            <span>Approved by {act.approved_by}</span>
                          </span>
                        ) : act.approval_status === "REJECTED" ? (
                          <span className="text-red-400">Rejected by operator</span>
                        ) : (
                          <span>Approval Status: <strong>{act.approval_status}</strong></span>
                        )}
                      </div>

                      <div className="flex items-center space-x-2">
                        {act.status === "PROPOSED" && (
                          <>
                            <button
                              onClick={() => setApprovalModalAction(act)}
                              disabled={actionOperating}
                              className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition-all"
                            >
                              Approve Action
                            </button>
                            <button
                              onClick={() => handleRejectAction(act)}
                              disabled={actionOperating}
                              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold transition-all border border-slate-700"
                            >
                              Reject
                            </button>
                          </>
                        )}

                        {act.status === "APPROVED" && (
                          <button
                            onClick={() => handleExecuteAction(act)}
                            disabled={actionOperating}
                            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold shadow-md shadow-emerald-950/40 transition-all"
                          >
                            <Play className="w-3 h-3 fill-white" />
                            <span>Execute in Simulation</span>
                          </button>
                        )}

                        {act.status === "EXECUTED" && act.rollback_status === "AVAILABLE" && (
                          <button
                            onClick={() => handleRollbackAction(act)}
                            disabled={actionOperating}
                            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-600/80 hover:bg-amber-600 text-white font-bold transition-all"
                          >
                            <RotateCcw className="w-3 h-3" />
                            <span>Rollback Action</span>
                          </button>
                        )}

                        {act.status === "FAILED" && (
                          <span className="text-red-400 text-[11px] font-bold">
                            {act.rollback_status === "ROLLED_BACK" ? "ROLLED BACK SAFELY" : "EXECUTION FAILED"}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Approval Modal */}
          {approvalModalAction && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
              <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-[#0c1220] p-6 shadow-2xl space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center space-x-2 text-sm font-mono font-bold text-white">
                    <UserCheck className="w-4 h-4 text-indigo-400" />
                    <span>Human Approval Gate &bull; {approvalModalAction.action_id}</span>
                  </div>
                  <button
                    onClick={() => setApprovalModalAction(null)}
                    className="text-xs font-mono text-slate-400 hover:text-white"
                  >
                    &times;
                  </button>
                </div>

                <div className="space-y-3 text-xs font-mono">
                  <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                    <div className="text-white font-bold">{approvalModalAction.name}</div>
                    <div className="text-slate-400">Target: {approvalModalAction.target_service_name} &bull; Risk: {approvalModalAction.risk_level}</div>
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] text-slate-400">Operator Sign-off Identity:</label>
                    <input
                      type="text"
                      value={approvalOperatorName}
                      onChange={(e) => setApprovalOperatorName(e.target.value)}
                      className="w-full bg-[#080d1a] border border-slate-800 rounded p-2 text-slate-200 text-xs font-mono"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] text-slate-400">Justification / Safety Comments:</label>
                    <textarea
                      value={approvalComment}
                      onChange={(e) => setApprovalComment(e.target.value)}
                      rows={2}
                      placeholder="e.g. Verified target service telemetry. Safe to restart in local simulation."
                      className="w-full bg-[#080d1a] border border-slate-800 rounded p-2 text-slate-200 text-xs font-mono"
                    />
                  </div>
                </div>

                <div className="flex justify-end space-x-2 pt-2 border-t border-slate-800">
                  <button
                    onClick={() => setApprovalModalAction(null)}
                    className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 text-xs font-mono"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleApproveAction}
                    disabled={actionOperating || !approvalOperatorName}
                    className="px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-bold"
                  >
                    Confirm Approval
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Verification Report Delta Inspector Modal */}
          {verificationModalAction && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
              <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-[#0c1220] p-6 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center space-x-2 text-sm font-mono font-bold text-white">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>Recovery Verification Report &bull; {verificationModalAction.action_id}</span>
                  </div>
                  <button
                    onClick={() => setVerificationModalAction(null)}
                    className="text-xs font-mono text-slate-400 hover:text-white"
                  >
                    &times;
                  </button>
                </div>

                <div className="flex-1 overflow-auto space-y-4 font-mono text-xs text-slate-300">
                  <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-950/20 space-y-1">
                    <div className="font-bold text-emerald-400">
                      EMPIRICAL OUTCOME: {verificationModalAction.verification_status}
                    </div>
                    <p className="text-[11px] text-slate-300 font-sans">
                      Independent verification evaluated fresh telemetry snapshots after execution.
                    </p>
                  </div>

                  {verificationModalAction.verification_details && (
                    <div className="space-y-2">
                      <span className="text-[11px] font-bold uppercase text-slate-400">Detailed Telemetry Delta:</span>
                      <pre className="p-4 rounded-xl bg-[#060a12] border border-slate-900 text-emerald-300 overflow-x-auto text-xs">
                        <code>
                          {JSON.stringify(JSON.parse(verificationModalAction.verification_details), null, 2)}
                        </code>
                      </pre>
                    </div>
                  )}

                  {verificationModalAction.execution_log && (
                    <div className="space-y-2">
                      <span className="text-[11px] font-bold uppercase text-slate-400">Execution Log:</span>
                      <pre className="p-3 rounded-lg bg-[#060a12] border border-slate-900 text-slate-400 overflow-x-auto text-xs whitespace-pre-wrap">
                        <code>{verificationModalAction.execution_log}</code>
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Raw Payload Inspector Modal */}
      {selectedRawPayload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-3xl rounded-2xl border border-slate-800 bg-[#0c1220] p-6 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2 text-sm font-mono font-bold text-white">
                <Code2 className="w-4 h-4 text-cyan-400" />
                <span>{selectedRawPayload.title}</span>
              </div>
              <button
                onClick={() => setSelectedRawPayload(null)}
                className="text-xs font-mono text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-900 border border-slate-800"
              >
                Close &times;
              </button>
            </div>

            <div className="flex-1 overflow-auto bg-[#060a12] p-4 rounded-xl border border-slate-900 font-mono text-xs text-slate-300">
              <pre>
                <code>
                  {(() => {
                    try {
                      return JSON.stringify(JSON.parse(selectedRawPayload.json), null, 2);
                    } catch {
                      return selectedRawPayload.json;
                    }
                  })()}
                </code>
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
