"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Server,
  Layers,
  Cpu,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Search,
  Filter,
  Shield,
  Activity,
  Box,
  Radio,
  Clock,
  Lock,
  ArrowLeft,
} from "lucide-react";
import { kubernetesApi } from "../../services/api";
import {
  KubernetesClusterOverview,
  KubernetesConnectionDetails,
  KubernetesDeployment,
  KubernetesNamespace,
  KubernetesNode,
  KubernetesPod,
  KubernetesResourceMetrics,
  InfrastructureEvent,
} from "../../types";

export default function KubernetesCommandCenter() {
  const [activeTab, setActiveTab] = useState<"overview" | "pods" | "deployments" | "events" | "resources">("overview");
  const [overview, setOverview] = useState<KubernetesClusterOverview | null>(null);
  const [connection, setConnection] = useState<KubernetesConnectionDetails | null>(null);
  const [nodes, setNodes] = useState<KubernetesNode[]>([]);
  const [namespaces, setNamespaces] = useState<KubernetesNamespace[]>([]);
  const [pods, setPods] = useState<KubernetesPod[]>([]);
  const [deployments, setDeployments] = useState<KubernetesDeployment[]>([]);
  const [events, setEvents] = useState<InfrastructureEvent[]>([]);
  const [metrics, setMetrics] = useState<KubernetesResourceMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Filters
  const [selectedNamespace, setSelectedNamespace] = useState<string>("");
  const [podSearch, setPodSearch] = useState<string>("");
  const [podPhaseFilter, setPodPhaseFilter] = useState<string>("");
  const [onlyWarningEvents, setOnlyWarningEvents] = useState<boolean>(false);

  const fetchClusterData = async () => {
    try {
      setRefreshing(true);
      const [ovRes, connRes, nodesRes, nsRes, podsRes, depsRes, evRes, metRes] = await Promise.allSettled([
        kubernetesApi.getClusterOverview(),
        kubernetesApi.getConnection(),
        kubernetesApi.listNodes(),
        kubernetesApi.listNamespaces(),
        kubernetesApi.listPods({
          namespace: selectedNamespace || undefined,
          phase: podPhaseFilter || undefined,
          search: podSearch || undefined,
        }),
        kubernetesApi.listDeployments(selectedNamespace || undefined),
        kubernetesApi.listEvents({
          namespace: selectedNamespace || undefined,
          onlyWarnings: onlyWarningEvents,
          limit: 100,
        }),
        kubernetesApi.getMetrics(undefined, selectedNamespace || undefined),
      ]);

      if (ovRes.status === "fulfilled") setOverview(ovRes.value);
      if (connRes.status === "fulfilled") setConnection(connRes.value);
      if (nodesRes.status === "fulfilled") setNodes(nodesRes.value);
      if (nsRes.status === "fulfilled") setNamespaces(nsRes.value);
      if (podsRes.status === "fulfilled") setPods(podsRes.value);
      if (depsRes.status === "fulfilled") setDeployments(depsRes.value);
      if (evRes.status === "fulfilled") setEvents(evRes.value);
      if (metRes.status === "fulfilled") setMetrics(metRes.value);
    } catch (err) {
      console.error("Failed to load Kubernetes data:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchClusterData();
    const interval = setInterval(fetchClusterData, 15000);
    return () => clearInterval(interval);
  }, [selectedNamespace, podPhaseFilter, onlyWarningEvents]);

  const isConnected = connection?.is_connected || overview?.connection_status === "CONNECTED";
  const isLive = connection?.is_live || overview?.is_live;

  return (
    <div className="space-y-6">
      {/* Top Banner & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#0d1322] border border-slate-800 p-6 rounded-xl shadow-lg">
        <div>
          <div className="mb-2">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-white transition group"
            >
              <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
              <span>Back to Overview</span>
            </Link>
          </div>
          <div className="flex items-center space-x-3">
            <Server className="w-6 h-6 text-emerald-400" />
            <h1 className="text-xl font-bold font-mono text-white tracking-tight">
              Kubernetes Live Command Center
            </h1>
            {isConnected ? (
              isLive ? (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-600 flex items-center gap-1.5 animate-pulse">
                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                  LIVE CLUSTER CONNECTED
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-purple-950 text-purple-300 border border-purple-600 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                  MOCK SANDBOX ACTIVE
                </span>
              )
            ) : (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-red-950 text-red-300 border border-red-700 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-red-400"></span>
                DISCONNECTED
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real Infrastructure Integration Engine (Phase 8.2) • Read-Only RBAC Enforced
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-400 flex items-center space-x-2">
            <Lock className="w-3.5 h-3.5 text-amber-400" />
            <span>Read-Only ServiceAccount</span>
          </div>

          <button
            onClick={fetchClusterData}
            disabled={refreshing}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-mono font-bold transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Disconnection Warning Banner if cluster is not reachable */}
      {!isConnected && (
        <div className="p-4 bg-amber-950/40 border border-amber-800/80 rounded-xl flex items-start space-x-3 text-xs font-mono text-amber-200">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <strong className="block text-white font-bold text-sm">
              No Kubernetes Cluster Connected
            </strong>
            <p>
              {connection?.last_error ||
                "IncidentX AI requires valid kubeconfig or ServiceAccount credentials. To connect a local cluster (Minikube, Kind, Docker Desktop), start the cluster or configure KUBERNETES_API_URL and KUBERNETES_READ_ONLY_TOKEN."}
            </p>
            <p className="text-slate-400 pt-1">
              Data isolation is actively enforced: DemoMesh simulated data is never masqueraded as live Kubernetes telemetry.
            </p>
          </div>
        </div>
      )}

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Nodes</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-xl font-bold font-mono text-white">{overview?.total_nodes ?? 0}</span>
            <span className="text-xs font-mono text-emerald-400">
              ({overview?.ready_nodes ?? 0} Ready)
            </span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Namespaces</span>
          <span className="text-xl font-bold font-mono text-white mt-1 block">
            {overview?.total_namespaces ?? namespaces.length}
          </span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Pods</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-xl font-bold font-mono text-white">{overview?.total_pods ?? pods.length}</span>
            <span className="text-xs font-mono text-blue-400">Total</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Deployments</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-xl font-bold font-mono text-white">{deployments.length}</span>
            <span className="text-xs font-mono text-emerald-400">
              ({overview?.healthy_deployments ?? 0} Healthy)
            </span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">K8s Version</span>
          <span className="text-sm font-bold font-mono text-blue-300 mt-2 block truncate">
            {overview?.kubernetes_version || "unknown"}
          </span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Metrics Server</span>
          <span
            className={`text-xs font-bold font-mono mt-2 inline-flex items-center gap-1 ${
              overview?.metrics_server_available ? "text-emerald-400" : "text-amber-400"
            }`}
          >
            {overview?.metrics_server_available ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5" /> AVAILABLE
              </>
            ) : (
              <>
                <XCircle className="w-3.5 h-3.5" /> NOT INSTALLED
              </>
            )}
          </span>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2 rounded-lg text-xs font-mono font-bold transition-colors ${
            activeTab === "overview"
              ? "bg-blue-600 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-800/60"
          }`}
        >
          Cluster Overview
        </button>
        <button
          onClick={() => setActiveTab("pods")}
          className={`px-4 py-2 rounded-lg text-xs font-mono font-bold transition-colors ${
            activeTab === "pods"
              ? "bg-blue-600 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-800/60"
          }`}
        >
          Pod Explorer ({pods.length})
        </button>
        <button
          onClick={() => setActiveTab("deployments")}
          className={`px-4 py-2 rounded-lg text-xs font-mono font-bold transition-colors ${
            activeTab === "deployments"
              ? "bg-blue-600 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-800/60"
          }`}
        >
          Deployment Explorer ({deployments.length})
        </button>
        <button
          onClick={() => setActiveTab("events")}
          className={`px-4 py-2 rounded-lg text-xs font-mono font-bold transition-colors ${
            activeTab === "events"
              ? "bg-blue-600 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-800/60"
          }`}
        >
          Live Events ({events.length})
        </button>
        <button
          onClick={() => setActiveTab("resources")}
          className={`px-4 py-2 rounded-lg text-xs font-mono font-bold transition-colors ${
            activeTab === "resources"
              ? "bg-blue-600 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-800/60"
          }`}
        >
          Resource Inspection
        </button>
      </div>

      {/* Namespace Filter Bar for sub-views */}
      {activeTab !== "overview" && (
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-900/40 border border-slate-800 rounded-lg text-xs font-mono">
          <div className="flex items-center space-x-3">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-blue-400" /> Namespace:
            </span>
            <select
              value={selectedNamespace}
              onChange={(e) => setSelectedNamespace(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1 text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="">All Namespaces</option>
              {namespaces.map((ns) => (
                <option key={ns.name} value={ns.name}>
                  {ns.name} ({ns.workload_count})
                </option>
              ))}
            </select>
          </div>

          {activeTab === "pods" && (
            <div className="flex items-center space-x-3">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2" />
                <input
                  type="text"
                  placeholder="Search pod name..."
                  value={podSearch}
                  onChange={(e) => setPodSearch(e.target.value)}
                  className="bg-slate-950 border border-slate-700 rounded pl-8 pr-3 py-1 text-slate-200 text-xs focus:outline-none focus:border-blue-500 w-48"
                />
              </div>
              <select
                value={podPhaseFilter}
                onChange={(e) => setPodPhaseFilter(e.target.value)}
                className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1 text-slate-200 text-xs focus:outline-none focus:border-blue-500"
              >
                <option value="">All Phases</option>
                <option value="Running">Running</option>
                <option value="CrashLoopBackOff">CrashLoopBackOff</option>
                <option value="Pending">Pending</option>
                <option value="Failed">Failed</option>
              </select>
            </div>
          )}

          {activeTab === "events" && (
            <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={onlyWarningEvents}
                onChange={(e) => setOnlyWarningEvents(e.target.checked)}
                className="rounded border-slate-700 bg-slate-950 text-blue-600 focus:ring-0"
              />
              <span>Warnings & Failures Only</span>
            </label>
          )}
        </div>
      )}

      {/* Tab 1: Cluster Overview & Node List */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Node Capacity Table */}
          <div className="bg-[#0f172a] border border-slate-800 rounded-xl overflow-hidden shadow">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <h3 className="text-sm font-bold font-mono text-slate-100 flex items-center gap-2">
                <Layers className="w-4 h-4 text-blue-400" /> Cluster Nodes Topology
              </h3>
              <span className="text-xs font-mono text-slate-400">{nodes.length} Nodes Discovered</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900/60 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-3">Node Name</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3">K8s Version</th>
                    <th className="px-6 py-3">OS / Arch</th>
                    <th className="px-6 py-3">Allocatable CPU</th>
                    <th className="px-6 py-3">Allocatable Memory</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {nodes.length > 0 ? (
                    nodes.map((node) => (
                      <tr key={node.name} className="hover:bg-slate-900/40">
                        <td className="px-6 py-3.5 font-bold text-white">{node.name}</td>
                        <td className="px-6 py-3.5">
                          {node.ready ? (
                            <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-semibold text-[11px]">
                              READY
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-800 font-semibold text-[11px]">
                              NOT READY
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-3.5 text-slate-300">{node.kubelet_version}</td>
                        <td className="px-6 py-3.5 text-slate-400">
                          {node.os_image} ({node.architecture})
                        </td>
                        <td className="px-6 py-3.5 text-blue-300 font-bold">{node.cpu_allocatable_cores} cores</td>
                        <td className="px-6 py-3.5 text-purple-300 font-bold">
                          {(node.memory_allocatable_mb / 1024).toFixed(1)} GB
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                        No nodes discovered. Ensure cluster is connected.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Pod Explorer */}
      {activeTab === "pods" && (
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl overflow-hidden shadow">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/60 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3">Pod Name</th>
                  <th className="px-6 py-3">Namespace</th>
                  <th className="px-6 py-3">Phase</th>
                  <th className="px-6 py-3">Restarts</th>
                  <th className="px-6 py-3">Pod IP</th>
                  <th className="px-6 py-3">Node</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {pods.length > 0 ? (
                  pods.map((p) => (
                    <tr key={p.name} className="hover:bg-slate-900/40">
                      <td className="px-6 py-3.5 font-bold text-white flex items-center gap-2">
                        <Box className="w-3.5 h-3.5 text-blue-400" />
                        {p.name}
                      </td>
                      <td className="px-6 py-3.5 text-slate-400">{p.namespace}</td>
                      <td className="px-6 py-3.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                            p.phase === "Running"
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                              : p.phase === "CrashLoopBackOff"
                              ? "bg-red-950 text-red-400 border border-red-800 animate-pulse"
                              : "bg-amber-950 text-amber-400 border border-amber-800"
                          }`}
                        >
                          {p.phase}
                        </span>
                      </td>
                      <td className="px-6 py-3.5">
                        {p.restart_count > 0 ? (
                          <span className="px-2 py-0.5 rounded bg-red-900/60 text-red-300 border border-red-700 font-bold">
                            {p.restart_count} restarts
                          </span>
                        ) : (
                          <span className="text-slate-500">0</span>
                        )}
                      </td>
                      <td className="px-6 py-3.5 text-slate-400">{p.pod_ip || "None"}</td>
                      <td className="px-6 py-3.5 text-slate-400">{p.node_name || "Unassigned"}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                      No pods matching query found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Deployment Explorer */}
      {activeTab === "deployments" && (
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl overflow-hidden shadow">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/60 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3">Deployment</th>
                  <th className="px-6 py-3">Namespace</th>
                  <th className="px-6 py-3">Desired</th>
                  <th className="px-6 py-3">Available</th>
                  <th className="px-6 py-3">Updated</th>
                  <th className="px-6 py-3">Rollout Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {deployments.length > 0 ? (
                  deployments.map((d) => (
                    <tr key={d.name} className="hover:bg-slate-900/40">
                      <td className="px-6 py-3.5 font-bold text-white">{d.name}</td>
                      <td className="px-6 py-3.5 text-slate-400">{d.namespace}</td>
                      <td className="px-6 py-3.5 text-white font-bold">{d.desired_replicas}</td>
                      <td className="px-6 py-3.5">
                        <span
                          className={`font-bold ${
                            d.available_replicas >= d.desired_replicas ? "text-emerald-400" : "text-amber-400"
                          }`}
                        >
                          {d.available_replicas}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-slate-300">{d.updated_replicas}</td>
                      <td className="px-6 py-3.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                            d.rollout_status === "Healthy"
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                              : "bg-amber-950 text-amber-400 border border-amber-800"
                          }`}
                        >
                          {d.rollout_status}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                      No deployments found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 4: Live Event Streamer */}
      {activeTab === "events" && (
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl overflow-hidden shadow">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/60 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3">Severity</th>
                  <th className="px-6 py-3">Reason</th>
                  <th className="px-6 py-3">Resource</th>
                  <th className="px-6 py-3">Message</th>
                  <th className="px-6 py-3">Count</th>
                  <th className="px-6 py-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {events.length > 0 ? (
                  events.map((ev) => (
                    <tr key={ev.id} className="hover:bg-slate-900/40">
                      <td className="px-6 py-3.5">
                        {ev.event_type === "Warning" || ev.reason in { CrashLoopBackOff: 1, OOMKilled: 1 } ? (
                          <span className="px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-800 font-bold text-[10px]">
                            WARNING
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800 text-[10px]">
                            NORMAL
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-3.5 font-bold text-white">{ev.reason}</td>
                      <td className="px-6 py-3.5 text-blue-300">
                        {ev.resource_kind}/{ev.resource_name}
                      </td>
                      <td className="px-6 py-3.5 text-slate-300 max-w-md truncate" title={ev.message}>
                        {ev.message}
                      </td>
                      <td className="px-6 py-3.5 text-slate-400">{ev.count}</td>
                      <td className="px-6 py-3.5 text-slate-500">{new Date(ev.timestamp).toLocaleTimeString()}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                      No cluster events recorded.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 5: Resource Inspection */}
      {activeTab === "resources" && (
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl overflow-hidden shadow">
          <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="text-sm font-bold font-mono text-slate-100 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-purple-400" /> Pod Resource Requests vs Measured Utilization
            </h3>
            <span className="text-xs font-mono text-slate-400">
              Metrics Server:{" "}
              {overview?.metrics_server_available ? (
                <span className="text-emerald-400 font-bold">ONLINE</span>
              ) : (
                <span className="text-amber-400">UNAVAILABLE (Showing configured requests/limits only)</span>
              )}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/60 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3">Pod</th>
                  <th className="px-6 py-3">Namespace</th>
                  <th className="px-6 py-3">CPU Request</th>
                  <th className="px-6 py-3">CPU Limit</th>
                  <th className="px-6 py-3">Measured CPU</th>
                  <th className="px-6 py-3">Mem Request</th>
                  <th className="px-6 py-3">Mem Limit</th>
                  <th className="px-6 py-3">Measured Mem</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {metrics.length > 0 ? (
                  metrics.map((m) => (
                    <tr key={m.resource_name} className="hover:bg-slate-900/40">
                      <td className="px-6 py-3.5 font-bold text-white">{m.resource_name}</td>
                      <td className="px-6 py-3.5 text-slate-400">{m.namespace}</td>
                      <td className="px-6 py-3.5 text-slate-300">{m.configured_cpu_request_cores} cores</td>
                      <td className="px-6 py-3.5 text-slate-400">{m.configured_cpu_limit_cores} cores</td>
                      <td className="px-6 py-3.5">
                        {m.measured_cpu_cores !== null && m.measured_cpu_cores !== undefined ? (
                          <span className="text-blue-300 font-bold">{m.measured_cpu_cores} cores</span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="px-6 py-3.5 text-slate-300">{m.configured_memory_request_mb} MB</td>
                      <td className="px-6 py-3.5 text-slate-400">{m.configured_memory_limit_mb} MB</td>
                      <td className="px-6 py-3.5">
                        {m.measured_memory_mb !== null && m.measured_memory_mb !== undefined ? (
                          <span className="text-purple-300 font-bold">{m.measured_memory_mb} MB</span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="px-6 py-8 text-center text-slate-500">
                      No pod resource metrics collected.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
