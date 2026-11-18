import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { abdmApi, patientsApi } from '../services/api';
import { AbhaProfile, AbdmStatus, AbdmShareProfile } from '../types';
import {
  ShieldCheck,
  CreditCard,
  Search,
  CheckCircle2,
  Copy,
  AlertCircle,
  QrCode,
  Phone,
  UserPlus,
  RefreshCw,
} from 'lucide-react';

export const AbhaPortal: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'create' | 'verify' | 'share'>('create');
  const navigate = useNavigate();

  // Live ABDM adapter status & Scan-and-Share queue
  const [abdmStatus, setAbdmStatus] = useState<AbdmStatus | null>(null);
  const [shareQueue, setShareQueue] = useState<AbdmShareProfile[]>([]);
  const [shareLoading, setShareLoading] = useState(false);

  const loadShareQueue = async () => {
    setShareLoading(true);
    try {
      const res = await abdmApi.getShareQueue();
      setShareQueue(res.items || []);
    } catch {
      // ignore if unauthenticated or offline
    } finally {
      setShareLoading(false);
    }
  };

  useEffect(() => {
    abdmApi.getStatus().then(setAbdmStatus).catch(() => {});
    loadShareQueue();
  }, []);

  const handleSimulateQrShare = async () => {
    setShareLoading(true);
    try {
      await abdmApi.triggerPatientShare({
        requestId: `qr-${Date.now()}`,
        intent: { type: 'PROFILE_SHARE' },
        metaData: { hipId: abdmStatus?.hfr_facility_id || 'HMS_HIP_SANDBOX', context: 'OPD-COUNTER-01' },
        profile: {
          patient: {
            abhaNumber: '91-4829-1029-4721',
            abhaAddress: `arun.kumar@${abdmStatus?.x_cm_id || 'sbx'}`,
            name: 'Arun Kumar',
            gender: 'M',
            yearOfBirth: 1991,
            identifiers: [{ type: 'MOBILE', value: '9876543210' }],
          },
        },
      });
      await loadShareQueue();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to simulate Scan & Share');
    } finally {
      setShareLoading(false);
    }
  };

  // Create ABHA states
  const [createMode, setCreateMode] = useState<'aadhaar_otp' | 'demographic'>('aadhaar_otp');
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [aadhaar, setAadhaar] = useState('');
  const [consentAgreed, setConsentAgreed] = useState(false);
  const [txnId, setTxnId] = useState('');
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);
  const [generatedProfile, setGeneratedProfile] = useState<AbhaProfile | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedAddress, setSelectedAddress] = useState('');

  // Resend OTP states (CRT_ABHA_106 / VRFY_ABHA_305 / VRFY_ABHA_405)
  const [resendCountdown, setResendCountdown] = useState(0);
  const [resendCount, setResendCount] = useState(0);

  // Demographic Form states (CRT_ABHA_301-309)
  const [demoForm, setDemoForm] = useState({
    name: '',
    gender: 'M',
    date_of_birth: '',
    aadhaar_number: '',
    mobile: '',
    state_code: '',
    district_code: '',
    address: '',
    pincode: '',
    consent_given: false,
  });

  // Verify ABHA states (VRFY_ABHA_101-405)
  const [verifyMode, setVerifyMode] = useState<'search' | 'aadhaar' | 'mobile' | 'comm_mobile'>('search');
  const [searchAbhaId, setSearchAbhaId] = useState('');
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [verifiedProfile, setVerifiedProfile] = useState<AbhaProfile | null>(null);
  const [verifyTxnId, setVerifyTxnId] = useState('');
  const [verifyOtpInput, setVerifyOtpInput] = useState('');
  const [verifyStep, setVerifyStep] = useState<1 | 2>(1);
  const [verifyIdentifier, setVerifyIdentifier] = useState('');

  // Countdown timer for resend OTP
  useEffect(() => {
    let timer: any;
    if (resendCountdown > 0) {
      timer = setInterval(() => {
        setResendCountdown((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [resendCountdown]);

  // Formatting Aadhaar (XXXX XXXX XXXX)
  const handleAadhaarChange = (val: string) => {
    const raw = val.replace(/\D/g, '').slice(0, 12);
    const formatted = raw.replace(/(\d{4})(?=\d)/g, '$1 ');
    setAadhaar(formatted);
  };

  // Step 1: Generate OTP (CRT_ABHA_104 / 105)
  const handleGenerateOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const rawAadhaar = aadhaar.replace(/\s+/g, '');
    if (rawAadhaar.length !== 12) {
      setError('Aadhaar Number is not valid');
      return;
    }
    if (!consentAgreed) {
      setError('You must accept the ABDM / UIDAI electronic consent to continue.');
      return;
    }

    setLoading(true);
    try {
      const res = await abdmApi.generateAadhaarOtp(rawAadhaar);
      const generatedTxn = res.txnId || res.txn_id || `txn-${Date.now()}`;
      setTxnId(generatedTxn);
      setSuccessNotice(res.message || 'OTP successfully dispatched to mobile linked with Aadhaar.');
      setStep(2);
      setResendCountdown(60);
      setResendCount(0);
    } catch (err: any) {
      console.error('OTP Gen error:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to send Aadhaar OTP. Try again.');
    } finally {
      setLoading(false);
    }
  };

  // Resend OTP (CRT_ABHA_106)
  const handleResendOtp = async () => {
    if (resendCountdown > 0 || resendCount >= 2 || !txnId) return;
    setLoading(true);
    try {
      await abdmApi.resendOtp(txnId, 'aadhaar');
      setResendCount((prev) => prev + 1);
      setResendCountdown(60);
      setSuccessNotice('OTP resent successfully. Please check your registered mobile.');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to resend OTP.');
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Verify OTP & fetch suggestions (CRT_ABHA_107 / 112 / 113)
  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (otp.length < 6) {
      setError('Please enter the 6-digit OTP received via SMS.');
      return;
    }

    setLoading(true);
    try {
      const res = await abdmApi.verifyAadhaarOtp(txnId, otp);
      const profile: AbhaProfile = {
        health_id: res.healthId || 'arun.kumar@abdm',
        health_id_number: res.healthIdNumber || '91-4829-1029-4721',
        name: res.name || 'Arun Kumar',
        first_name: res.firstName,
        last_name: res.lastName,
        gender: res.gender || 'MALE',
        year_of_birth: res.yearOfBirth || 1991,
        month_of_birth: res.monthOfBirth || 5,
        day_of_birth: res.dayOfBirth || 14,
        mobile: res.mobile || '9876543210',
        address: res.address || 'Flat 402, Shanti Vihar, Indiranagar',
        district: res.districtName || 'Bengaluru Urban',
        state: res.stateName || 'Karnataka',
        pincode: res.pincode || '560038',
        kycVerified: true,
      };

      setGeneratedProfile(profile);
      setSelectedAddress(profile.health_id);
      setStep(3);
      setSuccessNotice('Aadhaar authenticated! ABHA Digital Health Account created.');

      // Fetch ABHA suggestions (CRT_ABHA_112)
      try {
        const suggRes = await abdmApi.getAddressSuggestions(txnId);
        if (suggRes.abhaAddressList && suggRes.abhaAddressList.length > 0) {
          setSuggestions(suggRes.abhaAddressList);
        }
      } catch {
        setSuggestions([
          `arun.kumar@${abdmStatus?.x_cm_id || 'sbx'}`,
          `arunkumar1991@${abdmStatus?.x_cm_id || 'sbx'}`,
          `arun.k.91@${abdmStatus?.x_cm_id || 'sbx'}`,
        ]);
      }
    } catch (err: any) {
      console.error('Verify error:', err);
      setError(err.response?.data?.detail || err.message || 'Invalid or expired OTP.');
    } finally {
      setLoading(false);
    }
  };

  // Demographic Enrolment Submit (CRT_ABHA_301-309)
  const handleDemographicSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const rawAadhaar = demoForm.aadhaar_number.replace(/\s+/g, '');
    if (rawAadhaar.length !== 12) {
      setError('Aadhaar Number is not valid');
      return;
    }
    if (!demoForm.consent_given) {
      setError('User consent is mandatory before ABHA enrolment (CRT_ABHA_302).');
      return;
    }

    setLoading(true);
    try {
      const res = await abdmApi.enrolByDemographic({
        ...demoForm,
        aadhaar_number: rawAadhaar,
      });
      const profile: AbhaProfile = {
        health_id: res.healthId || `demo.patient@${abdmStatus?.x_cm_id || 'sbx'}`,
        health_id_number: res.healthIdNumber || '91-4829-1029-4721',
        name: demoForm.name,
        gender: demoForm.gender,
        year_of_birth: parseInt(demoForm.date_of_birth.split('-')[0] || '1990'),
        mobile: demoForm.mobile,
        address: demoForm.address,
        pincode: demoForm.pincode,
        kycVerified: true,
      };
      setGeneratedProfile(profile);
      setSelectedAddress(profile.health_id);
      setStep(3);
      setSuccessNotice('ABHA successfully created via Aadhaar Demographic Authentication (Offline Mode).');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Demographic authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  // Verify existing ABHA search
  const handleSearchAbha = async (e: React.FormEvent) => {
    e.preventDefault();
    setVerifyError(null);
    setVerifiedProfile(null);
    if (!searchAbhaId.trim()) {
      setVerifyError('Please enter an ABHA Address (e.g. user@abdm) or 14-digit ABHA Number.');
      return;
    }

    setVerifyLoading(true);
    try {
      const profile = await abdmApi.getAbhaProfile(searchAbhaId.trim());
      setVerifiedProfile(profile);
    } catch (err: any) {
      console.error('ABHA search error:', err);
      setVerifyError(
        err.response?.data?.detail || 'ABHA account not found on ABDM registry. Check ID and try again.'
      );
    } finally {
      setVerifyLoading(false);
    }
  };

  // Initiate OTP Verification for Aadhaar / Mobile (VRFY_ABHA_101/201/301/401)
  const handleInitiateVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setVerifyError(null);
    setVerifyLoading(true);
    try {
      let res: any;
      if (verifyMode === 'aadhaar') {
        const raw = verifyIdentifier.replace(/\s+/g, '');
        if (raw.length !== 12) {
          setVerifyError('Aadhaar Number is not valid');
          setVerifyLoading(false);
          return;
        }
        res = await abdmApi.loginByAadhaar(raw);
      } else if (verifyMode === 'mobile') {
        res = await abdmApi.generateMobileOtp(verifyIdentifier);
      } else {
        res = await abdmApi.loginByMobile(verifyIdentifier);
      }
      setVerifyTxnId(res.txnId || res.txn_id || `vtxn-${Date.now()}`);
      setVerifyStep(2);
      setSuccessNotice(res.message || 'Verification OTP sent to registered mobile.');
    } catch (err: any) {
      setVerifyError(err.response?.data?.detail || 'Failed to request verification OTP.');
    } finally {
      setVerifyLoading(false);
    }
  };

  // Confirm OTP Verification (VRFY_ABHA_102/202/302/402)
  const handleConfirmVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setVerifyError(null);
    if (verifyOtpInput.length < 6) {
      setVerifyError('Please enter the 6-digit verification OTP.');
      return;
    }
    setVerifyLoading(true);
    try {
      let res: any;
      if (verifyMode === 'aadhaar') {
        res = await abdmApi.verifyAadhaarLogin(verifyTxnId, verifyOtpInput);
      } else if (verifyMode === 'mobile') {
        res = await abdmApi.verifyMobileOtp(verifyTxnId, verifyOtpInput);
      } else {
        res = await abdmApi.verifyMobileLogin(verifyTxnId, verifyOtpInput);
      }
      const profile: AbhaProfile = {
        health_id: res.healthId || res.phrAddress?.[0] || 'arun.kumar@sbx',
        health_id_number: res.healthIdNumber || res.ABHANumber || '91-4829-1029-4721',
        name: res.name || 'Verified Patient',
        gender: res.gender || 'M',
        year_of_birth: res.yearOfBirth || 1991,
        mobile: res.mobile,
        address: res.address,
        district: res.districtName,
        state: res.stateName,
        pincode: res.pincode,
        kycVerified: true,
      };
      setVerifiedProfile(profile);
      setSuccessNotice('ABHA verified successfully via OTP authentication!');
    } catch (err: any) {
      setVerifyError(err.response?.data?.detail || 'Invalid OTP. Please check and try again.');
    } finally {
      setVerifyLoading(false);
    }
  };

  // View and Download ABHA Card (CRT_ABHA_114/115/209/308)
  const handleDownloadCard = () => {
    window.print();
  };

  // Auto-import ABHA profile into local patient registry
  const handleImportToPatient = async (p: AbhaProfile) => {
    try {
      const nameParts = p.name.split(' ');
      const firstName = nameParts[0] || 'Patient';
      const lastName = nameParts.slice(1).join(' ') || 'ABHA';
      const dob = `${p.year_of_birth}-${String(p.month_of_birth || 1).padStart(2, '0')}-${String(
        p.day_of_birth || 1
      ).padStart(2, '0')}`;

      await patientsApi.create({
        first_name: firstName,
        last_name: lastName,
        gender: p.gender === 'F' ? 'FEMALE' : p.gender === 'M' ? 'MALE' : 'OTHER',
        date_of_birth: dob,
        phone: p.mobile || '9876543210',
        email: p.email,
        address_line1: p.address,
        city: p.district || 'Bengaluru',
        state: p.state || 'Karnataka',
        pincode: p.pincode || '560001',
        abha_id: p.health_id_number,
      });

      alert(`Patient ${p.name} successfully imported into Hospital Registry with ABHA ${p.health_id_number}!`);
      navigate('/patients');
    } catch (err: any) {
      alert(`Could not import patient: ${err.response?.data?.detail || err.message}`);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert(`Copied "${text}" to clipboard!`);
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-brand-800 via-brand-700 to-indigo-900 rounded-2xl p-6 text-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/10 backdrop-blur-md rounded-full text-xs font-semibold text-emerald-300 mb-2">
            <ShieldCheck className="w-3.5 h-3.5" /> ABDM v3 M1 / M2 / M3 Adapter • Mode:{' '}
            {abdmStatus?.abdm_env || 'MOCK'}
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Ayushman Bharat Health Account (ABHA) Portal</h1>
          <p className="text-sm text-brand-100 mt-1 max-w-2xl">
            Generate 14-digit ABHA Numbers via Aadhaar e-KYC, verify digital health profiles on the National Health
            Authority (NHA) gateway, and manage ABHA QR Scan &amp; Share OPD check-ins.
          </p>
        </div>
        <div className="bg-white/10 backdrop-blur-md border border-white/20 p-4 rounded-xl flex items-center gap-3 self-start md:self-auto">
          <div className="p-2 bg-emerald-500 rounded-lg text-white">
            <CreditCard className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs uppercase font-medium text-brand-200">
              X-CM-ID: {abdmStatus?.x_cm_id || 'sbx'}
            </div>
            <div className="text-sm font-bold text-white">
              {abdmStatus?.abdm_env === 'MOCK' ? 'Sandbox Simulation' : abdmStatus?.access_status || 'Connected'}
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex flex-wrap border-b border-slate-200 bg-white rounded-t-xl px-4 pt-2 gap-4">
        <button
          onClick={() => setActiveTab('create')}
          className={`pb-3 px-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'create'
              ? 'border-brand-600 text-brand-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <CreditCard className="w-4 h-4" />
          Generate New ABHA via Aadhaar
        </button>
        <button
          onClick={() => setActiveTab('verify')}
          className={`pb-3 px-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'verify'
              ? 'border-brand-600 text-brand-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Search className="w-4 h-4" />
          Verify & Search Existing ABHA ID
        </button>
        <button
          onClick={() => {
            setActiveTab('share');
            loadShareQueue();
          }}
          className={`pb-3 px-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'share'
              ? 'border-brand-600 text-brand-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <QrCode className="w-4 h-4" />
          Scan &amp; Share OPD Counter
          {shareQueue.length > 0 && (
            <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.2 rounded-full font-bold">
              {shareQueue.length}
            </span>
          )}
        </button>
      </div>

      {/* TAB 1: CREATE ABHA VIA AADHAAR */}
      {activeTab === 'create' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            {/* Step Progress Indicators */}
            <div className="flex items-center justify-between mb-8 relative">
              <div className="absolute left-6 right-6 top-1/2 -translate-y-1/2 h-0.5 bg-slate-200 -z-0"></div>
              <div
                className={`flex items-center gap-2 z-10 bg-white pr-2 ${
                  step >= 1 ? 'text-brand-600 font-bold' : 'text-slate-400'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                    step >= 1 ? 'bg-brand-600 text-white' : 'bg-slate-200 text-slate-600'
                  }`}
                >
                  1
                </div>
                <span className="text-xs">Aadhaar Details</span>
              </div>

              <div
                className={`flex items-center gap-2 z-10 bg-white px-2 ${
                  step >= 2 ? 'text-brand-600 font-bold' : 'text-slate-400'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                    step >= 2 ? 'bg-brand-600 text-white' : 'bg-slate-200 text-slate-600'
                  }`}
                >
                  2
                </div>
                <span className="text-xs">UIDAI OTP</span>
              </div>

              <div
                className={`flex items-center gap-2 z-10 bg-white pl-2 ${
                  step >= 3 ? 'text-emerald-600 font-bold' : 'text-slate-400'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                    step >= 3 ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'
                  }`}
                >
                  3
                </div>
                <span className="text-xs">Digital ABHA Card</span>
              </div>
            </div>

            {error && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs flex items-center gap-2 mb-4">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {successNotice && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg text-xs flex items-center gap-2 mb-4">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{successNotice}</span>
              </div>
            )}

            {/* Mode Selector for ABHA Creation */}
            {step === 1 && (
              <div className="flex border border-slate-200 rounded-lg p-1 bg-slate-50 mb-6 gap-1">
                <button
                  type="button"
                  onClick={() => setCreateMode('aadhaar_otp')}
                  className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                    createMode === 'aadhaar_otp'
                      ? 'bg-white text-brand-700 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Create via Aadhaar OTP (CRT_ABHA_101)
                </button>
                <button
                  type="button"
                  onClick={() => setCreateMode('demographic')}
                  className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                    createMode === 'demographic'
                      ? 'bg-white text-brand-700 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Create via Demographic / Offline (CRT_ABHA_301)
                </button>
              </div>
            )}

            {/* STEP 1: Enter Aadhaar (OTP Mode) */}
            {step === 1 && createMode === 'aadhaar_otp' && (
              <form onSubmit={handleGenerateOtp} className="space-y-5">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                    Enter Patient 12-Digit Aadhaar Number
                  </label>
                  <div className="relative">
                    <CreditCard className="w-5 h-5 text-slate-400 absolute left-3 top-3" />
                    <input
                      type="text"
                      required
                      value={aadhaar}
                      onChange={(e) => handleAadhaarChange(e.target.value)}
                      placeholder="XXXX XXXX XXXX"
                      className="w-full pl-11 pr-4 py-2.5 text-lg font-mono tracking-widest border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                    />
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1.5">
                    Demo simulation mode: You may enter any 12 digits (e.g.{' '}
                    <span className="font-mono text-slate-700">9999 8888 7777</span>) to test OTP generation.
                  </p>
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                  <label className="flex items-start gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={consentAgreed}
                      onChange={(e) => setConsentAgreed(e.target.checked)}
                      className="mt-0.5 rounded text-brand-600 focus:ring-brand-500"
                    />
                    <span className="text-xs text-slate-600 leading-relaxed">
                      I voluntarily submit my Aadhaar number and consent to UIDAI authentication for the purpose of
                      creating my Ayushman Bharat Health Account (ABHA) under ABDM and Digital Personal Data Protection
                      (DPDP) Act 2023 (CRT_ABHA_102).
                    </span>
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={loading || !consentAgreed}
                  className="w-full py-3 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                >
                  {loading ? (
                    <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  ) : (
                    <>
                      <Phone className="w-4 h-4" />
                      Request Aadhaar Authentication OTP
                    </>
                  )}
                </button>
              </form>
            )}

            {/* STEP 1: Demographic Mode Form (CRT_ABHA_301-309) */}
            {step === 1 && createMode === 'demographic' && (
              <form onSubmit={handleDemographicSubmit} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                      Full Name (as on Aadhaar) *
                    </label>
                    <input
                      type="text"
                      required
                      value={demoForm.name}
                      onChange={(e) => setDemoForm({ ...demoForm, name: e.target.value })}
                      placeholder="e.g. Arun Kumar"
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Gender *</label>
                    <select
                      value={demoForm.gender}
                      onChange={(e) => setDemoForm({ ...demoForm, gender: e.target.value })}
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                    >
                      <option value="M">Male</option>
                      <option value="F">Female</option>
                      <option value="O">Other</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                      Date of Birth (YYYY-MM-DD) *
                    </label>
                    <input
                      type="date"
                      required
                      value={demoForm.date_of_birth}
                      onChange={(e) => setDemoForm({ ...demoForm, date_of_birth: e.target.value })}
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                      12-Digit Aadhaar Number *
                    </label>
                    <input
                      type="text"
                      required
                      maxLength={14}
                      value={demoForm.aadhaar_number}
                      onChange={(e) => setDemoForm({ ...demoForm, aadhaar_number: e.target.value })}
                      placeholder="XXXX XXXX XXXX"
                      className="w-full px-3 py-2 text-sm font-mono border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                      Mobile Number *
                    </label>
                    <input
                      type="tel"
                      required
                      maxLength={10}
                      value={demoForm.mobile}
                      onChange={(e) => setDemoForm({ ...demoForm, mobile: e.target.value })}
                      placeholder="10-digit mobile"
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Pincode</label>
                    <input
                      type="text"
                      maxLength={6}
                      value={demoForm.pincode}
                      onChange={(e) => setDemoForm({ ...demoForm, pincode: e.target.value })}
                      placeholder="e.g. 560038"
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Address</label>
                  <input
                    type="text"
                    value={demoForm.address}
                    onChange={(e) => setDemoForm({ ...demoForm, address: e.target.value })}
                    placeholder="Residential address as on Aadhaar"
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                  <label className="flex items-start gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={demoForm.consent_given}
                      onChange={(e) => setDemoForm({ ...demoForm, consent_given: e.target.checked })}
                      className="mt-0.5 rounded text-brand-600 focus:ring-brand-500"
                    />
                    <span className="text-xs text-slate-600 leading-relaxed">
                      I voluntarily submit my Aadhaar and demographic details and consent to authentication for creating
                      my Ayushman Bharat Health Account under ABDM (CRT_ABHA_302).
                    </span>
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={loading || !demoForm.consent_given}
                  className="w-full py-3 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                >
                  {loading ? (
                    <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  ) : (
                    <>
                      <ShieldCheck className="w-4 h-4" />
                      Authenticate Demographics &amp; Create ABHA
                    </>
                  )}
                </button>
              </form>
            )}

            {/* STEP 2: Enter OTP (CRT_ABHA_105 / 106) */}
            {step === 2 && (
              <form onSubmit={handleVerifyOtp} className="space-y-5">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                      Enter 6-Digit Aadhaar OTP
                    </label>
                    <span className="text-xs text-brand-600 font-mono">txnId: {txnId.slice(0, 14)}...</span>
                  </div>
                  <input
                    type="text"
                    maxLength={6}
                    required
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                    placeholder="123456"
                    className="w-full text-center py-3 text-2xl font-mono tracking-[0.5em] border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                  />
                  <div className="flex justify-between items-center mt-2 text-xs">
                    <p className="text-[11px] text-slate-500">
                      Demo OTP: Enter any 6 digits (e.g.{' '}
                      <span className="font-mono text-slate-700 font-bold">123456</span>)
                    </p>
                    <button
                      type="button"
                      onClick={handleResendOtp}
                      disabled={resendCountdown > 0 || resendCount >= 2 || loading}
                      className="text-brand-600 hover:text-brand-800 disabled:text-slate-400 font-semibold flex items-center gap-1 text-xs"
                    >
                      <RefreshCw className="w-3 h-3" />
                      {resendCountdown > 0
                        ? `Resend in ${resendCountdown}s`
                        : resendCount >= 2
                        ? 'Resend limit reached (2/2)'
                        : 'Resend OTP (CRT_ABHA_106)'}
                    </button>
                  </div>
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="py-2.5 px-4 border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-lg text-sm font-semibold transition-colors"
                  >
                    Back
                  </button>
                  <button
                    type="submit"
                    disabled={loading || otp.length < 6}
                    className="flex-1 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                  >
                    {loading ? (
                      <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                    ) : (
                      <>
                        <ShieldCheck className="w-4 h-4" />
                        Verify OTP & Issue ABHA ID
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}

            {/* STEP 3: Render ABHA Card */}
            {step === 3 && generatedProfile && (
              <div className="space-y-6">
                {/* Official Style Digital ABHA Card */}
                <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 text-white rounded-2xl p-6 shadow-xl border border-slate-700 relative overflow-hidden">
                  <div className="absolute top-0 right-0 -mr-8 -mt-8 w-36 h-36 bg-emerald-500/10 rounded-full blur-2xl"></div>

                  <div className="flex justify-between items-start border-b border-slate-700 pb-4 mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center border border-white/20">
                        <CreditCard className="w-6 h-6 text-emerald-400" />
                      </div>
                      <div>
                        <div className="text-[11px] font-bold tracking-widest text-emerald-400 uppercase">
                          National Health Authority
                        </div>
                        <div className="text-base font-bold tracking-tight">ABHA Digital Health ID</div>
                      </div>
                    </div>
                    <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-full font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> KYC Verified
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-4 mb-5">
                    <div className="col-span-2 space-y-3">
                      <div>
                        <div className="text-[10px] uppercase font-mono text-slate-400">14-Digit ABHA Number</div>
                        <div className="text-xl font-bold font-mono tracking-wider text-white flex items-center gap-2">
                          {generatedProfile.health_id_number}
                          <button
                            onClick={() => copyToClipboard(generatedProfile.health_id_number)}
                            title="Copy ABHA Number"
                            className="text-slate-400 hover:text-white"
                          >
                            <Copy className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      <div>
                        <div className="text-[10px] uppercase font-mono text-slate-400">ABHA Address (PHR)</div>
                        <div className="text-sm font-semibold text-emerald-300">{generatedProfile.health_id}</div>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-[10px] text-slate-400 block">Patient Name</span>
                          <span className="font-semibold">{generatedProfile.name}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block">Gender / DOB</span>
                          <span className="font-semibold">
                            {generatedProfile.gender} • {generatedProfile.year_of_birth}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col items-center justify-center bg-white/5 border border-white/10 rounded-xl p-3">
                      <QrCode className="w-20 h-20 text-slate-100 mb-1" />
                      <span className="text-[9px] text-slate-400 font-mono">Scan for Records</span>
                    </div>
                  </div>

                  <div className="text-[11px] text-slate-400 border-t border-slate-700/60 pt-3 flex items-center justify-between">
                    <span>Ayushman Bharat Digital Mission (ABDM) • Govt of India</span>
                    <span>Valid Across India</span>
                  </div>
                </div>

                {/* CRT_ABHA_112: Suggested ABHA Addresses */}
                {suggestions.length > 0 && (
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                    <div className="text-xs font-semibold text-slate-700 flex items-center justify-between">
                      <span>Available ABHA Address Suggestions (CRT_ABHA_112):</span>
                      <span className="text-[11px] text-brand-600 font-mono">Selected: {selectedAddress}</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {suggestions.map((sugg) => (
                        <button
                          key={sugg}
                          type="button"
                          onClick={() => setSelectedAddress(sugg)}
                          className={`px-3 py-1.5 text-xs rounded-lg border font-mono transition-colors ${
                            selectedAddress === sugg
                              ? 'bg-brand-600 text-white border-brand-600 font-bold'
                              : 'bg-white border-slate-300 text-slate-700 hover:border-brand-500'
                          }`}
                        >
                          {sugg}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={() =>
                      handleImportToPatient({
                        ...generatedProfile,
                        health_id: selectedAddress || generatedProfile.health_id,
                      })
                    }
                    className="flex-1 py-3 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-2 shadow-sm"
                  >
                    <UserPlus className="w-4 h-4" />
                    Register Directly into Patient Registry
                  </button>
                  <button
                    onClick={handleDownloadCard}
                    className="py-3 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-2 shadow-sm"
                    title="View & Print ABHA Card (CRT_ABHA_114/209/308)"
                  >
                    <CreditCard className="w-4 h-4" />
                    View &amp; Print Card
                  </button>
                  <button
                    onClick={() => {
                      setStep(1);
                      setAadhaar('');
                      setOtp('');
                      setGeneratedProfile(null);
                      setSuggestions([]);
                    }}
                    className="py-3 px-4 border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-lg text-sm font-semibold transition-colors"
                  >
                    Create Another ABHA
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Quick Help Drawer */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-brand-600" />
              ABDM Compliance Information
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              An <strong>ABHA (Ayushman Bharat Health Account)</strong> is a 14-digit unique health identity issued under
              the National Health Authority.
            </p>
            <div className="space-y-2.5 text-xs text-slate-600">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                <span>Enables paperless consultation and longitudinal medical history.</span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                <span>Complies with Digital Personal Data Protection (DPDP) Act 2023.</span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                <span>Interoperable across government and private hospitals via FHIR R4 standard.</span>
              </div>
            </div>
            <div className="pt-3 border-t border-slate-200">
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
                Standard Formats
              </div>
              <div className="text-xs text-slate-700 font-mono space-y-1">
                <div>ABHA No: 91-XXXX-XXXX-XXXX</div>
                <div>ABHA Address: user@abdm</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: VERIFY EXISTING ABHA */}
      {activeTab === 'verify' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
            {/* Verification Method Sub-Tabs */}
            <div className="flex flex-wrap border border-slate-200 rounded-lg p-1 bg-slate-50 gap-1 text-xs">
              <button
                type="button"
                onClick={() => {
                  setVerifyMode('search');
                  setVerifyStep(1);
                  setVerifyError(null);
                }}
                className={`flex-1 py-1.5 px-2 font-semibold rounded-md transition-colors ${
                  verifyMode === 'search' ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Search by ABHA
              </button>
              <button
                type="button"
                onClick={() => {
                  setVerifyMode('aadhaar');
                  setVerifyStep(1);
                  setVerifyError(null);
                  setVerifyIdentifier('');
                }}
                className={`flex-1 py-1.5 px-2 font-semibold rounded-md transition-colors ${
                  verifyMode === 'aadhaar' ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Aadhaar OTP (VRFY_101)
              </button>
              <button
                type="button"
                onClick={() => {
                  setVerifyMode('mobile');
                  setVerifyStep(1);
                  setVerifyError(null);
                  setVerifyIdentifier('');
                }}
                className={`flex-1 py-1.5 px-2 font-semibold rounded-md transition-colors ${
                  verifyMode === 'mobile' ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Mobile OTP (VRFY_201)
              </button>
              <button
                type="button"
                onClick={() => {
                  setVerifyMode('comm_mobile');
                  setVerifyStep(1);
                  setVerifyError(null);
                  setVerifyIdentifier('');
                }}
                className={`flex-1 py-1.5 px-2 font-semibold rounded-md transition-colors ${
                  verifyMode === 'comm_mobile' ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Comm Mobile (VRFY_301)
              </button>
            </div>

            {/* Mode 1: Search Form */}
            {verifyMode === 'search' && (
              <form onSubmit={handleSearchAbha} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                    Search &amp; Verify ABHA ID on NHA Gateway
                  </label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                      <input
                        type="text"
                        value={searchAbhaId}
                        onChange={(e) => setSearchAbhaId(e.target.value)}
                        placeholder="e.g. 91-4829-1029-4721 or priya.sharma@abdm"
                        className="w-full pl-9 pr-4 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent font-medium"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={verifyLoading}
                      className="py-2 px-5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
                    >
                      {verifyLoading ? (
                        <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                      ) : (
                        <>
                          <ShieldCheck className="w-4 h-4" />
                          Verify
                        </>
                      )}
                    </button>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1.5">
                    Enter an ABHA Number (14 digits) or an ABHA Address (@abdm) to retrieve verified demographic records.
                  </p>
                </div>
              </form>
            )}

            {/* Mode 2, 3, 4: OTP Verification Step 1 */}
            {verifyMode !== 'search' && verifyStep === 1 && (
              <form onSubmit={handleInitiateVerifyOtp} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                    {verifyMode === 'aadhaar'
                      ? 'Enter 12-Digit Aadhaar Number'
                      : verifyMode === 'mobile'
                      ? 'Enter ABHA-Linked Mobile Number'
                      : 'Enter Communication Mobile Number (VRFY_ABHA_301)'}
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      required
                      value={verifyIdentifier}
                      onChange={(e) => setVerifyIdentifier(e.target.value)}
                      placeholder={verifyMode === 'aadhaar' ? 'XXXX XXXX XXXX' : '9876543210'}
                      className="flex-1 px-4 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 font-mono"
                    />
                    <button
                      type="submit"
                      disabled={verifyLoading || !verifyIdentifier.trim()}
                      className="py-2 px-5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
                    >
                      {verifyLoading ? (
                        <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                      ) : (
                        <>
                          <Phone className="w-4 h-4" />
                          Send OTP
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </form>
            )}

            {/* Mode 2, 3, 4: OTP Verification Step 2 */}
            {verifyMode !== 'search' && verifyStep === 2 && (
              <form onSubmit={handleConfirmVerifyOtp} className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                      Enter 6-Digit OTP
                    </label>
                    <span className="text-xs text-brand-600 font-mono">txnId: {verifyTxnId.slice(0, 14)}...</span>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      maxLength={6}
                      required
                      value={verifyOtpInput}
                      onChange={(e) => setVerifyOtpInput(e.target.value.replace(/\D/g, ''))}
                      placeholder="123456"
                      className="flex-1 px-4 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 font-mono text-center tracking-widest text-lg"
                    />
                    <button
                      type="submit"
                      disabled={verifyLoading || verifyOtpInput.length < 6}
                      className="py-2 px-5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
                    >
                      {verifyLoading ? (
                        <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                      ) : (
                        <>
                          <ShieldCheck className="w-4 h-4" />
                          Verify &amp; Fetch ABHA
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </form>
            )}

            {verifyError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{verifyError}</span>
              </div>
            )}

            {/* Verified Patient Demographic Card */}
            {verifiedProfile && (
              <div className="border border-emerald-200 bg-emerald-50/40 rounded-xl p-5 space-y-5">
                <div className="flex items-center justify-between pb-3 border-b border-emerald-200">
                  <div className="flex items-center gap-2 text-emerald-800 font-bold text-sm">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    Verified Active Health Account
                  </div>
                  <span className="text-xs bg-emerald-100 text-emerald-800 font-semibold px-2.5 py-0.5 rounded-full">
                    KYC Verified
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-slate-500 block">Full Name</span>
                    <span className="font-bold text-slate-900 text-sm">{verifiedProfile.name}</span>
                  </div>

                  <div>
                    <span className="text-slate-500 block">ABHA Number</span>
                    <span className="font-mono font-bold text-slate-900 text-sm">
                      {verifiedProfile.health_id_number}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-500 block">ABHA Address</span>
                    <span className="font-semibold text-brand-700">{verifiedProfile.health_id}</span>
                  </div>

                  <div>
                    <span className="text-slate-500 block">Gender & DOB</span>
                    <span className="font-medium text-slate-800">
                      {verifiedProfile.gender} • {verifiedProfile.day_of_birth}/{verifiedProfile.month_of_birth}/
                      {verifiedProfile.year_of_birth}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-500 block">Linked Mobile</span>
                    <span className="font-medium text-slate-800">{verifiedProfile.mobile || 'N/A'}</span>
                  </div>

                  <div>
                    <span className="text-slate-500 block">Address & Pincode</span>
                    <span className="font-medium text-slate-800">
                      {verifiedProfile.address}, {verifiedProfile.district}, {verifiedProfile.pincode}
                    </span>
                  </div>
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => handleImportToPatient(verifiedProfile)}
                    className="py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-2 shadow-sm"
                  >
                    <UserPlus className="w-4 h-4" />
                    Import to Hospital Patient Registry
                  </button>
                  <button
                    onClick={() => copyToClipboard(verifiedProfile.health_id_number)}
                    className="py-2.5 px-4 border border-slate-300 text-slate-700 hover:bg-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    Copy ABHA ID
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Side Info */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <Search className="w-4 h-4 text-brand-600" />
              Quick Sample ABHA Records
            </h3>
            <p className="text-xs text-slate-600">
              Click any of the pre-verified demo identifiers to test gateway verification:
            </p>
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => {
                  setSearchAbhaId('priya.sharma@abdm');
                }}
                className="w-full text-left p-2.5 bg-white border border-slate-200 hover:border-brand-500 rounded-lg text-xs transition-colors"
              >
                <div className="font-semibold text-slate-800">priya.sharma@abdm</div>
                <div className="text-[11px] text-slate-500">Priya Sharma • Bengaluru Urban</div>
              </button>
              <button
                type="button"
                onClick={() => {
                  setSearchAbhaId('91-4829-1029-4721');
                }}
                className="w-full text-left p-2.5 bg-white border border-slate-200 hover:border-brand-500 rounded-lg text-xs transition-colors"
              >
                <div className="font-semibold text-slate-800">91-4829-1029-4721</div>
                <div className="text-[11px] text-slate-500">Arun Kumar • Bengaluru Urban</div>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: M1 ABHA QR SCAN & SHARE OPD COUNTER */}
      {activeTab === 'share' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Live ABHA QR Scan &amp; Share Check-In Queue
                </h3>
                <p className="text-xs text-slate-500">
                  Webhook Receiver: <code className="font-mono text-brand-700">/api/v1/abdm/v3/hip/patient-share</code>
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleSimulateQrShare}
                  disabled={shareLoading}
                  className="py-2 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm disabled:opacity-50"
                >
                  <QrCode className="w-3.5 h-3.5" /> Simulate QR Check-In
                </button>
                <button
                  onClick={loadShareQueue}
                  disabled={shareLoading}
                  className="py-2 px-3 border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${shareLoading ? 'animate-spin' : ''}`} /> Refresh
                </button>
              </div>
            </div>

            {shareQueue.length === 0 ? (
              <div className="p-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-300 space-y-2">
                <QrCode className="w-10 h-10 text-slate-400 mx-auto" />
                <div className="text-sm font-semibold text-slate-700">No Scan &amp; Share check-ins yet</div>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  When a patient scans the OPD Counter QR code using the ABHA PHR App, their verified profile and
                  instant counter token appear here automatically.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-slate-200 border border-slate-200 rounded-xl overflow-hidden">
                {shareQueue.map((item) => (
                  <div
                    key={item.id}
                    className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50"
                  >
                    <div className="flex items-center gap-3">
                      <div className="px-3 py-2 bg-brand-600 text-white rounded-lg font-mono font-bold text-xs">
                        {item.token_number}
                      </div>
                      <div>
                        <div className="text-sm font-bold text-slate-900">
                          {item.patient_name}{' '}
                          <span className="text-xs font-normal text-slate-500">
                            ({item.gender} • YOB {item.year_of_birth || '—'})
                          </span>
                        </div>
                        <div className="text-xs text-slate-600 font-mono">
                          {item.abha_address} {item.abha_number ? `• ${item.abha_number}` : ''}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          Counter: {item.counter_id || 'OPD-01'} • Mobile: {item.mobile_masked || 'Masked'}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() =>
                        handleImportToPatient({
                          health_id: item.abha_address,
                          health_id_number: item.abha_number || '91-4829-1029-4721',
                          name: item.patient_name,
                          gender: item.gender,
                          year_of_birth: item.year_of_birth || 1990,
                        })
                      }
                      className="py-1.5 px-3 bg-slate-900 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shrink-0"
                    >
                      <UserPlus className="w-3.5 h-3.5" /> Register &amp; Check-In
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 flex flex-col items-center text-center space-y-3">
            <div className="p-4 bg-white border-2 border-slate-900 rounded-2xl shadow-sm">
              <QrCode className="w-32 h-32 text-slate-900" />
            </div>
            <div className="text-sm font-bold text-slate-900">OPD Registration Counter QR</div>
            <div className="text-xs text-slate-600 font-mono">
              HFR ID: {abdmStatus?.hfr_facility_id || 'HMS_HIP_SANDBOX'}
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              ABDM Milestone 1 Scan &amp; Share desk poster. Patients scan with any ABHA PHR app to share verified
              demographics without manual data entry.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
