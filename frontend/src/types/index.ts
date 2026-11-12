export type UserRole =
  | 'SUPER_ADMIN'
  | 'HOSPITAL_ADMIN'
  | 'DOCTOR'
  | 'NURSE'
  | 'PHARMACIST'
  | 'LAB_TECHNICIAN'
  | 'RADIOLOGIST'
  | 'BILLING_CLERK'
  | 'FRONT_DESK';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  department?: string;
  registration_number?: string;
  phone?: string;
  is_active: boolean;
  is_verified: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Patient {
  id: string;
  registration_number: string; // UHID (e.g. UHID-YYYYMMDD-XXXXX)
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: 'MALE' | 'FEMALE' | 'OTHER' | 'UNDISCLOSED';
  phone: string;
  email?: string;
  address_line1?: string;
  city?: string;
  state?: string;
  pincode?: string;
  blood_group?: string;
  abha_id?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  created_at: string;
}

export type EncounterStatus =
  | 'SCHEDULED'
  | 'CHECKED_IN'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'ADMITTED'
  | 'DISCHARGED';

export interface Encounter {
  id: string;
  patient_id: string;
  doctor_id: string;
  encounter_type: 'OPD' | 'IPD' | 'EMERGENCY';
  status: EncounterStatus;
  token_number?: number;
  department: string;
  room_number?: string;
  chief_complaint?: string;
  priority: 'NORMAL' | 'URGENT' | 'EMERGENCY';
  created_at: string;
  patient?: Patient;
  doctor?: User;
}

export interface Vitals {
  temperature?: number;      // in °F
  systolic?: number;         // mmHg
  diastolic?: number;        // mmHg
  pulse?: number;            // bpm
  spo2?: number;             // %
  respiratory_rate?: number; // breaths/min
  weight?: number;           // kg
  height?: number;           // cm
  bmi?: number;
}

export interface ClinicalNote {
  id?: string;
  encounter_id: string;
  note_type: 'SOAP' | 'PROGRESS' | 'DISCHARGE_SUMMARY';
  subjective?: string;
  objective?: string;
  assessment?: string;
  plan?: string;
  vitals?: Vitals;
  created_at?: string;
}

export interface PrescriptionItem {
  drug_name: string;
  dosage: string;
  frequency: string;
  duration_days: number;
  instructions?: string;
}

export interface Prescription {
  id?: string;
  encounter_id: string;
  patient_id: string;
  items: PrescriptionItem[];
  notes?: string;
}

