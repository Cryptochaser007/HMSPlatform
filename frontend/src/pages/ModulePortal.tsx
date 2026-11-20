import React, { useEffect, useState } from 'react';
import api from '../services/api';

type ModuleItem = Record<string, unknown>;

export const ModulePortal: React.FC<{ title: string; description: string; endpoint?: string }> = ({ title, description, endpoint }) => {
  const [items, setItems] = useState<ModuleItem[]>([]);
  const [loading, setLoading] = useState(!!endpoint);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!endpoint) return;
    let active = true;
    setLoading(true);
    api.get(endpoint).then(({ data }) => {
      if (!active) return;
      const rows = Array.isArray(data) ? data : (data.items || []);
      setItems(rows as ModuleItem[]);
      setError('');
    }).catch(() => { if (active) setError('Could not load this module. Check your access and try again.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [endpoint]);

  return (
    <section className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
        <p className="mt-2 text-sm text-slate-600">{description}</p>
      </header>
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-800">{endpoint ? `Recent ${title.toLowerCase()}` : 'Module workspace'}</h2>
        {loading && <p className="mt-3 text-sm text-slate-500">Loading records…</p>}
        {error && <p role="alert" className="mt-3 text-sm text-rose-700">{error}</p>}
        {!loading && !error && !endpoint && <p className="mt-2 text-sm text-slate-500">Choose a workflow from the hospital navigation to continue.</p>}
        {!loading && !error && endpoint && items.length === 0 && <p className="mt-3 text-sm text-slate-500">No records found.</p>}
        {items.length > 0 && <ul className="mt-4 divide-y divide-slate-100">
          {items.slice(0, 10).map((item, index) => <li key={String(item.id || index)} className="grid gap-1 py-3 sm:grid-cols-3">
            <span className="font-medium text-slate-800">{String(item.patient_name || item.full_name || item.name || item.claim_number || item.bill_number || item.id || `Record ${index + 1}`)}</span>
            <span className="text-sm text-slate-600">{String(item.status || item.lifecycle_status || item.payment_status || '')}</span>
            <span className="text-sm text-slate-500">{String(item.created_at || item.createdAt || '')}</span>
          </li>)}
        </ul>}
      </div>
    </section>
  );
};
