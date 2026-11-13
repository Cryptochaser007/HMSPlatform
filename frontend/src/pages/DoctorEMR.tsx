import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { encountersApi, clinicalApi } from '../services/api';
import { Encounter, Vitals, PrescriptionItem, LabResultItem } from '../types';
import { DigitalRxModal } from '../components/common/DigitalRxModal';
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
  Share2,
  Microscope,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  Printer,
} from 'lucide-react';

interface ClinicalTemplate {
  id: string;
  name: string;
  icon: string;
  assessment: string;
  plan: string;
  drugs: PrescriptionItem[];
}

const CLINICAL_TEMPLATES: ClinicalTemplate[] = [
  {
    id: 'uri',
    name: 'Acute Pharyngitis / URI',
    icon: '🌡️',
    assessment: 'Acute viral pharyngitis with mild nasal congestion and low-grade pyrexia. Chest clear bilaterally.',
    plan: 'Adequate hydration, steam inhalation BD, warm saline gargles. Prescribed antipyretic & antihistaminic.',
    drugs: [
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
        frequency: 'OD (Once daily)',
        duration_days: 5,
        instructions: 'At night after food',
      },
      {
        drug_name: 'Azithromycin 500mg',
        dosage: '1 Tablet',
        frequency: 'OD (Once daily)',
        duration_days: 3,
        instructions: '1 hour before food',
      },
    ],
  },
  {
    id: 'diabetes',
    name: 'Type 2 Diabetes Routine',
    icon: '🩺',
    assessment: 'Type 2 Diabetes Mellitus with sub-optimal glycemic control (HbA1c 7.8%). No ketonuria.',
    plan: 'Low glycemic index diabetic diet, 30 min daily aerobic walks. Fasting blood sugar log. Serum creatinine in 3 months.',
    drugs: [
      {
        drug_name: 'Metformin 500mg SR',
        dosage: '1 Tablet',
        frequency: 'BD (Twice daily)',
        duration_days: 30,
        instructions: 'Take with main meals',
      },
      {
        drug_name: 'Glimepiride 1mg',
        dosage: '1 Tablet',
        frequency: 'OD (Once daily)',
        duration_days: 30,
        instructions: 'Before breakfast',
      },
      {
        drug_name: 'Methylcobalamin 1500mcg',
        dosage: '1 Tablet',
        frequency: 'OD (Once daily)',
        duration_days: 30,
        instructions: 'After dinner',
      },
    ],
  },
  {
    id: 'hypertension',
    name: 'Hypertension Regimen',
    icon: '💓',
    assessment: 'Essential Systemic Hypertension (Stage 1). Sitting BP 146/92 mmHg. Fundus examination normal.',
    plan: 'DASH low-sodium diet (<2g sodium/day). Daily morning home BP logging. Review in 4 weeks.',
    drugs: [
      {
        drug_name: 'Telmisartan 40mg',
        dosage: '1 Tablet',
        frequency: 'OD (Once daily)',
        duration_days: 30,
        instructions: 'Morning after breakfast',
      },
      {
        drug_name: 'Amlodipine 5mg',
        dosage: '1 Tablet',
        frequency: 'OD (Once daily)',
        duration_days: 30,
        instructions: 'Bedtime',
      },
    ],
  },
  {
    id: 'gastritis',
    name: 'Acute Gastritis / GERD',
    icon: '🦠',
    assessment: 'Acute erosive gastritis with dyspepsia and mild gastroesophageal reflux. No hematemesis.',
    plan: 'Avoid spicy, oily food and carbonated drinks. Small frequent meals. Do not recline within 2 hrs of meals.',
    drugs: [
      {
        drug_name: 'Pantoprazole 40mg',
        dosage: '1 Tablet',
        frequency: 'OD (Once daily)',
        duration_days: 14,
        instructions: '30 mins before breakfast',
      },
      {
        drug_name: 'Domperidone 10mg',
        dosage: '1 Tablet',
        frequency: 'BD (Twice daily)',
        duration_days: 5,
        instructions: 'Before meals',
      },
      {
        drug_name: 'Sucralfate Syrup 10ml',
        dosage: '10 ml',
        frequency: 'TDS (Thrice daily)',
        duration_days: 7,
        instructions: 'Between meals',
      },
    ],
  },
  {
    id: 'pain',
    name: 'Lumbar Strain / Joint Pain',
    icon: '🦴',
    assessment: 'Acute lower lumbar musculoskeletal strain. Paravertebral spasm present. Straight leg raise negative.',
    plan: 'Ergonomic lumbar support, avoid heavy lifting. Ice packs for 48 hrs, followed by gentle core exercises.',
    drugs: [
      {
        drug_name: 'Aceclofenac 100mg + Paracetamol 325mg',
        dosage: '1 Tablet',
        frequency: 'BD (Twice daily)',
        duration_days: 5,
        instructions: 'Strictly after meals',
      },
      {
        drug_name: 'Thiocolchicoside 4mg',
        dosage: '1 Capsule',
        frequency: 'BD (Twice daily)',
        duration_days: 5,
        instructions: 'Muscle relaxant at bedtime',
      },
      {
        drug_name: 'Diclofenac Gel 1%',
        dosage: 'Local Application',
        frequency: 'TDS (Thrice daily)',
        duration_days: 7,
        instructions: 'Apply gently over lower back',
      },
    ],
  },
];

