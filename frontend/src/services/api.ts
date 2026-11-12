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
  generateAadhaarOtp: async (aadhaar_number: string): Promise<{ txnId?: string; txn_id?: string; message?: string; mobileNumber?: string }> => {
    const res = await api.post('/abdm/abha/aadhaar/otp', { aadhaar_number });
    return res.data;
  },
  verifyAadhaarOtp: async (txn_id: string, otp: string): Promise<any> => {
    const res = await api.post('/abdm/abha/aadhaar/verify', { txn_id, otp });
    return res.data;
  },
  getAbhaProfile: async (abhaId: string): Promise<AbhaProfile> => {
    const res = await api.get<AbhaProfile>(`/abdm/abha/${encodeURIComponent(abhaId)}/profile`);
    return res.data;
  },
};

export default api;

