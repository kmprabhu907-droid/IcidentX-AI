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
  ExternalLink,
  TrendingUp,
  TrendingDown,
  ShieldAlert,
  Info,
  Gauge,
  Zap,
  Check,
  XCircle,
  Sparkles,
  HelpCircle,
  Database
} from "lucide-react";
import { api } from "../../services/api";
import { 
  ClusterOverview, 
  Trace, 
  LogRecord, 
  AnomalyAlert, 
  AnomalyRecordItem, 
  MetricBaselineItem, 
  DetectionStatus 
} from "../../types";

export default function TelemetryPage() {
  const [activeTab, setActiveTab] = useState<"metrics" | "traces" | "logs" | "anomalies">("metrics");
  const [overview, setOverview] = useState<ClusterOverview | null>(null);
  const [servicesData, setServicesData] = useState<Record<string, any>>({});
  const [alerts, setAlerts] = useState<AnomalyAlert[]>([]);
  const [traces, setTraces] = useState<Trace[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<Trace | null>(null);
  const [logs, setLogs] = useState<LogRecord[]>([]);

  // Stage 5.2 Anomaly & Resource Creep State
  const [anomalies, setAnomalies] = useState<AnomalyRecordItem[]>([]);
  const [selectedAnomaly, setSelectedAnomaly] = useState<AnomalyRecordItem | null>(null);
  const [detectionStatus, setDetectionStatus] = useState<DetectionStatus | null>(null);
  const [anomalyStatusFilter, setAnomalyStatusFilter] = useState<string>("");
  const [anomalySeverityFilter, setAnomalySeverityFilter] = useState<string>("");
  const [anomalyServiceFilter, setAnomalyServiceFilter] = useState<string>("");
  const [baselinesMap, setBaselinesMap] = useState<Record<string, MetricBaselineItem>>({});
  const [isTriggeringDetection, setIsTriggeringDetection] = useState<boolean>(false);
  const [statusUpdating, setStatusUpdating] = useState<boolean>(false);
  
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
      } else if (activeTab === "anomalies") {
        const [anomRes, detStatusRes] = await Promise.all([
          api.listAnomalies({
            service_name: anomalyServiceFilter || undefined,
            severity: anomalySeverityFilter || undefined,
            status: anomalyStatusFilter || undefined,
            page_size: 50,
          }).catch(() => ({ items: [], total: 0, page: 1, page_size: 50, total_pages: 0 })),
          api.getDetectionStatus().catch(() => null),
        ]);
        setAnomalies(anomRes.items || []);
        if (detStatusRes) setDetectionStatus(detStatusRes);
        if (selectedAnomaly) {
          const updated = anomRes.items.find(a => a.id === selectedAnomaly.id);
          if (updated) setSelectedAnomaly(updated);
        } else if (anomRes.items.length > 0) {
          setSelectedAnomaly(anomRes.items[0]);
        }
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
  }, [
    activeTab, 
    serviceFilter, 
    logLevelFilter, 
    logSearch, 
    traceOnlyErrors, 
    autoRefresh,
    anomalyStatusFilter,
    anomalySeverityFilter,
    anomalyServiceFilter
  ]);

  // Fetch baselines when selected anomaly changes
  useEffect(() => {
    if (selectedAnomaly?.service_name) {
      api.getServiceBaselines(selectedAnomaly.service_name)
        .then(res => setBaselinesMap(res.baselines || {}))
        .catch(() => setBaselinesMap({}));
    }
  }, [selectedAnomaly?.service_name]);

  const handleUpdateStatus = async (anomalyId: string, newStatus: string) => {
    try {
      setStatusUpdating(true);
      const updated = await api.updateAnomalyStatus(anomalyId, newStatus);
      setAnomalies(prev => prev.map(a => a.id === anomalyId ? updated : a));
      if (selectedAnomaly?.id === anomalyId) {
        setSelectedAnomaly(updated);
      }
    } catch (err) {
      console.error("Failed to update anomaly status:", err);
    } finally {
      setStatusUpdating(false);
    }
  };

  const handleTriggerDetection = async () => {
    try {
      setIsTriggeringDetection(true);
      await api.triggerDetectionCycle();
      await fetchTelemetry();
    } catch (err) {
      console.error("Failed to trigger detection cycle:", err);
    } finally {
      setIsTriggeringDetection(false);
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return "bg-red-500/10 text-red-400 border-red-500/30";
      case "HIGH":
        return "bg-orange-500/10 text-orange-400 border-orange-500/30";
      case "MEDIUM":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "LOW":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/30";
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ACTIVE":
        return "bg-red-500/10 text-red-400 border-red-500/30 animate-pulse";
      case "ACKNOWLEDGED":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "RESOLVED":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "FALSE_POSITIVE":
        return "bg-slate-500/10 text-slate-400 border-slate-500/30";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

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
            <span className={alerts.length > 0 || (detectionStatus?.active_anomalies_count || 0) > 0 ? "text-amber-400" : "text-emerald-400"}>
              {(detectionStatus?.active_anomalies_count ?? alerts.length)}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {detectionStatus ? `${detectionStatus.monitored_services} services monitored` : "Evaluated across detectors"}
          </div>
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

        <button
          onClick={() => setActiveTab("anomalies")}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition ${
            activeTab === "anomalies"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          <span>Anomalies & Resource Creep</span>
          {anomalies.filter(a => a.status === "ACTIVE").length > 0 && (
            <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-red-500/20 text-red-400 border border-red-500/30">
              {anomalies.filter(a => a.status === "ACTIVE").length}
            </span>
          )}
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
                        <td className="py-3 px-4 text-slate-200">
                          {data.throughput_rps ?? data.request_rate ?? 0} rps
                        </td>
                        <td className="py-3 px-4">
                          <span className={(data.error_rate_percent || 0) > 5 ? "text-red-400 font-bold" : "text-slate-300"}>
                            {(data.error_rate_percent || 0).toFixed(1)}%
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          {Math.round(data.p50_latency_ms || 0)}ms
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          <span className={(data.p95_latency_ms || 0) > 500 ? "text-amber-400 font-bold" : "text-slate-300"}>
                            {Math.round(data.p95_latency_ms || 0)}ms
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          {Math.round(data.p99_latency_ms || 0)}ms
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          {(data.cpu_usage_percent || 0).toFixed(1)}%
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          {(data.memory_usage_percent || 0).toFixed(1)}%
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          {data.db_pool_utilization !== undefined ? `${(data.db_pool_utilization).toFixed(1)}%` : "N/A"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Anomaly Alerts List */}
          <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span>Real-Time Anomaly Detection Alerts</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Instant statistical & dynamic threshold breaches across microservice nodes
                </p>
              </div>
              <span className="text-xs font-mono text-slate-400">
                {alerts.length} active notifications
              </span>
            </div>

            {alerts.length === 0 ? (
              <div className="bg-slate-900/50 border border-slate-800/80 rounded-xl p-8 text-center space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                <div className="text-sm font-semibold text-slate-200">All Nodes Within Nominal Baselines</div>
                <div className="text-xs text-slate-400">
                  No sudden spikes, pool saturation, or error rate anomalies detected in the last evaluation window.
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {alerts.map((alert) => (
                  <div
                    key={alert.alert_id}
                    className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase border ${
                            alert.severity === "CRITICAL"
                              ? "bg-red-500/10 text-red-400 border-red-500/30"
                              : alert.severity === "WARN"
                              ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                              : "bg-blue-500/10 text-blue-400 border-blue-500/30"
                          }`}
                        >
                          {alert.severity}
                        </span>
                        <span className="text-xs font-mono font-bold text-white">
                          [{alert.service_name}]
                        </span>
                        <span className="text-xs font-mono text-slate-400">
                          {alert.detector_type}
                        </span>
                      </div>
                      <span className="text-[11px] font-mono text-slate-400">
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </span>
                    </div>

                    <div className="text-sm text-slate-200">{alert.message}</div>

                    <div className="flex items-center gap-4 text-xs font-mono text-slate-400 pt-1 border-t border-slate-800/60">
                      <div>
                        Metric: <span className="text-slate-200">{alert.metric_name}</span>
                      </div>
                      <div>
                        Observed: <span className="text-amber-400 font-bold">{alert.current_value}</span>
                      </div>
                      <div>
                        Baseline: <span className="text-slate-200">{alert.threshold_or_baseline}</span>
                      </div>
                      {alert.deviation_sigma !== undefined && alert.deviation_sigma !== null && (
                        <div>
                          Deviation: <span className="text-red-400 font-bold">+{alert.deviation_sigma}σ</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Distributed Traces Waterfall */}
      {activeTab === "traces" && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 bg-[#0f172a] border border-slate-800 p-4 rounded-xl">
            <div className="flex flex-wrap items-center gap-3">
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

              <label className="flex items-center space-x-2 text-xs font-mono text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={traceOnlyErrors}
                  onChange={(e) => setTraceOnlyErrors(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-red-500 focus:ring-0"
                />
                <span>Only Error Traces</span>
              </label>
            </div>

            <div className="text-xs font-mono text-slate-400">
              Showing {traces.length} distributed traces
            </div>
          </div>

          {/* Trace List & Waterfall Split Pane */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left list: Traces */}
            <div className="lg:col-span-5 space-y-3 max-h-[640px] overflow-y-auto pr-1">
              {traces.length === 0 ? (
                <div className="p-8 text-center text-xs font-mono text-slate-400 bg-[#0f172a] border border-slate-800 rounded-xl">
                  No traces found matching filter.
                </div>
              ) : (
                traces.map((trace) => {
                  const isSelected = selectedTrace?.trace_id === trace.trace_id;
                  return (
                    <div
                      key={trace.trace_id}
                      onClick={() => setSelectedTrace(trace)}
                      className={`p-4 rounded-xl border transition cursor-pointer space-y-2 ${
                        isSelected
                          ? "bg-slate-800/90 border-blue-500/80 shadow-lg"
                          : "bg-[#0f172a] border-slate-800 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                              trace.has_error
                                ? "bg-red-500/10 text-red-400 border border-red-500/20"
                                : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            }`}
                          >
                            HTTP {trace.status_code}
                          </span>
                          <span className="text-xs font-bold text-white font-mono">
                            {trace.operation_name}
                          </span>
                        </div>
                        <span className="text-xs font-mono text-slate-400">
                          {Math.round(trace.duration_ms)}ms
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                        <span>Root: {trace.root_service}</span>
                        <span>{trace.span_count} spans</span>
                        <span>{new Date(trace.start_time).toLocaleTimeString()}</span>
                      </div>

                      <div className="text-[10px] font-mono text-slate-400 truncate">
                        ID: {trace.trace_id}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Right pane: Waterfall Spans View */}
            {selectedTrace && (
              <div className="lg:col-span-7 bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                      <span>Waterfall: {selectedTrace.operation_name}</span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded ${
                          selectedTrace.has_error
                            ? "bg-red-500/20 text-red-300"
                            : "bg-emerald-500/20 text-emerald-300"
                        }`}
                      >
                        {selectedTrace.duration_ms.toFixed(1)}ms total
                      </span>
                    </h3>
                    <p className="text-xs font-mono text-slate-400 mt-0.5">
                      Trace ID: {selectedTrace.trace_id}
                    </p>
                  </div>
                </div>

                {/* Spans Waterfall */}
                <div className="space-y-3 font-mono text-xs">
                  <div className="text-[11px] text-slate-400 font-mono uppercase tracking-wider">
                    Span Timeline Execution Hierarchy ({selectedTrace.spans.length} Spans)
                  </div>

                  <div className="space-y-2 pt-2">
                    {selectedTrace.spans.map((span) => {
                      const totalTraceDuration = Math.max(selectedTrace.duration_ms, 1);
                      const leftPercent = Math.min(
                        Math.max((span.start_offset_ms / totalTraceDuration) * 100, 0),
                        95
                      );
                      const widthPercent = Math.min(
                        Math.max((span.duration_ms / totalTraceDuration) * 100, 2),
                        100 - leftPercent
                      );

                      return (
                        <div
                          key={span.span_id}
                          className="p-3 rounded-lg bg-slate-900/70 border border-slate-800/80 space-y-2"
                        >
                          <div className="flex items-center justify-between text-[11px]">
                            <div className="flex items-center space-x-2">
                              <span className="font-bold text-slate-200">
                                {span.service_name}
                              </span>
                              <span className="text-slate-400">
                                → {span.operation_name || span.name}
                              </span>
                            </div>
                            <span
                              className={`font-semibold ${
                                span.status === "ERROR" ? "text-red-400" : "text-emerald-400"
                              }`}
                            >
                              {span.duration_ms.toFixed(1)}ms
                            </span>
                          </div>

                          {/* Relative Timing Bar */}
                          <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden relative">
                            <div
                              className={`h-full rounded-full ${
                                span.status === "ERROR" ? "bg-red-500" : "bg-blue-500"
                              }`}
                              style={{
                                marginLeft: `${leftPercent}%`,
                                width: `${widthPercent}%`,
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

      {/* Tab 4: Stage 5.2 Anomalies & Resource Creep Engine */}
      {activeTab === "anomalies" && (
        <div className="space-y-6">
          {/* Header Controls Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 bg-[#0f172a] border border-slate-800 p-4 rounded-xl">
            <div className="flex flex-wrap items-center gap-3">
              {/* Service Filter */}
              <select
                value={anomalyServiceFilter}
                onChange={(e) => setAnomalyServiceFilter(e.target.value)}
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

              {/* Severity Filter */}
              <select
                value={anomalySeverityFilter}
                onChange={(e) => setAnomalySeverityFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-xl px-3 py-1.5 font-mono"
              >
                <option value="">All Severities</option>
                <option value="CRITICAL">CRITICAL</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
                <option value="INFO">INFO</option>
              </select>

              {/* Status Filter */}
              <select
                value={anomalyStatusFilter}
                onChange={(e) => setAnomalyStatusFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-xl px-3 py-1.5 font-mono"
              >
                <option value="">All Statuses</option>
                <option value="ACTIVE">ACTIVE</option>
                <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
                <option value="RESOLVED">RESOLVED</option>
                <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
              </select>
            </div>

            <div className="flex items-center space-x-3">
              <span className="text-xs font-mono text-slate-400">
                {anomalies.length} anomaly records
              </span>

              <button
                onClick={handleTriggerDetection}
                disabled={isTriggeringDetection}
                className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3.5 py-1.5 rounded-xl text-xs font-medium transition"
              >
                <Sparkles className={`w-3.5 h-3.5 ${isTriggeringDetection ? "animate-spin" : ""}`} />
                <span>{isTriggeringDetection ? "Evaluating..." : "Trigger Detection Cycle"}</span>
              </button>
            </div>
          </div>

          {/* Anomaly Engine Status Sub-Banner */}
          {detectionStatus && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-[#0b101b] border border-slate-800/80 p-3 rounded-xl flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-mono uppercase text-slate-400">Engine Status</div>
                  <div className="text-sm font-bold font-mono text-emerald-400 flex items-center gap-1.5 mt-0.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    {detectionStatus.status}
                  </div>
                </div>
                <Gauge className="w-5 h-5 text-slate-400" />
              </div>

              <div className="bg-[#0b101b] border border-slate-800/80 p-3 rounded-xl flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-mono uppercase text-slate-400">Active Anomalies</div>
                  <div className="text-sm font-bold font-mono text-amber-400 mt-0.5">
                    {detectionStatus.active_anomalies_count}
                  </div>
                </div>
                <AlertTriangle className="w-5 h-5 text-slate-400" />
              </div>

              <div className="bg-[#0b101b] border border-slate-800/80 p-3 rounded-xl flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-mono uppercase text-slate-400">Monitored Services</div>
                  <div className="text-sm font-bold font-mono text-slate-200 mt-0.5">
                    {detectionStatus.monitored_services} Nodes
                  </div>
                </div>
                <Activity className="w-5 h-5 text-slate-400" />
              </div>

              <div className="bg-[#0b101b] border border-slate-800/80 p-3 rounded-xl flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-mono uppercase text-slate-400">Last Detection Cycle</div>
                  <div className="text-sm font-bold font-mono text-slate-300 mt-0.5 truncate max-w-[140px]">
                    {detectionStatus.last_detection_cycle 
                      ? new Date(detectionStatus.last_detection_cycle).toLocaleTimeString()
                      : "Pending"}
                  </div>
                </div>
                <Clock className="w-5 h-5 text-slate-400" />
              </div>
            </div>
          )}

          {/* Split Pane: Anomalies Feed & Deep SRE Diagnostic Inspection */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Anomalies Feed */}
            <div className="lg:col-span-5 space-y-3 max-h-[720px] overflow-y-auto pr-1">
              {anomalies.length === 0 ? (
                <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-8 text-center space-y-3">
                  <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
                  <div className="text-sm font-semibold text-slate-200">
                    No Anomalies Detected
                  </div>
                  <div className="text-xs text-slate-400 leading-relaxed">
                    Adaptive 3σ baselines, EWMA rapid shift models, and OLS linear trend regressions report all telemetry signals within nominal bounds.
                  </div>
                </div>
              ) : (
                anomalies.map((item) => {
                  const isSelected = selectedAnomaly?.id === item.id;
                  const confidencePct = Math.round((item.confidence || 0) * 100);

                  return (
                    <div
                      key={item.id}
                      onClick={() => setSelectedAnomaly(item)}
                      className={`p-4 rounded-xl border transition cursor-pointer space-y-3 ${
                        isSelected
                          ? "bg-slate-800/90 border-blue-500/80 shadow-lg"
                          : "bg-[#0f172a] border-slate-800 hover:border-slate-700"
                      }`}
                    >
                      {/* Top Badges */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${getSeverityBadge(item.severity)}`}>
                            {item.severity}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${getStatusBadge(item.status)}`}>
                            {item.status}
                          </span>
                          <span className="text-[10px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                            {item.detector_type.replace(/_/g, " ")}
                          </span>
                        </div>

                        <span className="text-[10px] font-mono text-slate-400">
                          {item.detected_at ? new Date(item.detected_at).toLocaleTimeString() : "--:--:--"}
                        </span>
                      </div>

                      {/* Service & Metric Name */}
                      <div>
                        <div className="text-sm font-bold text-white font-mono flex items-center gap-1.5">
                          <span className="text-purple-400">[{item.service_name}]</span>
                          <span>{item.metric_name}</span>
                        </div>
                      </div>

                      {/* Observed vs Baseline Stats */}
                      <div className="grid grid-cols-2 gap-2 text-xs font-mono bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
                        <div>
                          <div className="text-slate-400 text-[10px]">Observed vs Expected</div>
                          <div className="text-white font-bold mt-0.5">
                            {item.observed_value.toFixed(2)} <span className="text-slate-400 font-normal">/ {item.expected_baseline.toFixed(2)}</span>
                          </div>
                        </div>

                        <div>
                          <div className="text-slate-400 text-[10px]">Deviation</div>
                          <div className="text-red-400 font-bold mt-0.5">
                            {item.deviation > 0 ? `+${item.deviation.toFixed(2)}` : item.deviation.toFixed(2)}
                          </div>
                        </div>

                        {item.ewma_value !== undefined && item.ewma_value !== null && (
                          <div>
                            <div className="text-slate-400 text-[10px]">EWMA Smoothed</div>
                            <div className="text-blue-300 font-semibold mt-0.5">
                              {item.ewma_value.toFixed(2)}
                            </div>
                          </div>
                        )}

                        {item.trend_slope !== undefined && item.trend_slope !== null && item.trend_slope !== 0 && (
                          <div>
                            <div className="text-slate-400 text-[10px]">OLS Rate/min</div>
                            <div className={`font-semibold mt-0.5 flex items-center gap-1 ${item.trend_slope > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                              {item.trend_slope > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                              <span>{(item.trend_slope * 60).toFixed(2)}/min</span>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Confidence Score Bar */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                          <span>Detection Confidence</span>
                          <span className="text-slate-200 font-bold">{confidencePct}%</span>
                        </div>
                        <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              confidencePct >= 80 ? "bg-red-500" : confidencePct >= 60 ? "bg-amber-500" : "bg-blue-500"
                            }`}
                            style={{ width: `${confidencePct}%` }}
                          />
                        </div>
                      </div>

                      {/* Observation Count & Footer */}
                      <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-1 border-t border-slate-800/60">
                        <span>Observed: {item.observation_count} cycle{item.observation_count > 1 ? "s" : ""}</span>
                        <span className="text-blue-400 flex items-center gap-0.5 hover:underline">
                          <span>Inspect Diagnostics</span>
                          <ChevronRight className="w-3 h-3" />
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Right Column: Deep SRE Diagnostic Inspection */}
            <div className="lg:col-span-7">
              {selectedAnomaly ? (
                <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-6">
                  {/* Selected Anomaly Top Header & Status Actions */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${getSeverityBadge(selectedAnomaly.severity)}`}>
                          {selectedAnomaly.severity}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${getStatusBadge(selectedAnomaly.status)}`}>
                          {selectedAnomaly.status}
                        </span>
                        <span className="text-xs font-mono text-slate-400">
                          ID: {selectedAnomaly.id.slice(0, 16)}...
                        </span>
                      </div>
                      <h2 className="text-base font-bold text-white font-mono mt-1">
                        [{selectedAnomaly.service_name}] {selectedAnomaly.metric_name}
                      </h2>
                    </div>

                    {/* Status Action Buttons */}
                    <div className="flex items-center space-x-2">
                      {selectedAnomaly.status === "ACTIVE" && (
                        <button
                          onClick={() => handleUpdateStatus(selectedAnomaly.id, "ACKNOWLEDGED")}
                          disabled={statusUpdating}
                          className="px-2.5 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 text-xs font-mono transition"
                        >
                          Acknowledge
                        </button>
                      )}

                      {selectedAnomaly.status !== "RESOLVED" && (
                        <button
                          onClick={() => handleUpdateStatus(selectedAnomaly.id, "RESOLVED")}
                          disabled={statusUpdating}
                          className="px-2.5 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 text-xs font-mono transition"
                        >
                          Resolve
                        </button>
                      )}

                      {selectedAnomaly.status !== "FALSE_POSITIVE" && (
                        <button
                          onClick={() => handleUpdateStatus(selectedAnomaly.id, "FALSE_POSITIVE")}
                          disabled={statusUpdating}
                          className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-mono transition"
                        >
                          False Positive
                        </button>
                      )}

                      {(selectedAnomaly.status === "RESOLVED" || selectedAnomaly.status === "FALSE_POSITIVE" || selectedAnomaly.status === "ACKNOWLEDGED") && (
                        <button
                          onClick={() => handleUpdateStatus(selectedAnomaly.id, "ACTIVE")}
                          disabled={statusUpdating}
                          className="px-2.5 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/30 text-xs font-mono transition"
                        >
                          Re-activate
                        </button>
                      )}
                    </div>
                  </div>

                  {/* 10 SRE Diagnostic Questions & Answers Panel */}
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider text-slate-400">
                      <ShieldAlert className="w-4 h-4 text-blue-400" />
                      <span>SRE Autonomous Diagnostic Assessment (10 Key Answers)</span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                      {/* 1. What Happened */}
                      <div className="col-span-full bg-slate-900/80 p-3.5 rounded-xl border border-slate-800 space-y-1">
                        <div className="text-[10px] text-blue-400 uppercase font-semibold">1. What Happened?</div>
                        <div className="text-slate-200 text-xs leading-relaxed font-sans">
                          {selectedAnomaly.explanation?.what_happened || 
                            `Service '${selectedAnomaly.service_name}' exhibited an anomalous departure in metric '${selectedAnomaly.metric_name}' (observed ${selectedAnomaly.observed_value.toFixed(2)} vs expected ${selectedAnomaly.expected_baseline.toFixed(2)}).`}
                        </div>
                      </div>

                      {/* 2. Affected Service */}
                      <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                        <div className="text-[10px] text-slate-400 uppercase">2. Affected Service</div>
                        <div className="text-white font-bold">{selectedAnomaly.explanation?.affected_service || selectedAnomaly.service_name}</div>
                      </div>

                      {/* 3. Metric Changed */}
                      <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                        <div className="text-[10px] text-slate-400 uppercase">3. Metric Changed</div>
                        <div className="text-white font-bold">{selectedAnomaly.explanation?.metric_changed || selectedAnomaly.metric_name}</div>
                      </div>

                      {/* 4. Normal Baseline */}
                      <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                        <div className="text-[10px] text-slate-400 uppercase">4. Normal Baseline</div>
                        <div className="text-slate-200">
                          {selectedAnomaly.explanation?.normal_baseline || `${selectedAnomaly.expected_baseline.toFixed(2)} (Nominal μ)`}
                        </div>
                      </div>

                      {/* 5. Deviation Magnitude */}
                      <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                        <div className="text-[10px] text-slate-400 uppercase">5. Deviation Magnitude</div>
                        <div className="text-amber-400 font-bold">
                          {selectedAnomaly.explanation?.deviation_magnitude || `${selectedAnomaly.deviation.toFixed(2)} departure`}
                        </div>
                      </div>

                      {/* 6. Duration Abnormal */}
                      <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                        <div className="text-[10px] text-slate-400 uppercase">6. Duration Abnormal</div>
                        <div className="text-slate-200">
                          {selectedAnomaly.explanation?.duration_abnormal || `${selectedAnomaly.observation_count} cycles recorded`}
                        </div>
                      </div>

                      {/* 7. Corroborating Signals */}
                      <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 space-y-1">
                        <div className="text-[10px] text-slate-400 uppercase">7. Corroborating Signals</div>
                        <div className="text-slate-300">
                          {selectedAnomaly.explanation?.corroborating_signals || "Single signal observation"}
                        </div>
                      </div>

                      {/* 8. Confidence Assessment */}
                      <div className="col-span-full bg-slate-900/60 p-3.5 rounded-xl border border-slate-800/80 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="text-[10px] text-slate-400 uppercase">8. Confidence Assessment</div>
                          <span className="text-emerald-400 font-bold">
                            {(selectedAnomaly.confidence * 100).toFixed(1)}% Confidence
                          </span>
                        </div>
                        <div className="text-slate-300 text-[11px] leading-relaxed">
                          {selectedAnomaly.explanation?.confidence_assessment || 
                            `Confidence calculated from magnitude, persistence (${selectedAnomaly.observation_count} cycles), and historical baseline stability.`}
                        </div>
                        {selectedAnomaly.supporting_evidence?.confidence_breakdown && (
                          <div className="grid grid-cols-3 gap-2 pt-1 text-[10px] text-slate-400 border-t border-slate-800">
                            <div>Magnitude: <span className="text-slate-200">{(selectedAnomaly.supporting_evidence.confidence_breakdown.magnitude_score * 100).toFixed(0)}%</span></div>
                            <div>Persistence: <span className="text-slate-200">{(selectedAnomaly.supporting_evidence.confidence_breakdown.persistence_score * 100).toFixed(0)}%</span></div>
                            <div>Corroboration: <span className="text-slate-200">{(selectedAnomaly.supporting_evidence.confidence_breakdown.corroborating_score * 100).toFixed(0)}%</span></div>
                          </div>
                        )}
                      </div>

                      {/* 9. Projected Impact */}
                      <div className="col-span-full bg-slate-900/80 p-3.5 rounded-xl border border-red-500/20 space-y-1">
                        <div className="text-[10px] text-red-400 uppercase font-semibold">9. Projected Impact</div>
                        <div className="text-slate-200 text-xs leading-relaxed font-sans">
                          {selectedAnomaly.explanation?.projected_impact || 
                            "Unmitigated departure may lead to cascading latency spikes, database connection exhaustion, or process restart."}
                        </div>
                      </div>

                      {/* 10. Next Investigation Step */}
                      <div className="col-span-full bg-blue-950/20 p-3.5 rounded-xl border border-blue-500/30 space-y-1">
                        <div className="text-[10px] text-blue-400 uppercase font-semibold">10. Next Recommended Investigation Step</div>
                        <div className="text-blue-200 text-xs leading-relaxed font-sans">
                          {selectedAnomaly.explanation?.next_investigation_step || 
                            "Initiate automated multi-agent investigation workflow to correlate deployment revisions and distributed span waterfalls."}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Baseline & Nominal Bounds Inspector */}
                  {baselinesMap[selectedAnomaly.metric_name] && (
                    <div className="bg-[#0b101b] border border-slate-800 rounded-xl p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="text-xs font-mono font-bold text-white flex items-center gap-1.5">
                          <Database className="w-3.5 h-3.5 text-blue-400" />
                          <span>Historical Baseline Inspection ({selectedAnomaly.metric_name})</span>
                        </div>
                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          {baselinesMap[selectedAnomaly.metric_name].sample_count} Samples Loaded
                        </span>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
                        <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
                          <div className="text-[10px] text-slate-400">Mean (μ)</div>
                          <div className="text-white font-bold mt-0.5">
                            {baselinesMap[selectedAnomaly.metric_name].mean.toFixed(2)}
                          </div>
                        </div>

                        <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
                          <div className="text-[10px] text-slate-400">Std Dev (σ)</div>
                          <div className="text-white font-bold mt-0.5">
                            {baselinesMap[selectedAnomaly.metric_name].std_dev.toFixed(2)}
                          </div>
                        </div>

                        <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
                          <div className="text-[10px] text-slate-400">Nominal 3σ Range</div>
                          <div className="text-slate-300 mt-0.5">
                            [{baselinesMap[selectedAnomaly.metric_name].min_normal.toFixed(1)}, {baselinesMap[selectedAnomaly.metric_name].max_normal.toFixed(1)}]
                          </div>
                        </div>

                        <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
                          <div className="text-[10px] text-slate-400">History Validity</div>
                          <div className="text-emerald-400 font-bold mt-0.5">
                            {baselinesMap[selectedAnomaly.metric_name].has_sufficient_history ? "SUFFICIENT (≥10)" : "INSUFFICIENT"}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Supporting Evidence Details */}
                  {selectedAnomaly.supporting_evidence && (
                    <details className="text-xs font-mono bg-slate-900/40 border border-slate-800/80 rounded-xl p-3.5 space-y-2">
                      <summary className="text-slate-400 cursor-pointer hover:text-slate-200">
                        View Raw Diagnostic Metadata & Supporting Evidence
                      </summary>
                      <pre className="p-3 bg-slate-950 rounded-lg text-[11px] text-slate-300 overflow-x-auto mt-2">
                        {JSON.stringify(selectedAnomaly.supporting_evidence, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ) : (
                <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-12 text-center text-slate-400 space-y-2">
                  <Info className="w-8 h-8 text-slate-500 mx-auto" />
                  <div className="text-sm font-semibold text-slate-300">No Anomaly Selected</div>
                  <div className="text-xs">
                    Select an anomaly record from the feed to view its 10 SRE diagnostic answers, baseline inspection, and lifecycle controls.
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
