import React, { useState, useEffect } from 'react';
import { patientsApi } from '../services/api';
import { Patient } from '../types';
import {
  Users,
  UserPlus,
  Search,
  ShieldCheck,
  CheckCircle2,
  X,
  Phone,
  Calendar,
  MapPin,
  AlertCircle,
} from 'lucide-react';

export const Patients: React.FC = () => {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newlyCreatedUHID, setNewlyCreatedUHID] = useState<string | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    date_of_birth: '1990-01-01',
    gender: 'MALE' as 'MALE' | 'FEMALE' | 'OTHER',
    phone: '',
    email: '',
    address_line1: '',
    city: 'Mumbai',
    state: 'Maharashtra',
    pincode: '400001',
    blood_group: 'B+',
    abha_id: '',
  });

  const fetchPatients = async () => {
    try {
      setLoading(true);
      const res = await patientsApi.list(searchTerm || undefined);
      setPatients(res.items || []);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to fetch patients');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatients();
  }, [searchTerm]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const created = await patientsApi.create(formData);
      setNewlyCreatedUHID(created.registration_number);
      setIsModalOpen(false);
      // Reset form
      setFormData({
        first_name: '',
        last_name: '',
        date_of_birth: '1990-01-01',
        gender: 'MALE',
        phone: '',
        email: '',
        address_line1: '',
        city: 'Mumbai',
        state: 'Maharashtra',
        pincode: '400001',
        blood_group: 'B+',
        abha_id: '',
      });
      fetchPatients();
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to register patient');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Users className="w-6 h-6 text-brand-600" /> Patient Registry
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Auto-generating unique UHIDs with AES-256 field encryption & ABDM ABHA linkage.
          </p>
        </div>
        <button
          onClick={() => {
            setIsModalOpen(true);
            setNewlyCreatedUHID(null);
            setError(null);
          }}
          className="px-4 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center gap-2 shadow-sm"
        >
          <UserPlus className="w-4 h-4" />
          Register New Patient
        </button>
      </div>

      {/* Success Notification */}
      {newlyCreatedUHID && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <div>
              <div className="text-sm font-bold">Patient Successfully Registered!</div>
              <div className="text-xs text-emerald-700">
                Assigned UHID:{' '}
                <span className="font-mono font-bold bg-white px-2 py-0.5 rounded border border-emerald-300 ml-1">
                  {newlyCreatedUHID}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={() => setNewlyCreatedUHID(null)}
            className="text-emerald-600 hover:text-emerald-800 p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
        <Search className="w-4 h-4 text-slate-400 shrink-0 ml-1" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search by UHID, patient name, or phone number..."
          className="w-full text-sm text-slate-900 placeholder-slate-400 focus:outline-none"
        />
      </div>

      {/* Patient Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            <div className="inline-block animate-spin rounded-full h-6 w-6 border-2 border-brand-500 border-t-transparent mb-2" />
            <div>Loading encrypted patient records...</div>
          </div>
        ) : patients.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            <Users className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="font-semibold text-slate-700">No patients registered yet</p>
            <p className="text-xs text-slate-400 mt-1">
              Click &quot;Register New Patient&quot; above to add your first patient.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                  <th className="py-3 px-4">UHID</th>
                  <th className="py-3 px-4">Patient Name</th>
                  <th className="py-3 px-4">Gender & Age</th>
                  <th className="py-3 px-4">Phone / Contact</th>
                  <th className="py-3 px-4">ABHA ID</th>
                  <th className="py-3 px-4">Blood Group</th>
                  <th className="py-3 px-4">Registered</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-800">
                {patients.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-brand-700 text-xs">
                      {p.registration_number}
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-900">
                      {p.first_name} {p.last_name}
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-600">
                      <span className="capitalize">{p.gender.toLowerCase()}</span> • DOB: {p.date_of_birth}
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-600 flex items-center gap-1.5">
                      <Phone className="w-3 h-3 text-slate-400" />
                      {p.phone}
                    </td>
                    <td className="py-3 px-4 text-xs">
                      {p.abha_id ? (
                        <span className="inline-flex items-center gap-1 font-mono text-[11px] px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
                          <ShieldCheck className="w-3 h-3 text-emerald-600" />
                          {p.abha_id}
                        </span>
                      ) : (
                        <span className="text-slate-400 text-xs italic">Not linked</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-xs font-semibold text-slate-700">
                      {p.blood_group || '—'}
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-500">
                      {new Date(p.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Registration Modal Dialog */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex justify-center items-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full border border-slate-200 overflow-hidden max-h-[90vh] flex flex-col">
            <div className="p-5 bg-gradient-to-r from-brand-700 to-brand-900 text-white flex justify-between items-center">
              <div>
                <h3 className="text-lg font-bold">New Patient Registration</h3>
                <p className="text-xs text-brand-100">
                  DPDP & ABDM Compliant Demographic Onboarding
                </p>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-brand-200 hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1">
              {error && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    First Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                    placeholder="e.g. Ramesh"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Last Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                    placeholder="e.g. Kumar"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Date of Birth *
                  </label>
                  <input
                    type="date"
                    required
                    value={formData.date_of_birth}
                    onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Gender *
                  </label>
                  <select
                    value={formData.gender}
                    onChange={(e: any) => setFormData({ ...formData, gender: e.target.value })}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  >
                    <option value="MALE">Male</option>
                    <option value="FEMALE">Female</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Blood Group
                  </label>
                  <select
                    value={formData.blood_group}
                    onChange={(e) => setFormData({ ...formData, blood_group: e.target.value })}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  >
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Mobile Phone (10 digits) *
                  </label>
                  <input
                    type="tel"
                    required
                    pattern="^[6-9]\d{9}$"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="9876543210"
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="ramesh@example.com"
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                  14-Digit ABHA ID (Optional)
                </label>
                <input
                  type="text"
                  value={formData.abha_id}
                  onChange={(e) => setFormData({ ...formData, abha_id: e.target.value })}
                  placeholder="e.g. 91-1234-5678-9012 or user@abdm"
                  className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-brand-500 focus:outline-none font-mono"
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    City
                  </label>
                  <input
                    type="text"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    State
                  </label>
                  <input
                    type="text"
                    value={formData.state}
                    onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Pincode
                  </label>
                  <input
                    type="text"
                    pattern="^\d{6}$"
                    value={formData.pincode}
                    onChange={(e) => setFormData({ ...formData, pincode: e.target.value })}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  />
                </div>
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
                  disabled={submitting}
                  className="px-5 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center gap-2 disabled:opacity-50"
                >
                  {submitting ? 'Registering...' : 'Complete Registration & Generate UHID'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

