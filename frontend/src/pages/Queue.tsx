import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { encountersApi, patientsApi } from '../services/api';
import { Encounter, Patient } from '../types';
import {
  Clock,
  PlusCircle,
  Stethoscope,
  X,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';

export const Queue: React.FC = () => {
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Form State
  const [formData, setFormData] = useState({
    patient_id: '',
    doctor_id: '22222222-2222-2222-2222-222222222221', // Default to Dr. Rajesh Sharma
    department: 'General Medicine',
    encounter_type: 'OPD',
    chief_complaint: 'Fever and body aches for 3 days',
    priority: 'NORMAL',
  });

  const fetchData = async () => {
    try {
      setLoading(true);
      const [encountersRes, patientsRes] = await Promise.all([
        encountersApi.list(),
        patientsApi.list(),
      ]);
      setEncounters(encountersRes.items || []);
      setPatients(patientsRes.items || []);
      if (patientsRes.items?.length > 0 && !formData.patient_id) {
        setFormData((prev) => ({ ...prev, patient_id: patientsRes.items[0].id }));
      }
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to load queue data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateEncounter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.patient_id) {
      setError('Please select or register a patient first.');
      return;
    }
    setSubmitting(true);
    setError(null);

    try {
      await encountersApi.create(formData);
      setIsModalOpen(false);
      fetchData();
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to issue token');
    } finally {
      setSubmitting(false);
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'EMERGENCY':
        return <span className="px-2 py-0.5 text-[10px] font-bold bg-rose-100 text-rose-800 rounded-full">EMERGENCY</span>;
      case 'URGENT':
        return <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-100 text-amber-800 rounded-full">URGENT</span>;
      default:
        return <span className="px-2 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-700 rounded-full">Normal</span>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <span className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-100 text-emerald-800 rounded-full">Completed</span>;
      case 'IN_PROGRESS':
        return <span className="px-2 py-0.5 text-[10px] font-semibold bg-brand-100 text-brand-800 rounded-full">In Consultation</span>;
      default:
        return <span className="px-2 py-0.5 text-[10px] font-semibold bg-amber-100 text-amber-800 rounded-full">Waiting</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Clock className="w-6 h-6 text-amber-600" /> OPD Live Queue
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time outpatient tokens, triage priorities, and doctor consultation routing.
          </p>
        </div>
        <button
          onClick={() => {
            setIsModalOpen(true);
            setError(null);
          }}
          className="px-4 py-2.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center gap-2 shadow-sm"
        >
          <PlusCircle className="w-4 h-4" />
          Issue OPD Token
        </button>
      </div>

      {/* Queue Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            <div className="inline-block animate-spin rounded-full h-6 w-6 border-2 border-amber-500 border-t-transparent mb-2" />
            <div>Loading live OPD queue...</div>
          </div>
        ) : encounters.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            <Clock className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="font-semibold text-slate-700">The OPD queue is currently empty</p>
            <p className="text-xs text-slate-400 mt-1">
              Click &quot;Issue OPD Token&quot; to assign a registered patient to a doctor.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                  <th className="py-3 px-4">Token #</th>
                  <th className="py-3 px-4">Patient (UHID)</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Chief Complaint</th>
                  <th className="py-3 px-4">Priority</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-800">
                {encounters.map((enc) => (
                  <tr key={enc.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4">
                      <span className="font-mono text-base font-bold text-amber-700 bg-amber-50 px-2 py-1 rounded-lg border border-amber-200">
                        #{enc.token_number || '—'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900">
                        {enc.patient ? `${enc.patient.first_name} ${enc.patient.last_name}` : 'Patient'}
                      </div>
                      <div className="text-xs font-mono text-slate-500">
                        {enc.patient?.registration_number || enc.patient_id.slice(0, 8)}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-xs font-medium text-slate-700">
                      {enc.department}
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-600 max-w-xs truncate">
                      {enc.chief_complaint || 'General Checkup'}
                    </td>
                    <td className="py-3 px-4">{getPriorityBadge(enc.priority)}</td>
                    <td className="py-3 px-4">{getStatusBadge(enc.status)}</td>
                    <td className="py-3 px-4 text-right">
                      {enc.status !== 'COMPLETED' ? (
                        <button
                          onClick={() => navigate(`/emr?encounter_id=${enc.id}`)}
                          className="px-3 py-1.5 bg-brand-50 hover:bg-brand-100 text-brand-700 font-semibold rounded-lg text-xs transition-colors inline-flex items-center gap-1.5"
                        >
                          <Stethoscope className="w-3.5 h-3.5" />
                          Consult
                        </button>
                      ) : (
                        <span className="text-xs text-slate-400 font-medium inline-flex items-center gap-1">
                          <CheckCircle className="w-3.5 h-3.5 text-emerald-500" /> Done
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* New OPD Token Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex justify-center items-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden">
            <div className="p-5 bg-gradient-to-r from-amber-600 to-amber-700 text-white flex justify-between items-center">
              <div>
                <h3 className="text-lg font-bold">Issue New OPD Token</h3>
                <p className="text-xs text-amber-100">Assign Patient to Specialist Clinic</p>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-amber-200 hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateEncounter} className="p-6 space-y-4">
              {error && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                  Select Registered Patient *
                </label>
                {patients.length === 0 ? (
                  <div className="text-xs text-rose-600 p-2 bg-rose-50 rounded border border-rose-200">
                    No registered patients found. Please register a patient first in Patient Registry.
                  </div>
                ) : (
                  <select
                    required
                    value={formData.patient_id}
                    onChange={(e) => setFormData({ ...formData, patient_id: e.target.value })}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  >
                    {patients.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.first_name} {p.last_name} ({p.registration_number}) — {p.gender}, {p.phone}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Department *
                  </label>
                  <select
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  >
                    <option value="General Medicine">General Medicine</option>
                    <option value="Cardiology">Cardiology</option>
                    <option value="Orthopedics">Orthopedics</option>
                    <option value="Pediatrics">Pediatrics</option>
                    <option value="Gynecology">Gynecology</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Assigned Doctor *
                  </label>
                  <select
                    value={formData.doctor_id}
                    onChange={(e) => setFormData({ ...formData, doctor_id: e.target.value })}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  >
                    <option value="22222222-2222-2222-2222-222222222221">Dr. Rajesh Sharma</option>
                    <option value="22222222-2222-2222-2222-222222222222">Dr. Priya Patel</option>
                    <option value="22222222-2222-2222-2222-222222222223">Dr. Amit Verma</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                  Chief Complaint / Reason for Visit
                </label>
                <textarea
                  rows={2}
                  value={formData.chief_complaint}
                  onChange={(e) => setFormData({ ...formData, chief_complaint: e.target.value })}
                  placeholder="e.g. Acute chest pain, persistent dry cough, headache..."
                  className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-amber-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                  Triage Priority
                </label>
                <select
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                  className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-amber-500 focus:outline-none"
                >
                  <option value="NORMAL">Normal (Standard Queue)</option>
                  <option value="URGENT">Urgent (Priority Evaluation)</option>
                  <option value="EMERGENCY">Emergency (Immediate Intervention)</option>
                </select>
              </div>

              <div className="pt-4 border-t border-slate-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || patients.length === 0}
                  className="px-5 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center gap-2 disabled:opacity-50"
                >
                  {submitting ? 'Generating Token...' : 'Issue OPD Token'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

