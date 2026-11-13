import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { UserRole } from '../../types';
import {
  Search,
  LayoutDashboard,
  CreditCard,
  Users,
  Clock,
  Stethoscope,
  Bed,
  Sliders,
  UserPlus,
  UserCheck,
  X,
  CornerDownLeft,
} from 'lucide-react';

interface CommandItem {
  id: string;
  title: string;
  subtitle: string;
  category: 'Navigation' | 'Actions' | 'Role Simulation';
  shortcut?: string;
  icon: React.ComponentType<{ className?: string }>;
  action: () => void;
}

export const CommandPalette: React.FC<{ isOpen: boolean; onClose: () => void }> = ({
  isOpen,
  onClose,
}) => {
  const navigate = useNavigate();
  const { switchRoleDemo } = useAuth();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  const commands: CommandItem[] = [
    // Navigation
    {
      id: 'nav-dashboard',
      title: 'Dashboard Overview',
      subtitle: 'Hospital operations, patient census & clinical KPIs',
      category: 'Navigation',
      shortcut: 'Alt+D',
      icon: LayoutDashboard,
      action: () => {
        navigate('/');
        onClose();
      },
    },
    {
      id: 'nav-abha',
      title: 'ABHA Care Portal',
      subtitle: 'Aadhaar OTP e-KYC generation & NHA gateway verification',
      category: 'Navigation',
      shortcut: 'Alt+A',
      icon: CreditCard,
      action: () => {
        navigate('/abha');
        onClose();
      },
    },
    {
      id: 'nav-patients',
      title: 'Patient Registry',
      subtitle: 'Search UHID, register new patients, link ABHA numbers',
      category: 'Navigation',
      shortcut: 'Alt+P',
      icon: Users,
      action: () => {
        navigate('/patients');
        onClose();
      },
    },
    {
      id: 'nav-queue',
      title: 'OPD Waiting Queue',
      subtitle: 'Real-time patient triage, token priorities, wait times',
      category: 'Navigation',
      shortcut: 'Alt+Q',
      icon: Clock,
      action: () => {
        navigate('/queue');
        onClose();
      },
    },
    {
      id: 'nav-emr',
      title: 'Doctor Consultation (EMR)',
      subtitle: 'SOAP clinical notes, vitals recording & digital e-prescriptions',
      category: 'Navigation',
      shortcut: 'Alt+E',
      icon: Stethoscope,
      action: () => {
        navigate('/emr');
        onClose();
      },
    },
    {
      id: 'nav-wards',
      title: 'Inpatient Bed Occupancy Matrix',
      subtitle: 'Visual IPD ward map, bed census & patient admissions',
      category: 'Navigation',
      shortcut: 'Alt+W',
      icon: Bed,
      action: () => {
        navigate('/wards');
        onClose();
      },
    },
    {
      id: 'nav-rbac',
      title: 'RBAC Permission Matrix',
      subtitle: 'Inspect 9 hospital roles, access meters & DPDP boundaries',
      category: 'Navigation',
      shortcut: 'Alt+R',
      icon: Sliders,
      action: () => {
        navigate('/rbac');
        onClose();
      },
    },

    // Actions
    {
      id: 'act-register-patient',
      title: 'Register New Patient',
      subtitle: 'Open patient registration form with auto-assigned UHID',
      category: 'Actions',
      icon: UserPlus,
      action: () => {
        navigate('/patients');
        onClose();
      },
    },
    {
      id: 'act-create-abha',
      title: 'Create ABHA ID via Aadhaar',
      subtitle: 'Step-by-step OTP e-KYC digital health account creation',
      category: 'Actions',
      icon: CreditCard,
      action: () => {
        navigate('/abha');
        onClose();
      },
    },

    // Role Simulation
    {
      id: 'role-doctor',
      title: 'Simulate as Doctor (Consultant)',
      subtitle: 'Access clinical EMR, SOAP notes, and e-prescriptions',
      category: 'Role Simulation',
      icon: UserCheck,
      action: () => {
        switchRoleDemo('DOCTOR' as UserRole);
        onClose();
      },
    },
    {
      id: 'role-admin',
      title: 'Simulate as Hospital Admin',
      subtitle: 'Full oversight on operations, wards, and audit logs',
      category: 'Role Simulation',
      icon: UserCheck,
      action: () => {
        switchRoleDemo('HOSPITAL_ADMIN' as UserRole);
        onClose();
      },
    },
    {
      id: 'role-frontdesk',
      title: 'Simulate as Front Desk Receptionist',
      subtitle: 'Focus on patient admissions, token queuing, and UHID triage',
      category: 'Role Simulation',
      icon: UserCheck,
      action: () => {
        switchRoleDemo('FRONT_DESK' as UserRole);
        onClose();
      },
    },
    {
      id: 'role-pharmacist',
      title: 'Simulate as Registered Pharmacist',
      subtitle: 'Prescription dispensing and drug inventory management',
      category: 'Role Simulation',
      icon: UserCheck,
      action: () => {
        switchRoleDemo('PHARMACIST' as UserRole);
        onClose();
      },
    },
  ];

  const filtered = commands.filter((c) => {
    const q = query.toLowerCase().trim();
    if (!q) return true;
    return (
      c.title.toLowerCase().includes(q) ||
      c.subtitle.toLowerCase().includes(q) ||
      c.category.toLowerCase().includes(q)
    );
  });

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Handle keyboard events when modal is open
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev < filtered.length - 1 ? prev + 1 : 0));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : filtered.length - 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filtered[selectedIndex]) {
          filtered[selectedIndex].action();
        }
      } else if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filtered, selectedIndex, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Header */}
        <div className="p-4 border-b border-slate-200 flex items-center gap-3 bg-slate-50">
          <Search className="w-5 h-5 text-slate-400 shrink-0" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a clinical command, page, or action... (e.g. 'emr', 'abha', 'doctor')"
            className="w-full bg-transparent text-sm text-slate-900 placeholder-slate-400 focus:outline-none font-medium"
          />
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Command List */}
        <div className="max-h-96 overflow-y-auto p-2 divide-y divide-slate-100">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No matching clinical commands found for <span className="font-semibold text-slate-700">"{query}"</span>
            </div>
          ) : (
            filtered.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              const Icon = item.icon;

              return (
                <div
                  key={item.id}
                  onClick={() => item.action()}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`p-3 rounded-xl flex items-center justify-between cursor-pointer transition-colors ${
                    isSelected ? 'bg-brand-50 border border-brand-200/60' : 'hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                        isSelected ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-900 flex items-center gap-2">
                        {item.title}
                        <span className="text-[10px] font-normal px-1.5 py-0.2 bg-slate-100 text-slate-500 rounded">
                          {item.category}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 line-clamp-1">{item.subtitle}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {item.shortcut && (
                      <span className="text-[10px] font-mono font-semibold px-2 py-0.5 bg-slate-100 border border-slate-200 text-slate-600 rounded">
                        {item.shortcut}
                      </span>
                    )}
                    {isSelected && <CornerDownLeft className="w-4 h-4 text-brand-600" />}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts hint */}
        <div className="px-4 py-2.5 bg-slate-50 border-t border-slate-200 text-[11px] text-slate-500 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="px-1.5 py-0.5 bg-white border border-slate-300 rounded font-mono text-[10px]">↑</kbd>{' '}
              <kbd className="px-1.5 py-0.5 bg-white border border-slate-300 rounded font-mono text-[10px]">↓</kbd>{' '}
              Navigate
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 bg-white border border-slate-300 rounded font-mono text-[10px]">Enter</kbd>{' '}
              Select
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 bg-white border border-slate-300 rounded font-mono text-[10px]">Esc</kbd>{' '}
              Close
            </span>
          </div>
          <span className="font-semibold text-brand-700">HMS Quick Navigation</span>
        </div>
      </div>
    </div>
  );
};
