"use client";

import { useEffect, useState } from "react";
import { 
  Radio, 
  Activity, 
  AlertTriangle, 
  CheckCircle2, 
  Search, 
  RefreshCw, 
  SlidersHorizontal,
  ChevronRight,
  Clock,
  Layers,
  Terminal,
  FileText,
  ExternalLink
} from "lucide-react";
import { api } from "../../services/api";
import { ClusterOverview, Trace, LogRecord, AnomalyAlert } from "../../types";

export default function TelemetryPage() {
  const [activeTab, setActiveTab] = useState<"metrics" | "traces" | "logs">("metrics");
  const [overview, setOverview] = useState<ClusterOverview | null>(null);
  const [servicesData, setServicesData] = useState<Record<string, any>>({});
  const [alerts, setAlerts] = useState<AnomalyAlert[]>([]);
  const [traces, setTraces] = useState<Trace[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<Trace | null>(null);
  const [logs, setLogs] = useState<LogRecord[]>([]);
  
  // Filters
  const [serviceFilter, setServiceFilter] = useState<string>("");
  const [logLevelFilter, setLogLevelFilter] = useState<string>("");
  const [logSearch, setLogSearch] = useState<string>("");
  const [traceOnlyErrors, setTraceOnlyErrors] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchTelemetry = async () => {
    try {
      const [ovRes, svcRes, alertRes] = await Promise.all([
        api.getClusterOverview().catch(() => null),
        api.listLiveServices().catch(() => ({ services: {}, data_source: "LIVE" })),
        api.listAlerts(30).catch(() => []),
      ]);

      setOverview(ovRes);
      setServicesData(svcRes.services || {});
      setAlerts(alertRes || []);

      if (activeTab === "traces") {
        const traceRes = await api.listTraces({
          limit: 30,
          service: serviceFilter || undefined,
          only_errors: traceOnlyErrors,
        });
        setTraces(traceRes.traces || []);
        if (selectedTrace) {
          const updated = traceRes.traces.find(t => t.trace_id === selectedTrace.trace_id);
          if (updated) setSelectedTrace(updated);
        }
      } else if (activeTab === "logs") {
        const logRes = await api.listLogs({
          limit: 80,
          service: serviceFilter || undefined,
          level: logLevelFilter || undefined,
          search: logSearch || undefined,
        });
        setLogs(logRes.logs || []);
      }
    } catch (err) {
      console.error("Failed to load telemetry:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTelemetry();
    if (!autoRefresh) return;
    const interval = setInterval(fetchTelemetry, 2500);
    return () => clearInterval(interval);
  }, [activeTab, serviceFilter, logLevelFilter, logSearch, traceOnlyErrors, autoRefresh]);

  const isSimulated = overview?.data_source === "SIMULATED";

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">Telemetry Explorer</h1>
            <span
              className={`px-2.5 py-1 rounded-full text-[11px] font-mono font-bold tracking-wider uppercase border ${
                isSimulated
                  ? "bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse"
                  : "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
              }`}
            >
              {isSimulated ? "SIMULATED TELEMETRY" : "LIVE TELEMETRY"}
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Real-time OpenTelemetry distributed traces, Prometheus operational metrics, and correlated logs.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <label className="flex items-center space-x-2 text-xs font-mono text-slate-400 cursor-pointer bg-slate-900 px-3 py-2 rounded-xl border border-slate-800">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-blue-500 focus:ring-0"
            />
            <span>Auto Refresh (2.5s)</span>
          </label>
          <button
            onClick={() => fetchTelemetry()}
            className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 px-3.5 py-2 rounded-xl text-xs font-medium transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Cluster KPI Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#0f172a] border border-slate-800 p-4 rounded-xl">
          <div className="text-xs font-mono text-slate-400 uppercase">Throughput</div>
          <div className="text-2xl font-bold font-mono text-white mt-1">
            {overview?.total_request_rate ?? "--"} <span className="text-xs text-slate-400 font-normal">rps</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Cluster-wide ingress & internal</div>
        </div>

        <div className="bg-[#0f172a] border border-slate-800 p-4 rounded-xl">
          <div className="text-xs font-mono text-slate-400 uppercase">Error Rate</div>
          <div className="text-2xl font-bold font-mono text-white mt-1">
            <span className={overview && overview.overall_error_rate > 5 ? "text-red-400" : "text-emerald-400"}>
              {overview?.overall_error_rate ?? "--"}%
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Threshold limit: 5.0%</div>
        </div>

        <div className="bg-[#0f172a] border border-slate-800 p-4 rounded-xl">
          <div className="text-xs font-mono text-slate-400 uppercase">P95 Tail Latency</div>
          <div className="text-2xl font-bold font-mono text-white mt-1">
            <span className={overview && overview.max_p95_latency_ms > 1000 ? "text-amber-400" : "text-white"}>
              {overview?.max_p95_latency_ms ?? "--"} <span className="text-xs text-slate-400 font-normal">ms</span>
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Avg: {overview?.avg_p95_latency_ms ?? "--"}ms</div>
        </div>

        <div className="bg-[#0f172a] border border-slate-800 p-4 rounded-xl">
          <div className="text-xs font-mono text-slate-400 uppercase">Active Anomalies</div>
          <div className="text-2xl font-bold font-mono text-white mt-1">
            <span className={alerts.length > 0 ? "text-amber-400" : "text-emerald-400"}>
              {alerts.length}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Evaluated across 5 detectors</div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 gap-6">
        <button
          onClick={() => setActiveTab("metrics")}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition ${
            activeTab === "metrics"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Activity className="w-4 h-4" />
          <span>Real-time Metrics & Alerts</span>
        </button>

        <button
          onClick={() => setActiveTab("traces")}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition ${
            activeTab === "traces"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Distributed Traces Waterfall</span>
        </button>

        <button
          onClick={() => setActiveTab("logs")}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition ${
            activeTab === "logs"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Correlated Log Stream</span>
        </button>
      </div>

      {/* Tab 1: Real-Time Metrics & Anomaly Alerts */}
      {activeTab === "metrics" && (
        <div className="space-y-6">
          {/* Microservices Metrics Table */}
          <div className="bg-[#0f172a] border border-slate-800 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <h2 className="text-sm font-bold text-white tracking-wide uppercase font-mono">
                Microservice Telemetry Mesh (7 Nodes)
              </h2>
              <span className="text-xs font-mono text-slate-400">1-Second Resolution</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/60 text-slate-400 font-mono uppercase text-[10px] border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Service</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Throughput</th>
                    <th className="py-3 px-4">Error Rate</th>
                    <th className="py-3 px-4">P50</th>
                    <th className="py-3 px-4">P95</th>
                    <th className="py-3 px-4">P99</th>
                    <th className="py-3 px-4">CPU</th>
                    <th className="py-3 px-4">Memory</th>
                    <th className="py-3 px-4">DB Pool</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {Object.entries(servicesData).map(([name, data]: [string, any]) => {
                    const health = data.health_status || "HEALTHY";
                    return (
                      <tr key={name} className="hover:bg-slate-800/30 transition">
                        <td className="py-3 px-4 font-semibold text-white flex items-center gap-2">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              health === "HEALTHY"
                                ? "bg-emerald-500"
                                : health === "DEGRADED"
                                ? "bg-amber-500 animate-pulse"
                                : "bg-red-500 animate-pulse"
                            }`}
                          />
                          {name}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              health === "HEALTHY"
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                : health === "DEGRADED"
                                ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                : "bg-red-500/10 text-red-400 border border-red-500/20"
                            }`}
                          >
                            {health}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-200">{data.request_rate ?? "--"} rps</td>
                        <td className="py-3 px-4">
                          <span className={data.error_rate > 5 ? "text-red-400 font-bold" : "text-slate-300"}>
                            {data.error_rate ?? "0.0"}%
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-300">{data.latency_p50_ms ?? "--"}ms</td>
                        <td className="py-3 px-4">
                          <span className={data.latency_p95_ms > 800 ? "text-amber-400 font-bold" : "text-slate-300"}>
                            {data.latency_p95_ms ?? "--"}ms
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={data.latency_p99_ms > 1500 ? "text-red-400 font-bold" : "text-slate-300"}>
                            {data.latency_p99_ms ?? "--"}ms
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={data.cpu_utilization > 85 ? "text-red-400 font-bold" : "text-slate-300"}>
                            {data.cpu_utilization ?? "--"}%
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={data.memory_utilization > 85 ? "text-amber-400 font-bold" : "text-slate-300"}>
                            {data.memory_utilization ?? "--"}%
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={data.db_pool_utilization > 80 ? "text-red-400 font-bold" : "text-slate-400"}>
                            {data.db_pool_utilization > 0 ? `${data.db_pool_utilization}%` : "--"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Anomaly Alerts Feed */}
          <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-white tracking-wide uppercase font-mono flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Live Anomaly Alert Stream (5 Detector Engines)
              </h2>
              <span className="text-xs font-mono text-slate-400">Total: {alerts.length}</span>
            </div>

            {alerts.length === 0 ? (
              <div className="text-center py-10 text-slate-400 text-xs font-mono bg-slate-900/40 rounded-xl border border-slate-800/80">
                <CheckCircle2 className="w-6 h-6 text-emerald-500 mx-auto mb-2" />
                No anomalies detected. All 5 detection engines reporting within normal bounds.
              </div>
            ) : (
              <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
                {alerts.map((alert) => (
                  <div
                    key={alert.alert_id}
                    className="p-3 bg-slate-900/70 border border-slate-800 rounded-xl flex items-start justify-between gap-4 text-xs font-mono"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            alert.severity === "CRITICAL"
                              ? "bg-red-500/10 text-red-400 border border-red-500/30"
                              : "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                          }`}
                        >
                          {alert.severity}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-blue-400 border border-slate-700">
                          {alert.detector_type}
                        </span>
                        <span className="text-white font-semibold">{alert.service_name}</span>
                      </div>
                      <p className="text-slate-300 text-xs font-sans">{alert.message}</p>
                    </div>
                    <div className="text-[10px] text-slate-400 whitespace-nowrap">
                      {new Date(alert.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Distributed Trace Waterfall */}
      {activeTab === "traces" && (
        <div className="space-y-6">
          {/* Controls */}
          <div className="flex flex-wrap items-center justify-between gap-4 bg-[#0f172a] border border-slate-800 p-4 rounded-xl">
            <div className="flex items-center gap-3">
              <select
                value={serviceFilter}
                onChange={(e) => setServiceFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-xl px-3 py-2 font-mono"
              >
                <option value="">All Services</option>
                <option value="api-gateway">api-gateway</option>
                <option value="order-service">order-service</option>
                <option value="payment-service">payment-service</option>
                <option value="auth-service">auth-service</option>
                <option value="inventory-service">inventory-service</option>
              </select>

              <label className="flex items-center space-x-2 text-xs font-mono text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={traceOnlyErrors}
                  onChange={(e) => setTraceOnlyErrors(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-red-500 focus:ring-0"
                />
                <span>Errors Only</span>
              </label>
            </div>
            <div className="text-xs font-mono text-slate-400">
              Showing {traces.length} recent traces
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Traces List */}
            <div className={`space-y-2.5 ${selectedTrace ? "lg:col-span-5" : "lg:col-span-12"}`}>
              {traces.length === 0 ? (
                <div className="bg-[#0f172a] border border-slate-800 p-8 rounded-xl text-center text-xs font-mono text-slate-400">
                  No traces match current filters.
                </div>
              ) : (
                traces.map((trace) => {
                  const isSelected = selectedTrace?.trace_id === trace.trace_id;
                  return (
                    <div
                      key={trace.trace_id}
                      onClick={() => setSelectedTrace(trace)}
                      className={`p-4 rounded-xl border cursor-pointer transition ${
                        isSelected
                          ? "bg-blue-600/10 border-blue-500/40"
                          : "bg-[#0f172a] border-slate-800 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs font-mono mb-1.5">
                        <span className="font-semibold text-white truncate max-w-[200px]">
                          {trace.operation_name}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            trace.has_error
                              ? "bg-red-500/10 text-red-400 border border-red-500/20"
                              : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          }`}
                        >
                          HTTP {trace.status_code}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                        <span>Root: {trace.root_service}</span>
                        <span className="text-slate-300 font-semibold">{trace.duration_ms} ms</span>
                      </div>
                      <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 mt-2 pt-2 border-t border-slate-800/80">
                        <span>ID: {trace.trace_id.slice(0, 12)}...</span>
                        <span>{trace.span_count} spans</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Trace Waterfall Detail Pane */}
            {selectedTrace && (
              <div className="lg:col-span-7 bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-white font-mono">{selectedTrace.operation_name}</h3>
                    <p className="text-[11px] font-mono text-slate-400 mt-0.5">
                      Trace ID: <span className="text-blue-400">{selectedTrace.trace_id}</span>
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedTrace(null)}
                    className="text-slate-400 hover:text-white text-xs font-mono"
                  >
                    Close
                  </button>
                </div>

                <div className="space-y-3">
                  <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                    Span Hierarchy & Waterfall Timing ({selectedTrace.duration_ms}ms total)
                  </div>

                  <div className="space-y-2.5">
                    {selectedTrace.spans.map((span) => {
                      const maxDur = Math.max(selectedTrace.duration_ms, 1.0);
                      const leftPercent = (span.start_offset_ms / maxDur) * 100.0;
                      const widthPercent = Math.max((span.duration_ms / maxDur) * 100.0, 3.0);

                      return (
                        <div key={span.span_id} className="p-3 bg-slate-900/80 rounded-xl border border-slate-800 text-xs font-mono space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <span className="font-semibold text-white">{span.service_name}</span>
                              <span className="text-slate-400 text-[11px]">{span.name}</span>
                            </div>
                            <span
                              className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                                span.status === "ERROR"
                                  ? "bg-red-500/10 text-red-400 border border-red-500/20"
                                  : "text-emerald-400"
                              }`}
                            >
                              {span.duration_ms}ms
                            </span>
                          </div>

                          {/* Waterfall timing bar */}
                          <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden relative">
                            <div
                              className={`h-full rounded-full ${
                                span.status === "ERROR" ? "bg-red-500" : "bg-blue-500"
                              }`}
                              style={{
                                marginLeft: `${Math.min(leftPercent, 95)}%`,
                                width: `${Math.min(widthPercent, 100 - leftPercent)}%`,
                              }}
                            />
                          </div>

                          {span.error_message && (
                            <div className="p-2 bg-red-950/40 border border-red-800/40 rounded text-red-300 text-[11px]">
                              {span.error_message}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Correlated Log Stream */}
      {activeTab === "logs" && (
        <div className="space-y-4">
          {/* Log Controls */}
          <div className="flex flex-wrap items-center justify-between gap-4 bg-[#0f172a] border border-slate-800 p-4 rounded-xl">
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search log messages..."
                  value={logSearch}
                  onChange={(e) => setLogSearch(e.target.value)}
                  className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-xl pl-8 pr-3 py-1.5 font-mono w-60"
                />
              </div>

              <select
                value={serviceFilter}
                onChange={(e) => setServiceFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-xl px-3 py-1.5 font-mono"
              >
                <option value="">All Services</option>
                <option value="api-gateway">api-gateway</option>
                <option value="order-service">order-service</option>
                <option value="payment-service">payment-service</option>
                <option value="auth-service">auth-service</option>
                <option value="inventory-service">inventory-service</option>
                <option value="postgres-db">postgres-db</option>
                <option value="redis-cache">redis-cache</option>
              </select>

              <select
                value={logLevelFilter}
                onChange={(e) => setLogLevelFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-xl px-3 py-1.5 font-mono"
              >
                <option value="">All Levels</option>
                <option value="INFO">INFO</option>
                <option value="WARN">WARN</option>
                <option value="ERROR">ERROR</option>
              </select>
            </div>

            <div className="text-xs font-mono text-slate-400">
              {logs.length} correlated log events
            </div>
          </div>

          {/* Log Stream Container */}
          <div className="bg-[#0b101b] border border-slate-800 rounded-xl p-4 font-mono text-xs max-h-[600px] overflow-y-auto space-y-2">
            {logs.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                No logs match query.
              </div>
            ) : (
              logs.map((log) => (
                <div
                  key={log.id}
                  className="p-2.5 rounded-lg bg-slate-900/60 hover:bg-slate-800/50 border border-slate-800/80 flex items-start gap-3 transition"
                >
                  <span className="text-slate-400 text-[10px] whitespace-nowrap pt-0.5">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>

                  <span
                    className={`px-1.5 py-0.2 rounded text-[10px] font-bold shrink-0 ${
                      log.level === "ERROR"
                        ? "bg-red-500/10 text-red-400 border border-red-500/20"
                        : log.level === "WARN"
                        ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                    }`}
                  >
                    {log.level}
                  </span>

                  <span className="text-purple-400 font-semibold shrink-0">
                    [{log.service_name}]
                  </span>

                  <span className="text-slate-300 break-all flex-1">
                    {log.message}
                  </span>

                  {log.trace_id && (
                    <span className="text-slate-400 text-[10px] shrink-0 font-mono">
                      trace:{log.trace_id.slice(0, 8)}
                    </span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
