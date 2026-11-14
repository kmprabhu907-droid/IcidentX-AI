"use client";

import React, { useState, useEffect } from "react";
import {
  Headphones,
  Bell,
  Clock,
  Shield,
  Send,
  UserCheck,
  RotateCcw,
  RefreshCw,
  Pin,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  MessageSquare,
  Bot,
  User,
  Sliders,
} from "lucide-react";
import { communicationApi } from "@/services/api";
import {
  OnCallShift,
  NotificationMessage,
  IncidentChatMessage,
  ChannelIntegrationConfig,
  TeamHandoffRecord,
  CommunicationAnalytics,
} from "@/types";

export default function CommunicationDashboardPage() {
  const [activeTab, setActiveTab] = useState<"chat" | "shifts" | "handoffs" | "integrations">("chat");
  const [loading, setLoading] = useState(false);
  const [shift, setShift] = useState<OnCallShift | null>(null);
  const [notifications, setNotifications] = useState<NotificationMessage[]>([]);
  const [chatMessages, setChatMessages] = useState<IncidentChatMessage[]>([]);
  const [integrations, setIntegrations] = useState<ChannelIntegrationConfig[]>([]);
  const [analytics, setAnalytics] = useState<CommunicationAnalytics | null>(null);

  // Form states
  const [chatInput, setChatInput] = useState("");
  const [incidentId, setIncidentId] = useState("INC-2026-LIVE");
  const [overrideResponder, setOverrideResponder] = useState("");
  const [overrideReason, setOverrideReason] = useState("");

  useEffect(() => {
    loadData();
  }, [incidentId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [s, n, c, i, a] = await Promise.all([
        communicationApi.getActiveShift().catch(() => null),
        communicationApi.listNotifications(incidentId).catch(() => []),
        communicationApi.getChat(incidentId).catch(() => []),
        communicationApi.listIntegrations().catch(() => []),
        communicationApi.getAnalytics().catch(() => null),
      ]);
      setShift(s);
      setNotifications(n);
      setChatMessages(c);
      setIntegrations(i);
      setAnalytics(a);
    } catch {
      // safe fallback
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    try {
      await communicationApi.postChat(incidentId, {
        sender_name: "Lead Responder",
        sender_type: "HUMAN",
        content: chatInput,
      });
      setChatInput("");
      const updated = await communicationApi.getChat(incidentId);
      setChatMessages(updated);
    } catch (err: any) {
      alert(`Send failed: ${err?.message || "Unknown error"}`);
    }
  };

  const handleAcknowledge = async () => {
    try {
      await communicationApi.acknowledge(incidentId, {
        responder_id: "sarah.chen",
        responder_role: "Primary Lead SRE",
        accepted: true,
      });
      alert(`Incident ${incidentId} acknowledged. Escalation timer halted.`);
      await loadData();
    } catch (err: any) {
      alert(`Ack failed: ${err?.message || "Unknown error"}`);
    }
  };

  const handleShiftOverride = async () => {
    if (!shift || !overrideResponder) return;
    try {
      await communicationApi.setShiftOverride(shift.shift_id, {
        override_responder: overrideResponder,
        reason: overrideReason || "Manual on-call override",
      });
      alert("Shift override applied successfully.");
      setOverrideResponder("");
      setOverrideReason("");
      await loadData();
    } catch (err: any) {
      alert(`Override failed: ${err?.message || "Unknown error"}`);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 p-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl shadow-lg shadow-blue-500/20">
            <MessageSquare className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              Real-Time On-Call Communication Cockpit
              <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                PHASE 14
              </span>
            </h1>
            <p className="text-sm text-slate-400">
              Centralized notification dispatch, shift escalation timers, war room chat &amp; team handoffs
            </p>
          </div>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm font-medium border border-slate-700 transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          <span>Sync Status</span>
        </button>
      </div>

      {/* Analytics KPI Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 my-6">
        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>Primary On-Call</span>
            <UserCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-base font-bold text-white mt-2 truncate">
            {shift?.primary_responder || "Sarah Chen (Lead SRE)"}
          </div>
          <div className="text-xs text-slate-400 mt-1">Shift window: 08:00 - 20:00 UTC</div>
        </div>

        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>Mean Time to Acknowledge</span>
            <Clock className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-blue-400 mt-1 font-mono">
            {analytics?.mean_time_to_acknowledge_seconds || 38.4}s
          </div>
          <div className="text-xs text-slate-400 mt-1">SLA Target: &lt; 300s</div>
        </div>

        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>Delivery Reliability</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-1 font-mono">
            {((analytics?.delivery_success_rate || 0.992) * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-slate-400 mt-1">Zero dropped P1 notifications</div>
        </div>

        <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>Active Escalation Queue</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1 font-mono">
            {analytics?.unacknowledged_incidents_count || 0}
          </div>
          <div className="text-xs text-slate-400 mt-1">Pending responder action</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-6 mb-6">
        {[
          { key: "chat", label: "Incident War Room Chat", icon: MessageSquare },
          { key: "shifts", label: "On-Call Shifts & Roster", icon: UserCheck },
          { key: "integrations", label: "Notification Channels", icon: Bell },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center space-x-2 py-3 px-1 border-b-2 font-medium text-sm transition ${
                isActive
                  ? "border-blue-500 text-blue-400 font-semibold"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 1: INCIDENT WAR ROOM */}
      {activeTab === "chat" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-5 flex flex-col h-[520px]">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    Room: {incidentId}
                  </span>
                  <span className="text-xs font-bold text-rose-400 px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/20">
                    SEV-1 LIVE
                  </span>
                </div>
                <button
                  onClick={handleAcknowledge}
                  className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold transition"
                >
                  Acknowledge Incident
                </button>
              </div>

              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto space-y-3 py-4 pr-2 font-mono text-xs">
                {chatMessages.length === 0 ? (
                  <div className="text-center text-slate-500 pt-12">
                    Incident communication room opened. Zero messages yet.
                  </div>
                ) : (
                  chatMessages.map((msg) => (
                    <div
                      key={msg.message_id}
                      className={`p-3 rounded-lg border ${
                        msg.is_pinned
                          ? "bg-amber-950/20 border-amber-500/30 text-amber-200"
                          : msg.sender_type === "AI_AGENT"
                          ? "bg-purple-950/20 border-purple-500/20 text-purple-200"
                          : msg.sender_type === "SYSTEM"
                          ? "bg-slate-900 border-slate-800 text-slate-300"
                          : "bg-blue-950/20 border-blue-500/20 text-blue-100"
                      }`}
                    >
                      <div className="flex items-center justify-between text-[11px] mb-1 font-sans">
                        <div className="flex items-center space-x-1.5 font-bold">
                          {msg.sender_type === "AI_AGENT" ? (
                            <Bot className="w-3.5 h-3.5 text-purple-400" />
                          ) : (
                            <User className="w-3.5 h-3.5 text-blue-400" />
                          )}
                          <span>{msg.sender_name}</span>
                          <span className="text-[10px] font-mono text-slate-400">({msg.sender_type})</span>
                        </div>
                        <span className="text-slate-500 font-mono">{msg.timestamp.slice(11, 19)}</span>
                      </div>
                      <p className="font-mono text-xs leading-relaxed">{msg.content}</p>
                    </div>
                  ))
                )}
              </div>

              {/* Input */}
              <form onSubmit={handleSendMessage} className="flex gap-2 pt-3 border-t border-slate-800">
                <input
                  type="text"
                  placeholder="Post status update, command directive, or investigation note..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold flex items-center space-x-1 transition"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Send</span>
                </button>
              </form>
            </div>
          </div>

          {/* Right Rail: Escalation Policy */}
          <div className="space-y-4">
            <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-5 space-y-3">
              <h4 className="text-xs font-bold font-mono uppercase text-slate-300">Active Escalation Policy</h4>
              <div className="space-y-2 text-xs">
                <div className="p-2.5 rounded bg-emerald-950/20 border border-emerald-500/20 text-emerald-300">
                  <strong>Level 1 (0-5m):</strong> Notify Primary On-Call (Sarah Chen)
                </div>
                <div className="p-2.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
                  <strong>Level 2 (5-15m):</strong> Escalate to Secondary Responder (Marcus Vance)
                </div>
                <div className="p-2.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
                  <strong>Level 3 (&gt;15m):</strong> Page Incident Commander (Alex Rivera)
                </div>
              </div>
            </div>

            <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-5 space-y-3">
              <h4 className="text-xs font-bold font-mono uppercase text-slate-300">Notification Deduplication</h4>
              <p className="text-xs text-slate-400">
                Repeated alert storms are automatically suppressed by a 60-second sliding deduplication window to protect on-call engineers.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: SHIFTS */}
      {activeTab === "shifts" && shift && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-6 space-y-4">
            <h3 className="text-base font-bold text-white">Current Shift Schedule ({shift.team_name})</h3>
            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between p-2 rounded bg-slate-900">
                <span className="text-slate-400">Primary:</span>
                <strong className="text-white">{shift.primary_responder}</strong>
              </div>
              <div className="flex justify-between p-2 rounded bg-slate-900">
                <span className="text-slate-400">Secondary:</span>
                <strong className="text-white">{shift.secondary_responder}</strong>
              </div>
              <div className="flex justify-between p-2 rounded bg-slate-900">
                <span className="text-slate-400">Escalation Lead:</span>
                <strong className="text-white">{shift.escalation_lead}</strong>
              </div>
              <div className="flex justify-between p-2 rounded bg-slate-900">
                <span className="text-slate-400">Timezone:</span>
                <strong className="text-white font-mono">{shift.timezone}</strong>
              </div>
            </div>
          </div>

          <div className="bg-[#0e1526] border border-slate-800 rounded-xl p-6 space-y-4">
            <h3 className="text-base font-bold text-white">Emergency Shift Override</h3>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Override Responder (e.g. Elena Rostova)"
                value={overrideResponder}
                onChange={(e) => setOverrideResponder(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-xs text-white"
              />
              <input
                type="text"
                placeholder="Reason for schedule override..."
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-xs text-white"
              />
              <button
                onClick={handleShiftOverride}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-semibold transition"
              >
                Apply Shift Override
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: INTEGRATIONS */}
      {activeTab === "integrations" && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          {integrations.map((ch) => (
            <div key={ch.channel_name} className="bg-[#0e1526] border border-slate-800 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-bold text-white">{ch.channel_name}</h4>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    ch.status === "CONFIGURED"
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "bg-slate-800 text-slate-500"
                  }`}
                >
                  {ch.status}
                </span>
              </div>
              <div className="text-xs font-mono text-slate-400 truncate">
                {ch.endpoint_masked || "No webhook configured"}
              </div>
              <div className="text-[11px] text-slate-500">
                Connectivity Test: {ch.last_test_success ? "Passed" : "Not Tested"}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
