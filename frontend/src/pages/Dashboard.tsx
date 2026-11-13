import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { patientsApi, encountersApi } from '../services/api';
import {
  Users,
  Clock,
  Stethoscope,
  ArrowRight,
  ShieldCheck,
  CreditCard,
  Sliders,
  Bed,
  Command,
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    patientCount: 0,
    activeEncounters: 0,
    loading: true,
  });

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [patientsRes, encountersRes] = await Promise.all([
          patientsApi.list().catch(() => ({ total: 0 })),
          encountersApi.list({ status_filter: 'CHECKED_IN' }).catch(() => ({ total: 0 })),
        ]);
        setStats({
          patientCount: patientsRes.total,
          activeEncounters: encountersRes.total,
          loading: false,
        });
      } catch (err) {
        console.error('Failed to load dashboard metrics', err);
        setStats((prev) => ({ ...prev, loading: false }));
      }
    };

    fetchDashboardData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-brand-800 to-brand-900 rounded-2xl p-6 text-white shadow-md flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <span className="text-xs uppercase tracking-wider font-semibold text-brand-200">
            Clinical Care Operations
          </span>
          <h2 className="text-2xl font-bold mt-1">Welcome back, {user?.full_name}</h2>
          <p className="text-sm text-brand-100 mt-1">
            Department of {user?.department || 'Hospital Administration'} • Role: {user?.role}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => navigate('/abha')}
            className="px-3.5 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg text-xs font-semibold transition-colors shadow-sm flex items-center gap-1.5"
          >
            <CreditCard className="w-3.5 h-3.5" />
            Generate ABHA
          </button>
          <button
            onClick={() => navigate('/wards')}
            className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-colors shadow-sm flex items-center gap-1.5"
          >
            <Bed className="w-3.5 h-3.5" />
            Ward Census
          </button>
          <button
            onClick={() => navigate('/emr')}
            className="px-3.5 py-2 bg-white text-brand-800 hover:bg-brand-50 rounded-lg text-xs font-semibold transition-colors shadow-sm flex items-center gap-1.5"
          >
            <Stethoscope className="w-3.5 h-3.5" />
            Doctor Station
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Waiting in OPD
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {stats.loading ? '...' : stats.activeEncounters}
            </div>
            <div className="text-xs text-amber-600 font-medium mt-1 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" /> Tokens In Queue
            </div>
          </div>
          <div className="w-12 h-12 bg-amber-50 rounded-xl flex items-center justify-center text-amber-600">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Registered Patients
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {stats.loading ? '...' : stats.patientCount}
            </div>
            <div className="text-xs text-brand-600 font-medium mt-1 flex items-center gap-1">
              <Users className="w-3.5 h-3.5" /> UHID Assigned
            </div>
          </div>
          <div className="w-12 h-12 bg-brand-50 rounded-xl flex items-center justify-center text-brand-600">
            <Users className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              IPD Bed Census
            </div>
            <div className="text-2xl font-bold text-indigo-600 mt-1">75%</div>
            <div className="text-xs text-indigo-600 font-medium mt-1 flex items-center gap-1">
              <Bed className="w-3.5 h-3.5" /> 42 Occupied / 14 Vacant
            </div>
          </div>
          <div className="w-12 h-12 bg-indigo-50 rounded-xl flex items-center justify-center text-indigo-600">
            <Bed className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              ABDM Status
            </div>
            <div className="text-2xl font-bold text-emerald-600 mt-1">Active</div>
            <div className="text-xs text-emerald-600 font-medium mt-1 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" /> M1, M2, M3 Compliant
            </div>
          </div>
          <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center text-emerald-600">
            <ShieldCheck className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Keyboard Shortcuts Hint Banner */}
      <div className="p-3 bg-gradient-to-r from-slate-900 to-indigo-950 text-white rounded-xl flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <Command className="w-4 h-4 text-emerald-400" />
          <span className="font-bold">Keyboard-First Clinical Power:</span>
          <span className="text-slate-300">
            Press <kbd className="px-1.5 py-0.5 bg-white/10 rounded font-mono text-[11px]">Ctrl+K</kbd> anywhere for Quick Commands. Use <kbd className="px-1.5 py-0.5 bg-white/10 rounded font-mono text-[11px]">Alt+E</kbd> for EMR, <kbd className="px-1.5 py-0.5 bg-white/10 rounded font-mono text-[11px]">Alt+W</kbd> for Wards, <kbd className="px-1.5 py-0.5 bg-white/10 rounded font-mono text-[11px]">Alt+A</kbd> for ABHA.
          </span>
        </div>
        <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full font-mono">
          Instant Navigation Active
        </span>
      </div>

      {/* Quick Launch Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <div
          onClick={() => navigate('/abha')}
          className="bg-white p-6 rounded-xl border border-slate-200 hover:border-emerald-500 cursor-pointer transition-all hover:shadow-md group"
        >
          <div className="w-10 h-10 bg-emerald-50 rounded-lg flex items-center justify-center text-emerald-600 mb-4 group-hover:scale-110 transition-transform">
            <CreditCard className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-slate-900 group-hover:text-emerald-600 transition-colors">
            ABHA Care Portal
          </h3>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">
            Generate 14-digit ABHA Numbers using Aadhaar OTP e-KYC, verify existing digital IDs on the NHA gateway, and import records directly.
          </p>
          <div className="mt-4 flex items-center text-xs font-semibold text-emerald-600 gap-1 group-hover:gap-2 transition-all">
            Open ABHA Portal <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </div>

        <div
          onClick={() => navigate('/wards')}
          className="bg-white p-6 rounded-xl border border-slate-200 hover:border-indigo-500 cursor-pointer transition-all hover:shadow-md group"
        >
          <div className="w-10 h-10 bg-indigo-50 rounded-lg flex items-center justify-center text-indigo-600 mb-4 group-hover:scale-110 transition-transform">
            <Bed className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
            Inpatient Bed & Ward Map
          </h3>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">
            Live visual bed census for MICU, General Wards, and Emergency. Manage admissions, bed cleaning, and discharges.
          </p>
          <div className="mt-4 flex items-center text-xs font-semibold text-indigo-600 gap-1 group-hover:gap-2 transition-all">
            View Bed Matrix <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </div>

        <div
          onClick={() => navigate('/emr')}
          className="bg-white p-6 rounded-xl border border-slate-200 hover:border-brand-500 cursor-pointer transition-all hover:shadow-md group"
        >
          <div className="w-10 h-10 bg-brand-50 rounded-lg flex items-center justify-center text-brand-600 mb-4 group-hover:scale-110 transition-transform">
            <Stethoscope className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-slate-900 group-hover:text-brand-600 transition-colors">
            Doctor Consultation (EMR)
          </h3>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">
            CPOE 1-click clinical quick-sets, FHIR R4 abnormal lab reports, and SMS/WhatsApp digital prescription dispatch.
          </p>
          <div className="mt-4 flex items-center text-xs font-semibold text-brand-600 gap-1 group-hover:gap-2 transition-all">
            Open Doctor Station <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </div>

        <div
          onClick={() => navigate('/rbac')}
          className="bg-white p-6 rounded-xl border border-slate-200 hover:border-slate-800 cursor-pointer transition-all hover:shadow-md group"
        >
          <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center text-slate-700 mb-4 group-hover:scale-110 transition-transform">
            <Sliders className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-slate-900 group-hover:text-slate-900 transition-colors">
            RBAC Access Matrix
          </h3>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">
            Explore 9 hospital roles, information access meters, and fine-grained permissions under DPDP Act 2023.
          </p>
          <div className="mt-4 flex items-center text-xs font-semibold text-slate-700 gap-1 group-hover:gap-2 transition-all">
            Inspect RBAC Matrix <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </div>
      </div>
    </div>
  );
};
