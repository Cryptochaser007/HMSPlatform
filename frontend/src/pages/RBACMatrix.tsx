import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';
import {
  ShieldCheck,
  CheckCircle2,
  Eye,
  Lock,
  UserCheck,
  Sliders,
  FileText,
  CreditCard,
  Info,
} from 'lucide-react';

interface RoleDetail {
  role: UserRole;
  title: string;
  department: string;
  accessScore: number; // percentage
  summary: string;
  piiAccess: string;
  emrAccess: string;
  financialAccess: string;
}

const ROLES_INFO: RoleDetail[] = [
  {
    role: 'SUPER_ADMIN',
    title: 'Super Administrator',
    department: 'IT & Platform Security',
    accessScore: 100,
    summary: 'Complete platform control, user lifecycle management, database administration, and security auditing.',
    piiAccess: 'Full Access to Patient & Staff PII for compliance audits.',
    emrAccess: 'Full Access (read/write/audit) across all medical records.',
    financialAccess: 'Full access to hospital accounts, billing invoices, and financial reports.',
  },
  {
    role: 'HOSPITAL_ADMIN',
    title: 'Hospital Administrator',
    department: 'Hospital Management & Operations',
    accessScore: 88,
    summary: 'Oversees hospital operations, staff onboarding, department allocations, quality assurance, and compliance.',
    piiAccess: 'Full read/write access to administrative and demographic records.',
    emrAccess: 'Audit read-only access to clinical documentation for quality review.',
    financialAccess: 'Full oversight of revenue, departmental billing, and claims.',
  },
  {
    role: 'DOCTOR',
    title: 'Physician / Consultant',
    department: 'Clinical Care / Outpatient / Inpatient',
    accessScore: 78,
    summary: 'Primary care provider with full clinical autonomy: diagnoses, SOAP notes, prescriptions, and lab orders.',
    piiAccess: 'Full access to clinical demographic data for patients under consultation.',
    emrAccess: 'Complete clinical authority (Read/Write SOAP, Diagnoses, Vitals, Discharge summaries).',
    financialAccess: 'Read-only view of consultation charge items; no payment processing.',
  },
  {
    role: 'NURSE',
    title: 'Staff Nurse / Clinical Care',
    department: 'Wards / ICU / Triage',
    accessScore: 60,
    summary: 'Inpatient care monitoring, regular vitals recording, bed management, and medication administration.',
    piiAccess: 'Demographics and emergency contact details for assigned ward patients.',
    emrAccess: 'Read notes and enter hourly vitals, nursing care progress, and fluid charts.',
    financialAccess: 'Restricted (no access to patient financial or billing accounts).',
  },
  {
    role: 'PHARMACIST',
    title: 'Registered Pharmacist',
    department: 'Hospital Pharmacy & Dispensing',
    accessScore: 45,
    summary: 'Validates doctor prescriptions, dispenses medicines, logs batch lot numbers, and monitors drug inventory.',
    piiAccess: 'Limited to patient name, UHID, age, and prescribed medication regimen.',
    emrAccess: 'Read-only access to active prescriptions (sensitive psychiatric/HIV notes redacted).',
    financialAccess: 'Create medication invoices and receive counter payments.',
  },
  {
    role: 'LAB_TECHNICIAN',
    title: 'Laboratory Technician',
    department: 'Central Pathology & Biochemistry',
    accessScore: 42,
    summary: 'Processes diagnostic blood/tissue samples, enters test observations, and releases verified reports.',
    piiAccess: 'Minimal: Specimen barcode, UHID, age, and biological sex only.',
    emrAccess: 'Read lab requisition; create & verify laboratory diagnostic reports.',
    financialAccess: 'Restricted.',
  },
  {
    role: 'RADIOLOGIST',
    title: 'Consultant Radiologist',
    department: 'Radiology & Medical Imaging',
    accessScore: 50,
    summary: 'Reviews X-ray, CT, MRI scans, uploads DICOM imaging studies, and signs diagnostic radiology reports.',
    piiAccess: 'Patient UHID, age, and relevant clinical imaging referral indication.',
    emrAccess: 'Read radiology requisitions; write official imaging interpretation reports.',
    financialAccess: 'Restricted.',
  },
  {
    role: 'BILLING_CLERK',
    title: 'Billing & Cashier Specialist',
    department: 'Finance & Insurance TPA Desk',
    accessScore: 48,
    summary: 'Calculates procedure and bed charges, handles insurance pre-authorization, and issues receipts.',
    piiAccess: 'Patient billing demographic info, insurance policy numbers, and emergency contact.',
    emrAccess: 'Restricted from clinical SOAP notes (can only view billable procedure codes).',
    financialAccess: 'Full read/write on invoices, payments, insurance claims, and tariff sheets.',
  },
  {
    role: 'FRONT_DESK',
    title: 'Front Desk / Patient Triage',
    department: 'Reception & Admissions',
    accessScore: 38,
    summary: 'Patient registration, UHID issuance, ABHA Aadhaar creation, token generation, and bed booking.',
    piiAccess: 'Full read/write for basic demographic data, phone numbers, and emergency contacts.',
    emrAccess: 'Strictly Restricted (Zero access to diagnoses, clinical notes, or doctor investigations).',
    financialAccess: 'Collect initial consultation OPD token fees and bed advance deposits.',
  },
];

