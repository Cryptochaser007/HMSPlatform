import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Clock,
  Stethoscope,
  ExternalLink,
  Activity,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Sidebar: React.FC = () => {
  const { user } = useAuth();

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Patients (UHID / ABHA)', path: '/patients', icon: Users },
    { name: 'OPD Queue', path: '/queue', icon: Clock },
    { name: 'Doctor Consultation (EMR)', path: '/emr', icon: Stethoscope },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 min-h-[calc(100vh-4rem)] border-r border-slate-800">
      <div className="p-4 space-y-1">
        <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider px-3 mb-2">
          Clinical Navigation
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`
            }
          >
            <item.icon className="w-4 h-4 shrink-0" />
            {item.name}
          </NavLink>
        ))}
      </div>

      <div className="mt-auto p-4 border-t border-slate-800 space-y-3">
        <div className="bg-slate-800/70 p-3 rounded-lg border border-slate-700/60">
          <div className="flex items-center gap-2 text-xs text-emerald-400 font-semibold mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            Cloud API Active
          </div>
          <p className="text-[11px] text-slate-400">
            Connected to Supabase PostgreSQL in Mumbai (`ap-south-1`).
          </p>
        </div>

        <a
          href="/docs"
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-between text-xs font-medium text-slate-400 hover:text-white px-3 py-2 rounded-lg bg-slate-800/40 hover:bg-slate-800 transition-colors"
        >
          <span className="flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-brand-400" />
            Swagger API Docs
          </span>
          <ExternalLink className="w-3.5 h-3.5 opacity-60" />
        </a>
      </div>
    </aside>
  );
};

