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
  X
} from "lucide-react";
import { api } from "../../services/api";
import { Incident } from "../../types";

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newSummary, setNewSummary] = useState("");
  const [newSeverity, setNewSeverity] = useState("SEV-2");
  const [newImpact, setNewImpact] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchIncidents = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listIncidents(page, 20, statusFilter || undefined, severityFilter || undefined);
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
  }, [page, severityFilter, statusFilter]);

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
        impact_scope: newImpact.trim() || undefined,
      });
      setIsModalOpen(false);
      setNewTitle("");
      setNewSummary("");
      setNewImpact("");
      fetchIncidents();
    } catch (err: any) {
      alert(`Error creating incident: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case "SEV-1": return "bg-red-500/10 text-red-400 border-red-500/30";
      case "SEV-2": return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "SEV-3": return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      default: return "bg-slate-500/10 text-slate-400 border-slate-500/30";
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            Incident Register
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-medium">
            Active and resolved infrastructure incidents with verified causal histories.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-mono font-bold text-white shadow-lg shadow-blue-500/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Incident</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl border border-slate-800 bg-[#0e1424]">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
            <Filter className="w-3.5 h-3.5" />
            <span>Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => { setSeverityFilter(e.target.value); setPage(1); }}
              className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 text-xs font-mono"
            >
              <option value="">All Severities</option>
              <option value="SEV-1">SEV-1 (Critical)</option>
              <option value="SEV-2">SEV-2 (High)</option>
              <option value="SEV-3">SEV-3 (Medium)</option>
              <option value="SEV-4">SEV-4 (Low)</option>
            </select>
          </div>

          <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
            <span>Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 text-xs font-mono"
            >
              <option value="">All Statuses</option>
              <option value="DETECTED">DETECTED</option>
              <option value="INVESTIGATING">INVESTIGATING</option>
              <option value="MITIGATING">MITIGATING</option>
              <option value="RESOLVED">RESOLVED</option>
              <option value="CLOSED">CLOSED</option>
            </select>
          </div>
        </div>

        <span className="text-xs font-mono text-slate-400">
          Showing <strong className="text-white">{incidents.length}</strong> of <strong className="text-white">{total}</strong> records
        </span>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl border border-red-500/30 bg-red-950/20 text-red-300 text-xs font-mono">
          {error}
        </div>
      )}

      {/* Incidents Table / List */}
      <div className="rounded-xl border border-slate-800 bg-[#0e1424] overflow-hidden shadow-sm">
        {loading ? (
          <div className="py-16 text-center text-xs font-mono text-slate-500">
            Fetching incident records from PostgreSQL...
          </div>
        ) : incidents.length === 0 ? (
          <div className="py-16 text-center text-xs font-mono text-slate-500 space-y-2">
            <p>No incidents match the active filter criteria.</p>
            <button
              onClick={() => { setSeverityFilter(""); setStatusFilter(""); }}
              className="text-blue-400 underline font-semibold"
            >
              Clear Filters
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {incidents.map((incident) => (
              <Link
                key={incident.id}
                href={`/incidents/${incident.id}`}
                className="block p-4 hover:bg-slate-800/40 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div className="flex items-center space-x-3">
                    <span className={`text-[10px] font-mono font-bold px-2.5 py-1 rounded-md border ${getSeverityBadge(incident.severity)}`}>
                      {incident.severity}
                    </span>
                    <div>
                      <h3 className="text-sm font-semibold text-white tracking-tight">
                        {incident.title}
                      </h3>
                      {incident.summary && (
                        <p className="text-xs text-slate-400 line-clamp-1 mt-0.5">
                          {incident.summary}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-4 shrink-0 text-xs font-mono text-slate-400">
                    <span className="px-2 py-0.5 rounded border border-slate-700 bg-slate-900 text-slate-300">
                      {incident.status}
                    </span>
                    <span className="text-[11px] text-slate-500 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {new Date(incident.detected_at).toLocaleString()}
                    </span>
                    <ArrowRight className="w-4 h-4 text-slate-600" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Creation Modal */}
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
              Create New Incident Record
            </h2>
            <p className="text-xs text-slate-400 mb-4 font-sans">
              Registers a new failure event into PostgreSQL and initializes the investigation plane.
            </p>

            <form onSubmit={handleCreate} className="space-y-4">
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
                    <option value="SEV-1">SEV-1 (Critical Outage)</option>
                    <option value="SEV-2">SEV-2 (High Degradation)</option>
                    <option value="SEV-3">SEV-3 (Medium Impact)</option>
                    <option value="SEV-4">SEV-4 (Low / Cosmetic)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">Impact Scope</label>
                  <input
                    type="text"
                    placeholder="e.g. order-service, api-gw"
                    value={newImpact}
                    onChange={(e) => setNewImpact(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white font-sans focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">Summary / Initial Observations</label>
                <textarea
                  rows={3}
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
                  {isSubmitting ? "Creating..." : "Register Incident"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
