import React, { useState, useEffect } from 'react';
import { BedItem, WardOccupancyStats } from '../types';
import { patientsApi } from '../services/api';
import {
  Bed,
  CheckCircle2,
  AlertTriangle,
  Building2,
  Activity,
  Plus,
  RefreshCw,
  LogOut,
  X,
  Sparkles,
} from 'lucide-react';

const INITIAL_BEDS: BedItem[] = [
  // ICU
  {
    id: 'bed-icu-01',
    ward_name: 'Medical Intensive Care Unit (MICU)',
    ward_type: 'ICU',
    bed_number: 'ICU-01',
    status: 'OCCUPIED',
    daily_charge: 5000,
    patient_name: 'Rajesh K. Mehta',
    patient_uhid: 'UHID-2026-1048',
    attending_doctor: 'Dr. Sharma (Pulmonology)',
    admitted_at: '2026-11-10',
  },
  {
    id: 'bed-icu-02',
    ward_name: 'Medical Intensive Care Unit (MICU)',
    ward_type: 'ICU',
    bed_number: 'ICU-02',
    status: 'OCCUPIED',
    daily_charge: 5000,
    patient_name: 'Sunita Devi',
    patient_uhid: 'UHID-2026-1089',
    attending_doctor: 'Dr. Varma (Cardiology)',
    admitted_at: '2026-11-12',
  },
  {
    id: 'bed-icu-03',
    ward_name: 'Medical Intensive Care Unit (MICU)',
    ward_type: 'ICU',
    bed_number: 'ICU-03',
    status: 'AVAILABLE',
    daily_charge: 5000,
  },
  {
    id: 'bed-icu-04',
    ward_name: 'Medical Intensive Care Unit (MICU)',
    ward_type: 'ICU',
    bed_number: 'ICU-04',
    status: 'MAINTENANCE',
    daily_charge: 5000,
  },

  // General Ward Male
  {
    id: 'bed-gw-101',
    ward_name: 'General Ward - Male (Floor 2)',
    ward_type: 'GENERAL',
    bed_number: 'GWM-101',
    status: 'OCCUPIED',
    daily_charge: 1200,
    patient_name: 'Arun Kumar',
    patient_uhid: 'UHID-2026-0921',
    attending_doctor: 'Dr. Rajesh Sharma',
    admitted_at: '2026-11-11',
  },
  {
    id: 'bed-gw-102',
    ward_name: 'General Ward - Male (Floor 2)',
    ward_type: 'GENERAL',
    bed_number: 'GWM-102',
    status: 'AVAILABLE',
    daily_charge: 1200,
  },
  {
    id: 'bed-gw-103',
    ward_name: 'General Ward - Male (Floor 2)',
    ward_type: 'GENERAL',
    bed_number: 'GWM-103',
    status: 'AVAILABLE',
    daily_charge: 1200,
  },
  {
    id: 'bed-gw-104',
    ward_name: 'General Ward - Male (Floor 2)',
    ward_type: 'GENERAL',
    bed_number: 'GWM-104',
    status: 'OCCUPIED',
    daily_charge: 1200,
    patient_name: 'Manoj Tiwari',
    patient_uhid: 'UHID-2026-1102',
    attending_doctor: 'Dr. Mukherjee',
    admitted_at: '2026-11-13',
  },

  // General Ward Female
  {
    id: 'bed-gwf-201',
    ward_name: 'General Ward - Female (Floor 2)',
    ward_type: 'GENERAL',
    bed_number: 'GWF-201',
    status: 'OCCUPIED',
    daily_charge: 1200,
    patient_name: 'Pooja Iyer',
    patient_uhid: 'UHID-2026-0814',
    attending_doctor: 'Dr. Neha Gupta',
    admitted_at: '2026-11-09',
  },
  {
    id: 'bed-gwf-202',
    ward_name: 'General Ward - Female (Floor 2)',
    ward_type: 'GENERAL',
    bed_number: 'GWF-202',
    status: 'AVAILABLE',
    daily_charge: 1200,
  },
  {
    id: 'bed-gwf-203',
    ward_name: 'General Ward - Female (Floor 2)',
    ward_type: 'GENERAL',
    bed_number: 'GWF-203',
    status: 'MAINTENANCE',
    daily_charge: 1200,
  },

  // Private Deluxe
  {
    id: 'bed-del-301',
    ward_name: 'Private Deluxe Wing (Floor 3)',
    ward_type: 'DELUXE',
    bed_number: 'DEL-301',
    status: 'OCCUPIED',
    daily_charge: 4500,
    patient_name: 'Anand Mahindra',
    patient_uhid: 'UHID-2026-0701',
    attending_doctor: 'Dr. Ananya Roy',
    admitted_at: '2026-11-08',
  },
  {
    id: 'bed-del-302',
    ward_name: 'Private Deluxe Wing (Floor 3)',
    ward_type: 'DELUXE',
    bed_number: 'DEL-302',
    status: 'AVAILABLE',
    daily_charge: 4500,
  },
  {
    id: 'bed-del-303',
    ward_name: 'Private Deluxe Wing (Floor 3)',
    ward_type: 'DELUXE',
    bed_number: 'DEL-303',
    status: 'RESERVED',
    daily_charge: 4500,
  },

  // Emergency / Trauma
  {
    id: 'bed-emg-01',
    ward_name: 'Emergency & Trauma Bay (Ground Floor)',
    ward_type: 'EMERGENCY',
    bed_number: 'EMG-01',
    status: 'OCCUPIED',
    daily_charge: 3000,
    patient_name: 'Emergency Trauma Pt #4',
    patient_uhid: 'UHID-2026-1199',
    attending_doctor: 'Dr. Emergency Incharge',
    admitted_at: '2026-11-13',
  },
  {
    id: 'bed-emg-02',
    ward_name: 'Emergency & Trauma Bay (Ground Floor)',
    ward_type: 'EMERGENCY',
    bed_number: 'EMG-02',
    status: 'AVAILABLE',
    daily_charge: 3000,
  },
];

