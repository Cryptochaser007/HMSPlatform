import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard,
  Users,
  Clock,
  Stethoscope,
  ExternalLink,
  Activity,
  CreditCard,
  Sliders,
  Bed,
  Lock,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { user } = useAuth();

  const navItems = [
    {
      name: 'Dashboard',
      path: '/',
      shortcut: 'Alt+D',
      icon: LayoutDashboard,
      allowedRoles: [
        'SUPER_ADMIN',
        'HOSPITAL_ADMIN',
        'DOCTOR',
        'NURSE',
        'PHARMACIST',
        'LAB_TECHNICIAN',
        'RADIOLOGIST',
        'BILLING_CLERK',
        'FRONT_DESK',
      ],
    },
    {
      name: 'ABHA Care Portal',
      path: '/abha',
      shortcut: 'Alt+A',
      icon: CreditCard,
      allowedRoles: ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'DOCTOR', 'FRONT_DESK', 'NURSE'],
    },
    {
      name: 'Patients (UHID / ABHA)',
      path: '/patients',
      shortcut: 'Alt+P',
      icon: Users,
      allowedRoles: ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'DOCTOR', 'FRONT_DESK', 'NURSE', 'BILLING_CLERK'],
    },
    {
      name: 'OPD Queue',
      path: '/queue',
      shortcut: 'Alt+Q',
      icon: Clock,
      allowedRoles: ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'DOCTOR', 'FRONT_DESK', 'NURSE'],
    },
    {
      name: 'Doctor Consultation (EMR)',
      path: '/emr',
      shortcut: 'Alt+E',
      icon: Stethoscope,
      allowedRoles: ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'DOCTOR'],
    },
    {
      name: 'Inpatient Beds & Wards',
      path: '/wards',
      shortcut: 'Alt+W',
      icon: Bed,
      allowedRoles: ['SUPER_ADMIN', 'HOSPITAL_ADMIN', 'DOCTOR', 'NURSE', 'FRONT_DESK'],
    },
    {
      name: 'RBAC Permission Matrix',
      path: '/rbac',
      shortcut: 'Alt+R',
      icon: Sliders,
      allowedRoles: [
        'SUPER_ADMIN',
        'HOSPITAL_ADMIN',
        'DOCTOR',
        'NURSE',
        'PHARMACIST',
        'LAB_TECHNICIAN',
        'RADIOLOGIST',
        'BILLING_CLERK',
        'FRONT_DESK',
      ],
    },
  ];

  const currentRole = user?.role || 'DOCTOR';

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 min-h-[calc(100vh-4rem)] border-r border-slate-800">
      <div className="p-4 space-y-1">
        <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider px-3 mb-2 flex items-center justify-between">
          <span>Clinical Navigation</span>
          <span className="text-[10px] text-brand-400 font-mono">{currentRole}</span>
        </div>
        {navItems.map((item) => {
          const isAllowed = item.allowedRoles.includes(currentRole);

          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-600 text-white shadow-sm'
                    : isAllowed
                    ? 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                    : 'text-slate-600 hover:text-slate-400 hover:bg-slate-800/30'
                }`
              }
            >
              <div className="flex items-center gap-3">
                <item.icon className="w-4 h-4 shrink-0" />
                <span className={!isAllowed ? 'line-through opacity-70' : ''}>{item.name}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-[9px] font-mono opacity-50 hidden group-hover:inline">
                  {item.shortcut}
                </span>
                {!isAllowed && (
                  <span title="Restricted for this role under DPDP">
                    <Lock className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                  </span>
                )}
              </div>
            </NavLink>
          );
        })}
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