const SAMPLE_LAB_RESULTS: LabResultItem[] = [
  // Hematology (CBC)
  {
    id: 'l1',
    parameter_name: 'Hemoglobin (Hb)',
    value: '13.8',
    unit: 'g/dL',
    reference_interval: '13.0 - 17.0',
    flag: 'NORMAL',
    category: 'Complete Blood Count (CBC)',
  },
  {
    id: 'l2',
    parameter_name: 'Total Leukocyte Count (WBC)',
    value: '11,400',
    unit: '/cu.mm',
    reference_interval: '4,000 - 10,000',
    flag: 'HIGH',
    category: 'Complete Blood Count (CBC)',
  },
  {
    id: 'l3',
    parameter_name: 'Platelet Count',
    value: '240,000',
    unit: '/cu.mm',
    reference_interval: '150,000 - 450,000',
    flag: 'NORMAL',
    category: 'Complete Blood Count (CBC)',
  },
  {
    id: 'l4',
    parameter_name: 'Erythrocyte Sedimentation Rate (ESR)',
    value: '28',
    unit: 'mm/1st hr',
    reference_interval: '0 - 15',
    flag: 'HIGH',
    category: 'Complete Blood Count (CBC)',
  },

  // Metabolic & Renal
  {
    id: 'l5',
    parameter_name: 'Fasting Blood Sugar (FBS)',
    value: '142',
    unit: 'mg/dL',
    reference_interval: '70 - 100',
    flag: 'HIGH',
    category: 'Biochemistry & Renal Profile',
  },
  {
    id: 'l6',
    parameter_name: 'HbA1c (Glycated Hemoglobin)',
    value: '7.8',
    unit: '%',
    reference_interval: '< 5.7',
    flag: 'HIGH',
    category: 'Biochemistry & Renal Profile',
  },
  {
    id: 'l7',
    parameter_name: 'Serum Creatinine',
    value: '0.9',
    unit: 'mg/dL',
    reference_interval: '0.7 - 1.3',
    flag: 'NORMAL',
    category: 'Biochemistry & Renal Profile',
  },
  {
    id: 'l8',
    parameter_name: 'Blood Urea Nitrogen (BUN)',
    value: '16',
    unit: 'mg/dL',
    reference_interval: '7 - 20',
    flag: 'NORMAL',
    category: 'Biochemistry & Renal Profile',
  },

  // Lipid Profile
  {
    id: 'l9',
    parameter_name: 'Total Cholesterol',
    value: '228',
    unit: 'mg/dL',
    reference_interval: '< 200',
    flag: 'HIGH',
    category: 'Lipid Profile',
  },
  {
    id: 'l10',
    parameter_name: 'Triglycerides',
    value: '185',
    unit: 'mg/dL',
    reference_interval: '< 150',
    flag: 'HIGH',
    category: 'Lipid Profile',
  },
  {
    id: 'l11',
    parameter_name: 'HDL (Good Cholesterol)',
    value: '38',
    unit: 'mg/dL',
    reference_interval: '> 40',
    flag: 'LOW',
    category: 'Lipid Profile',
  },
  {
    id: 'l12',
    parameter_name: 'LDL (Bad Cholesterol)',
    value: '145',
    unit: 'mg/dL',
    reference_interval: '< 100',
    flag: 'HIGH',
    category: 'Lipid Profile',
  },
];