export const WardOccupancy: React.FC = () => {
  const [beds, setBeds] = useState<BedItem[]>(INITIAL_BEDS);
  const [wardFilter, setWardFilter] = useState<string>('ALL');
  const [selectedBed, setSelectedBed] = useState<BedItem | null>(null);
  const [admitModalOpen, setAdmitModalOpen] = useState(false);
  const [patientList, setPatientList] = useState<any[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  useEffect(() => {
    // Load patient list for quick admission
    patientsApi
      .list()
      .then((res) => setPatientList(res.items || []))
      .catch(() => {});
  }, []);

  // Compute Census Stats
  const totalBeds = beds.length;
  const occupiedCount = beds.filter((b) => b.status === 'OCCUPIED').length;
  const availableCount = beds.filter((b) => b.status === 'AVAILABLE').length;
  const maintenanceCount = beds.filter((b) => b.status === 'MAINTENANCE').length;
  const reservedCount = beds.filter((b) => b.status === 'RESERVED').length;
  const occupancyRate = Math.round((occupiedCount / totalBeds) * 100);

  const stats: WardOccupancyStats = {
    total_beds: totalBeds,
    occupied: occupiedCount,
    available: availableCount,
    maintenance: maintenanceCount,
    reserved: reservedCount,
    occupancy_rate: occupancyRate,
  };

  const filteredBeds =
    wardFilter === 'ALL' ? beds : beds.filter((b) => b.ward_type === wardFilter);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const handleToggleMaintenance = (bedId: string) => {
    setBeds((prev) =>
      prev.map((b) => {
        if (b.id === bedId) {
          const nextStatus = b.status === 'MAINTENANCE' ? 'AVAILABLE' : 'MAINTENANCE';
          showToast(`Bed ${b.bed_number} marked as ${nextStatus}!`);
          return { ...b, status: nextStatus };
        }
        return b;
      })
    );
  };

  const handleDischarge = (bedId: string) => {
    setBeds((prev) =>
      prev.map((b) => {
        if (b.id === bedId) {
          showToast(`Patient discharged! Bed ${b.bed_number} is now undergoing cleaning.`);
          return {
            ...b,
            status: 'MAINTENANCE',
            patient_name: undefined,
            patient_uhid: undefined,
            attending_doctor: undefined,
            admitted_at: undefined,
          };
        }
        return b;
      })
    );
  };

  const handleOpenAdmit = (bed: BedItem) => {
    setSelectedBed(bed);
    setAdmitModalOpen(true);
  };

  const handleConfirmAdmission = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBed) return;

    const chosenPatient = patientList.find((p) => p.id === selectedPatientId) || {
      first_name: 'Walk-in',
      last_name: 'Patient',
      registration_number: 'UHID-2026-NEW',
    };

    setBeds((prev) =>
      prev.map((b) => {
        if (b.id === selectedBed.id) {
          return {
            ...b,
            status: 'OCCUPIED',
            patient_name: `${chosenPatient.first_name} ${chosenPatient.last_name}`,
            patient_uhid: chosenPatient.registration_number,
            attending_doctor: 'Dr. Attending Physician',
            admitted_at: new Date().toISOString().split('T')[0],
          };
        }
        return b;
      })
    );

    showToast(`Patient admitted to Bed ${selectedBed.bed_number}!`);
    setAdmitModalOpen(false);
    setSelectedBed(null);
  };

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toastMsg && (
        <div className="fixed top-20 right-6 z-50 p-3 bg-slate-900 text-white text-xs font-semibold rounded-xl shadow-xl border border-slate-700 flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
          <Sparkles className="w-4 h-4 text-emerald-400" />
          <span>{toastMsg}</span>
        </div>
      )}

      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-brand-900 rounded-2xl p-6 text-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/10 backdrop-blur-md rounded-full text-xs font-semibold text-emerald-300 mb-2">
            <Activity className="w-3.5 h-3.5" /> Live Inpatient Census & Bed Tracking
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Inpatient Ward & Bed Occupancy Matrix</h1>
          <p className="text-sm text-slate-300 mt-1 max-w-2xl">
            Real-time visual floor plan for ICUs, General Wards, Private Suites, and Emergency Triage. Manage admissions,
            bed sanitization, and patient discharges seamlessly.
          </p>
        </div>
        <div className="bg-white/10 backdrop-blur-md border border-white/20 p-4 rounded-xl flex items-center gap-4 self-start md:self-auto">
          <div>
            <div className="text-xs uppercase font-medium text-slate-300">Hospital Occupancy</div>
            <div className="text-2xl font-bold text-white">{stats.occupancy_rate}%</div>
          </div>
          <div className="h-10 w-0.5 bg-white/20"></div>
          <div>
            <div className="text-xs uppercase font-medium text-slate-300">Available Beds</div>
            <div className="text-2xl font-bold text-emerald-400">{stats.available}</div>
          </div>
        </div>
      </div>

      {/* KPI Census Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase">Total Capacity</div>
            <div className="text-2xl font-bold text-slate-900 mt-1">{stats.total_beds} Beds</div>
            <div className="text-[11px] text-slate-400 mt-0.5">Across 4 Floors</div>
          </div>
          <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center text-slate-700">
            <Building2 className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase">Occupied</div>
            <div className="text-2xl font-bold text-blue-600 mt-1">{stats.occupied} Beds</div>
            <div className="text-[11px] text-blue-600 font-medium mt-0.5">{stats.occupancy_rate}% Census Rate</div>
          </div>
          <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center text-blue-600">
            <Bed className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase">Available / Vacant</div>
            <div className="text-2xl font-bold text-emerald-600 mt-1">{stats.available} Beds</div>
            <div className="text-[11px] text-emerald-600 font-medium mt-0.5">Ready for Admission</div>
          </div>
          <div className="w-10 h-10 bg-emerald-50 rounded-lg flex items-center justify-center text-emerald-600">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase">Sanitization / Cleaning</div>
            <div className="text-2xl font-bold text-amber-600 mt-1">{stats.maintenance} Beds</div>
            <div className="text-[11px] text-amber-600 font-medium mt-0.5">Sterilization Active</div>
          </div>
          <div className="w-10 h-10 bg-amber-50 rounded-lg flex items-center justify-center text-amber-600">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Ward Filter Bar */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2 text-xs font-semibold">
          {[
            { id: 'ALL', label: 'All Hospital Wards' },
            { id: 'ICU', label: 'ICU / Critical Care' },
            { id: 'GENERAL', label: 'General Wards' },
            { id: 'DELUXE', label: 'Private Deluxe' },
            { id: 'EMERGENCY', label: 'Emergency & Trauma' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setWardFilter(tab.id)}
              className={`py-2 px-3.5 rounded-lg border transition-all ${
                wardFilter === tab.id
                  ? 'bg-brand-600 text-white border-brand-600 shadow-sm'
                  : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-xs text-slate-600">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-emerald-500"></span> Available
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-blue-500"></span> Occupied
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-amber-500"></span> Cleaning
          </span>
        </div>
      </div>

      {/* Visual Floor Grid Map */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {filteredBeds.map((bed) => {
          const isOccupied = bed.status === 'OCCUPIED';
          const isAvailable = bed.status === 'AVAILABLE';
          const isMaintenance = bed.status === 'MAINTENANCE';

          return (
            <div
              key={bed.id}
              className={`rounded-2xl border p-5 shadow-sm transition-all flex flex-col justify-between ${
                isAvailable
                  ? 'bg-white border-emerald-300 hover:border-emerald-500 hover:shadow-md'
                  : isOccupied
                  ? 'bg-blue-50/40 border-blue-200'
                  : 'bg-amber-50/40 border-amber-200'
              }`}
            >
              {/* Top Card Info */}
              <div>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs ${
                        isAvailable
                          ? 'bg-emerald-100 text-emerald-800'
                          : isOccupied
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      <Bed className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="text-base font-bold text-slate-900">{bed.bed_number}</div>
                      <div className="text-[10px] text-slate-500">{bed.ward_type}</div>
                    </div>
                  </div>

                  <span
                    className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                      isAvailable
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        : isOccupied
                        ? 'bg-blue-100 text-blue-800 border border-blue-300'
                        : 'bg-amber-100 text-amber-800 border border-amber-300'
                    }`}
                  >
                    {bed.status}
                  </span>
                </div>

                <div className="text-xs text-slate-600 font-medium mb-2">{bed.ward_name}</div>

                {/* Patient Occupancy Details */}
                {isOccupied && (
                  <div className="p-3 bg-white border border-blue-100 rounded-xl space-y-1.5 text-xs mb-3 shadow-xs">
                    <div>
                      <span className="text-[10px] text-slate-400 uppercase font-semibold block">Patient</span>
                      <span className="font-bold text-slate-900">{bed.patient_name}</span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-600">
                      <span className="font-mono text-brand-700">{bed.patient_uhid}</span>
                      <span>Adm: {bed.admitted_at}</span>
                    </div>
                    <div className="text-[11px] text-slate-500 font-medium">{bed.attending_doctor}</div>
                  </div>
                )}

                {isMaintenance && (
                  <div className="p-3 bg-white border border-amber-200 rounded-xl text-xs text-amber-800 space-y-1 mb-3">
                    <div className="font-semibold flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600" /> Bed Under Sterilization
                    </div>
                    <p className="text-[11px] text-slate-500">Scheduled linen change & infection control sweep.</p>
                  </div>
                )}

                {isAvailable && (
                  <div className="p-3 bg-emerald-50/50 border border-emerald-100 rounded-xl text-xs text-emerald-800 space-y-1 mb-3">
                    <div className="font-semibold flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Ready for Immediate Intake
                    </div>
                    <div className="text-[11px] text-slate-500">₹{bed.daily_charge}/day tariff rate</div>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="pt-2 border-t border-slate-200/60 flex items-center gap-2">
                {isAvailable && (
                  <button
                    onClick={() => handleOpenAdmit(bed)}
                    className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-1.5 shadow-sm"
                  >
                    <Plus className="w-3.5 h-3.5" /> Admit Patient
                  </button>
                )}

                {isOccupied && (
                  <button
                    onClick={() => handleDischarge(bed.id)}
                    className="w-full py-2 bg-slate-900 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 shadow-sm"
                  >
                    <LogOut className="w-3.5 h-3.5" /> Discharge Patient
                  </button>
                )}

                {isMaintenance && (
                  <button
                    onClick={() => handleToggleMaintenance(bed.id)}
                    className="w-full py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 shadow-sm"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Mark Ready
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Patient Admission Modal */}
      {admitModalOpen && selectedBed && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
          <div
            className="w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 bg-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bed className="w-4 h-4 text-emerald-400" />
                <span className="text-sm font-bold">Admit Patient to Bed {selectedBed.bed_number}</span>
              </div>
              <button
                onClick={() => setAdmitModalOpen(false)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleConfirmAdmission} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Select Patient from Registry
                </label>
                <select
                  required
                  value={selectedPatientId}
                  onChange={(e) => setSelectedPatientId(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 font-medium"
                >
                  <option value="">-- Choose patient --</option>
                  {patientList.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.first_name} {p.last_name} ({p.registration_number})
                    </option>
                  ))}
                </select>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
                <div>
                  <strong>Ward:</strong> {selectedBed.ward_name}
                </div>
                <div>
                  <strong>Tariff:</strong> ₹{selectedBed.daily_charge} per day
                </div>
                <div>
                  <strong>Bed Type:</strong> {selectedBed.ward_type}
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setAdmitModalOpen(false)}
                  className="flex-1 py-2 px-3 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
                >
                  Confirm Admission
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
