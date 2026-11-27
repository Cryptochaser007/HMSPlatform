import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Printer, X } from 'lucide-react';
import { patientsApi } from '../../services/api';
import type { PrescriptionItem } from '../../types';

interface DigitalRxModalProps {
  onClose: () => void;
  patientId: string;
  doctorName?: string;
  department: string;
  diagnosis: string;
  prescriptions: PrescriptionItem[];
}

type PatientLookup =
  | { status: 'loading' | 'unavailable' }
  | { status: 'verified'; name: string; uhid: string };

export const DigitalRxModal = ({
  onClose, patientId, doctorName, department, diagnosis, prescriptions,
}: DigitalRxModalProps) => {
  const [lookup, setLookup] = useState<PatientLookup>({ status: 'loading' });

  useEffect(() => {
    let open = true;

    async function verifyPatient() {
      try {
        const patient = await patientsApi.get(patientId);
        const firstName = patient?.first_name?.trim();
        const lastName = patient?.last_name?.trim();
        const uhid = patient?.registration_number?.trim();
        if (!open) return;
        if (patient?.id === patientId && firstName && lastName && uhid) {
          setLookup({ status: 'verified', name: firstName + ' ' + lastName, uhid });
          return;
        }
      } catch {
        // Keep printing blocked if the patient cannot be retrieved.
      }
      if (open) setLookup({ status: 'unavailable' });
    }

    void verifyPatient();
    return () => { open = false; };
  }, [patientId]);

  function printPrescription() {
    if (lookup.status === 'verified') window.print();
  }

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="rx-preview-title"
      className="rx-preview fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-900/60 p-4 print:static print:block print:overflow-visible print:bg-white print:p-0"
    >
      <style media="print">{'body > :not(.rx-preview) { display: none !important; }'}</style>
      <div className="w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-xl print:max-w-none print:overflow-visible print:rounded-none print:shadow-none">
        <div className="flex items-center justify-between bg-slate-900 p-4 text-white print:hidden">
          <h2 id="rx-preview-title" className="text-sm font-bold">Prescription Preview</h2>
          <button type="button" onClick={onClose} aria-label="Close prescription preview">
            <X className="h-4 w-4" />
          </button>
        </div>

        {lookup.status === 'loading' && (
          <p role="status" className="p-6 text-sm text-slate-600 print:hidden">Verifying the selected patient…</p>
        )}
        {lookup.status === 'unavailable' && (
          <p role="alert" className="p-6 text-sm text-rose-700 print:hidden">
            The selected patient could not be verified. Printing is unavailable.
          </p>
        )}
        {lookup.status === 'verified' && (
          <article id="printable-rx" className="max-h-[65vh] space-y-6 overflow-y-auto p-6 print:max-h-none print:overflow-visible">
            <header className="border-b border-slate-800 pb-4">
              <h3 className="text-xl font-bold text-slate-900">Draft Prescription</h3>
              <p className="text-sm text-slate-600">{department}</p>
              {doctorName && <p className="text-sm text-slate-600">Prepared by {doctorName}</p>}
            </header>

            <dl className="grid grid-cols-2 gap-3 rounded-lg border border-slate-200 p-3 text-sm">
              <div>
                <dt className="text-slate-600">Patient Name</dt>
                <dd className="font-bold text-slate-900">{lookup.name}</dd>
              </div>
              <div>
                <dt className="text-slate-600">UHID</dt>
                <dd className="font-mono font-bold text-slate-900">{lookup.uhid}</dd>
              </div>
            </dl>

            {diagnosis && (
              <section>
                <h4 className="mb-1 text-sm font-bold text-slate-700">Provisional Clinical Diagnosis</h4>
                <p className="text-sm text-slate-900">{diagnosis}</p>
              </section>
            )}

            <section>
              <h4 className="mb-2 text-sm font-bold text-slate-700">Prescribed Medications (Rx)</h4>
              <table className="w-full border-collapse text-left text-xs">
                <thead className="border-b border-slate-200">
                  <tr>
                    <th className="p-2">Drug &amp; Formulation</th>
                    <th className="p-2">Dosage</th>
                    <th className="p-2">Frequency</th>
                    <th className="p-2">Duration</th>
                    <th className="p-2">Instructions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {prescriptions.map((item, index) => (
                    <tr key={index} className="print:break-inside-avoid">
                      <td className="p-2 font-bold">{item.drug_name}</td>
                      <td className="p-2">{item.dosage}</td>
                      <td className="p-2">{item.frequency}</td>
                      <td className="p-2">{item.duration_days} days</td>
                      <td className="p-2">{item.instructions}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </article>
        )}

        <div className="flex justify-end gap-2 border-t border-slate-200 bg-slate-50 p-4 print:hidden">
          <button
            type="button"
            onClick={printPrescription}
            disabled={lookup.status !== 'verified'}
            className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-bold disabled:opacity-50"
          >
            <Printer className="h-4 w-4" /> Print Prescription
          </button>
          <button type="button" onClick={onClose} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-bold text-white">
            Close
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
};