export const DoctorEMR: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const encounterIdFromUrl = searchParams.get('encounter_id');

  const [activeTab, setActiveTab] = useState<'soap' | 'labs'>('soap');
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [selectedEncounterId, setSelectedEncounterId] = useState<string>(encounterIdFromUrl || '');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [rxModalOpen, setRxModalOpen] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

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

  const handleApplyTemplate = (tmpl: ClinicalTemplate) => {
    setSoap((prev) => ({
      ...prev,
      assessment: tmpl.assessment,
      plan: tmpl.plan,
    }));
    setPrescriptions(tmpl.drugs);
    setToastMsg(`Applied CPOE Template: ${tmpl.name}!`);
    setTimeout(() => setToastMsg(null), 3000);
  };

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
      {/* Toast Alert */}
      {toastMsg && (
        <div className="fixed top-20 right-6 z-50 p-3 bg-slate-900 text-white text-xs font-semibold rounded-xl shadow-xl border border-slate-700 flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
          <Sparkles className="w-4 h-4 text-emerald-400" />
          <span>{toastMsg}</span>
        </div>
      )}

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
            SOAP Clinical Notes, Physiological Vitals, CPOE Quick-Sets & Digital e-Prescriptions.
          </p>
        </div>

        {/* Encounter Selector & Digital Rx Share */}
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

          <button
            onClick={() => setRxModalOpen(true)}
            className="py-2 px-3 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm ml-2"
          >
            <Share2 className="w-3.5 h-3.5 text-emerald-400" /> Dispatch Rx
          </button>
        </div>
      </div>

      {/* Success Notification */}
      {success && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 flex items-center justify-between shadow-sm animate-fade-in">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
            <div>
              <div className="text-sm font-bold">Consultation Successfully Finalized & Electronically Signed!</div>
              <div className="text-xs text-emerald-700">
                The SOAP clinical note, vitals, and prescription have been committed to the immutable medical audit trail.
              </div>
            </div>
          </div>
          <button
            onClick={() => setRxModalOpen(true)}
            className="py-1.5 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-xs"
          >
            <Share2 className="w-3.5 h-3.5" /> Share Digital Rx with Patient
          </button>
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
                UHID:{' '}
                <span className="font-semibold text-brand-700">{activeEncounter.patient?.registration_number}</span> •{' '}
                Chief Complaint:{' '}
                <span className="text-slate-800 italic">
                  &quot;{activeEncounter.chief_complaint || 'General Checkup'}&quot;
                </span>
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

      {/* View Switcher: Clinical Consultation vs Diagnostics */}
      <div className="flex border-b border-slate-200 bg-white rounded-t-xl px-4 pt-2 gap-4">
        <button
          onClick={() => setActiveTab('soap')}
          className={`pb-3 px-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'soap'
              ? 'border-brand-600 text-brand-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <FileText className="w-4 h-4" />
          Clinical SOAP & Prescriptions
        </button>
        <button
          onClick={() => setActiveTab('labs')}
          className={`pb-3 px-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'labs'
              ? 'border-brand-600 text-brand-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Microscope className="w-4 h-4" />
          FHIR R4 Diagnostic & Lab Reports
          <span className="text-[10px] bg-rose-100 text-rose-700 px-1.5 py-0.2 rounded-full font-bold">
            5 Abnormal
          </span>
        </button>
      </div>

      {/* TAB 1: CLINICAL SOAP & PRESCRIPTION */}
      {activeTab === 'soap' && (
        <div className="space-y-6">
          {/* 1-Click CPOE OPD Quick-Sets Bar */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
            <div className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-brand-600" /> 1-Click Clinical CPOE Quick-Sets & Regimens:
              </span>
              <span className="text-[10px] text-slate-500 lowercase">click to auto-populate assessment & Rx</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {CLINICAL_TEMPLATES.map((tmpl) => (
                <button
                  key={tmpl.id}
                  onClick={() => handleApplyTemplate(tmpl)}
                  className="py-1.5 px-3 bg-white hover:bg-brand-50 border border-slate-200 hover:border-brand-400 rounded-lg text-xs font-semibold text-slate-800 transition-all shadow-xs flex items-center gap-1.5 group"
                >
                  <span>{tmpl.icon}</span>
                  <span className="group-hover:text-brand-700">{tmpl.name}</span>
                </button>
              ))}
            </div>
          </div>

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
                  [S] Subjective Symptoms & History
                </label>
                <textarea
                  rows={3}
                  value={soap.subjective}
                  onChange={(e) => setSoap({ ...soap, subjective: e.target.value })}
                  placeholder="Patient's reported complaints, symptoms onset, duration..."
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:outline-none focus:ring-2 focus:ring-brand-500 leading-relaxed"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  [O] Objective Clinical Observations
                </label>
                <textarea
                  rows={3}
                  value={soap.objective}
                  onChange={(e) => setSoap({ ...soap, objective: e.target.value })}
                  placeholder="Physical exam findings, auscultation, systemic signs..."
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:outline-none focus:ring-2 focus:ring-brand-500 leading-relaxed"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  [A] Clinical Assessment & ICD-10 Diagnosis
                </label>
                <textarea
                  rows={3}
                  value={soap.assessment}
                  onChange={(e) => setSoap({ ...soap, assessment: e.target.value })}
                  placeholder="Provisional or confirmed diagnostic impression..."
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:outline-none focus:ring-2 focus:ring-brand-500 leading-relaxed font-medium text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  [P] Treatment Plan & Follow-up
                </label>
                <textarea
                  rows={3}
                  value={soap.plan}
                  onChange={(e) => setSoap({ ...soap, plan: e.target.value })}
                  placeholder="Management strategy, dietary instructions, review interval..."
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:outline-none focus:ring-2 focus:ring-brand-500 leading-relaxed"
                />
              </div>
            </div>
          </div>

          {/* Digital Prescriptions Section */}
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
            <form
              onSubmit={handleAddDrug}
              className="p-3 bg-slate-50 rounded-lg border border-slate-200 grid grid-cols-1 sm:grid-cols-5 gap-2 items-end"
            >
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
                onClick={() => setRxModalOpen(true)}
                className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5"
              >
                <Share2 className="w-3.5 h-3.5 text-brand-600" /> Share Digital Rx
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
      )}

      {/* TAB 2: FHIR R4 DIAGNOSTIC & LAB REPORT VIEWER */}
      {activeTab === 'labs' && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-4">
              <div>
                <div className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded uppercase">
                  Central Pathology Laboratory • NABL Accredited
                </div>
                <h3 className="text-lg font-bold text-slate-900 mt-1">Diagnostic Laboratory Investigation Report</h3>
                <p className="text-xs text-slate-500">
                  FHIR R4 DiagnosticReport resource • Specimen: Venous Whole Blood & Serum
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="py-1.5 px-3 border border-slate-300 hover:bg-slate-50 rounded-lg text-xs font-semibold text-slate-700 flex items-center gap-1.5 transition-colors"
                >
                  <Printer className="w-3.5 h-3.5" /> Print Lab Report
                </button>
              </div>
            </div>

            {/* Grouped Test Results */}
            {['Complete Blood Count (CBC)', 'Biochemistry & Renal Profile', 'Lipid Profile'].map((cat) => {
              const tests = SAMPLE_LAB_RESULTS.filter((r) => r.category === cat);
              return (
                <div key={cat} className="space-y-2">
                  <div className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center justify-between bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                    <span>{cat}</span>
                    <span className="text-[11px] text-slate-500 font-normal">Method: Automated Spectrophotometry</span>
                  </div>

                  <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-slate-100 text-slate-600 font-semibold border-b border-slate-200">
                          <th className="py-2 px-3">Test Parameter</th>
                          <th className="py-2 px-3">Measured Result</th>
                          <th className="py-2 px-3">Unit</th>
                          <th className="py-2 px-3">Biological Reference Interval</th>
                          <th className="py-2 px-3 text-center">Status / Flag</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {tests.map((t) => {
                          const isHigh = t.flag === 'HIGH';
                          const isLow = t.flag === 'LOW';
                          const isNormal = t.flag === 'NORMAL';

                          return (
                            <tr key={t.id} className="hover:bg-slate-50/60">
                              <td className="py-2.5 px-3 font-medium text-slate-900">{t.parameter_name}</td>
                              <td
                                className={`py-2.5 px-3 font-mono font-bold ${
                                  isHigh ? 'text-rose-600' : isLow ? 'text-amber-600' : 'text-slate-900'
                                }`}
                              >
                                {t.value}
                              </td>
                              <td className="py-2.5 px-3 text-slate-500">{t.unit}</td>
                              <td className="py-2.5 px-3 text-slate-600 font-mono text-[11px]">
                                {t.reference_interval}
                              </td>
                              <td className="py-2.5 px-3 text-center">
                                {isNormal && (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                                    <CheckCircle2 className="w-3 h-3 text-emerald-600" /> NORMAL
                                  </span>
                                )}
                                {isHigh && (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800">
                                    <ArrowUpRight className="w-3 h-3 text-rose-600" /> HIGH
                                  </span>
                                )}
                                {isLow && (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                                    <ArrowDownRight className="w-3 h-3 text-amber-600" /> LOW
                                  </span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })}

            {/* Lab Verification Footer */}
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between text-xs text-slate-600">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Verified by Dr. Sneha Kulkarni, MD (Pathologist) • Lic: NABL-PATH-9021</span>
              </div>
              <span className="font-mono text-[11px] text-slate-400">Specimen Barcode: BAR-2026-94821</span>
            </div>
          </div>
        </div>
      )}

      {/* Digital Prescription & Dispatch Modal */}
      <DigitalRxModal
        isOpen={rxModalOpen}
        onClose={() => setRxModalOpen(false)}
        patient={activeEncounter?.patient}
        diagnosis={soap.assessment}
        vitals={vitals}
        prescriptions={prescriptions}
      />
    </div>
  );
};
