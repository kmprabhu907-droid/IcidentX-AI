"use client";

import { useEffect, useState } from "react";
import { 
  Server, 
  Plus, 
  Network, 
  CheckCircle2, 
  AlertCircle, 
  ArrowRight,
  RefreshCw,
  X,
  Layers
} from "lucide-react";
import { api } from "../../services/api";
import { Service, ServiceDependency } from "../../types";

export default function ServicesPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [dependencies, setDependencies] = useState<ServiceDependency[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Service Modal
  const [isServiceModalOpen, setIsServiceModalOpen] = useState(false);
  const [svcName, setSvcName] = useState("");
  const [svcTier, setSvcTier] = useState("Tier-2");
  const [svcType, setSvcType] = useState("service");
  const [svcLang, setSvcLang] = useState("Go");
  const [isSubmittingService, setIsSubmittingService] = useState(false);

  // New Dependency Modal
  const [isDepModalOpen, setIsDepModalOpen] = useState(false);
  const [depSource, setDepSource] = useState("");
  const [depTarget, setDepTarget] = useState("");
  const [depProtocol, setDepProtocol] = useState("gRPC");
  const [isSubmittingDep, setIsSubmittingDep] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [svcRes, depRes] = await Promise.all([
        api.listServices(1, 100),
        api.listDependencies().catch(() => ({ items: [], total: 0 })),
      ]);
      setServices(svcRes.items);
      setDependencies(depRes.items);
    } catch (err: any) {
      setError(err.message || "Failed to load services and dependencies.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateService = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!svcName.trim()) return;

    setIsSubmittingService(true);
    try {
      await api.createService({
        name: svcName.trim().toLowerCase(),
        tier: svcTier,
        service_type: svcType,
        language: svcLang,
        health_status: "HEALTHY",
      });
      setIsServiceModalOpen(false);
      setSvcName("");
      loadData();
    } catch (err: any) {
      alert(`Error creating service: ${err.message}`);
    } finally {
      setIsSubmittingService(false);
    }
  };

  const handleCreateDependency = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!depSource || !depTarget) return;

    setIsSubmittingDep(true);
    try {
      await fetch("http://localhost:8000/api/v1/dependencies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_service_id: depSource,
          target_service_id: depTarget,
          protocol: depProtocol,
          is_critical: true,
        }),
      });
      setIsDepModalOpen(false);
      loadData();
    } catch (err: any) {
      alert(`Error creating dependency: ${err.message}`);
    } finally {
      setIsSubmittingDep(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            Service Topology Inventory
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-medium">
            Production microservices, database clusters, and dependency mesh graph.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => setIsDepModalOpen(true)}
            disabled={services.length < 2}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-xs font-mono font-bold text-slate-200 transition-all disabled:opacity-50"
          >
            <Network className="w-3.5 h-3.5 text-purple-400" />
            <span>Link Dependency</span>
          </button>

          <button
            onClick={() => setIsServiceModalOpen(true)}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-mono font-bold text-white shadow-lg shadow-blue-500/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Register Service</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl border border-red-500/30 bg-red-950/20 text-red-300 text-xs font-mono">
          {error}
        </div>
      )}

      {/* Services Grid */}
      <div className="rounded-xl border border-slate-800 bg-[#0e1424] p-5">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <Server className="w-4 h-4 text-blue-400" />
            <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-200">
              Registered Microservices ({services.length})
            </h3>
          </div>
          <button onClick={loadData} className="text-xs font-mono text-slate-400 hover:text-white flex items-center gap-1">
            <RefreshCw className="w-3 h-3" /> Sync
          </button>
        </div>

        {loading ? (
          <div className="py-12 text-center text-xs font-mono text-slate-500">
            Querying service catalog from PostgreSQL...
          </div>
        ) : services.length === 0 ? (
          <div className="py-12 text-center text-xs font-mono text-slate-500 space-y-2">
            <p>No services registered in the database yet.</p>
            <button
              onClick={() => setIsServiceModalOpen(true)}
              className="text-blue-400 underline font-semibold"
            >
              + Register First Microservice
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {services.map((svc) => (
              <div
                key={svc.id}
                className="p-4 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-slate-700 transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono font-bold text-white">{svc.name}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    {svc.tier}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mt-3 pt-2 border-t border-slate-800/80">
                  <span>Type: <strong className="text-slate-300">{svc.service_type}</strong></span>
                  <span className="text-emerald-400 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                    {svc.health_status}
                  </span>
                </div>
                {svc.language && (
                  <div className="text-[10px] font-mono text-slate-500 mt-1">
                    Stack: {svc.language}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Dependencies List */}
      <div className="rounded-xl border border-slate-800 bg-[#0e1424] p-5">
        <div className="flex items-center space-x-2 mb-4 pb-3 border-b border-slate-800">
          <Network className="w-4 h-4 text-purple-400" />
          <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-200">
            Active Dependency Links ({dependencies.length})
          </h3>
        </div>

        {dependencies.length === 0 ? (
          <div className="py-8 text-center text-xs font-mono text-slate-500">
            No topological dependencies mapped yet. Click &quot;Link Dependency&quot; above to connect services.
          </div>
        ) : (
          <div className="space-y-2">
            {dependencies.map((dep) => {
              const sourceSvc = services.find(s => s.id === dep.source_service_id);
              const targetSvc = services.find(s => s.id === dep.target_service_id);
              return (
                <div
                  key={dep.id}
                  className="p-3 rounded-lg border border-slate-800 bg-slate-900/40 flex items-center justify-between text-xs font-mono"
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-white font-bold">{sourceSvc?.name || dep.source_service_id.slice(0, 8)}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                    <span className="text-blue-400 font-bold">{targetSvc?.name || dep.target_service_id.slice(0, 8)}</span>
                  </div>
                  <span className="text-[10px] text-slate-400 px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                    {dep.protocol}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Register Service Modal */}
      {isServiceModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl relative">
            <button
              onClick={() => setIsServiceModalOpen(false)}
              className="absolute top-5 right-5 p-1 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <h2 className="text-base font-bold text-white font-mono mb-1">Register Microservice</h2>
            <p className="text-xs text-slate-400 mb-4 font-sans">
              Adds an infrastructure node to the service topology mesh.
            </p>

            <form onSubmit={handleCreateService} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">Service Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. order-service"
                  value={svcName}
                  onChange={(e) => setSvcName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">Tier</label>
                  <select
                    value={svcTier}
                    onChange={(e) => setSvcTier(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white font-mono"
                  >
                    <option value="Tier-1">Tier-1 (Mission Critical)</option>
                    <option value="Tier-2">Tier-2 (Core Service)</option>
                    <option value="Tier-3">Tier-3 (Auxiliary)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">Type</label>
                  <select
                    value={svcType}
                    onChange={(e) => setSvcType(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white font-mono"
                  >
                    <option value="service">Microservice</option>
                    <option value="gateway">Ingress Gateway</option>
                    <option value="database">Database</option>
                    <option value="cache">Distributed Cache</option>
                    <option value="queue">Message Queue</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">Language / Runtime</label>
                <input
                  type="text"
                  placeholder="e.g. Go 1.23, Node.js 22, Rust"
                  value={svcLang}
                  onChange={(e) => setSvcLang(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsServiceModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-slate-700 text-xs font-mono text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingService}
                  className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-mono font-bold text-white shadow-md shadow-blue-500/20"
                >
                  {isSubmittingService ? "Saving..." : "Add Service"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Link Dependency Modal */}
      {isDepModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl relative">
            <button
              onClick={() => setIsDepModalOpen(false)}
              className="absolute top-5 right-5 p-1 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <h2 className="text-base font-bold text-white font-mono mb-1">Link Service Dependency</h2>
            <p className="text-xs text-slate-400 mb-4 font-sans">
              Declares a directional call dependency: Source calls Target.
            </p>

            <form onSubmit={handleCreateDependency} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">Source (Upstream Caller) *</label>
                <select
                  required
                  value={depSource}
                  onChange={(e) => setDepSource(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white font-mono"
                >
                  <option value="">Select source service...</option>
                  {services.map((s) => (
                    <option key={s.id} value={s.id}>{s.name} ({s.service_type})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">Target (Downstream Callee) *</label>
                <select
                  required
                  value={depTarget}
                  onChange={(e) => setDepTarget(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white font-mono"
                >
                  <option value="">Select target service...</option>
                  {services.filter(s => s.id !== depSource).map((s) => (
                    <option key={s.id} value={s.id}>{s.name} ({s.service_type})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">Protocol</label>
                <input
                  type="text"
                  value={depProtocol}
                  onChange={(e) => setDepProtocol(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white font-mono"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsDepModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-slate-700 text-xs font-mono text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingDep}
                  className="px-5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-xs font-mono font-bold text-white shadow-md shadow-purple-500/20"
                >
                  {isSubmittingDep ? "Linking..." : "Create Link"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
