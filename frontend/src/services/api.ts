import axios from 'axios';
import {
  User,
  Patient,
  Encounter,
  ClinicalNote,
  Prescription,
  AbhaProfile,
  SignupData,
  WardOccupancyStats,
  WardSetupStatus,
  WardSetupWard,
  AbdmStatus,
  AbdmShareProfile,
  AbdmConsentArtefact,
  LongitudinalTimelineRecord,
} from '../types';

// In production, Vite routes /api/v1 through Vercel rewrites to backend directly.
// In dev, vite.config.ts proxies /api to backend.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  withCredentials: true,
  xsrfCookieName: 'csrf_token',
  xsrfHeaderName: 'X-CSRF-Token',
  withXSRFToken: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

let refreshInFlight: Promise<unknown> | null = null;

// Response Interceptor: Catch 401 and redirect to Login
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as (typeof error.config & { _sessionRetry?: boolean }) | undefined;
    const authPath = String(originalRequest?.url || '');
    if (error.response?.status === 401 && originalRequest && !originalRequest._sessionRetry
        && !authPath.includes('/auth/login') && !authPath.includes('/auth/refresh')
        && !authPath.includes('/auth/signup')) {
      originalRequest._sessionRetry = true;
      try {
        // Refresh uses the HttpOnly refresh cookie and XSRF double-submit header.
        if (!refreshInFlight) {
          refreshInFlight = api.post('/auth/refresh').finally(() => { refreshInFlight = null; });
        }
        await refreshInFlight;
        return api.request(originalRequest);
      } catch (refreshError: any) {
        if (refreshError.response?.status === 401 && !window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    } else if (error.response?.status === 401 && !window.location.pathname.includes('/login')) {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  registerHospital: async (data: {
    hospital_name: string; slug: string; admin_name: string;
    admin_email: string; admin_password: string;
  }): Promise<void> => { await api.post('/tenants/register', data); },
  login: async (email: string, password: string): Promise<void> => {
    await api.post('/auth/login', { email, password });
  },
  logout: async (): Promise<void> => { await api.post('/auth/logout'); },
  signup: async (data: SignupData): Promise<User> => {
    const res = await api.post<User>('/auth/signup', data);
    return res.data;
  },
  getMe: async (): Promise<User> => {
    const res = await api.get<User>('/auth/me');
    return res.data;
  },
};

export const registryApi = {
  syncFacility: async (facilityId: string): Promise<any> => (await api.post('/registry/hfr/sync', null, { params: { facility_id: facilityId } })).data,
  syncPractitioner: async (registrationNumber: string, council: string): Promise<any> => (await api.post('/registry/hpr/sync', null, { params: { registration_number: registrationNumber, council } })).data,
};

export const referralsApi = {
  list: async (patientId?: string): Promise<{ items: any[]; total: number }> => (await api.get('/referrals', { params: { patient_id: patientId } })).data,
  create: async (data: Record<string, unknown>): Promise<any> => (await api.post('/referrals', data)).data,
  updateStatus: async (id: string, status: string): Promise<any> => (await api.patch(`/referrals/${id}/status`, null, { params: { new_status: status } })).data,
};

export const insuranceApi = {
  listPolicies: async (patientId?: string): Promise<{ items: any[]; total: number }> => (await api.get('/insurance/policies', { params: { patient_id: patientId } })).data,
  createPolicy: async (data: Record<string, unknown>): Promise<any> => (await api.post('/insurance/policies', data)).data,
  listClaims: async (patientId?: string): Promise<{ items: any[]; total: number }> => (await api.get('/insurance/claims', { params: { patient_id: patientId } })).data,
  createClaim: async (data: Record<string, unknown>): Promise<any> => (await api.post('/insurance/claims', data)).data,
  updateClaimStatus: async (id: string, status: string): Promise<any> => (await api.patch(`/insurance/claims/${id}/status`, null, { params: { new_status: status } })).data,
};

export const patientsApi = {
  list: async (search?: string): Promise<{ items: Patient[]; total: number }> => {
    const res = await api.get('/patients/', { params: { search, page_size: 50 } });
    return res.data;
  },
  create: async (patient: Partial<Patient>): Promise<Patient> => {
    const res = await api.post<Patient>('/patients/', patient);
    return res.data;
  },
  get: async (id: string): Promise<Patient> => {
    const res = await api.get<Patient>(`/patients/${id}`);
    return res.data;
  },
};

export const encountersApi = {
  listAssignableDoctors: async (): Promise<{ id: string; full_name: string }[]> => {
    const res = await api.get('/encounters/assignable-doctors');
    return res.data;
  },
  list: async (params?: { doctor_id?: string; status_filter?: string }): Promise<{ items: Encounter[]; total: number }> => {
    const res = await api.get('/encounters/', { params: { ...params, page_size: 50 } });
    return res.data;
  },
  create: async (encounter: {
    patient_id: string;
    doctor_id: string;
    department: string;
    encounter_type?: string;
    chief_complaint?: string;
    priority?: string;
  }): Promise<Encounter> => {
    const res = await api.post<Encounter>('/encounters/', encounter);
    return res.data;
  },
  updateStatus: async (encounterId: string, status: string): Promise<Encounter> => {
    const res = await api.put<Encounter>(`/encounters/${encounterId}`, { status });
    return res.data;
  },
};

export const clinicalApi = {
  createNote: async (note: ClinicalNote): Promise<ClinicalNote> => {
    const res = await api.post<ClinicalNote>('/clinical/notes', note);
    return res.data;
  },
  getNotes: async (encounterId: string): Promise<ClinicalNote[]> => {
    const res = await api.get<ClinicalNote[]>(`/clinical/notes/${encounterId}`);
    return res.data;
  },
  createPrescription: async (prescription: Prescription): Promise<Prescription> => {
    const res = await api.post<Prescription>('/clinical/prescriptions', prescription);
    return res.data;
  },
};

export const abdmApi = {
  getStatus: async (): Promise<AbdmStatus> => {
    const res = await api.get<AbdmStatus>('/abdm/status');
    return res.data;
  },
  generateAadhaarOtp: async (aadhaar_number: string): Promise<{ txnId?: string; txn_id?: string; message?: string; mobileNumber?: string }> => {
    const res = await api.post('/abdm/abha/aadhaar/otp', { aadhaar_number });
    return res.data;
  },
  verifyAadhaarOtp: async (txn_id: string, otp: string): Promise<any> => {
    const res = await api.post('/abdm/abha/aadhaar/verify', { txn_id, otp });
    return res.data;
  },
  generateMobileOtp: async (mobile_number: string): Promise<{ txnId?: string; message?: string }> => {
    const res = await api.post('/abdm/abha/mobile/otp', { mobile_number });
    return res.data;
  },
  verifyMobileOtp: async (txn_id: string, otp: string): Promise<any> => {
    const res = await api.post('/abdm/abha/mobile/verify', { txn_id, otp });
    return res.data;
  },
  searchAbhaAddress: async (abha_id: string): Promise<any> => {
    const res = await api.post('/abdm/abha/address/search', { abha_id });
    return res.data;
  },
  getAbhaProfile: async (abhaId: string): Promise<AbhaProfile> => {
    const res = await api.get<AbhaProfile>(`/abdm/abha/${encodeURIComponent(abhaId)}/profile`);
    return res.data;
  },
  triggerPatientShare: async (payload: any): Promise<any> => {
    const res = await api.post('/abdm/v3/hip/patient-share', payload);
    return res.data;
  },
  getShareQueue: async (): Promise<{ items: AbdmShareProfile[]; total: number }> => {
    const res = await api.get('/abdm/v3/hip/patient-share/queue');
    return res.data;
  },
  requestHiuConsent: async (payload: {
    patient_abha: string;
    purpose: string;
    purpose_code: string;
    date_from: string;
    date_to: string;
    hi_types: string[];
  }): Promise<AbdmConsentArtefact & { message?: string }> => {
    const res = await api.post('/abdm/hiu/consent/request', payload);
    return res.data;
  },
  listHiuConsents: async (patient_abha?: string): Promise<{ items: AbdmConsentArtefact[]; total: number }> => {
    const res = await api.get('/abdm/hiu/consents', { params: { patient_abha } });
    return res.data;
  },
  fetchHiuHealthInfo: async (
    consent_artefact_id: string
  ): Promise<{
    transaction_id: string;
    status: string;
    encryption_verified?: string;
    records_decrypted?: number;
    timeline?: LongitudinalTimelineRecord[];
  }> => {
    const res = await api.post('/abdm/hiu/health-info/fetch', { consent_artefact_id });
    return res.data;
  },
  getLongitudinalRecords: async (
    patient_abha: string
  ): Promise<{ items: LongitudinalTimelineRecord[]; total: number }> => {
    const res = await api.get(`/abdm/hiu/records/${encodeURIComponent(patient_abha)}`);
    return res.data;
  },
  resendOtp: async (
    txn_id: string,
    otp_system: string = 'aadhaar'
  ): Promise<{ txnId?: string; message?: string }> => {
    const res = await api.post('/abdm/abha/resend-otp', { txn_id, otp_system });
    return res.data;
  },
  enrolByDemographic: async (data: {
    aadhaar_number: string;
    name: string;
    date_of_birth: string;
    gender: string;
    mobile: string;
    consent_given: boolean;
    state_code?: string;
    district_code?: string;
    address?: string;
    pincode?: string;
  }): Promise<any> => {
    const res = await api.post('/abdm/abha/enrol/demographic', data);
    return res.data;
  },
  loginByMobile: async (mobile: string): Promise<{ txnId?: string; message?: string }> => {
    const res = await api.post('/abdm/abha/login/mobile', { mobile });
    return res.data;
  },
  verifyMobileLogin: async (txn_id: string, otp: string): Promise<any> => {
    const res = await api.post('/abdm/abha/login/mobile/verify', { txn_id, otp });
    return res.data;
  },
  loginByAadhaar: async (aadhaar_number: string): Promise<{ txnId?: string; message?: string }> => {
    const res = await api.post('/abdm/abha/login/aadhaar', { aadhaar_number });
    return res.data;
  },
  verifyAadhaarLogin: async (txn_id: string, otp: string): Promise<any> => {
    const res = await api.post('/abdm/abha/login/aadhaar/verify', { txn_id, otp });
    return res.data;
  },
  getAbhaCard: async (abha_token: string): Promise<any> => {
    const res = await api.post('/abdm/abha/card', { abha_token });
    return res.data;
  },
  getAbhaQr: async (abha_token: string): Promise<any> => {
    const res = await api.post('/abdm/abha/qr', { abha_token });
    return res.data;
  },
  getAddressSuggestions: async (txn_id: string): Promise<{ txnId: string; abhaAddressList: string[] }> => {
    const res = await api.get('/abdm/abha/suggestions', { params: { txn_id } });
    return res.data;
  },
};

export const wardsApi = {
  getSetup: async (signal?: AbortSignal): Promise<WardSetupStatus> => {
    const res = await api.get<WardSetupStatus>('/wards/setup', { signal });
    return res.data;
  },
  saveSetup: async (mode: 'INPATIENT' | 'OPD_ONLY', wards: WardSetupWard[]): Promise<WardSetupStatus> => {
    const res = await api.post<WardSetupStatus>('/wards/setup', { mode, wards });
    return res.data;
  },
  getOccupancy: async (signal?: AbortSignal): Promise<WardOccupancyStats> => {
    const res = await api.get<WardOccupancyStats>('/wards/occupancy', { signal });
    return res.data;
  },
  listWards: async (): Promise<any[]> => {
    const res = await api.get('/wards/');
    return res.data;
  },
  updateBedStatus: async (bedId: string, status: string): Promise<any> => {
    const res = await api.put(`/wards/beds/${bedId}/status`, { status });
    return res.data;
  },
};

export default api;

