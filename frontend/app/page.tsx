"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  AlertTriangle, 
  Server, 
  Activity, 
  ShieldCheck, 
  ArrowRight, 
  Clock, 
  Terminal,
  RefreshCw,
  Radio,
  Flame,
  CheckCircle2,
  AlertCircle
} from "lucide-react";
import { api } from "../services/api";
import { Incident, Service, AuditLog, SystemHealth, ClusterOverview } from "../types";

export default function DashboardPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [overview, setOverview] = useState<ClusterOverview | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [incRes, svcRes, auditRes, healthRes, ovRes] = await Promise.all([
        api.listIncidents(1, 6),
        api.listServices(1, 100),
        api.listAuditLogs(1, 5),
        api.getHealth().catch(() => null),
        api.getClusterOverview().catch(() => null),
      ]);
      setIncidents(incRes.items);
      setServices(svcRes.items);
      setAuditLogs(auditRes.items);
      setHealth(healthRes);
      setOverview(ovRes);
    } catch (err: any) {
      setError(err.message || "Failed to load system dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, []);

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case "SEV-1": return "bg-red-500/10 text-red-400 border-red-500/30";
      case "SEV-2": return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "SEV-3": return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      default: return "bg-slate-500/10 text-slate-400 border-slate-500/30";
    }
  };

  const isSimulated = overview?.data_source === "SIMULATED";

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">System Reliability Overview</h1>
            <span
              className={`px-2.5 py-1 rounded-full text-[11px] font-mono font-bold tracking-wider uppercase border ${
                isSimulated
                  ? "bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse"
                  : "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
              }`}
            >
              {isSimulated ? "DATA: SIMULATED" : "DATA: LIVE"}
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Real-time autonomous observability, multi-signal anomaly correlation, and incident triage.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Link
            href="/simulation"
            className="flex items-center space-x-2 bg-red-600/10 hover:bg-red-600/20 text-red-400 border border-red-500/30 px-3.5 py-2 rounded-xl text-xs font-mono font-medium transition"
          >
            <Flame className="w-3.5 h-3.5 text-red-400" />
            <span>Chaos Lab</span>
          </Link>
          <Link
            href="/telemetry"
            className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3.5 py-2 rounded-xl text-xs font-mono font-medium transition"
          >
            <Radio className="w-3.5 h-3.5 text-blue-400" />
            <span>Telemetry</span>
          </Link>
          <button
            onClick={() => loadData()}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* KPI Cards Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">Cluster Health</div>
            <div className="text-xl font-bold text-white mt-1 flex items-center gap-2">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  overview?.cluster_status === "HEALTHY"
                    ? "bg-emerald-500"
                    : overview?.cluster_status === "DEGRADED"
                    ? "bg-amber-500 animate-pulse"
                    : "bg-red-500 animate-pulse"
                }`}
              />
              {overview?.cluster_status ?? "HEALTHY"}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {overview?.healthy_services ?? 7} healthy / {overview?.total_services ?? 7} services
            </div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">Throughput</div>
            <div className="text-2xl font-bold font-mono text-white mt-1">
              {overview?.total_request_rate ?? "--"} <span className="text-xs text-slate-400 font-normal">rps</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">Ingress + Service Mesh</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
            <Activity className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">Cluster Error Rate</div>
            <div className="text-2xl font-bold font-mono mt-1">
              <span className={overview && overview.overall_error_rate > 5 ? "text-red-400 font-bold" : "text-emerald-400"}>
                {overview?.overall_error_rate ?? "0.0"}%
              </span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">Threshold limit: 5.0%</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
            <AlertCircle className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-[#0f172a] border border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">P95 Tail Latency</div>
            <div className="text-2xl font-bold font-mono text-white mt-1">
              <span className={overview && overview.max_p95_latency_ms > 1000 ? "text-amber-400" : "text-white"}>
                {overview?.max_p95_latency_ms ?? "--"} <span className="text-xs text-slate-400 font-normal">ms</span>
              </span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">Avg: {overview?.avg_p95_latency_ms ?? "--"}ms</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
            <Clock className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Main Two Column Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Recent Incidents */}
        <div className="lg:col-span-7 bg-[#0f172a] border border-slate-800 rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-white tracking-wide uppercase font-mono flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Autonomous Incident Detection Stream
              </h2>
              <Link href="/incidents" className="text-xs font-mono text-blue-400 hover:text-blue-300 flex items-center gap-1">
                <span>View all</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {incidents.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-xs font-mono bg-slate-900/40 rounded-xl border border-slate-800/80">
                <CheckCircle2 className="w-6 h-6 text-emerald-500 mx-auto mb-2" />
                No active incidents detected. All services operating normally.
              </div>
            ) : (
              <div className="space-y-3">
                {incidents.map((incident) => (
                  <Link
                    key={incident.id}
                    href={`/incidents/${incident.id}`}
                    className="block p-3.5 rounded-xl bg-slate-900/60 hover:bg-slate-800/60 border border-slate-800/90 transition group"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${getSeverityBadge(incident.severity)}`}>
                            {incident.severity}
                          </span>
                          <span className="text-xs font-bold text-slate-200 group-hover:text-blue-400 transition">
                            {incident.title}
                          </span>
                        </div>
                        {incident.summary && (
                          <p className="text-[11px] text-slate-400 mt-1 line-clamp-1">{incident.summary}</p>
                        )}
                      </div>
                      <span className="text-[10px] font-mono text-slate-400 whitespace-nowrap">
                        {new Date(incident.detected_at).toLocaleTimeString()}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="pt-4 mt-4 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono text-slate-400">
            <span>Correlation Engine: ACTIVE</span>
            <Link href="/incidents" className="text-blue-400 hover:underline">
              Inspect Courtroom & Evidence →
            </Link>
          </div>
        </div>

        {/* Right Column: Microservices Mesh Grid */}
        <div className="lg:col-span-5 bg-[#0f172a] border border-slate-800 rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-white tracking-wide uppercase font-mono flex items-center gap-2">
                <Server className="w-4 h-4 text-blue-400" />
                E-Commerce Mesh Topology
              </h2>
              <Link href="/services" className="text-xs font-mono text-blue-400 hover:text-blue-300 flex items-center gap-1">
                <span>Services</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="space-y-2.5">
              {services.map((svc) => (
                <div
                  key={svc.id}
                  className="p-3 bg-slate-900/60 rounded-xl border border-slate-800/80 flex items-center justify-between text-xs font-mono"
                >
                  <div className="flex items-center space-x-2.5">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        svc.health_status === "HEALTHY"
                          ? "bg-emerald-500"
                          : svc.health_status === "DEGRADED"
                          ? "bg-amber-500 animate-pulse"
                          : "bg-red-500 animate-pulse"
                      }`}
                    />
                    <span className="text-slate-200 font-semibold">{svc.name}</span>
                    <span className="text-[10px] text-slate-400">({svc.service_type})</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] text-slate-400">{svc.tier}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                        svc.health_status === "HEALTHY"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-red-500/10 text-red-400 border border-red-500/20"
                      }`}
                    >
                      {svc.health_status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-4 mt-4 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono text-slate-400">
            <span>7 Distributed Nodes</span>
            <Link href="/telemetry" className="text-blue-400 hover:underline">
              View Waterfall Traces →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
