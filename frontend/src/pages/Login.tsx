import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../services/api';
import {
  Lock,
  Mail,
  ShieldAlert,
  ArrowRight,
  Stethoscope,
  ShieldCheck,
  UserPlus,
  CheckCircle2,
} from 'lucide-react';

export const Login: React.FC = () => {
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Signup fields
  const [fullName, setFullName] = useState('');
  const [hospitalName, setHospitalName] = useState('');
  const [hospitalSlug, setHospitalSlug] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      const serverDetail = err.response?.data?.detail;
      if (serverDetail) {
        setError(serverDetail);
      } else if (err.code === 'ERR_NETWORK' || !err.response) {
        setError(
          'Cannot connect to backend API server. Verify backend status or VITE_BACKEND_URL proxy configuration.'
        );
      } else {
        setError(`Request failed with status ${err.response.status}: ${err.message || 'Unknown error'}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      await authApi.registerHospital({
        hospital_name: hospitalName,
        slug: hospitalSlug,
        admin_email: signupEmail,
        admin_password: signupPassword,
        admin_name: fullName,
      });

      setSuccessMsg(`Hospital registered for ${fullName}. Signing you in…`);
      // Auto login with new credentials
      try {
        await login(signupEmail, signupPassword);
        navigate('/');
      } catch {
        setEmail(signupEmail);
        setPassword(signupPassword);
        setMode('login');
        setSuccessMsg('Account registered! Please sign in with your credentials.');
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg || 'Validation failed').join(', '));
      } else {
        setError(err.message || 'Failed to create account. Please check inputs.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDemoFill = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
    setSuccessMsg(null);
    setMode('login');
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center items-center p-4">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
        {/* Header Banner */}
        <div className="bg-gradient-to-r from-brand-700 to-brand-900 p-6 text-white text-center relative">
          <div className="inline-flex p-3 bg-white/10 rounded-2xl backdrop-blur-sm mb-3">
            <Stethoscope className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight">HMS Clinical Portal</h2>
          <p className="text-sm text-brand-100 mt-1 flex items-center justify-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-300" /> ABDM & NABH 5th Edition Ready
          </p>
        </div>

        {/* Tab Selector */}
        <div className="flex border-b border-slate-200 bg-slate-50 text-sm font-semibold text-slate-600">
          <button
            type="button"
            onClick={() => {
              setMode('login');
              setError(null);
            }}
            className={`flex-1 py-3 text-center border-b-2 transition-all flex items-center justify-center gap-2 ${
              mode === 'login'
                ? 'border-brand-600 text-brand-700 bg-white shadow-sm'
                : 'border-transparent hover:text-slate-900'
            }`}
          >
            <Lock className="w-4 h-4" />
            Staff Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('signup');
              setError(null);
            }}
            className={`flex-1 py-3 text-center border-b-2 transition-all flex items-center justify-center gap-2 ${
              mode === 'signup'
                ? 'border-brand-600 text-brand-700 bg-white shadow-sm'
                : 'border-transparent hover:text-slate-900'
            }`}
          >
            <UserPlus className="w-4 h-4" />
            Register Hospital
          </button>
        </div>

        {/* Alerts */}
        <div className="px-6 pt-4">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs flex items-center gap-2 mb-3">
              <ShieldAlert className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
          {successMsg && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-700 text-xs flex items-center gap-2 mb-3">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}
        </div>

        {/* Sign In Form */}
        {mode === 'login' && (
          <form onSubmit={handleLoginSubmit} className="p-6 pt-2 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Staff Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="doctor@hms.local"
                  className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
            >
              {loading ? (
                <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
              ) : (
                <>
                  Sign In to Clinical Workspace
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        )}

        {mode === 'signup' && (
          <form onSubmit={handleSignupSubmit} className="p-6 pt-2 space-y-4">
            <label className="block text-sm font-medium">
              Hospital name
              <input required minLength={2} maxLength={255} value={hospitalName}
                onChange={(e) => setHospitalName(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 p-2" />
            </label>
            <label className="block text-sm font-medium">
              Hospital slug
              <input required minLength={2} maxLength={80} pattern="[a-z0-9]+(-[a-z0-9]+)*"
                placeholder="city-general-hospital" value={hospitalSlug}
                onChange={(e) => setHospitalSlug(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 p-2" />
            </label>
            <label className="block text-sm font-medium">
              Administrator name
              <input required minLength={2} maxLength={255} value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 p-2" />
            </label>
            <label className="block text-sm font-medium">
              Administrator email
              <input required type="email" autoComplete="email" value={signupEmail}
                onChange={(e) => setSignupEmail(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 p-2" />
            </label>
            <label className="block text-sm font-medium">
              Password
              <input required type="password" autoComplete="new-password" minLength={8} maxLength={72}
                value={signupPassword} onChange={(e) => setSignupPassword(e.target.value)}
                className="mt-1 w-full rounded border border-slate-300 p-2" />
            </label>
            <p className="text-xs text-slate-600">Your trial includes an OPD department and simulated ABHA workflows.</p>
            <button type="submit" disabled={loading}
              className="w-full rounded bg-brand-600 p-3 font-semibold text-white disabled:opacity-50">
              {loading ? 'Registering hospital…' : 'Register Hospital'}
            </button>
          </form>
        )}

        {/* Quick Demo Logins Section */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center justify-between">
            <span>One-Click Pre-Seeded Demo Accounts</span>
            <span className="text-[10px] text-brand-600 bg-brand-50 px-2 py-0.5 rounded font-mono">RBAC Testing</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              type="button"
              onClick={() => handleDemoFill('admin@hms.local', 'Admin@123')}
              className="p-2 bg-white border border-slate-300 hover:border-brand-500 rounded-lg text-left transition-colors group"
            >
              <div className="font-semibold text-slate-800 group-hover:text-brand-600">Hospital Admin</div>
              <div className="text-[10px] text-slate-500">admin@hms.local (Full Access)</div>
            </button>
            <button
              type="button"
              onClick={() => handleDemoFill('dr.sharma@hms.local', 'Staff@123')}
              className="p-2 bg-white border border-slate-300 hover:border-brand-500 rounded-lg text-left transition-colors group"
            >
              <div className="font-semibold text-slate-800 group-hover:text-brand-600">Dr. Rajesh Sharma</div>
              <div className="text-[10px] text-slate-500">dr.sharma@hms.local (EMR/Rx)</div>
            </button>
            <button
              type="button"
              onClick={() => handleDemoFill('reception@hms.local', 'Staff@123')}
              className="p-2 bg-white border border-slate-300 hover:border-brand-500 rounded-lg text-left transition-colors group"
            >
              <div className="font-semibold text-slate-800 group-hover:text-brand-600">Front Desk</div>
              <div className="text-[10px] text-slate-500">reception@hms.local (Queue/UHID)</div>
            </button>
            <button
              type="button"
              onClick={() => handleDemoFill('pharmacy@hms.local', 'Staff@123')}
              className="p-2 bg-white border border-slate-300 hover:border-brand-500 rounded-lg text-left transition-colors group"
            >
              <div className="font-semibold text-slate-800 group-hover:text-brand-600">Pharmacist</div>
              <div className="text-[10px] text-slate-500">pharmacy@hms.local (Dispensing)</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
