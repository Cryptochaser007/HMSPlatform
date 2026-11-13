import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { UserRole } from '../../types';
import { CommandPalette } from '../common/CommandPalette';
import {
  LogOut,
  User as UserIcon,
  ShieldCheck,
  SlidersHorizontal,
  Command,
  Search,
} from 'lucide-react';

export const Header: React.FC = () => {
  const { user, logout, switchRoleDemo } = useAuth();
  const navigate = useNavigate();
  const [paletteOpen, setPaletteOpen] = useState(false);

  const roles: { value: UserRole; label: string }[] = [
    { value: 'SUPER_ADMIN', label: 'Super Admin' },
    { value: 'HOSPITAL_ADMIN', label: 'Hospital Admin' },
    { value: 'DOCTOR', label: 'Doctor (Consultant)' },
    { value: 'NURSE', label: 'Nurse' },
    { value: 'FRONT_DESK', label: 'Front Desk' },
    { value: 'PHARMACIST', label: 'Pharmacist' },
    { value: 'LAB_TECHNICIAN', label: 'Lab Technician' },
    { value: 'RADIOLOGIST', label: 'Radiologist' },
    { value: 'BILLING_CLERK', label: 'Billing Clerk' },
  ];

  // Global Keyboard Shortcuts Listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Toggle Command Palette (Ctrl+K or Cmd+K)
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((prev) => !prev);
        return;
      }

      // Alt Shortcuts for Rapid Clinical Navigation
      if (e.altKey && !e.ctrlKey && !e.metaKey) {
        const k = e.key.toLowerCase();
        if (k === '1' || k === 'd') {
          e.preventDefault();
          navigate('/');
        } else if (k === '2' || k === 'a') {
          e.preventDefault();
          navigate('/abha');
        } else if (k === '3' || k === 'p') {
          e.preventDefault();
          navigate('/patients');
        } else if (k === '4' || k === 'q') {
          e.preventDefault();
          navigate('/queue');
        } else if (k === '5' || k === 'e') {
          e.preventDefault();
          navigate('/emr');
        } else if (k === '6' || k === 'w') {
          e.preventDefault();
          navigate('/wards');
        } else if (k === '7' || k === 'r') {
          e.preventDefault();
          navigate('/rbac');
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate]);

  return (
    <>
      <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-30 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="bg-brand-600 text-white p-2 rounded-lg font-bold flex items-center justify-center shadow-md shadow-brand-500/20">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
              HMS Platform
              <span className="text-[11px] font-semibold tracking-wide uppercase px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-emerald-600" /> ABDM & NABH
              </span>
            </h1>
          </div>
        </div>

        {/* Global Action Search & Shortcuts */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setPaletteOpen(true)}
            className="hidden sm:flex items-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-600 px-3 py-1.5 rounded-lg text-xs font-semibold border border-slate-200 transition-colors group"
            title="Press Ctrl+K or Cmd+K to launch command search"
          >
            <Search className="w-3.5 h-3.5 text-slate-400 group-hover:text-brand-600" />
            <span className="hidden md:inline text-slate-500">Quick Command...</span>
            <div className="flex items-center gap-0.5 text-[10px] font-mono text-slate-400 bg-white border border-slate-300 px-1.5 py-0.2 rounded shadow-2xs">
              <Command className="w-2.5 h-2.5" /> K
            </div>
          </button>

          {/* Quick Role Simulator Switcher for Demo */}
          {user && (
            <div className="hidden lg:flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg text-xs">
              <SlidersHorizontal className="w-3.5 h-3.5 text-brand-600" />
              <span className="font-semibold text-slate-600">Simulate Role:</span>
              <select
                value={user.role}
                onChange={(e) => switchRoleDemo(e.target.value as UserRole)}
                className="bg-transparent font-bold text-brand-700 focus:outline-none cursor-pointer"
              >
                {roles.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {user && (
            <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
              <div className="w-9 h-9 bg-brand-50 border border-brand-200 rounded-full flex items-center justify-center text-brand-700">
                <UserIcon className="w-5 h-5" />
              </div>
              <div className="text-right hidden sm:block">
                <div className="text-sm font-semibold text-slate-800">{user.full_name}</div>
                <div className="text-xs text-slate-500 font-medium">
                  <span className="inline-block px-1.5 py-0.2 bg-slate-100 rounded text-slate-700 font-mono text-[10px] mr-1 font-semibold">
                    {user.role}
                  </span>
                  {user.department && `• ${user.department}`}
                </div>
              </div>
              <button
                onClick={logout}
                title="Logout"
                className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors ml-2"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Global Command Palette Overlay */}
      <CommandPalette isOpen={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </>
  );
};
