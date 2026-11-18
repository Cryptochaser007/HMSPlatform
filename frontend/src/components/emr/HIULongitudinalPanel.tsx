import React, { useState, useEffect } from 'react';
import { abdmApi } from '../../services/api';
import { AbdmConsentArtefact, LongitudinalTimelineRecord } from '../../types';
import {
  ShieldCheck,
  Lock,
  Send,
  Download,
  Building2,
  Stethoscope,
  Pill,
  FileText,
  Activity,
  CheckCircle2,
  AlertCircle,
  Clock,
} from 'lucide-react';

interface HIULongitudinalPanelProps {
  defaultPatientAbha?: string;
}

const ALL_HI_TYPES = [
  'OPConsultation',
  'Prescription',
  'DiagnosticReport',
  'DischargeSummary',
];

export const HIULongitudinalPanel: React.FC<HIULongitudinalPanelProps> = ({
  defaultPatientAbha,
}) => {
  const [patientAbha, setPatientAbha] = useState(defaultPatientAbha || 'arun.kumar@sbx');
  const [purpose, setPurpose] = useState('Care Management');
  const [purposeCode, setPurposeCode] = useState('CAREMGT');
  const [dateFrom, setDateFrom] = useState('2025-01-01');
  const [dateTo, setDateTo] = useState(new Date().toISOString().split('T')[0]);
  const [selectedHiTypes, setSelectedHiTypes] = useState<string[]>(ALL_HI_TYPES);

  const [consents, setConsents] = useState<AbdmConsentArtefact[]>([]);
  const [timeline, setTimeline] = useState<LongitudinalTimelineRecord[]>([]);
  const [requesting, setRequesting] = useState(false);
  const [fetchingId, setFetchingId] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (defaultPatientAbha) {
      setPatientAbha(defaultPatientAbha);
    }
  }, [defaultPatientAbha]);

  const refreshConsentsAndRecords = async (abha: string) => {
    try {
      const [cRes, rRes] = await Promise.all([
        abdmApi.listHiuConsents(abha).catch(() => ({ items: [] })),
        abdmApi.getLongitudinalRecords(abha).catch(() => ({ items: [] })),
      ]);
      setConsents(cRes.items || []);
      setTimeline(rRes.items || []);
    } catch {
      // ignore initial load error
    }
  };

  useEffect(() => {
    if (patientAbha) {
      refreshConsentsAndRecords(patientAbha);
    }
  }, [patientAbha]);

  const toggleHiType = (t: string) => {
    setSelectedHiTypes((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );
  };

  const handleRequestConsent = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setStatusMsg(null);
    if (!patientAbha.trim()) {
      setErrorMsg('Please enter a valid patient ABHA address.');
      return;
    }
    if (selectedHiTypes.length === 0) {
      setErrorMsg('Select at least one Health Information (HI) Type.');
      return;
    }

    setRequesting(true);
    try {
      const res = await abdmApi.requestHiuConsent({
        patient_abha: patientAbha.trim(),
        purpose,
        purpose_code: purposeCode,
        date_from: new Date(dateFrom).toISOString(),
        date_to: new Date(dateTo).toISOString(),
        hi_types: selectedHiTypes,
      });
      setStatusMsg(res.message || `Consent request created (${res.status}).`);
      await refreshConsentsAndRecords(patientAbha.trim());
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Consent request failed.');
    } finally {
      setRequesting(false);
    }
  };

  const handleFetchAndDecrypt = async (consentId: string) => {
    setFetchingId(consentId);
    setErrorMsg(null);
    setStatusMsg(null);
    try {
      const res = await abdmApi.fetchHiuHealthInfo(consentId);
      if (res.timeline) {
        setTimeline(res.timeline);
      } else {
        await refreshConsentsAndRecords(patientAbha.trim());
      }
      setStatusMsg(
        res.records_decrypted
          ? `Fetched & decrypted ${res.records_decrypted} NRCeS FHIR R4 bundle(s) via ${res.encryption_verified || 'Fidelius ECDH + AES-256-GCM'}.`
          : `HI request dispatched (txn: ${res.transaction_id}). Awaiting HIP encrypted data push.`
      );
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to fetch health records.');
    } finally {
      setFetchingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Info */}
      <div className="bg-gradient-to-r from-indigo-950 via-slate-900 to-brand-900 text-white p-5 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 text-[11px] font-bold text-emerald-300 bg-white/10 px-2.5 py-0.5 rounded-full mb-1.5">
            <Lock className="w-3 h-3" /> ABDM Milestone 3 (HIU) • Fidelius Curve25519 + AES-256-GCM
          </div>
          <h3 className="text-lg font-bold">Cross-Hospital Longitudinal Health Record (HIU)</h3>
          <p className="text-xs text-slate-300 mt-0.5 max-w-2xl">
            Request patient consent via the NHA Consent Manager, fetch encrypted FHIR R4 records from external
            hospitals, and inspect the decrypted clinical timeline inline.
          </p>
        </div>
        <div className="text-xs bg-white/10 border border-white/15 rounded-lg px-3.5 py-2 font-mono">
          <div>Cipher: X25519 + HKDF-SHA256</div>
          <div className="text-emerald-300">AEAD: AES-256-GCM</div>
        </div>
      </div>

      {statusMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{statusMsg}</span>
        </div>
      )}
      {errorMsg && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Consent Initiation Form & Active Consents */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <form
          onSubmit={handleRequestConsent}
          className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4"
        >
          <div className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-brand-600" />
            1. Initiate ABDM Consent Request
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                Patient ABHA Address
              </label>
              <input
                type="text"
                required
                value={patientAbha}
                onChange={(e) => setPatientAbha(e.target.value)}
                placeholder="arun.kumar@sbx"
                className="w-full text-xs border border-slate-300 rounded-lg p-2 font-mono focus:ring-2 focus:ring-brand-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                Purpose of Care
              </label>
              <select
                value={purposeCode}
                onChange={(e) => {
                  setPurposeCode(e.target.value);
                  setPurpose(e.target.options[e.target.selectedIndex].text);
                }}
                className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
              >
                <option value="CAREMGT">Care Management</option>
                <option value="BTG">Break the Glass (Emergency)</option>
                <option value="PUBHLTH">Public Health</option>
                <option value="HPAYMT">Healthcare Payment / Claims</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                Records From Date
              </label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-lg p-2 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                Records To Date
              </label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-lg p-2 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-600 mb-1.5">
              Requested Health Information (HI) Types
            </label>
            <div className="flex flex-wrap gap-2">
              {ALL_HI_TYPES.map((t) => {
                const active = selectedHiTypes.includes(t);
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => toggleHiType(t)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition-colors ${
                      active
                        ? 'bg-brand-600 text-white border-brand-600'
                        : 'bg-slate-50 text-slate-600 border-slate-300 hover:bg-slate-100'
                    }`}
                  >
                    {t}
                  </button>
                );
              })}
            </div>
          </div>

          <button
            type="submit"
            disabled={requesting}
            className="w-full py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            {requesting ? 'Dispatching Consent Request...' : 'Request Consent via ABDM CM'}
          </button>
        </form>

        {/* Active Consent Artefacts List */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
          <div className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-600" />
              2. Consent Artefacts ({consents.length})
            </span>
          </div>

          {consents.length === 0 ? (
            <div className="p-6 text-center bg-slate-50 rounded-xl border border-dashed border-slate-300 text-xs text-slate-500">
              No consent artefacts yet for <span className="font-mono font-semibold">{patientAbha}</span>.
              Initiate a consent request on the left to fetch longitudinal records.
            </div>
          ) : (
            <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
              {consents.map((c) => (
                <div
                  key={c.consent_id}
                  className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between gap-3"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-900 truncate">
                        {c.consent_id}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          c.status === 'GRANTED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : c.status === 'REQUESTED'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}
                      >
                        {c.status}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      {c.purpose_text} • {(c.hi_types || []).join(', ')}
                    </div>
                  </div>

                  <button
                    onClick={() => handleFetchAndDecrypt(c.consent_id)}
                    disabled={c.status !== 'GRANTED' || fetchingId === c.consent_id}
                    className="py-1.5 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shrink-0 disabled:opacity-40"
                  >
                    <Download className="w-3.5 h-3.5" />
                    {fetchingId === c.consent_id ? 'Decrypting...' : 'Fetch & Decrypt'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Decrypted Longitudinal Health Record Timeline */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div>
            <h4 className="text-base font-bold text-slate-900">
              3. Decrypted Longitudinal Health Record Timeline (FHIR R4)
            </h4>
            <p className="text-xs text-slate-500">
              Cross-facility clinical records decrypted with ephemeral X25519 ECDH keys
            </p>
          </div>
          <span className="text-xs font-semibold bg-brand-50 text-brand-700 border border-brand-200 px-2.5 py-1 rounded-full">
            {timeline.length} Record(s)
          </span>
        </div>

        {timeline.length === 0 ? (
          <div className="p-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-300 text-xs text-slate-500">
            Click <strong>Fetch &amp; Decrypt</strong> on any <strong>GRANTED</strong> consent artefact above to
            render decrypted external clinical records here.
          </div>
        ) : (
          <div className="relative border-l-2 border-brand-200 ml-3 space-y-5 pl-6">
            {timeline.map((rec) => (
              <div
                key={rec.bundle_id}
                className="relative bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3"
              >
                <span className="absolute -left-[31px] top-4 w-3.5 h-3.5 rounded-full bg-brand-600 ring-4 ring-white" />

                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-slate-900">{rec.document_type}</span>
                      <span className="text-[10px] font-mono bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">
                        {rec.decryption_cipher || 'Fidelius Verified'}
                      </span>
                    </div>
                    <div className="text-xs text-slate-600 flex flex-wrap items-center gap-3 mt-1">
                      <span className="flex items-center gap-1">
                        <Building2 className="w-3.5 h-3.5 text-brand-600" /> {rec.facility_name}
                      </span>
                      <span className="flex items-center gap-1">
                        <Stethoscope className="w-3.5 h-3.5 text-slate-500" /> {rec.practitioner_name}
                      </span>
                    </div>
                  </div>
                  <div className="text-xs font-mono text-slate-500">
                    {new Date(rec.date).toLocaleDateString('en-IN', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                    })}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                  {rec.diagnoses.length > 0 && (
                    <div className="bg-white p-3 rounded-lg border border-slate-200">
                      <div className="font-bold text-slate-700 flex items-center gap-1 mb-1">
                        <FileText className="w-3.5 h-3.5 text-brand-600" /> Diagnoses (ICD-10)
                      </div>
                      <ul className="list-disc list-inside text-slate-600 space-y-0.5">
                        {rec.diagnoses.map((d, idx) => (
                          <li key={idx}>{d}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {rec.medications.length > 0 && (
                    <div className="bg-white p-3 rounded-lg border border-slate-200">
                      <div className="font-bold text-slate-700 flex items-center gap-1 mb-1">
                        <Pill className="w-3.5 h-3.5 text-emerald-600" /> Prescribed Medications
                      </div>
                      <ul className="space-y-1 text-slate-600">
                        {rec.medications.map((m, idx) => (
                          <li key={idx}>
                            <span className="font-semibold text-slate-800">{m.name}</span>
                            {m.dosage ? ` — ${m.dosage}` : ''}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {(rec.observations.length > 0 || rec.diagnostic_reports.length > 0) && (
                    <div className="bg-white p-3 rounded-lg border border-slate-200">
                      <div className="font-bold text-slate-700 flex items-center gap-1 mb-1">
                        <Activity className="w-3.5 h-3.5 text-rose-500" /> Observations &amp; Reports
                      </div>
                      <ul className="space-y-1 text-slate-600">
                        {rec.observations.map((o, idx) => (
                          <li key={idx}>
                            {o.name}: <strong className="font-mono">{o.value} {o.unit}</strong>
                          </li>
                        ))}
                        {rec.diagnostic_reports.map((r, idx) => (
                          <li key={`r-${idx}`} className="text-[11px] text-slate-700">
                            <strong>{r.title}:</strong> {r.conclusion}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

