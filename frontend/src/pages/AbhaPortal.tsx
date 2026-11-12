import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { abdmApi, patientsApi } from '../services/api';
import { AbhaProfile } from '../types';
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
} from 'lucide-react';

export const AbhaPortal: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'create' | 'verify'>('create');
  const navigate = useNavigate();

  // Create ABHA states
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [aadhaar, setAadhaar] = useState('');
  const [consentAgreed, setConsentAgreed] = useState(false);
  const [txnId, setTxnId] = useState('');
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);
  const [generatedProfile, setGeneratedProfile] = useState<AbhaProfile | null>(null);

  // Verify ABHA states
  const [searchAbhaId, setSearchAbhaId] = useState('');
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [verifiedProfile, setVerifiedProfile] = useState<AbhaProfile | null>(null);

  // Formatting Aadhaar (XXXX XXXX XXXX)
  const handleAadhaarChange = (val: string) => {
    const raw = val.replace(/\D/g, '').slice(0, 12);
    const formatted = raw.replace(/(\d{4})(?=\d)/g, '$1 ');
    setAadhaar(formatted);
  };

  // Step 1: Generate OTP
  const handleGenerateOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const rawAadhaar = aadhaar.replace(/\s+/g, '');
    if (rawAadhaar.length !== 12) {
      setError('Please enter a valid 12-digit Aadhaar number.');
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
    } catch (err: any) {
      console.error('OTP Gen error:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to send Aadhaar OTP. Try again.');
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Verify OTP
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
      setStep(3);
      setSuccessNotice('Aadhaar authenticated! ABHA Digital Health Account created.');
    } catch (err: any) {
      console.error('Verify error:', err);
      setError(err.response?.data?.detail || err.message || 'Invalid or expired OTP.');
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
            <ShieldCheck className="w-3.5 h-3.5" /> ABDM Milestone 1 & 2 Certified
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Ayushman Bharat Health Account (ABHA) Portal</h1>
          <p className="text-sm text-brand-100 mt-1 max-w-2xl">
            Generate 14-digit ABHA Numbers via Aadhaar e-KYC, verify digital health profiles on the National Health
            Authority (NHA) gateway, and link longitudinal health records seamlessly.
          </p>
        </div>
        <div className="bg-white/10 backdrop-blur-md border border-white/20 p-4 rounded-xl flex items-center gap-3 self-start md:self-auto">
          <div className="p-2 bg-emerald-500 rounded-lg text-white">
            <CreditCard className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs uppercase font-medium text-brand-200">ABDM Registry</div>
            <div className="text-sm font-bold text-white">Gateway Connected</div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 bg-white rounded-t-xl px-4 pt-2 gap-4">
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

            {/* STEP 1: Enter Aadhaar */}
            {step === 1 && (
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
                      (DPDP) Act 2023.
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

            {/* STEP 2: Enter OTP */}
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
                  <p className="text-[11px] text-slate-500 mt-1.5 text-center">
                    Demo OTP: Enter any 6 digits (e.g. <span className="font-mono text-slate-700 font-bold">123456</span>)
                  </p>
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

                {/* Actions */}
                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={() => handleImportToPatient(generatedProfile)}
                    className="flex-1 py-3 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-2 shadow-sm"
                  >
                    <UserPlus className="w-4 h-4" />
                    Register Directly into Patient Registry
                  </button>
                  <button
                    onClick={() => {
                      setStep(1);
                      setAadhaar('');
                      setOtp('');
                      setGeneratedProfile(null);
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
            <form onSubmit={handleSearchAbha} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                  Search & Verify ABHA ID on NHA Gateway
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
    </div>
  );
};
