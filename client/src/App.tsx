import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './contexts/AuthContext';
import { TenantProvider } from './contexts/TenantContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { DashboardLayout } from './components/dashboard/DashboardLayout';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { ProfilePage } from './pages/ProfilePage';
import { TransactionsPage } from './pages/TransactionsPage';
import { TaxDocumentsPage } from './pages/TaxDocumentsPage';
import { CertificatesPage } from './pages/CertificatesPage';
import { SecurityPage } from './pages/SecurityPage';
import { AdminPage } from './pages/AdminPage';
import BillingPage from './pages/BillingPage';
import { ErrorBoundary } from './components/ErrorBoundary';
import { TenantOnboarding } from './components/tenant/TenantOnboarding';

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <TenantProvider>
            <Toaster position="top-right" />
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/onboarding" element={<TenantOnboarding />} />
              
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <DashboardLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<DashboardPage />} />
                <Route path="profile" element={<ProfilePage />} />
                <Route path="security" element={<SecurityPage />} />
                <Route path="transactions" element={<TransactionsPage />} />
                <Route path="tax-documents" element={<TaxDocumentsPage />} />
                <Route path="certificates" element={<CertificatesPage />} />
                <Route path="admin" element={<AdminPage />} />
                <Route path="billing" element={<BillingPage />} />
              </Route>
            </Routes>
          </TenantProvider>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
