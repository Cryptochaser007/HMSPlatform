import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Layout } from './components/layout/Layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Patients } from './pages/Patients';
import { Queue } from './pages/Queue';
import { DoctorEMR } from './pages/DoctorEMR';
import { AbhaPortal } from './pages/AbhaPortal';
import { RBACMatrix } from './pages/RBACMatrix';
import { WardOccupancy } from './pages/WardOccupancy';
import { ModulePortal } from './pages/ModulePortal';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col justify-center items-center">
        <div className="animate-spin rounded-full h-8 w-8 border-3 border-brand-600 border-t-transparent mb-3" />
        <div className="text-xs font-semibold text-slate-500">Loading Clinical Session...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="abha" element={<AbhaPortal />} />
            <Route path="patients" element={<Patients />} />
            <Route path="queue" element={<Queue />} />
            <Route path="emr" element={<DoctorEMR />} />
            <Route path="wards" element={<WardOccupancy />} />
            <Route path="rbac" element={<RBACMatrix />} />
            <Route path="patient-portal" element={<ModulePortal title="Patient Portal" description="Patient appointments, records, consent and care updates." />} />
            <Route path="admin" element={<ModulePortal title="Administration" description="Hospital configuration, staff access and registry management." />} />
            <Route path="billing" element={<ModulePortal title="Billing & Insurance" description="Billing, pre-authorization and claim lifecycle." endpoint="/insurance/claims" />} />
            <Route path="pharmacy" element={<ModulePortal title="Pharmacy" description="Medication dispensing and pharmacy operations." endpoint="/pharmacy/drugs" />} />
            <Route path="laboratory" element={<ModulePortal title="Laboratory" description="Laboratory orders, results and verification." endpoint="/lab/tests" />} />
            <Route path="radiology" element={<ModulePortal title="Radiology" description="Imaging orders, reports and review." endpoint="/radiology/orders" />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
