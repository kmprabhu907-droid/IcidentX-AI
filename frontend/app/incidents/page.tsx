"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Plus,
  Search,
  Filter,
  Clock,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  X,
  ShieldAlert,
  Radio,
  Server,
  Zap,
  UserCheck,
  Flame,
  ArrowUpRight,
  Activity,
  Send,
  Sliders,
} from "lucide-react";
import { api } from "../../services/api";
import { Incident, IncidentStatistics, AlertIngestResponse } from "../../types";

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [stats, setStats] = useState<IncidentStatistics | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [environmentFilter, setEnvironmentFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Incident Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newSummary, setNewSummary] = useState("");
  const [newSeverity, setNewSeverity] = useState("P2");
  const [newEnvironment, setNewEnvironment] = useState("DEMOMESH");
  const [newImpact, setNewImpact] = useState("");
  const [newOwner, setNewOwner] = useState("IncidentX AI (Tier-1)");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Simulate Inbound Alert Webhook Modal State
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);
  const [alertSource, setAlertSource] = useState("alertmanager");
  const [alertServiceName, setAlertServiceName] = useState("checkout-service");
  const [alertName, setAlertName] = useState("HighHttp5xxErrorRate");
  const [alertSeverity, setAlertSeverity] = useState("P1");
  const [alertEnvironment, setAlertEnvironment] = useState("DEMOMESH");
  const [alertDescription, setAlertDescription] = useState(
    "Checkout service HTTP 500 error rate surged to 42.8% (>5% threshold) over 3m window."
  );
  const [isAlertSubmitting, setIsAlertSubmitting] = useState(false);
  const [alertIngestResult, setAlertIngestResult] = useState<AlertIngestResponse | null>(null);

  const fetchStats = async () => {
    try {
      const data = await api.getIncidentStatistics();
      setStats(data);
    } catch (err: any) {
      console.warn("Could not fetch incident statistics:", err);
    }
  };

  const fetchIncidents = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listIncidents(
        page,
        20,
        statusFilter || undefined,
        severityFilter || undefined,
        environmentFilter || undefined,
        undefined,
        undefined,
        searchQuery.trim() || undefined
      );
      setIncidents(data.items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || "Failed to load incidents.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
    fetchStats();
  }, [page, severityFilter, statusFilter, environmentFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchIncidents();
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    setIsSubmitting(true);
    try {
      await api.createIncident({
        title: newTitle.trim(),
        summary: newSummary.trim() || undefined,
        severity: newSeverity,
        status: "DETECTED",
        environment: newEnvironment,
        impact_scope: newImpact.trim() || undefined,
        owner_name: newOwner,
        assigned_team: "Platform SRE",
      });
      setIsModalOpen(false);
      setNewTitle("");
      setNewSummary("");
      setNewImpact("");
      fetchIncidents();
      fetchStats();
    } catch (err: any) {
      alert(`Error creating incident: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSimulateAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsAlertSubmitting(true);
    setAlertIngestResult(null);
    try {
      let rawPayload: Record<string, any> = {};
      if (alertSource === "alertmanager") {
        rawPayload = {
          alerts: [
            {
              status: "firing",
              labels: {
                alertname: alertName,
                service: alertServiceName,
                severity: alertSeverity,
                environment: alertEnvironment,
              },
              annotations: {
                summary: alertDescription,
                description: alertDescription,
              },
            },
          ],
        };
      } else if (alertSource === "grafana") {
        rawPayload = {
          ruleName: alertName,
          state: "alerting",
          tags: { service: alertServiceName, severity: alertSeverity },
          message: alertDescription,
        };
      } else {
        rawPayload = {
          reason: alertName,
          message: alertDescription,
          involvedObject: { name: alertServiceName, kind: "Pod" },
          type: "Warning",
        };
      }

      const res = await api.ingestAlert({
        source: alertSource,
        alert_name: alertName,
        service_name: alertServiceName,
        severity: alertSeverity,
        environment: alertEnvironment,
        description: alertDescription,
        raw_payload: rawPayload,
      });

      setAlertIngestResult(res);
      fetchIncidents();
      fetchStats();
    } catch (err: any) {
      alert(`Alert ingestion failed: ${err.message}`);
    } finally {
      setIsAlertSubmitting(false);
    }
  };

  const handleQuickAcknowledge = async (incidentId: string) => {
    try {
      await api.acknowledgeIncident(incidentId, "sre-quick-action", "On-Call SRE");
      fetchIncidents();
      fetchStats();
    } catch (err: any) {
      alert(`Failed to acknowledge incident: ${err.message}`);
    }
  };

  const getSeverityBadge = (sev: string) => {
    const s = sev.toUpperCase();
    if (s === "P1" || s === "SEV-1" || s === "CRITICAL") {
      return "bg-rose-500/10 text-rose-400 border-rose-500/30";
    }
    if (s === "P2" || s === "SEV-2" || s === "HIGH") {
      return "bg-amber-500/10 text-amber-400 border-amber-500/30";
    }
    if (s === "P3" || s === "SEV-3" || s === "MEDIUM") {
      return "bg-blue-500/10 text-blue-400 border-blue-500/30";
    }
    return "bg-slate-500/10 text-slate-400 border-slate-500/30";
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "DETECTED":
        return "bg-amber-500/10 text-amber-300 border-amber-500/30 animate-pulse";
      case "ACKNOWLEDGED":
        return "bg-blue-500/10 text-blue-300 border-blue-500/30";
      case "INVESTIGATING":
        return "bg-purple-500/15 text-purple-300 border-purple-500/40 font-semibold";
      case "ROOT_CAUSE_IDENTIFIED":
        return "bg-cyan-500/15 text-cyan-300 border-cyan-500/40";
      case "REMEDIATION_PENDING":
        return "bg-orange-500/15 text-orange-300 border-orange-500/40";
      case "REMEDIATING":
        return "bg-indigo-500/15 text-indigo-300 border-indigo-500/40";
      case "VERIFYING":
        return "bg-teal-500/15 text-teal-300 border-teal-500/40";
      case "RESOLVED":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "CLOSED":
        return "bg-slate-700/30 text-slate-400 border-slate-700";
      case "REOPENED":
        return "bg-rose-500/20 text-rose-300 border-rose-500/40";
      case "SUPPRESSED":
        return "bg-zinc-800 text-zinc-400 border-zinc-700";
      case "CANCELLED":
        return "bg-zinc-900 text-zinc-500 border-zinc-800";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2 font-mono">
              On-Call Incident Command Center
            </h1>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              LIVE TELEMETRY
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-sans">
            Centralized incident lifecycle management, real-time alert ingestion, ownership SLA, and 11-agent AI investigation.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsAlertModalOpen(true)}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/40 text-xs font-mono font-semibold text-purple-300 transition-all shadow-sm"
          >
            <Radio className="w-3.5 h-3.5 text-purple-400 animate-pulse" />
            <span>Simulate Inbound Alert</span>
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-mono font-bold text-white shadow-lg shadow-blue-500/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Incident</span>
          </button>
        </div>
      </div>

      {/* Module 9.5: 6 Overview Status Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-3.5 rounded-xl border border-slate-800 bg-[#0e1424]">
          <div className="flex items-center justify-between text-slate-400 text-[11px] font-mono">
            <span>Active Incidents</span>
            <Activity className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div className="text-xl font-bold text-white font-mono mt-1">
            {stats ? stats.total_active : incidents.filter((i) => !["RESOLVED", "CLOSED", "CANCELLED"].includes(i.status)).length}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Under management</div>
        </div>

        <div className="p-3.5 rounded-xl border border-rose-500/30 bg-rose-950/15">
          <div className="flex items-center justify-between text-rose-300 text-[11px] font-mono">
            <span>Critical P1</span>
            <Flame className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
          </div>
          <div className="text-xl font-bold text-rose-300 font-mono mt-1">
            {stats ? stats.p1_critical : incidents.filter((i) => i.severity === "P1" || i.severity === "SEV-1").length}
          </div>
          <div className="text-[10px] text-rose-400/70 mt-0.5">High blast radius</div>
        </div>

        <div className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-950/15">
          <div className="flex items-center justify-between text-amber-300 text-[11px] font-mono">
            <span>High P2</span>
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-xl font-bold text-amber-300 font-mono mt-1">
            {stats ? stats.p2_high : incidents.filter((i) => i.severity === "P2" || i.severity === "SEV-2").length}
          </div>
          <div className="text-[10px] text-amber-400/70 mt-0.5">Core feature degraded</div>
        </div>

        <div className="p-3.5 rounded-xl border border-purple-500/30 bg-purple-950/15">
          <div className="flex items-center justify-between text-purple-300 text-[11px] font-mono">
            <span>Investigating</span>
            <Zap className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <div className="text-xl font-bold text-purple-300 font-mono mt-1">
            {stats ? stats.investigating : incidents.filter((i) => i.status === "INVESTIGATING").length}
          </div>
          <div className="text-[10px] text-purple-400/70 mt-0.5">Agents active</div>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-800 bg-[#0e1424]">
          <div className="flex items-center justify-between text-slate-400 text-[11px] font-mono">
            <span>Unassigned</span>
            <UserCheck className="w-3.5 h-3.5 text-yellow-400" />
          </div>
          <div className="text-xl font-bold text-yellow-300 font-mono mt-1">
            {stats ? stats.unassigned : incidents.filter((i) => !i.owner_id || i.owner_name === "Unassigned").length}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Awaiting responder</div>
        </div>

        <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-950/15">
          <div className="flex items-center justify-between text-emerald-300 text-[11px] font-mono">
            <span>Resolved</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-emerald-300 font-mono mt-1">
            {stats ? stats.resolved_count : incidents.filter((i) => ["RESOLVED", "CLOSED"].includes(i.status)).length}
          </div>
          <div className="text-[10px] text-emerald-400/70 mt-0.5">
            Avg MTTR: {stats?.mean_time_to_resolve_seconds ? `${stats.mean_time_to_resolve_seconds}s` : "42s"}
          </div>
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl border border-slate-800 bg-[#0e1424]">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search Form */}
          <form onSubmit={handleSearchSubmit} className="flex items-center relative">
            <Search className="w-3.5 h-3.5 absolute left-3 text-slate-500" />
            <input
              type="text"
              placeholder="Search title, service, summary..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 w-56 font-sans"
            />
          </form>

          {/* Severity Dropdown */}
          <div className="flex items-center space-x-1.5 text-xs font-mono text-slate-400">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <span>Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setPage(1);
              }}
              className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 text-xs font-mono"
            >
              <option value="">All Severities</option>
              <option value="P1">P1 (Critical Outage)</option>
              <option value="P2">P2 (High Degradation)</option>
              <option value="P3">P3 (Medium Impact)</option>
              <option value="P4">P4 (Low / Info)</option>
              <option value="SEV-1">SEV-1</option>
              <option value="SEV-2">SEV-2</option>
            </select>
          </div>

          {/* Lifecycle Status Dropdown (12 States) */}
          <div className="flex items-center space-x-1.5 text-xs font-mono text-slate-400">
            <span>Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 text-xs font-mono"
            >
              <option value="">All Lifecycle States</option>
              <option value="DETECTED">DETECTED</option>
              <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
              <option value="INVESTIGATING">INVESTIGATING</option>
              <option value="ROOT_CAUSE_IDENTIFIED">ROOT_CAUSE_IDENTIFIED</option>
              <option value="REMEDIATION_PENDING">REMEDIATION_PENDING</option>
              <option value="REMEDIATING">REMEDIATING</option>
              <option value="VERIFYING">VERIFYING</option>
              <option value="RESOLVED">RESOLVED</option>
              <option value="CLOSED">CLOSED</option>
              <option value="REOPENED">REOPENED</option>
              <option value="SUPPRESSED">SUPPRESSED</option>
              <option value="CANCELLED">CANCELLED</option>
            </select>
          </div>

          {/* Environment Dropdown */}
          <div className="flex items-center space-x-1.5 text-xs font-mono text-slate-400">
            <span>Env:</span>
            <select
              value={environmentFilter}
              onChange={(e) => {
                setEnvironmentFilter(e.target.value);
                setPage(1);
              }}
              className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 text-xs font-mono"
            >
              <option value="">All Environments</option>
              <option value="DEMOMESH">DEMOMESH (Simulated)</option>
              <option value="KUBERNETES">KUBERNETES (Cluster Live)</option>
            </select>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => {
              fetchIncidents();
              fetchStats();
            }}
            className="p-1.5 rounded-lg border border-slate-700 bg-slate-900 text-slate-400 hover:text-white transition-colors"
            title="Refresh incident list"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <span className="text-xs font-mono text-slate-400">
            Showing <strong className="text-white">{incidents.length}</strong> of{" "}
            <strong className="text-white">{total}</strong> records
          </span>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl border border-red-500/30 bg-red-950/20 text-red-300 text-xs font-mono">
          {error}
        </div>
      )}

      {/* Live Incident Table */}
      <div className="rounded-xl border border-slate-800 bg-[#0e1424] overflow-hidden shadow-sm">
        {loading ? (
          <div className="py-16 text-center text-xs font-mono text-slate-500">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-blue-500" />
            Loading real-time incident command records...
          </div>
        ) : incidents.length === 0 ? (
          <div className="py-16 text-center text-xs font-mono text-slate-500 space-y-2">
            <p>No incidents match the active filter criteria.</p>
            <button
              onClick={() => {
                setSeverityFilter("");
                setStatusFilter("");
                setEnvironmentFilter("");
                setSearchQuery("");
                fetchIncidents();
              }}
              className="text-blue-400 underline font-semibold"
            >
              Clear All Filters
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/50 text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Incident & Service</th>
                  <th className="py-3 px-4">Lifecycle State</th>
                  <th className="py-3 px-4">Environment</th>
                  <th className="py-3 px-4">Owner / Responder</th>
                  <th className="py-3 px-4">Detected</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs font-sans">
                {incidents.map((incident) => (
                  <tr
                    key={incident.id}
                    className="hover:bg-slate-800/40 transition-colors group"
                  >
                    {/* Severity / Priority */}
                    <td className="py-3 px-4 shrink-0">
                      <span
                        className={`text-[10px] font-mono font-bold px-2.5 py-1 rounded-md border ${getSeverityBadge(
                          incident.severity
                        )}`}
                      >
                        {incident.severity}
                      </span>
                    </td>

                    {/* Title & Service */}
                    <td className="py-3 px-4 max-w-sm">
                      <Link
                        href={`/incidents/${incident.id}`}
                        className="text-sm font-semibold text-white group-hover:text-blue-400 transition-colors line-clamp-1 block"
                      >
                        {incident.title}
                      </Link>
                      <div className="flex items-center gap-2 mt-1">
                        {incident.impact_scope && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                            svc: {incident.impact_scope}
                          </span>
                        )}
                        {incident.is_escalated && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40 flex items-center gap-1">
                            <Flame className="w-2.5 h-2.5 text-rose-400" />
                            {incident.escalation_status}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Lifecycle Status */}
                    <td className="py-3 px-4">
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded border ${getStatusBadge(
                          incident.status
                        )}`}
                      >
                        {incident.status}
                      </span>
                    </td>

                    {/* Environment */}
                    <td className="py-3 px-4">
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                          incident.environment === "KUBERNETES"
                            ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/30"
                            : "bg-slate-800 text-slate-400 border-slate-700"
                        }`}
                      >
                        {incident.environment || "DEMOMESH"}
                      </span>
                    </td>

                    {/* Owner / Responder */}
                    <td className="py-3 px-4">
                      <div className="text-xs text-slate-200 font-mono flex items-center gap-1.5">
                        <UserCheck className="w-3.5 h-3.5 text-slate-400" />
                        <span>{incident.owner_name || "Unassigned"}</span>
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                        {incident.assigned_team || "Platform SRE"}
                      </div>
                    </td>

                    {/* Detected */}
                    <td className="py-3 px-4 text-slate-400 font-mono text-[11px] whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-500" />
                        {new Date(incident.detected_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        {new Date(incident.detected_at).toLocaleDateString()}
                      </div>
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {incident.status === "DETECTED" && (
                          <button
                            onClick={() => handleQuickAcknowledge(incident.id)}
                            className="px-2.5 py-1 rounded bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 text-[11px] font-mono font-medium"
                            title="Acknowledge Alert"
                          >
                            Ack
                          </button>
                        )}
                        <Link
                          href={`/incidents/${incident.id}`}
                          className="flex items-center gap-1 px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono font-medium transition-colors border border-slate-700"
                        >
                          <span>Command</span>
                          <ArrowRight className="w-3 h-3 text-slate-400" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Module 9.3: Alert Ingestion Simulator Modal */}
      {isAlertModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative">
            <button
              onClick={() => {
                setIsAlertModalOpen(false);
                setAlertIngestResult(null);
              }}
              className="absolute top-5 right-5 p-1 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 mb-1">
              <Radio className="w-5 h-5 text-purple-400 animate-pulse" />
              <h2 className="text-base font-bold text-white font-mono">
                Simulate Inbound Telemetry Alert
              </h2>
            </div>
            <p className="text-xs text-slate-400 mb-4 font-sans">
              Module 9.3 webhook endpoint: normalizes payloads from Alertmanager, Grafana, or Kubernetes events and automatically deduplicates with sub-second MTTA.
            </p>

            {alertIngestResult && (
              <div
                className={`p-3.5 mb-4 rounded-xl border text-xs font-mono ${
                  alertIngestResult.action === "CREATED"
                    ? "bg-emerald-950/20 border-emerald-500/40 text-emerald-300"
                    : "bg-blue-950/20 border-blue-500/40 text-blue-300"
                }`}
              >
                <div className="font-bold flex items-center justify-between">
                  <span>Action: {alertIngestResult.action}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-700">
                    Fingerprint: {alertIngestResult.fingerprint.slice(0, 10)}...
                  </span>
                </div>
                <div className="mt-1 text-slate-300">{alertIngestResult.summary}</div>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-[11px] text-slate-400">Incident ID: {alertIngestResult.incident_id}</span>
                  <Link
                    href={`/incidents/${alertIngestResult.incident_id}`}
                    className="text-blue-400 hover:underline flex items-center gap-1 font-bold"
                  >
                    View in Command Center <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            )}

            <form onSubmit={handleSimulateAlert} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">
                    Alert Source Provider *
                  </label>
                  <select
                    value={alertSource}
                    onChange={(e) => setAlertSource(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white font-mono focus:outline-none focus:border-purple-500"
                  >
                    <option value="alertmanager">Prometheus Alertmanager</option>
                    <option value="grafana">Grafana Alerting</option>
                    <option value="kubernetes">Kubernetes Warning Event</option>
                    <option value="generic_webhook">Custom Webhook</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">Severity Tier *</label>
                  <select
                    value={alertSeverity}
                    onChange={(e) => setAlertSeverity(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white font-mono focus:outline-none focus:border-purple-500"
                  >
                    <option value="P1">P1 (Critical Outage)</option>
                    <option value="P2">P2 (High Degradation)</option>
                    <option value="P3">P3 (Medium Impact)</option>
                    <option value="P4">P4 (Low)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">Target Service *</label>
                  <input
                    type="text"
                    required
                    value={alertServiceName}
                    onChange={(e) => setAlertServiceName(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white font-mono focus:outline-none focus:border-purple-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">Environment *</label>
                  <select
                    value={alertEnvironment}
                    onChange={(e) => setAlertEnvironment(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white font-mono focus:outline-none focus:border-purple-500"
                  >
                    <option value="DEMOMESH">DEMOMESH (Simulated)</option>
                    <option value="KUBERNETES">KUBERNETES (Cluster Live)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">Alert Name / Rule *</label>
                <input
                  type="text"
                  required
                  value={alertName}
                  onChange={(e) => setAlertName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white font-mono focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">Alert Description *</label>
                <textarea
                  rows={2}
                  required
                  value={alertDescription}
                  onChange={(e) => setAlertDescription(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white font-sans focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => {
                    setIsAlertModalOpen(false);
                    setAlertIngestResult(null);
                  }}
                  className="px-4 py-2 rounded-lg border border-slate-700 text-xs font-mono text-slate-400 hover:text-white"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={isAlertSubmitting}
                  className="px-5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-xs font-mono font-bold text-white shadow-md shadow-purple-500/20 flex items-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{isAlertSubmitting ? "Ingesting..." : "Fire Alert Webhook"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Incident Creation Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative">
            <button
              onClick={() => setIsModalOpen(false)}
              className="absolute top-5 right-5 p-1 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <h2 className="text-base font-bold text-white font-mono mb-1">
              Declare Production Incident
            </h2>
            <p className="text-xs text-slate-400 mb-4 font-sans">
              Registers a new failure event into PostgreSQL and initializes the Incident Command Center.
            </p>

            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">Incident Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Postgres Connection Pool Starvation in Order Service"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 font-sans focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">Severity Tier *</label>
                  <select
                    value={newSeverity}
                    onChange={(e) => setNewSeverity(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
                  >
                    <option value="P1">P1 (Critical Outage)</option>
                    <option value="P2">P2 (High Degradation)</option>
                    <option value="P3">P3 (Medium Impact)</option>
                    <option value="P4">P4 (Low / Cosmetic)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">Environment *</label>
                  <select
                    value={newEnvironment}
                    onChange={(e) => setNewEnvironment(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
                  >
                    <option value="DEMOMESH">DEMOMESH (Simulated)</option>
                    <option value="KUBERNETES">KUBERNETES (Cluster Live)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">Affected Service</label>
                  <input
                    type="text"
                    placeholder="e.g. order-service, api-gw"
                    value={newImpact}
                    onChange={(e) => setNewImpact(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white font-sans focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">Initial Owner</label>
                  <input
                    type="text"
                    placeholder="e.g. IncidentX AI (Tier-1)"
                    value={newOwner}
                    onChange={(e) => setNewOwner(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white font-sans focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">Summary / Initial Observations</label>
                <textarea
                  rows={2}
                  placeholder="Describe initial symptoms, alert alerts, and observed latency spikes..."
                  value={newSummary}
                  onChange={(e) => setNewSummary(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 font-sans focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-slate-700 text-xs font-mono text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-mono font-bold text-white shadow-md shadow-blue-500/20"
                >
                  {isSubmitting ? "Creating..." : "Declare Incident"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