type AccessLevel = 'FULL' | 'VIEW' | 'RESTRICTED';

interface MatrixRow {
  category: string;
  permission: string;
  description: string;
  access: Record<UserRole, AccessLevel>;
}

const PERMISSION_MATRIX: MatrixRow[] = [
  // Patient & Identity
  {
    category: 'Patient Demographics & Identity',
    permission: 'Create / Register New Patient (UHID)',
    description: 'Issue unique hospital identifier, register demographic PII.',
    access: {
      SUPER_ADMIN: 'FULL',
      HOSPITAL_ADMIN: 'FULL',
      DOCTOR: 'FULL',
      NURSE: 'RESTRICTED',
      PHARMACIST: 'RESTRICTED',
      LAB_TECHNICIAN: 'RESTRICTED',
      RADIOLOGIST: 'RESTRICTED',
      BILLING_CLERK: 'RESTRICTED',
      FRONT_DESK: 'FULL',
    },
  },
  {
    category: 'Patient Demographics & Identity',
    permission: 'ABHA ID Aadhaar Linking & KYC',
    description: 'Verify patient identity with UIDAI / ABDM and link 14-digit ABHA.',
    access: {
      SUPER_ADMIN: 'FULL',
      HOSPITAL_ADMIN: 'FULL',
      DOCTOR: 'FULL',
      NURSE: 'RESTRICTED',
      PHARMACIST: 'RESTRICTED',
      LAB_TECHNICIAN: 'RESTRICTED',
      RADIOLOGIST: 'RESTRICTED',
      BILLING_CLERK: 'RESTRICTED',
      FRONT_DESK: 'FULL',
    },
  },
  {
    category: 'Patient Demographics & Identity',
    permission: 'Delete / Merge Patient UHID',
    description: 'Permanent record deletion or duplicate identity deduplication.',
    access: {
      SUPER_ADMIN: 'FULL',
      HOSPITAL_ADMIN: 'FULL',
      DOCTOR: 'RESTRICTED',
      NURSE: 'RESTRICTED',
      PHARMACIST: 'RESTRICTED',
      LAB_TECHNICIAN: 'RESTRICTED',
      RADIOLOGIST: 'RESTRICTED',
      BILLING_CLERK: 'RESTRICTED',
      FRONT_DESK: 'RESTRICTED',
    },
  },

  // Clinical & EMR
  {
    category: 'Clinical EMR & Health Records',
    permission: 'Write Clinical SOAP & Diagnoses',
    description: 'Record subjective symptoms, objective findings, ICD-10 diagnoses.',
    access: {
      SUPER_ADMIN: 'FULL',
      HOSPITAL_ADMIN: 'VIEW',
      DOCTOR: 'FULL',
      NURSE: 'RESTRICTED',
      PHARMACIST: 'RESTRICTED',
      LAB_TECHNICIAN: 'RESTRICTED',
      RADIOLOGIST: 'RESTRICTED',
      BILLING_CLERK: 'RESTRICTED',
      FRONT_DESK: 'RESTRICTED',
    },
  },
  {
    category: 'Clinical EMR & Health Records',
    permission: 'Record Patient Vitals & Triage',
    description: 'Enter BP, Pulse, SpO2, Temperature, Respiratory Rate, and Weight.',
    access: {
      SUPER_ADMIN: 'FULL',
      HOSPITAL_ADMIN: 'VIEW',
      DOCTOR: 'FULL',
      NURSE: 'FULL',
      PHARMACIST: 'RESTRICTED',
      LAB_TECHNICIAN: 'RESTRICTED',
      RADIOLOGIST: 'RESTRICTED',
      BILLING_CLERK: 'RESTRICTED',
      FRONT_DESK: 'VIEW',
    },
  },
  {
    category: 'Clinical EMR & Health Records',
    permission: 'View Longitudinal Clinical History',
    description: 'Inspect past encounters, chronic conditions, and previous therapies.',
    access: {
      SUPER_ADMIN: 'FULL',
      HOSPITAL_ADMIN: 'VIEW',
      DOCTOR: 'FULL',
      NURSE: 'VIEW',
      PHARMACIST: 'RESTRICTED',
      LAB_TECHNICIAN: 'RESTRICTED',
      RADIOLOGIST: 'VIEW',
      BILLING_CLERK: 'RESTRICTED',
      FRONT_DESK: 'RESTRICTED',
    },
  },

  // Pharmacy & Prescriptions
  {
    category: 'Pharmacy & Prescriptions',
    permission: 'Prescribe Medication Regimens',
    description: 'Authorise dosage, frequency, route, and duration of drugs.',
    access: {
      SUPER_ADMIN: 'FULL',
      HOSPITAL_ADMIN: 'VIEW',
      DOCTOR: 'FULL',
      NURSE: 'VIEW',
      PHARMACIST: 'VIEW',
      LAB_TECHNICIAN: 'RESTRICTED',
      RADIOLOGIST: 'RESTRICTED',
      BILLING_CLERK: 'VIEW',
      FRONT_DESK: 'RESTRICTED',
    },
  },
  {
    category: 'Pharmacy & Prescriptions',
    permission: 'Dispense Drugs & Log Batches',
    description: 'Fulfil prescription, check contraindications, deduct inventory.',
    access: {
      SUPER_ADMIN: 'FULL',
      HOSPITAL_ADMIN: 'FULL',
      DOCTOR: 'RESTRICTED',
      NURSE: 'RESTRICTED',
      PHARMACIST: 'FULL',
      LAB_TECHNICIAN: 'RESTRICTED',
      RADIOLOGIST: 'RESTRICTED',
      BILLING_CLERK: 'RESTRICTED',
      FRONT_DESK: 'RESTRICTED',
    },
  },

  // Diagnostics & Lab
  {
    category: 'Laboratory & Radiology Diagnostics',
    permission: 'Order Lab & Imaging Investigations',
    description: 'Requisition pathology tests, ultrasounds, MRI, or X-rays.',
    access: {
      SUPER_ADMIN: 'FULL',
      HOSPITAL_ADMIN: 'VIEW',
      DOCTOR: 'FULL',
      NURSE: 'RESTRICTED',
      PHARMACIST: 'RESTRICTED',
      LAB_TECHNICIAN: 'RESTRICTED',
      RADIOLOGIST: 'FULL',
      BILLING_CLERK: 'VIEW',
      FRONT_DESK: 'RESTRICTED',
    },
  },
  {
    category: 'Laboratory & Radiology Diagnostics',
    permission: 'Verify & Release Lab Results',
    description: 'Validate numerical specimen values against biological reference intervals.',
    access: {
      SUPER_ADMIN: 'FULL',
      HOSPITAL_ADMIN: 'VIEW',
      DOCTOR: 'VIEW',
      NURSE: 'VIEW',
      PHARMACIST: 'RESTRICTED',
      LAB_TECHNICIAN: 'FULL',
      RADIOLOGIST: 'RESTRICTED',
      BILLING_CLERK: 'RESTRICTED',
      FRONT_DESK: 'RESTRICTED',
    },
  },

  // Financials & Billing
  {
    category: 'Finance, Billing & Insurance',
    permission: 'Generate Invoices & Receive Payments',
    description: 'Itemise hospital charges, collect counter cash/cards, issue receipts.',
    access: {
      SUPER_ADMIN: 'FULL',
      HOSPITAL_ADMIN: 'FULL',
      DOCTOR: 'RESTRICTED',
      NURSE: 'RESTRICTED',
      PHARMACIST: 'FULL',
      LAB_TECHNICIAN: 'RESTRICTED',
      RADIOLOGIST: 'RESTRICTED',
      BILLING_CLERK: 'FULL',
      FRONT_DESK: 'FULL',
    },
  },

  // Platform Administration & Audit
  {
    category: 'Security, Users & Audit Trail',
    permission: 'Manage Staff Accounts & Credentials',
    description: 'Create hospital users, assign RBAC roles, deactivate accounts.',
    access: {
      SUPER_ADMIN: 'FULL',
      HOSPITAL_ADMIN: 'FULL',
      DOCTOR: 'RESTRICTED',
      NURSE: 'RESTRICTED',
      PHARMACIST: 'RESTRICTED',
      LAB_TECHNICIAN: 'RESTRICTED',
      RADIOLOGIST: 'RESTRICTED',
      BILLING_CLERK: 'RESTRICTED',
      FRONT_DESK: 'RESTRICTED',
    },
  },
  {
    category: 'Security, Users & Audit Trail',
    permission: 'View Immutable Audit Logs',
    description: 'Inspect cryptographic access trails, login IPs, and data modifications.',
    access: {
      SUPER_ADMIN: 'FULL',
      HOSPITAL_ADMIN: 'FULL',
      DOCTOR: 'RESTRICTED',
      NURSE: 'RESTRICTED',
      PHARMACIST: 'RESTRICTED',
      LAB_TECHNICIAN: 'RESTRICTED',
      RADIOLOGIST: 'RESTRICTED',
      BILLING_CLERK: 'RESTRICTED',
      FRONT_DESK: 'RESTRICTED',
    },
  },
];

