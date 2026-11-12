import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { encountersApi, clinicalApi } from '../services/api';
import { Encounter, Vitals, PrescriptionItem } from '../types';
import {
  Stethoscope,
  Activity,
  FileText,
  Pill,
  CheckCircle2,
  AlertCircle,
  Plus,
  Trash2,
  ArrowLeft,
} from 'lucide-react';

export const DoctorEMR: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const encounterIdFromUrl = searchParams.get('encounter_id');

  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [selectedEncounterId, setSelectedEncounterId] = useState<string>(encounterIdFromUrl || '');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Vitals State
  const [vitals, setVitals] = useState<Vitals>({
    temperature: 98.6,
    systolic: 120,
    diastolic: 80,
    pulse: 76,
    spo2: 99,
    weight: 70,
    height: 175,
  });

  // Computed BMI
  const bmi =
    vitals.weight && vitals.height
      ? (vitals.weight / Math.pow(vitals.height / 100, 2)).toFixed(1)
      : '—';

  // SOAP Note State
  const [soap, setSoap] = useState({
    subjective: 'Patient reports persistent headache and mild fatigue for the past 48 hours. No shortness of breath.',
    objective: 'Chest clear bilaterally. Heart sounds S1 S2 heard, no murmurs. Abdomen soft, non-tender. Throat mildly congested.',
    assessment: 'Acute viral pharyngitis with tension headache. Rule out secondary hypertension.',
    plan: 'Adequate hydration, warm saline gargles. Prescribed antipyretic and antihistaminic. Follow-up after 3 days if fever persists.',
  });

  // Prescriptions State
  const [prescriptions, setPrescriptions] = useState<PrescriptionItem[]>([
    {
      drug_name: 'Paracetamol 650mg',
      dosage: '1 Tablet',
      frequency: 'TDS (Thrice daily)',
      duration_days: 3,
      instructions: 'After food for fever/body aches',
    },
    {
      drug_name: 'Cetirizine 10mg',
      dosage: '1 Tablet',
      frequency: 'OD (Once daily at bedtime)',
      duration_days: 5,
      instructions: 'At night after meals',
    },
  ]);

  const [newDrug, setNewDrug] = useState<PrescriptionItem>({
    drug_name: '',
    dosage: '1 Tablet',
    frequency: 'BD (Twice daily)',
    duration_days: 5,
    instructions: 'After meals',
  });

  useEffect(() => {
    const fetchEncounters = async () => {
      try {
        setLoading(true);
        const res = await encountersApi.list();
        setEncounters(res.items || []);
        if (!selectedEncounterId && res.items?.length > 0) {
          setSelectedEncounterId(res.items[0].id);
        }
      } catch (err: any) {
        console.error(err);
        setError('Failed to fetch waiting encounters');
      } finally {
        setLoading(false);
      }
    };

    fetchEncounters();
  }, []);

  const activeEncounter = encounters.find((e) => e.id === selectedEncounterId);

  const handleAddDrug = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDrug.drug_name.trim()) return;
    setPrescriptions([...prescriptions, newDrug]);
    setNewDrug({
      drug_name: '',
      dosage: '1 Tablet',
      frequency: 'BD (Twice daily)',
      duration_days: 5,
      instructions: 'After meals',
    });
  };

  const handleRemoveDrug = (index: number) => {
    setPrescriptions(prescriptions.filter((_, i) => i !== index));
  };

  const handleSaveConsultation = async () => {
    if (!selectedEncounterId) {
      setError('Please select an active encounter to consult.');
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      // 1. Save SOAP Note with Vitals
      await clinicalApi.createNote({
        encounter_id: selectedEncounterId,
        note_type: 'SOAP',
        subjective: soap.subjective,
        objective: soap.objective,
        assessment: soap.assessment,
        plan: soap.plan,
        vitals: {
          ...vitals,
          bmi: parseFloat(bmi as string) || undefined,
        },
      });

      // 2. Mark Encounter as Completed
      await encountersApi.updateStatus(selectedEncounterId, 'COMPLETED');

      setSuccess(true);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to finalize consultation note');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Navigation */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <button
            onClick={() => navigate('/queue')}
            className="text-xs font-semibold text-slate-500 hover:text-slate-800 flex items-center gap-1 mb-1 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to OPD Queue
          </button>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Stethoscope className="w-6 h-6 text-brand-600" /> Doctor Consultation Station (EMR)
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            SOAP Clinical Notes, Real-Time Vitals, and Digital e-Prescriptions.
          </p>
        </div>

        {/* Encounter Selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-slate-600 shrink-0">Consulting Patient:</label>
          {loading ? (
            <span className="text-xs text-slate-400">Loading queue...</span>
          ) : (
            <select
              value={selectedEncounterId}
              onChange={(e) => {
                setSelectedEncounterId(e.target.value);
                setSuccess(false);
              }}
              className="text-sm font-semibold bg-white border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-brand-500 focus:outline-none"
            >
              {encounters.map((enc) => (
                <option key={enc.id} value={enc.id}>
                  Token #{enc.token_number || '—'} •{' '}
                  {enc.patient ? `${enc.patient.first_name} ${enc.patient.last_name}` : 'Patient'}{' '}
                  ({enc.status})
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Success Notification */}
      {success && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 flex items-center gap-3 shadow-sm animate-fade-in">
          <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
          <div>
            <div className="text-sm font-bold">Consultation Successfully Finalized!</div>
            <div className="text-xs text-emerald-700">
              The SOAP clinical note, vitals, and prescription have been signed and committed to the immutable medical record.
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Patient Clinical Banner */}
      {activeEncounter && (
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-brand-50 rounded-xl flex items-center justify-center text-brand-700 font-bold font-mono text-lg border border-brand-200">
              #{activeEncounter.token_number || '1'}
            </div>
            <div>
              <div className="text-base font-bold text-slate-900">
                {activeEncounter.patient
                  ? `${activeEncounter.patient.first_name} ${activeEncounter.patient.last_name}`
                  : 'Patient Record'}
                <span className="ml-2 font-normal text-xs text-slate-500">
                  {activeEncounter.patient?.gender} • DOB: {activeEncounter.patient?.date_of_birth}
                </span>
              </div>
              <div className="text-xs text-slate-500 font-mono mt-0.5">
                UHID: <span className="font-semibold text-brand-700">{activeEncounter.patient?.registration_number}</span> •{' '}
                Chief Complaint: <span className="text-slate-800 italic">&quot;{activeEncounter.chief_complaint || 'General Checkup'}&quot;</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 bg-brand-50 text-brand-700 border border-brand-200 rounded-lg text-xs font-semibold">
              {activeEncounter.department}
            </span>
            <span className="px-2.5 py-1 bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold">
              Status: {activeEncounter.status}
            </span>
          </div>
        </div>
      )}

      {/* Vitals Recording Section */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
          <Activity className="w-4 h-4 text-rose-500" /> Patient Vitals & Physiological Telemetry
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div className="text-[10px] font-semibold text-slate-500 uppercase">Temp (°F)</div>
            <input
              type="number"
              step="0.1"
              value={vitals.temperature || ''}
              onChange={(e) => setVitals({ ...vitals, temperature: parseFloat(e.target.value) })}
              className="w-full bg-white text-sm font-bold text-slate-900 border border-slate-300 rounded p-1 mt-1 focus:ring-1 focus:ring-brand-500 focus:outline-none"
            />
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div className="text-[10px] font-semibold text-slate-500 uppercase">BP (Sys / Dia)</div>
            <div className="flex items-center gap-1 mt-1">
              <input
                type="number"
                value={vitals.systolic || ''}
                onChange={(e) => setVitals({ ...vitals, systolic: parseInt(e.target.value) })}
                className="w-1/2 bg-white text-sm font-bold text-slate-900 border border-slate-300 rounded p-1 focus:outline-none"
                placeholder="120"
              />
              <span className="text-slate-400">/</span>
              <input
                type="number"
                value={vitals.diastolic || ''}
                onChange={(e) => setVitals({ ...vitals, diastolic: parseInt(e.target.value) })}
                className="w-1/2 bg-white text-sm font-bold text-slate-900 border border-slate-300 rounded p-1 focus:outline-none"
                placeholder="80"
              />
            </div>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div className="text-[10px] font-semibold text-slate-500 uppercase">Pulse (bpm)</div>
            <input
              type="number"
              value={vitals.pulse || ''}
              onChange={(e) => setVitals({ ...vitals, pulse: parseInt(e.target.value) })}
              className="w-full bg-white text-sm font-bold text-slate-900 border border-slate-300 rounded p-1 mt-1 focus:ring-1 focus:ring-brand-500 focus:outline-none"
            />
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div className="text-[10px] font-semibold text-slate-500 uppercase">SpO2 (%)</div>
            <input
              type="number"
              value={vitals.spo2 || ''}
              onChange={(e) => setVitals({ ...vitals, spo2: parseInt(e.target.value) })}
              className="w-full bg-white text-sm font-bold text-slate-900 border border-slate-300 rounded p-1 mt-1 focus:ring-1 focus:ring-brand-500 focus:outline-none"
            />
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div className="text-[10px] font-semibold text-slate-500 uppercase">Weight & Height</div>
            <div className="flex items-center gap-1 mt-1">
              <input
                type="number"
                value={vitals.weight || ''}
                onChange={(e) => setVitals({ ...vitals, weight: parseFloat(e.target.value) })}
                className="w-1/2 bg-white text-sm font-bold text-slate-900 border border-slate-300 rounded p-1 focus:outline-none"
                placeholder="kg"
              />
              <span className="text-slate-400">kg</span>
              <input
                type="number"
                value={vitals.height || ''}
                onChange={(e) => setVitals({ ...vitals, height: parseFloat(e.target.value) })}
                className="w-1/2 bg-white text-sm font-bold text-slate-900 border border-slate-300 rounded p-1 focus:outline-none"
                placeholder="cm"
              />
            </div>
          </div>

          <div className="p-3 bg-brand-50/60 rounded-lg border border-brand-200 text-center flex flex-col justify-center">
            <div className="text-[10px] font-semibold text-brand-700 uppercase">Auto BMI</div>
            <div className="text-lg font-bold text-brand-800 mt-0.5">{bmi}</div>
          </div>
        </div>
      </div>

      {/* SOAP Clinical Note Section */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
          <FileText className="w-4 h-4 text-brand-600" /> Structured SOAP Documentation (NABH Mandated)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              [S] Subjective — Chief Complaint & History
            </label>
            <textarea
              rows={3}
              value={soap.subjective}
              onChange={(e) => setSoap({ ...soap, subjective: e.target.value })}
              className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              [O] Objective — Examination & Vitals Findings
            </label>
            <textarea
              rows={3}
              value={soap.objective}
              onChange={(e) => setSoap({ ...soap, objective: e.target.value })}
              className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              [A] Assessment — Diagnosis / Clinical Impression
            </label>
            <textarea
              rows={3}
              value={soap.assessment}
              onChange={(e) => setSoap({ ...soap, assessment: e.target.value })}
              className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              [P] Plan — Investigations, Advice & Follow-Up
            </label>
            <textarea
              rows={3}
              value={soap.plan}
              onChange={(e) => setSoap({ ...soap, plan: e.target.value })}
              className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-brand-500 focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* e-Prescription Section */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
          <Pill className="w-4 h-4 text-emerald-600" /> Digital e-Prescription (Pharmacy Fulfillment)
        </h3>

        {/* Prescription Table */}
        <div className="border border-slate-200 rounded-lg overflow-hidden">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 text-slate-600 border-b border-slate-200 font-semibold">
                <th className="py-2.5 px-3">Medication Name</th>
                <th className="py-2.5 px-3">Dosage</th>
                <th className="py-2.5 px-3">Frequency</th>
                <th className="py-2.5 px-3">Duration</th>
                <th className="py-2.5 px-3">Special Instructions</th>
                <th className="py-2.5 px-3 text-right">Remove</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {prescriptions.map((p, idx) => (
                <tr key={idx} className="hover:bg-slate-50">
                  <td className="py-2.5 px-3 font-semibold text-slate-900">{p.drug_name}</td>
                  <td className="py-2.5 px-3">{p.dosage}</td>
                  <td className="py-2.5 px-3 font-mono">{p.frequency}</td>
                  <td className="py-2.5 px-3">{p.duration_days} days</td>
                  <td className="py-2.5 px-3 text-slate-500">{p.instructions || '—'}</td>
                  <td className="py-2.5 px-3 text-right">
                    <button
                      onClick={() => handleRemoveDrug(idx)}
                      className="text-slate-400 hover:text-rose-600 p-1 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Quick Add Drug Form */}
        <form onSubmit={handleAddDrug} className="p-3 bg-slate-50 rounded-lg border border-slate-200 grid grid-cols-1 sm:grid-cols-5 gap-2 items-end">
          <div className="sm:col-span-2">
            <label className="block text-[10px] font-semibold text-slate-600 uppercase mb-1">
              Drug Name
            </label>
            <input
              type="text"
              required
              value={newDrug.drug_name}
              onChange={(e) => setNewDrug({ ...newDrug, drug_name: e.target.value })}
              placeholder="e.g. Amoxicillin 500mg"
              className="w-full text-xs border border-slate-300 rounded p-1.5 bg-white focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-[10px] font-semibold text-slate-600 uppercase mb-1">
              Frequency
            </label>
            <select
              value={newDrug.frequency}
              onChange={(e) => setNewDrug({ ...newDrug, frequency: e.target.value })}
              className="w-full text-xs border border-slate-300 rounded p-1.5 bg-white focus:outline-none"
            >
              <option value="OD (Once daily)">OD (Once daily)</option>
              <option value="BD (Twice daily)">BD (Twice daily)</option>
              <option value="TDS (Thrice daily)">TDS (Thrice daily)</option>
              <option value="QID (4 times daily)">QID (4 times daily)</option>
              <option value="SOS (As needed)">SOS (As needed)</option>
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-semibold text-slate-600 uppercase mb-1">
              Days
            </label>
            <input
              type="number"
              min="1"
              value={newDrug.duration_days}
              onChange={(e) => setNewDrug({ ...newDrug, duration_days: parseInt(e.target.value) })}
              className="w-full text-xs border border-slate-300 rounded p-1.5 bg-white focus:outline-none"
            />
          </div>

          <div>
            <button
              type="submit"
              className="w-full py-1.5 px-3 bg-slate-800 hover:bg-slate-900 text-white rounded text-xs font-semibold flex items-center justify-center gap-1 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" /> Add Drug
            </button>
          </div>
        </form>
      </div>

      {/* Action Footer */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row justify-between items-center gap-3">
        <div className="text-xs text-slate-500">
          Clicking Finalize writes to the SHA-256 cryptographic audit chain and marks the encounter completed.
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => navigate('/queue')}
            className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSaveConsultation}
            disabled={saving || !selectedEncounterId}
            className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-colors flex items-center gap-2 shadow-md shadow-emerald-500/20 disabled:opacity-50"
          >
            {saving ? (
              'Signing & Committing...'
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Sign & Finalize Consultation
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

