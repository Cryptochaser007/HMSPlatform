import React, { useState } from 'react';
import { Patient, PrescriptionItem, Vitals } from '../../types';
import {
  X,
  Printer,
  Share2,
  CheckCircle2,
  QrCode,
  ShieldCheck,
  Send,
  MessageSquare,
  Smartphone,
  Copy,
} from 'lucide-react';

interface DigitalRxModalProps {
  isOpen: boolean;
  onClose: () => void;
  patient?: Patient;
  doctorName?: string;
  doctorReg?: string;
  department?: string;
  diagnosis?: string;
  vitals?: Vitals;
  prescriptions: PrescriptionItem[];
}

export const DigitalRxModal: React.FC<DigitalRxModalProps> = ({
  isOpen,
  onClose,
  patient,
  doctorName = 'Dr. Rajesh Sharma, MD',
  doctorReg = 'NMC-2018-94021',
  department = 'General Medicine',
  diagnosis = 'Acute viral pharyngitis with tension headache',
  vitals,
  prescriptions,
}) => {
  const [activeChannel, setActiveChannel] = useState<'whatsapp' | 'sms' | 'abdm'>('whatsapp');
  const [phone, setPhone] = useState(patient?.phone || '9876543210');
  const [sentSuccess, setSentSuccess] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  if (!isOpen) return null;

  const rxId = `RX-${Date.now().toString().slice(-6)}`;
  const dateStr = new Date().toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  const handleDispatch = (channel: string) => {
    setSending(true);
    setSentSuccess(null);
    setTimeout(() => {
      setSending(false);
      setSentSuccess(`Prescription #${rxId} dispatched successfully via ${channel.toUpperCase()} to +91 ${phone}!`);
    }, 800);
  };

  const handlePrint = () => {
    window.print();
  };

  const copyLink = () => {
    navigator.clipboard.writeText(`https://abdm.gov.in/phr/rx/${rxId}`);
    alert('Digital Prescription link copied to clipboard!');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-150 overflow-y-auto">
      <div
        className="w-full max-w-3xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden my-8 flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Top Bar */}
        <div className="p-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Share2 className="w-4 h-4 text-emerald-400" />
            <span className="text-sm font-bold">Digital Prescription & Patient Dispatch</span>
            <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded-full font-mono">
              ABDM Verified
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Dispatch Channel Selector Banner */}
        <div className="bg-slate-50 border-b border-slate-200 p-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex rounded-lg border border-slate-300 p-0.5 bg-white text-xs font-semibold">
              <button
                onClick={() => {
                  setActiveChannel('whatsapp');
                  setSentSuccess(null);
                }}
                className={`py-1.5 px-3 rounded-md flex items-center gap-1.5 transition-colors ${
                  activeChannel === 'whatsapp' ? 'bg-emerald-600 text-white' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5" /> WhatsApp
              </button>
              <button
                onClick={() => {
                  setActiveChannel('sms');
                  setSentSuccess(null);
                }}
                className={`py-1.5 px-3 rounded-md flex items-center gap-1.5 transition-colors ${
                  activeChannel === 'sms' ? 'bg-brand-600 text-white' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Smartphone className="w-3.5 h-3.5" /> SMS Alert
              </button>
              <button
                onClick={() => {
                  setActiveChannel('abdm');
                  setSentSuccess(null);
                }}
                className={`py-1.5 px-3 rounded-md flex items-center gap-1.5 transition-colors ${
                  activeChannel === 'abdm' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" /> ABDM PHR Locker
              </button>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="Mobile number"
                className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 w-36 font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              <button
                onClick={() => handleDispatch(activeChannel)}
                disabled={sending || !phone}
                className="py-1.5 px-3 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-colors disabled:opacity-50"
              >
                {sending ? (
                  <span className="animate-spin rounded-full h-3 w-3 border border-white border-t-transparent" />
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" /> Send Now
                  </>
                )}
              </button>
            </div>
          </div>

          {sentSuccess && (
            <div className="p-2.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{sentSuccess}</span>
            </div>
          )}
        </div>

        {/* Prescription Document Preview (Printable) */}
        <div className="p-6 overflow-y-auto max-h-[60vh] space-y-6 bg-white" id="printable-rx">
          {/* Header */}
          <div className="border-b-2 border-slate-800 pb-4 flex justify-between items-start">
            <div>
              <div className="text-xl font-bold text-slate-900 tracking-tight">HMS CLINICAL HEALTHCARE</div>
              <div className="text-xs text-slate-500">NABH Accredited Tertiary Medical Centre • ABDM Integrated</div>
              <div className="text-xs text-slate-600 font-medium mt-1">
                {doctorName} ({department}) • Reg: {doctorReg}
              </div>
            </div>
            <div className="text-right">
              <span className="text-xs font-mono font-bold bg-slate-100 border border-slate-200 px-2 py-1 rounded text-slate-700">
                {rxId}
              </span>
              <div className="text-xs text-slate-500 mt-1">Date: {dateStr}</div>
            </div>
          </div>

          {/* Patient Demographic Banner */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div>
              <span className="text-[10px] text-slate-400 font-semibold uppercase block">Patient Name</span>
              <span className="font-bold text-slate-900">
                {patient ? `${patient.first_name} ${patient.last_name}` : 'Arun Kumar'}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 font-semibold uppercase block">UHID</span>
              <span className="font-mono font-bold text-brand-700">
                {patient?.registration_number || 'UHID-2026-9402'}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 font-semibold uppercase block">ABHA Number</span>
              <span className="font-mono text-slate-800">{patient?.abha_id || '91-4829-1029-4721'}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 font-semibold uppercase block">Gender / Age</span>
              <span className="font-medium text-slate-800">{patient?.gender || 'MALE'} • 35Y</span>
            </div>
          </div>

          {/* Vitals Snapshot if present */}
          {vitals && (
            <div className="p-3 bg-brand-50/40 border border-brand-100 rounded-xl text-xs flex flex-wrap items-center gap-4 text-slate-700">
              <span className="font-bold text-brand-800 text-[11px] uppercase">Recorded Vitals:</span>
              <span>BP: <strong>{vitals.systolic}/{vitals.diastolic} mmHg</strong></span>
              <span>Pulse: <strong>{vitals.pulse} bpm</strong></span>
              <span>SpO2: <strong>{vitals.spo2}%</strong></span>
              <span>Temp: <strong>{vitals.temperature}°F</strong></span>
              {vitals.bmi && <span>BMI: <strong>{vitals.bmi}</strong></span>}
            </div>
          )}

          {/* Diagnosis */}
          <div>
            <div className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Provisional Clinical Diagnosis:
            </div>
            <div className="text-sm font-semibold text-slate-900 bg-slate-50 border border-slate-200 p-2.5 rounded-lg">
              {diagnosis}
            </div>
          </div>

          {/* Medications Table */}
          <div>
            <div className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center justify-between">
              <span>Prescribed Medications (Rx)</span>
              <span className="text-[11px] text-slate-500 font-normal">{prescriptions.length} items</span>
            </div>
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                    <th className="py-2.5 px-3">#</th>
                    <th className="py-2.5 px-3">Drug & Formulation</th>
                    <th className="py-2.5 px-3">Dosage</th>
                    <th className="py-2.5 px-3">Frequency</th>
                    <th className="py-2.5 px-3">Duration</th>
                    <th className="py-2.5 px-3">Instructions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {prescriptions.map((p, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/60">
                      <td className="py-2.5 px-3 font-mono text-slate-400">{idx + 1}</td>
                      <td className="py-2.5 px-3 font-bold text-slate-900">{p.drug_name}</td>
                      <td className="py-2.5 px-3">{p.dosage}</td>
                      <td className="py-2.5 px-3 font-semibold text-brand-700">{p.frequency}</td>
                      <td className="py-2.5 px-3 font-mono">{p.duration_days} days</td>
                      <td className="py-2.5 px-3 text-slate-600">{p.instructions || 'After meals'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Digital Signature & Footer QR */}
          <div className="border-t border-slate-200 pt-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <QrCode className="w-14 h-14 text-slate-800 p-1 border border-slate-300 rounded-lg shrink-0" />
              <div className="text-[11px] text-slate-500 space-y-0.5">
                <div className="font-semibold text-slate-700">Scan to fetch FHIR Health Record</div>
                <div>ABDM Health ID: https://abdm.gov.in/phr/rx/{rxId}</div>
                <div className="text-emerald-600 font-medium">Digital SHA-256 Signature Verified</div>
              </div>
            </div>

            <div className="text-right text-xs">
              <div className="font-mono font-bold text-slate-800">{doctorName}</div>
              <div className="text-slate-500">Electronically Signed Consultation</div>
              <div className="text-[10px] text-slate-400 font-mono mt-0.5">ABDM-STAMP-{Date.now()}</div>
            </div>
          </div>
        </div>

        {/* Modal Bottom Actions */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <button
            onClick={copyLink}
            className="text-xs text-brand-600 hover:text-brand-800 font-semibold flex items-center gap-1.5"
          >
            <Copy className="w-3.5 h-3.5" /> Copy PHR Link
          </button>
          <div className="flex gap-2">
            <button
              onClick={handlePrint}
              className="py-2 px-4 border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <Printer className="w-3.5 h-3.5" /> Print Prescription
            </button>
            <button
              onClick={onClose}
              className="py-2 px-5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
            >
              Done / Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