export const RBACMatrix: React.FC = () => {
  const { user, switchRoleDemo } = useAuth();
  const [selectedRole, setSelectedRole] = useState<UserRole>(user?.role || 'DOCTOR');
  const [filterCategory, setFilterCategory] = useState<string>('ALL');

  const currentRoleInfo = ROLES_INFO.find((r) => r.role === selectedRole) || ROLES_INFO[2];

  const categories = ['ALL', ...Array.from(new Set(PERMISSION_MATRIX.map((m) => m.category)))];

  const filteredMatrix =
    filterCategory === 'ALL'
      ? PERMISSION_MATRIX
      : PERMISSION_MATRIX.filter((m) => m.category === filterCategory);

  const renderBadge = (level: AccessLevel) => {
    switch (level) {
      case 'FULL':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Full Access
          </span>
        );
      case 'VIEW':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-100 text-blue-800 border border-blue-300">
            <Eye className="w-3 h-3 text-blue-600" /> View Only
          </span>
        );
      case 'RESTRICTED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-500 border border-slate-200">
            <Lock className="w-3 h-3 text-slate-400" /> Restricted
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-brand-900 rounded-2xl p-6 text-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/10 backdrop-blur-md rounded-full text-xs font-semibold text-emerald-300 mb-2">
            <ShieldCheck className="w-3.5 h-3.5" /> DPDP Act 2023 & NABH 5th Edition Standard
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Role-Based Access Control (RBAC) Matrix</h1>
          <p className="text-sm text-slate-300 mt-1 max-w-2xl">
            Granular permission boundaries governing who can access patient records, clinical notes, prescriptions, and
            billing data under statutory privacy and medical confidentiality laws.
          </p>
        </div>
        <div className="bg-white/10 backdrop-blur-md border border-white/20 p-4 rounded-xl flex items-center gap-3 self-start md:self-auto">
          <div className="p-2 bg-brand-500 rounded-lg text-white">
            <Sliders className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs uppercase font-medium text-slate-300">Active Viewing Role</div>
            <div className="text-sm font-bold text-white font-mono">{user?.role}</div>
          </div>
        </div>
      </div>

      {/* Role Picker Carousel / Pills */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
          Select Role to Inspect Access Boundaries & Simulate Permissions:
        </div>
        <div className="flex flex-wrap gap-2">
          {ROLES_INFO.map((r) => (
            <button
              key={r.role}
              onClick={() => setSelectedRole(r.role)}
              className={`py-2 px-3.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-2 border ${
                selectedRole === r.role
                  ? 'bg-brand-600 text-white border-brand-600 shadow-sm ring-2 ring-brand-500/20'
                  : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
              }`}
            >
              <span>{r.title}</span>
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
                  selectedRole === r.role ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-600'
                }`}
              >
                {r.accessScore}%
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Role Detail Spotlight */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[11px] font-mono text-brand-600 font-bold uppercase tracking-wider">
                {currentRoleInfo.department}
              </span>
              <h2 className="text-xl font-bold text-slate-900">{currentRoleInfo.title}</h2>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-slate-900">{currentRoleInfo.accessScore}%</div>
              <div className="text-[10px] text-slate-500 font-semibold uppercase">Platform Scope</div>
            </div>
          </div>

          {/* Access Meter */}
          <div>
            <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  currentRoleInfo.accessScore >= 80
                    ? 'bg-emerald-500'
                    : currentRoleInfo.accessScore >= 50
                    ? 'bg-brand-500'
                    : 'bg-amber-500'
                }`}
                style={{ width: `${currentRoleInfo.accessScore}%` }}
              ></div>
            </div>
          </div>

          <p className="text-xs text-slate-600 leading-relaxed">{currentRoleInfo.summary}</p>

          <button
            onClick={() => switchRoleDemo(selectedRole)}
            className="w-full py-2.5 px-4 bg-slate-900 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold transition-colors flex items-center justify-center gap-2 shadow-sm"
          >
            <UserCheck className="w-4 h-4 text-emerald-400" />
            Simulate App Session as {currentRoleInfo.title}
          </button>
        </div>

        {/* Boundary Breakdown Cards */}
        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
              <UserCheck className="w-4 h-4 text-brand-600" />
              Patient PII Boundary
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">{currentRoleInfo.piiAccess}</p>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
              <FileText className="w-4 h-4 text-emerald-600" />
              Clinical / EMR Boundary
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">{currentRoleInfo.emrAccess}</p>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
              <CreditCard className="w-4 h-4 text-amber-600" />
              Billing & Revenue
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">{currentRoleInfo.financialAccess}</p>
          </div>
        </div>
      </div>

      {/* Interactive Permission Matrix Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Hospital Operational Permission Matrix</h3>
            <p className="text-xs text-slate-500">Cross-departmental comparison of authorization levels</p>
          </div>

          {/* Filter Dropdown */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-600">Module:</span>
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="px-3 py-1.5 text-xs font-medium border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-100 text-[11px] font-bold text-slate-700 uppercase tracking-wider border-b border-slate-200">
                <th className="py-3 px-4 w-72">Operation / Resource</th>
                <th className="py-3 px-3 text-center">Selected: {selectedRole}</th>
                <th className="py-3 px-3 text-center">DOCTOR</th>
                <th className="py-3 px-3 text-center">NURSE</th>
                <th className="py-3 px-3 text-center">FRONT_DESK</th>
                <th className="py-3 px-3 text-center">PHARMACIST</th>
                <th className="py-3 px-3 text-center">LAB_TECH</th>
                <th className="py-3 px-3 text-center">ADMIN</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {filteredMatrix.map((item, idx) => (
                <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4">
                    <div className="font-semibold text-slate-800">{item.permission}</div>
                    <div className="text-[11px] text-slate-500">{item.description}</div>
                  </td>
                  <td className="py-3 px-3 text-center bg-brand-50/40 border-x border-brand-100 font-medium">
                    {renderBadge(item.access[selectedRole])}
                  </td>
                  <td className="py-3 px-3 text-center">{renderBadge(item.access.DOCTOR)}</td>
                  <td className="py-3 px-3 text-center">{renderBadge(item.access.NURSE)}</td>
                  <td className="py-3 px-3 text-center">{renderBadge(item.access.FRONT_DESK)}</td>
                  <td className="py-3 px-3 text-center">{renderBadge(item.access.PHARMACIST)}</td>
                  <td className="py-3 px-3 text-center">{renderBadge(item.access.LAB_TECHNICIAN)}</td>
                  <td className="py-3 px-3 text-center">{renderBadge(item.access.HOSPITAL_ADMIN)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Legend Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-600">
          <div className="flex items-center gap-4">
            <span className="font-semibold">Legend:</span>
            <span className="flex items-center gap-1.5">{renderBadge('FULL')} Can modify, prescribe or bill</span>
            <span className="flex items-center gap-1.5">{renderBadge('VIEW')} Read-only observation</span>
            <span className="flex items-center gap-1.5">{renderBadge('RESTRICTED')} Blocked by DPDP policy</span>
          </div>
          <div className="text-[11px] text-slate-500 flex items-center gap-1">
            <Info className="w-3.5 h-3.5" />
            Permissions are cryptographically enforced on all FastAPI backend endpoints.
          </div>
        </div>
      </div>
    </div>
  );
};
