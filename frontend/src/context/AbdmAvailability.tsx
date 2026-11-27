import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { abdmApi } from '../services/api';

const AbdmAvailability = createContext(false);

export const ABHA_UNAVAILABLE = 'ABHA integration is unavailable in this pilot.';

export function AbdmAvailabilityProvider({ children }: { children: ReactNode }) {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    let current = true;
    abdmApi.getStatus().then(status => {
      if (current) setEnabled(status?.integration_enabled === true);
    }).catch(() => {
      if (current) setEnabled(false);
    });
    return () => { current = false; };
  }, []);

  return <AbdmAvailability.Provider value={enabled}>{children}</AbdmAvailability.Provider>;
}

export const useAbdmEnabled = () => useContext(AbdmAvailability);
