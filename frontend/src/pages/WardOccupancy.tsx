import { useEffect, useState } from 'react';
import { Bed, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { wardsApi } from '../services/api';
import { wardLabels } from '../types';
import type { BedItem, WardOccupancyStats, WardType } from '../types';

const bedStatuses: Record<BedItem['status'], { label: string; style: string }> = {
  AVAILABLE: { label: 'Available', style: 'bg-emerald-50 text-emerald-800' },
  OCCUPIED: { label: 'Occupied', style: 'bg-blue-50 text-blue-800' },
  MAINTENANCE: { label: 'Maintenance', style: 'bg-amber-50 text-amber-800' },
  RESERVED: { label: 'Reserved', style: 'bg-violet-50 text-violet-800' },
};

type InventoryState =
  | { status: 'loading' | 'error' }
  | { status: 'loaded'; inventory: WardOccupancyStats };

export const WardOccupancy = () => {
  const { user } = useAuth();
  const [state, setState] = useState<InventoryState>({ status: 'loading' });
  const [refresh, setRefresh] = useState(0);
  const [filter, setFilter] = useState<WardType | 'ALL'>('ALL');

  useEffect(() => {
    const controller = new AbortController();
    wardsApi.getOccupancy(controller.signal).then(inventory => {
      if (controller.signal.aborted) return;
      if (!Array.isArray(inventory?.wards)) {
        setState({ status: 'error' });
        return;
      }
      setState({ status: 'loaded', inventory });
    }).catch(() => {
      if (!controller.signal.aborted) setState({ status: 'error' });
    });
    return () => controller.abort();
  }, [refresh]);

  function refreshInventory() {
    setState({ status: 'loading' });
    setRefresh(previous => previous + 1);
  }

  const inventory = state.status === 'loaded' ? state.inventory : null;
  const wardTypes = [...new Set(inventory?.wards.map(ward => ward.ward_type))];
  const selectedType = filter !== 'ALL' && wardTypes.includes(filter) ? filter : 'ALL';
  const visibleWards = inventory?.wards.filter(ward => selectedType === 'ALL' || ward.ward_type === selectedType);
  const census = inventory ? [
    { label: 'Total beds', value: inventory.total_beds },
    { label: 'Available', value: inventory.available },
    { label: 'Occupied', value: inventory.occupied },
    { label: 'Maintenance', value: inventory.maintenance },
    { label: 'Reserved', value: inventory.reserved },
  ] : [];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-slate-900 p-6 text-white">
        <div>
          <h1 className="text-2xl font-bold">Inpatient Ward &amp; Bed Occupancy Matrix</h1>
          {inventory && (
            <p className="mt-1 text-sm text-slate-300">Hospital occupancy {inventory.occupancy_rate}%</p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {user?.role === 'HOSPITAL_ADMIN' && (
            <Link to="/wards/setup" className="rounded-lg bg-white px-3 py-2 text-sm font-medium text-slate-900">
              Ward and bed setup
            </Link>
          )}
          <button
            type="button"
            onClick={refreshInventory}
            disabled={state.status === 'loading'}
            className="flex items-center gap-2 rounded-lg border border-slate-500 px-3 py-2 text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" /> Refresh beds
          </button>
        </div>
      </header>

      {state.status === 'loading' && <p role="status" className="text-sm text-slate-600">Loading bed inventory…</p>}
      {state.status === 'error' && (
        <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          Bed inventory could not be loaded. Use Refresh beds to try again.
        </p>
      )}
      {inventory && (
        <>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {census.map(({ label, value }) => (
              <div key={label} className="rounded-xl border border-slate-200 bg-white p-4">
                <dt className="text-sm text-slate-600">{label}</dt>
                <dd className="text-2xl font-bold text-slate-900">{value}</dd>
              </div>
            ))}
          </dl>

          {inventory.total_beds === 0 ? (
            <p className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-700">
              No beds have been configured for this hospital.
            </p>
          ) : (
            <>
              <label className="flex flex-wrap items-center gap-2 text-sm font-medium text-slate-700">
                Ward type
                <select
                  value={selectedType}
                  onChange={event => setFilter(event.target.value as WardType | 'ALL')}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-2"
                >
                  <option value="ALL">All hospital wards</option>
                  {wardTypes.map(type => <option key={type} value={type}>{wardLabels[type]}</option>)}
                </select>
              </label>

              {visibleWards?.map(ward => (
                <section key={ward.id} className="space-y-3">
                  <div>
                    <h2 className="text-lg font-semibold text-slate-900">{ward.name}</h2>
                    <p className="text-sm text-slate-600">{wardLabels[ward.ward_type]} · Floor {ward.floor}</p>
                  </div>
                  {ward.beds.length === 0 && <p className="text-sm text-slate-600">No beds in this ward.</p>}
                  <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {ward.beds.map(bed => (
                      <li key={bed.id} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4">
                        <Bed className="h-5 w-5 shrink-0 text-slate-500" aria-hidden="true" />
                        <span className="font-semibold text-slate-900">{bed.bed_number}</span>
                        <span className={`ml-auto rounded-full px-2 py-1 text-xs font-medium ${bedStatuses[bed.status].style}`}>
                          {bedStatuses[bed.status].label}
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </>
          )}
        </>
      )}
    </div>
  );
};
