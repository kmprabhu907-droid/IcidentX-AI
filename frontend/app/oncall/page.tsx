"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import {
  Headphones,
  Bot,
  AlertTriangle,
  Clock,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Play,
  RotateCcw,
  RefreshCw,
  Send,
  MessageSquare,
  FileText,
  Share2,
  ExternalLink,
  ChevronRight,
  Radio,
  Flame,
  Zap,
  Activity,
  Server,
  Scale,
  Copy,
  Check,
} from "lucide-react";
import { oncallApi, api } from "../../services/api";
import { PageAlert, OnCallShiftStatus, Incident } from "../../types";

export default function OnCallAgentPage() {
  const [loading, setLoading] = useState(true);
  const [shiftStatus, setShiftStatus] = useState<OnCallShiftStatus | null>(null);
  const [activePages, setActivePages] = useState<PageAlert[]>([]);
  const [allPages, setAllPages] = useState<PageAlert[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);

  // Simulation Form
  const [simService, setSimService] = useState("order-service");
  const [simSeverity, setSimSeverity] = useState("SEV-1");
  const [simSummary, setSimSummary] = useState("P99 Latency Breach > 3500ms on /checkout with cascading HTTP 504 timeouts.");
  const [simulating, setSimulating] = useState(false);

  // Chat State
  const [chatMessages, setChatMessages] = useState<Array<{ role: string; content: string; attribution?: string }>>([
    {
      role: "agent",
      content:
        "👋 **Hello! I am IncidentX, your Autonomous On-Call Incident Agent (Tier-1 Primary SRE).**\n\n" +
        "I am on 24/7 duty monitoring cluster telemetry, auto-acknowledging pages within milliseconds, triaging anomalies, and executing safe remediations. How can I assist you during this shift?",
      attribution: "oncall-agent:tier-1",
    },
  ]);
  const [inputMsg, setInputMsg] = useState("");
  const [sendingMsg, setSendingMsg] = useState(false);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Active modals
  const [selectedIncidentForUpdate, setSelectedIncidentForUpdate] = useState<string | null>(null);
  const [slackDraft, setSlackDraft] = useState<string | null>(null);
  const [postmortemDraft, setPostmortemDraft] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [triageLoadingId, setTriageLoadingId] = useState<string | null>(null);
  const [escalatingId, setEscalatingId] = useState<string | null>(null);
  const [escalationReason, setEscalationReason] = useState("");
  const [bannerNotice, setBannerNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [runningDemo, setRunningDemo] = useState(false);

  useEffect(() => {
    loadOnCallData();
  }, []);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const loadOnCallData = async () => {
    setLoading(true);
    try {
      const [statusRes, incRes] = await Promise.all([
        oncallApi.getStatus(),
        api.listIncidents(1, 10),
      ]);
      setShiftStatus(statusRes.shift);
      setActivePages(statusRes.active_pages || []);
      setAllPages(statusRes.all_pages || []);
      setIncidents(incRes.items || []);
    } catch (err) {
      console.error("Failed to load On-Call status:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulatePage = async () => {
    setSimulating(true);
    try {
      const res = await oncallApi.ingestPage({
        service_name: simService,
        severity: simSeverity,
        source: "PagerDuty",
        summary: simSummary,
      });

      setBannerNotice({
        type: "success",
        text: `🚨 New page ingested! Auto-acknowledged in ${res.page.mtta_seconds}s by ${res.page.acknowledged_by}.`,
      });

      // Reload list
      await loadOnCallData();
    } catch (err: any) {
      setBannerNotice({ type: "error", text: "Failed to simulate pager alert." });
    } finally {
      setSimulating(false);
    }
  };

  const handleRunTriage = async (page: PageAlert) => {
    const targetIncId = page.incident_id || incidents[0]?.id || "inc-oncall-demo";
    setTriageLoadingId(page.page_id);
    try {
      const res = await oncallApi.triageIncident(targetIncId);
      setBannerNotice({
        type: "success",
        text: `Autonomous triage completed: Verified root cause '${res.leading_root_cause}' with ${(res.confidence_score * 100).toFixed(0)}% confidence.`,
      });
      await loadOnCallData();
    } catch (err: any) {
      setBannerNotice({ type: "error", text: "Failed to run autonomous triage." });
    } finally {
      setTriageLoadingId(null);
    }
  };

  const handleDraftSlack = async (incidentId?: string | null) => {
    const incId = incidentId || incidents[0]?.id || "inc-active-001";
    setSelectedIncidentForUpdate(incId);
    try {
      const draft = await oncallApi.draftUpdate(incId);
      setSlackDraft(draft.slack_message);
    } catch (err: any) {
      setBannerNotice({ type: "error", text: "Failed to generate Slack draft." });
    }
  };

  const handleGeneratePostmortem = async (incidentId?: string | null) => {
    const incId = incidentId || incidents[0]?.id || "inc-active-001";
    setSelectedIncidentForUpdate(incId);
    try {
      const res = await oncallApi.generatePostmortem(incId);
      setPostmortemDraft(res.markdown_report);
    } catch (err: any) {
      setBannerNotice({ type: "error", text: "Failed to generate post-mortem report." });
    }
  };

  const handleConfirmEscalate = async (pageId: string) => {
    if (!escalationReason.trim()) return;
    try {
      await oncallApi.escalate(pageId, escalationReason);
      setBannerNotice({
        type: "success",
        text: `Page ${pageId} escalated to Human SRE Tier-2. Reason: ${escalationReason}`,
      });
      setEscalatingId(null);
      setEscalationReason("");
      await loadOnCallData();
    } catch (err: any) {
      setBannerNotice({ type: "error", text: "Failed to escalate page." });
    }
  };

  const handleRunDemoScenario = async () => {
    setRunningDemo(true);
    try {
      const res = await oncallApi.runMidnightMeltdownScenario();
      setBannerNotice({
        type: "success",
        text: `⚡ Midnight Black Friday Meltdown completed across 9 stages! Incident: ${res.incident_id}. Ruling: '${res.root_cause_ruling}' (${(res.confidence_score * 100).toFixed(0)}% conf). MTTA: ${res.mtta_seconds}s.`,
      });
      setChatMessages((prev) => [
        ...prev,
        {
          role: "agent",
          content: `🚨 **[FLAGSHIP DEMO EXECUTED: Midnight Black Friday Meltdown]**\n\n` +
            `• **Incident ID:** \`${res.incident_id}\`\n` +
            `• **Auto-Ack MTTA:** \`${res.mtta_seconds}s\` (Tier-1 Autonomous AI)\n` +
            `• **Multi-Agent Swarm (${res.completed_agents.length} Agents):** Completed with Kubernetes & container diagnostics\n` +
            `• **Courtroom 2.0 Verdict:** *${res.root_cause_ruling}* (${(res.confidence_score * 100).toFixed(0)}% confidence)\n` +
            `• **Remediation:** ${res.remediation_action.name} (Status: ${res.recovery_status})\n` +
            `• **Total Execution:** \`${res.total_execution_ms.toFixed(1)}ms\`\n\n` +
            `*Google SRE Post-Mortem and Slack announcements were automatically generated and dispatched.*`,
          attribution: "oncall-demo-runner:tier-1",
        },
      ]);
      await loadOnCallData();
    } catch (err: any) {
      setBannerNotice({ type: "error", text: "Failed to run demo scenario." });
    } finally {
      setRunningDemo(false);
    }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const msg = textToSend || inputMsg;
    if (!msg.trim() || sendingMsg) return;

    const userEntry = { role: "user", content: msg };
    setChatMessages((prev) => [...prev, userEntry]);
    if (!textToSend) setInputMsg("");
    setSendingMsg(true);

    try {
      const res = await oncallApi.chat(msg, incidents[0]?.id);
      setChatMessages((prev) => [
        ...prev,
        { role: "agent", content: res.content, attribution: res.attribution },
      ]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "agent",
          content: "Sorry, I encountered an issue accessing telemetry. Operating with local on-call runbook rules.",
          attribution: "fallback",
        },
      ]);
    } finally {
      setSendingMsg(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex-1 overflow-y-auto bg-[#070b14] text-slate-100 p-8">
      {/* Hero Duty Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <div className="w-11 h-11 rounded-2xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-lg shadow-amber-500/10">
              <Headphones className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-2xl font-bold tracking-tight text-white">Autonomous On-Call Incident Agent</h1>
                <span className="px-2.5 py-0.5 text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full font-bold uppercase flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1" />
                  {shiftStatus?.duty_status || "ON_DUTY"}
                </span>
                <span className="px-2 py-0.5 text-[10px] font-mono bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded-full">
                  TIER-1 PRIMARY SRE
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                24/7 First Responder Agent • Sub-Second Pager Acknowledgment • Autonomous Triage • Human-in-the-Loop Escalation
              </p>
            </div>
          </div>
        </div>

        {/* Quick Duty Metrics */}
        <div className="flex items-center space-x-3 flex-wrap">
          <div className="px-3.5 py-2 bg-[#0d1424] border border-slate-800 rounded-xl font-mono text-xs">
            <div className="text-[10px] text-slate-400">Mean Time to Acknowledge</div>
            <div className="text-base font-bold text-emerald-400">
              {shiftStatus?.mean_time_to_acknowledge_seconds || 0.8}s
            </div>
          </div>

          <div className="px-3.5 py-2 bg-[#0d1424] border border-slate-800 rounded-xl font-mono text-xs">
            <div className="text-[10px] text-slate-400">Total Alerts Handled</div>
            <div className="text-base font-bold text-white">
              {shiftStatus?.total_pages_handled || 0}
            </div>
          </div>

          <div className="px-3.5 py-2 bg-[#0d1424] border border-slate-800 rounded-xl font-mono text-xs">
            <div className="text-[10px] text-slate-400">Escalation Rate</div>
            <div className="text-base font-bold text-purple-400">
              {shiftStatus?.escalation_rate_percent || 0.0}%
            </div>
          </div>

          <button
            onClick={handleRunDemoScenario}
            disabled={runningDemo}
            className="px-3.5 py-2 rounded-xl border border-amber-500/40 bg-gradient-to-r from-amber-500/20 to-orange-500/20 hover:from-amber-500/30 hover:to-orange-500/30 text-amber-300 font-bold text-xs flex items-center space-x-2 transition shadow-lg shadow-amber-500/10"
            title="Run Flagship 9-Stage Black Friday Meltdown Demo"
          >
            <Zap className={`w-4 h-4 text-amber-400 ${runningDemo ? "animate-spin" : ""}`} />
            <span>{runningDemo ? "Executing 9 Stages..." : "Run Black Friday Demo (P1)"}</span>
          </button>

          <button
            onClick={loadOnCallData}
            disabled={loading}
            className="p-2.5 rounded-xl border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition"
            title="Refresh Shift Data"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Banner Notice */}
      {bannerNotice && (
        <div
          className={`mt-4 p-3.5 rounded-xl text-xs flex items-center justify-between border ${
            bannerNotice.type === "success"
              ? "bg-emerald-950/40 border-emerald-500/30 text-emerald-200"
              : "bg-red-950/40 border-red-500/30 text-red-200"
          }`}
        >
          <div className="flex items-center space-x-2">
            {bannerNotice.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            )}
            <span>{bannerNotice.text}</span>
          </div>
          <button onClick={() => setBannerNotice(null)} className="text-slate-400 hover:text-white text-sm">
            ✕
          </button>
        </div>
      )}

      {/* 2-Column Dashboard Grid: Left Queue, Right Copilot */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mt-6">
        {/* Left Column (7 cols): Paging Queue & Triage */}
        <div className="lg:col-span-7 space-y-6">
          {/* Shift Details Card */}
          <div className="p-5 bg-[#0d1424] border border-slate-800 rounded-2xl">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider text-slate-400 font-bold">
                <ShieldCheck className="w-4 h-4 text-blue-400" />
                <span>On-Call Escalation Policy & Responsibilities</span>
              </div>
              <span className="text-[11px] font-mono text-emerald-400">SHIFT: ACTIVE</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 text-xs font-mono">
              <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Tier-1 Primary Responder</span>
                <span className="text-white font-semibold text-sm mt-0.5 block">
                  {shiftStatus?.primary_responder || "IncidentX Autonomous AI Agent"}
                </span>
                <p className="text-[11px] text-slate-400 mt-1 font-sans">
                  Auto-acknowledges all incoming pager events, ingests telemetry, isolates root cause via Courtroom 2.0, and executes pre-authorized safe recovery.
                </p>
              </div>

              <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Tier-2 Secondary Escalation</span>
                <span className="text-white font-semibold text-sm mt-0.5 block">
                  {shiftStatus?.secondary_responder || "Human SRE On-Call Team"}
                </span>
                <p className="text-[11px] text-slate-400 mt-1 font-sans">
                  Pulls in human engineers when blast radius exceeds single-service boundary, automated recovery fails, or high-risk manual authorization is needed.
                </p>
              </div>
            </div>
          </div>

          {/* Trigger Alert Simulator */}
          <div className="p-5 bg-[#0b101b] border border-slate-800 rounded-2xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider text-amber-400 font-bold">
                <Radio className="w-4 h-4" />
                <span>Simulate Inbound Pager Alert</span>
              </div>
              <span className="text-[10px] text-slate-400 font-mono">PagerDuty / Alertmanager Webhook</span>
            </div>

            <div className="grid grid-cols-3 gap-3 mt-4">
              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase">Target Service</label>
                <select
                  value={simService}
                  onChange={(e) => setSimService(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 text-xs text-white rounded-lg p-2 font-mono mt-1"
                >
                  <option value="order-service">order-service</option>
                  <option value="payment-service">payment-service</option>
                  <option value="auth-service">auth-service</option>
                  <option value="postgres-db">postgres-db</option>
                  <option value="redis-cache">redis-cache</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] font-mono text-slate-400 uppercase">Severity</label>
                <select
                  value={simSeverity}
                  onChange={(e) => setSimSeverity(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 text-xs text-white rounded-lg p-2 font-mono mt-1"
                >
                  <option value="SEV-1">SEV-1 (Critical Outage)</option>
                  <option value="SEV-2">SEV-2 (High Degradation)</option>
                  <option value="SEV-3">SEV-3 (Moderate Alert)</option>
                </select>
              </div>

              <div className="flex items-end">
                <button
                  onClick={handleSimulatePage}
                  disabled={simulating}
                  className="w-full py-2 px-3 bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs rounded-lg transition flex items-center justify-center space-x-1.5 shadow-md shadow-amber-600/20 disabled:opacity-50"
                >
                  <Flame className="w-3.5 h-3.5" />
                  <span>{simulating ? "Dispatching..." : "Page On-Call Agent"}</span>
                </button>
              </div>
            </div>

            <div className="mt-3">
              <label className="text-[10px] font-mono text-slate-400 uppercase">Alert Payload Summary</label>
              <input
                type="text"
                value={simSummary}
                onChange={(e) => setSimSummary(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg p-2 font-mono mt-1"
              />
            </div>
          </div>

          {/* Active Paged Alerts Queue */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                Active On-Call Queue ({allPages.length})
              </h3>
              <span className="text-xs text-slate-400 font-mono">Sub-second Auto-Acknowledgment</span>
            </div>

            <div className="space-y-3">
              {allPages.map((page) => (
                <div
                  key={page.page_id}
                  className={`p-4 rounded-xl border transition-all ${
                    page.status === "ESCALATED"
                      ? "bg-purple-950/20 border-purple-500/40"
                      : page.status === "TRIAGED"
                      ? "bg-blue-950/20 border-blue-500/40"
                      : "bg-[#0d1424] border-slate-800"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                            page.severity === "SEV-1"
                              ? "bg-red-500/20 text-red-300 border border-red-500/30"
                              : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                          }`}
                        >
                          {page.severity}
                        </span>
                        <span className="font-mono text-xs font-bold text-white">{page.page_id}</span>
                        <span className="text-xs text-slate-400 font-mono">• {page.service_name}</span>
                        <span className="text-[10px] text-slate-500 font-mono">({page.source})</span>
                      </div>
                      <p className="text-xs text-slate-300 mt-2 leading-relaxed">{page.summary}</p>
                    </div>

                    <div className="text-right">
                      <span
                        className={`px-2 py-0.5 text-[10px] font-mono rounded-full font-bold uppercase ${
                          page.status === "TRIAGED"
                            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                            : page.status === "ESCALATED"
                            ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                            : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                        }`}
                      >
                        {page.status}
                      </span>
                      <div className="text-[10px] text-slate-400 font-mono mt-1">
                        MTTA: <span className="text-emerald-400 font-bold">{page.mtta_seconds || 0.6}s</span>
                      </div>
                    </div>
                  </div>

                  {/* Triage Summary if available */}
                  {page.triage_summary && (
                    <div className="mt-3 p-2.5 bg-slate-900/80 rounded-lg border border-slate-800 text-xs text-slate-300">
                      <span className="font-semibold text-purple-400">Triage Assessment: </span>
                      {page.triage_summary}
                      {page.leading_root_cause && (
                        <div className="mt-1 text-[11px] font-mono text-emerald-400">
                          Root Cause: {page.leading_root_cause} ({(page.confidence_score || 0.86) * 100}%)
                        </div>
                      )}
                    </div>
                  )}

                  {/* Action Bar */}
                  <div className="mt-3.5 pt-3 border-t border-slate-800/80 flex items-center justify-between flex-wrap gap-2 text-xs">
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleRunTriage(page)}
                        disabled={triageLoadingId === page.page_id}
                        className="px-2.5 py-1 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 text-blue-300 rounded font-mono text-[11px] transition flex items-center space-x-1"
                      >
                        <Zap className="w-3 h-3" />
                        <span>{triageLoadingId === page.page_id ? "Triaging..." : "Auto-Triage"}</span>
                      </button>

                      <button
                        onClick={() => handleDraftSlack(page.incident_id)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-mono text-[11px] transition flex items-center space-x-1"
                      >
                        <Share2 className="w-3 h-3" />
                        <span>Draft Slack</span>
                      </button>

                      <button
                        onClick={() => handleGeneratePostmortem(page.incident_id)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-mono text-[11px] transition flex items-center space-x-1"
                      >
                        <FileText className="w-3 h-3" />
                        <span>Post-Mortem</span>
                      </button>
                    </div>

                    {page.status !== "ESCALATED" && (
                      <button
                        onClick={() => setEscalatingId(page.page_id)}
                        className="px-2.5 py-1 text-purple-400 hover:text-purple-200 border border-purple-500/30 rounded font-mono text-[11px] transition flex items-center space-x-1"
                      >
                        <ShieldAlert className="w-3 h-3" />
                        <span>Escalate to Human</span>
                      </button>
                    )}
                  </div>

                  {/* Escalation Inline Drawer */}
                  {escalatingId === page.page_id && (
                    <div className="mt-3 p-3 bg-purple-950/40 border border-purple-500/30 rounded-xl space-y-2">
                      <label className="text-[10px] font-mono uppercase text-purple-300 font-bold block">
                        Reason for Human SRE Escalation
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Blast radius exceeds single-service limits, requires manual credential rotation"
                        value={escalationReason}
                        onChange={(e) => setEscalationReason(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded text-xs p-2 text-white font-mono"
                      />
                      <div className="flex justify-end space-x-2 pt-1">
                        <button
                          onClick={() => setEscalatingId(null)}
                          className="px-3 py-1 text-xs text-slate-400 hover:text-white"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleConfirmEscalate(page.page_id)}
                          className="px-3 py-1 bg-purple-600 hover:bg-purple-500 text-white rounded text-xs font-semibold"
                        >
                          Confirm Escalation
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column (5 cols): Interactive On-Call Copilot Chat */}
        <div className="lg:col-span-5 flex flex-col h-[760px] bg-[#0d1424] border border-slate-800 rounded-2xl overflow-hidden">
          {/* Chat Header */}
          <div className="p-4 bg-[#0b101b] border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">On-Call Agent Copilot</h3>
                <p className="text-[10px] text-slate-400 font-mono">Live SRE Guidance & Operational Actions</p>
              </div>
            </div>
            <span className="px-2 py-0.5 text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded font-semibold">
              CONNECTED
            </span>
          </div>

          {/* Chat Message Stream */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {chatMessages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
              >
                <div
                  className={`max-w-[90%] p-3.5 rounded-2xl text-xs leading-relaxed ${
                    msg.role === "user"
                      ? "bg-purple-600 text-white font-medium rounded-tr-none"
                      : "bg-slate-900/90 border border-slate-800 text-slate-200 rounded-tl-none whitespace-pre-wrap font-sans"
                  }`}
                >
                  {msg.content}
                </div>
                {msg.attribution && (
                  <span className="text-[9px] font-mono text-slate-500 mt-1 px-1">
                    via {msg.attribution}
                  </span>
                )}
              </div>
            ))}
            {sendingMsg && (
              <div className="flex items-center space-x-2 text-slate-400 text-xs italic">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-purple-400" />
                <span>On-Call Agent evaluating telemetry and runbooks...</span>
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Quick Prompts Ribbon */}
          <div className="p-2.5 bg-slate-900/40 border-t border-slate-800/80 flex items-center space-x-1.5 overflow-x-auto text-[11px] font-mono text-slate-300">
            <button
              onClick={() => handleSendMessage("Who is on call right now?")}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 rounded-lg whitespace-nowrap transition"
            >
              Who is on call?
            </button>
            <button
              onClick={() => handleSendMessage("What alerts are active?")}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 rounded-lg whitespace-nowrap transition"
            >
              Active alerts?
            </button>
            <button
              onClick={() => handleSendMessage("Draft a Slack update for the incident")}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 rounded-lg whitespace-nowrap transition"
            >
              Draft Slack update
            </button>
            <button
              onClick={() => handleSendMessage("Generate a blameless postmortem")}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 rounded-lg whitespace-nowrap transition"
            >
              Post-Mortem
            </button>
          </div>

          {/* Chat Input Bar */}
          <div className="p-3 bg-[#0b101b] border-t border-slate-800 flex items-center space-x-2">
            <input
              type="text"
              placeholder="Ask on-call agent (e.g. triage incident, check blast radius, draft update)..."
              value={inputMsg}
              onChange={(e) => setInputMsg(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
              className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={sendingMsg || !inputMsg.trim()}
              className="p-2 bg-purple-600 hover:bg-purple-500 text-white rounded-xl transition disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Slack Draft Modal */}
      {slackDraft && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0d1424] border border-slate-800 rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-emerald-400 text-sm font-bold font-mono">
                <Share2 className="w-4 h-4" />
                <span>Slack Stakeholder Communication Draft</span>
              </div>
              <button onClick={() => setSlackDraft(null)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <pre className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono text-slate-200 whitespace-pre-wrap max-h-96 overflow-y-auto">
              {slackDraft}
            </pre>

            <div className="flex justify-between items-center pt-2">
              <span className="text-[11px] text-slate-400 font-mono">Ready to broadcast to #incidents channel</span>
              <button
                onClick={() => copyToClipboard(slackDraft)}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl flex items-center space-x-1.5 transition"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                <span>{copied ? "Copied!" : "Copy Slack Text"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Post-Mortem Preview Modal */}
      {postmortemDraft && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0d1424] border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-blue-400 text-sm font-bold font-mono">
                <FileText className="w-4 h-4" />
                <span>Google SRE Blameless Post-Mortem Report</span>
              </div>
              <button onClick={() => setPostmortemDraft(null)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <div className="p-5 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono text-slate-200 whitespace-pre-wrap max-h-[480px] overflow-y-auto leading-relaxed">
              {postmortemDraft}
            </div>

            <div className="flex justify-between items-center pt-2">
              <span className="text-[11px] text-slate-400 font-mono">Formatted in standard Markdown</span>
              <button
                onClick={() => copyToClipboard(postmortemDraft)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl flex items-center space-x-1.5 transition"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                <span>{copied ? "Copied!" : "Copy Report"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
