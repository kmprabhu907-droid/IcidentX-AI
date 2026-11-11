"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { 
  ShieldCheck, 
  Lock, 
  Mail, 
  User, 
  KeyRound, 
  CheckCircle2, 
  AlertCircle, 
  ArrowRight,
  LogOut,
  Building,
  Sparkles
} from "lucide-react";
import { api } from "../../services/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("SRE_ENGINEER");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<any>(null);

  useEffect(() => {
    // Check if user is already authenticated
    const stored = typeof window !== "undefined" ? localStorage.getItem("incidentx_user") : null;
    if (stored) {
      try {
        setCurrentUser(JSON.parse(stored));
      } catch (_) {}
    }
    // Also verify with /auth/me
    api.getMe()
      .then((data: any) => {
        setCurrentUser(data);
        if (typeof window !== "undefined") {
          localStorage.setItem("incidentx_user", JSON.stringify(data));
        }
      })
      .catch(() => {
        // Not authenticated or token expired
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      if (mode === "login") {
        const res = await api.login({ email, password });
        setCurrentUser(res.user);
        setSuccess("Authentication successful! Redirecting to Reliability Command Center...");
        setTimeout(() => {
          router.push("/reliability");
        }, 1200);
      } else {
        await api.register({
          email,
          password,
          full_name: fullName,
          role,
        });
        setSuccess("Account successfully created! Signing you in...");
        const res = await api.login({ email, password });
        setCurrentUser(res.user);
        setTimeout(() => {
          router.push("/reliability");
        }, 1200);
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed. Please verify credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await api.logout();
    setCurrentUser(null);
    setSuccess("Logged out successfully.");
  };

  const handleQuickDemoFill = (demoRole: "admin" | "sre" | "viewer") => {
    if (demoRole === "admin") {
      setEmail("root.admin@incidentx.internal");
      setPassword("EnterpriseSecret2026!");
      setFullName("Root Administrator");
      setRole("SUPER_ADMIN");
    } else if (demoRole === "sre") {
      setEmail("lead.sre@incidentx.internal");
      setPassword("EnterpriseSecret2026!");
      setFullName("Lead SRE Engineer");
      setRole("SRE_ENGINEER");
    } else {
      setEmail("auditor@incidentx.internal");
      setPassword("EnterpriseSecret2026!");
      setFullName("Security Auditor");
      setRole("SECURITY_AUDITOR");
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      {/* Page Title */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-600/10 border border-blue-500/20 text-blue-400 mb-4 shadow-lg shadow-blue-500/10">
          <ShieldCheck className="w-8 h-8" />
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Enterprise Access Management
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Cryptographically signed JWT bearer authentication and 6-tier Role-Based Access Control (RBAC)
        </p>
      </div>

      {currentUser ? (
        /* Authenticated Active Session Card */
        <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-8 shadow-2xl">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
            <div>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                ACTIVE AUTHENTICATED SESSION
              </span>
              <h2 className="text-2xl font-bold text-white">{currentUser.full_name}</h2>
              <p className="text-sm font-mono text-slate-400">{currentUser.email}</p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => router.push("/reliability")}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-colors flex items-center gap-2"
              >
                Go to Command Center <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleLogout}
                className="px-4 py-2 rounded-lg border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 text-red-400 font-semibold text-xs transition-colors flex items-center gap-2"
              >
                <LogOut className="w-3.5 h-3.5" /> Sign Out
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
              <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Assigned Role</span>
              <p className="text-lg font-bold text-blue-400 mt-1 font-mono">{currentUser.role}</p>
              <p className="text-xs text-slate-400 mt-0.5">
                {currentUser.is_superuser ? "Platform Superuser Elevation" : "Standard Scoped Member"}
              </p>
            </div>

            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
              <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">User ID</span>
              <p className="text-xs font-mono text-slate-300 mt-2 truncate" title={currentUser.id}>
                {currentUser.id}
              </p>
              <p className="text-xs text-slate-400 mt-1">Tenant Organization: default-org</p>
            </div>

            <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40">
              <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Last Authenticated</span>
              <p className="text-xs font-mono text-slate-300 mt-2">
                {currentUser.last_login_at ? new Date(currentUser.last_login_at).toLocaleTimeString() : "Just now"}
              </p>
              <p className="text-xs text-emerald-400 mt-1">Token Status: Valid</p>
            </div>
          </div>

          <div className="mt-6 pt-6 border-t border-slate-800">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Effective Capability Grants ({currentUser.permissions?.length || 0})
            </h3>
            <div className="flex flex-wrap gap-2">
              {currentUser.permissions?.map((perm: string) => (
                <span
                  key={perm}
                  className="px-2.5 py-1 rounded-md text-xs font-mono bg-slate-800/80 text-slate-300 border border-slate-700"
                >
                  {perm}
                </span>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* Sign-In / Registration Form */
        <div className="rounded-2xl border border-slate-800 bg-[#0d1322] p-8 shadow-2xl max-w-xl mx-auto">
          {/* Mode Switcher Tabs */}
          <div className="flex rounded-xl bg-slate-900/80 p-1 border border-slate-800 mb-6">
            <button
              onClick={() => { setMode("login"); setError(null); }}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                mode === "login"
                  ? "bg-blue-600 text-white shadow-md shadow-blue-500/20"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Sign In to IncidentX
            </button>
            <button
              onClick={() => { setMode("register"); setError(null); }}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                mode === "register"
                  ? "bg-blue-600 text-white shadow-md shadow-blue-500/20"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Register Account
            </button>
          </div>

          {/* Quick Demo Pre-fill Pill Bar */}
          <div className="mb-6 p-3 rounded-xl border border-blue-500/20 bg-blue-500/5">
            <div className="flex items-center gap-1.5 text-xs text-blue-400 font-semibold mb-2">
              <Sparkles className="w-3.5 h-3.5" /> Demo Quick Select:
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => handleQuickDemoFill("admin")}
                className="px-2.5 py-1 rounded-lg text-xs bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 font-mono transition-colors"
              >
                Super Admin
              </button>
              <button
                type="button"
                onClick={() => handleQuickDemoFill("sre")}
                className="px-2.5 py-1 rounded-lg text-xs bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 font-mono transition-colors"
              >
                Lead SRE
              </button>
              <button
                type="button"
                onClick={() => handleQuickDemoFill("viewer")}
                className="px-2.5 py-1 rounded-lg text-xs bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 font-mono transition-colors"
              >
                Auditor (Read-Only)
              </button>
            </div>
          </div>

          {/* Alerts */}
          {error && (
            <div className="mb-5 p-3 rounded-lg border border-red-500/30 bg-red-500/10 text-red-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="mb-5 p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{success}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Full Name
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Maya Chen"
                    className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-slate-800 bg-slate-900/60 text-slate-200 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Work Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@enterprise.com"
                  className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-slate-800 bg-slate-900/60 text-slate-200 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-slate-800 bg-slate-900/60 text-slate-200 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
            </div>

            {mode === "register" && (
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Initial Enterprise Role
                </label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-lg border border-slate-800 bg-slate-900/60 text-slate-200 text-sm focus:outline-none focus:border-blue-500 transition-colors"
                >
                  <option value="SRE_ENGINEER">SRE Engineer (Remediation & Chaos Controls)</option>
                  <option value="INCIDENT_RESPONDER">Incident Responder (Triage & Approvals)</option>
                  <option value="SECURITY_AUDITOR">Security Auditor (Read-Only Compliance)</option>
                  <option value="READ_ONLY_VIEWER">Read-Only Viewer</option>
                </select>
                <p className="text-[11px] text-slate-500 mt-1">
                  Note: The first registered account in the system is automatically elevated to SUPER_ADMIN.
                </p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold text-sm transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2"
            >
              {loading ? (
                <span>Authenticating with IncidentX...</span>
              ) : mode === "login" ? (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              ) : (
                <>
                  <span>Create Account</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
