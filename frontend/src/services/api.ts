import axios from 'axios';
import {
  AuthTokens,
  User,
  Patient,
  Encounter,
  ClinicalNote,
  Prescription,
  AbhaProfile,
  SignupData,
  WardOccupancyStats,
  AbdmStatus,
  AbdmShareProfile,
  AbdmConsentArtefact,
  LongitudinalTimelineRecord,
} from '../types';

// In production, Vite routes /api/v1 through Vercel rewrites to backend directly.
// In dev, vite.config.ts proxies /api to backend.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach JWT Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response Interceptor: Catch 401 and redirect to Login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !window.location.pathname.includes('/login')) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: async (email: string, password: string): Promise<AuthTokens> => {
    const res = await api.post<AuthTokens>('/auth/login', { email, password });
    return res.data;
  },
  signup: async (data: SignupData): Promise<User> => {
    const res = await api.post<User>('/auth/signup', data);
    return res.data;
  },
  getMe: async (): Promise<User> => {
    const res = await api.get<User>('/auth/me');
    return res.data;
  },
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
  getOccupancy: async (): Promise<WardOccupancyStats> => {
    const res = await api.get('/wards/occupancy');
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

