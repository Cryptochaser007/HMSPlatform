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

export interface AbhaProfile {
  health_id: string;
  health_id_number: string;
  name: string;
  first_name?: string;
  middle_name?: string;
  last_name?: string;
  gender: string;
  year_of_birth: number;
  month_of_birth?: number;
  day_of_birth?: number;
  mobile?: string;
  email?: string;
  address?: string;
  district?: string;
  state?: string;
  pincode?: string;
  kycVerified?: boolean;
  profile_photo?: string;
}

export interface SignupData {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
  department?: string;
  registration_number?: string;
  phone?: string;
}

export interface LabResultItem {
  id: string;
  parameter_name: string;
  value: string;
  unit: string;
  reference_interval: string;
  flag: 'NORMAL' | 'HIGH' | 'LOW';
  category: string;
}

export interface BedItem {
  id: string;
  ward_name: string;
  ward_type: 'ICU' | 'GENERAL' | 'DELUXE' | 'EMERGENCY';
  bed_number: string;
  status: 'AVAILABLE' | 'OCCUPIED' | 'MAINTENANCE' | 'RESERVED';
  daily_charge: number;
  patient_name?: string;
  patient_uhid?: string;
  attending_doctor?: string;
  admitted_at?: string;
}

export interface WardOccupancyStats {
  total_beds: number;
  occupied: number;
  available: number;
  maintenance: number;
  reserved: number;
  occupancy_rate: number;
}

export interface AbdmStatus {
  abdm_env: 'MOCK' | 'SANDBOX' | 'PRODUCTION';
  gateway_url: string;
  abha_url: string;
  x_cm_id: string;
  hfr_facility_id: string;
  bridge_id_configured: boolean;
  credentials_configured: boolean;
  access_status: string;
}

export interface AbdmShareProfile {
  id: string;
  request_id: string;
  hip_id: string;
  counter_id?: string;
  token_number: string;
  abha_number?: string;
  abha_address: string;
  patient_name: string;
  gender: string;
  year_of_birth?: number;
  mobile_masked?: string;
  patient_id?: string;
  status: string;
  expires_at?: string;
  created_at?: string;
}

export interface AbdmConsentArtefact {
  consent_id: string;
  consent_request_id?: string;
  patient_abha: string;
  purpose_code: string;
  purpose_text: string;
  status: 'REQUESTED' | 'GRANTED' | 'DENIED' | 'REVOKED' | 'EXPIRED';
  hi_types: string[];
  date_from: string;
  date_to: string;
  created_at?: string;
  abdm_mode?: string;
}

export interface LongitudinalTimelineRecord {
  bundle_id: string;
  document_type: string;
  date: string;
  facility_name: string;
  practitioner_name: string;
  care_context_reference?: string;
  decryption_cipher?: string;
  diagnoses: string[];
  medications: { name: string; dosage: string }[];
  observations: { name: string; value: number | string; unit: string }[];
  diagnostic_reports: { title: string; conclusion: string }[];
}




