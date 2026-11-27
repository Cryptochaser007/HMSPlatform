import { isAxiosError } from 'axios';
import { useEffect, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { wardsApi } from '../services/api';
import { wardLabels } from '../types';
import type { WardSetupStatus, WardSetupWard, WardType } from '../types';

type SetupState = WardSetupStatus['status'] | 'loading' | 'error';
type WardDraft = Omit<WardSetupWard, 'floor' | 'total_beds'> & {
  key: number;
  floor: string;
  total_beds: string;
};

const newWard = (key: number): WardDraft => ({
  key, name: '', ward_type: 'GENERAL', floor: '0', total_beds: '1',
});

function useWardSetupStatus(enabled: boolean): SetupState {
  const [status, setStatus] = useState<SetupState>('loading');

  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    wardsApi.getSetup(controller.signal).then(result => {
      if (!controller.signal.aborted) setStatus(result.status);
    }).catch(() => {
      if (!controller.signal.aborted) setStatus('error');
    });
    return () => controller.abort();
  }, [enabled]);

  return status;
}

export const WardSetupOnboarding = ({ children }: { children: ReactNode }) => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'HOSPITAL_ADMIN';
  const status = useWardSetupStatus(isAdmin);

  if (isAdmin && status === 'loading') return <p role="status">Checking ward setup…</p>;
  if (isAdmin && status === 'pending') return <Navigate to="/wards/setup" replace />;
  return children;
};

export const WardSetup = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'HOSPITAL_ADMIN';
  const status = useWardSetupStatus(isAdmin);
  const navigate = useNavigate();
  const nextKey = useRef(1);
  const [wards, setWards] = useState<WardDraft[]>([newWard(0)]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const totalBeds = wards.reduce((total, ward) => total + Number(ward.total_beds), 0);

  function updateWard(key: number, changes: Partial<Omit<WardDraft, 'key'>>) {
    setWards(current => current.map(ward => ward.key === key ? { ...ward, ...changes } : ward));
  }

  async function save(mode: 'INPATIENT' | 'OPD_ONLY') {
    const inventory = mode === 'OPD_ONLY' ? [] : wards.map(ward => ({
      name: ward.name.trim(),
      ward_type: ward.ward_type,
      floor: Number(ward.floor),
      total_beds: Number(ward.total_beds),
    }));
    setError('');
    if (mode === 'INPATIENT') {
      const names = inventory.map(ward => ward.name.toLowerCase());
      if (names.some(name => !name) || names.length !== new Set(names).size) {
        setError('Give each ward a distinct name.');
        return;
      }
      if (totalBeds > 1000) {
        setError('Set up at most 1,000 beds at a time.');
        return;
      }
    }
    setSaving(true);
    try {
      await wardsApi.saveSetup(mode, inventory);
      navigate(mode === 'OPD_ONLY' ? '/' : '/wards', { replace: true });
    } catch (failure) {
      const detail = isAxiosError(failure) ? failure.response?.data?.detail : undefined;
      setError(typeof detail === 'string' ? detail : 'Ward and bed setup could not be saved. Check your entries and try again.');
    } finally {
      setSaving(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void save('INPATIENT');
  }

  if (!isAdmin) return <Navigate to="/wards" replace />;

  return (
    <section className="max-w-4xl space-y-5">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Set up wards and beds</h1>
        <p className="mt-1 text-sm text-slate-600">
          Add each inpatient ward and its bed count. The beds will appear in your hospital’s beds matrix.
        </p>
      </header>

      {status === 'loading' && <p role="status">Checking ward setup…</p>}
      {status === 'error' && <p role="alert">Could not check ward setup. Refresh this page to try again.</p>}
      {status === 'configured' && (
        <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-5">
          <p>Wards and beds are already configured for this hospital.</p>
          <Link to="/wards" className="font-semibold text-brand-700">View beds matrix</Link>
        </div>
      )}
      {(status === 'pending' || status === 'skipped') && (
        <>
          {status === 'skipped' && (
            <p className="rounded-lg bg-slate-100 p-3 text-sm">This facility is set up for OPD only. Add wards below if you now offer inpatient care.</p>
          )}
          <form onSubmit={submit}>
            <fieldset disabled={saving} className="space-y-4">
              {wards.map((ward, index) => {
                const prefix = Array.from(ward.name.trim()).slice(0, 3).join('').toUpperCase();
                const count = Number(ward.total_beds);
                const example = prefix && ward.floor && Number.isInteger(count) && count > 0
                  ? `${prefix}-${Number(ward.floor)}01${count > 1 ? ` to ${prefix}-${Number(ward.floor)}${String(count).padStart(2, '0')}` : ''}`
                  : '';
                return (
                  <fieldset key={ward.key} className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
                    <legend className="px-1 text-sm font-semibold text-slate-700">Ward {index + 1}</legend>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      <label className="space-y-1 text-sm">Ward name
                        <input required maxLength={100} value={ward.name} placeholder="e.g. General East"
                          onChange={event => updateWard(ward.key, { name: event.target.value })}
                          className="block w-full rounded-lg border border-slate-300 px-3 py-2" />
                      </label>
                      <label className="space-y-1 text-sm">Ward type
                        <select value={ward.ward_type} onChange={event => updateWard(ward.key, { ward_type: event.target.value as WardType })}
                          className="block w-full rounded-lg border border-slate-300 px-3 py-2">
                          {Object.entries(wardLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                        </select>
                      </label>
                      <label className="space-y-1 text-sm">Floor
                        <input type="number" required min={-10} max={100} value={ward.floor}
                          onChange={event => updateWard(ward.key, { floor: event.target.value })}
                          className="block w-full rounded-lg border border-slate-300 px-3 py-2" />
                      </label>
                      <label className="space-y-1 text-sm">Number of beds
                        <input type="number" required min={1} max={500} value={ward.total_beds}
                          onChange={event => updateWard(ward.key, { total_beds: event.target.value })}
                          className="block w-full rounded-lg border border-slate-300 px-3 py-2" />
                      </label>
                    </div>
                    <div className="flex min-h-5 justify-between gap-3 text-sm text-slate-600">
                      <span>{example && <>Bed labels <strong>{example}</strong></>}</span>
                      {wards.length > 1 && (
                        <button type="button" className="text-rose-700" aria-label={`Remove ward ${index + 1}`}
                          onClick={() => setWards(current => current.filter(row => row.key !== ward.key))}>Remove</button>
                      )}
                    </div>
                  </fieldset>
                );
              })}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <button type="button" disabled={wards.length >= 50} className="font-semibold text-brand-700 disabled:opacity-50"
                  onClick={() => {
                    const ward = newWard(nextKey.current++);
                    setWards(current => [...current, ward]);
                  }}>Add another ward</button>
                <strong aria-live="polite">Total beds {totalBeds}</strong>
              </div>
              {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
              <div className="flex flex-wrap gap-3">
                <button type="submit" className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
                  {saving ? 'Saving…' : 'Save wards and beds'}
                </button>
                {status === 'pending' && (
                  <button type="button" onClick={() => void save('OPD_ONLY')}
                    className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold disabled:opacity-50">
                    Skip for now (OPD only)
                  </button>
                )}
              </div>
            </fieldset>
          </form>
        </>
      )}
      <Link to="/queue" className="inline-block text-sm font-semibold text-brand-700">Continue to OPD queue</Link>
    </section>
  );
};
