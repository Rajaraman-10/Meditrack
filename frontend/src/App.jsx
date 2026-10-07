import { lazy, Suspense, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/useAuth'
import ProtectedRoute from './components/ProtectedRoute'
import RoleRoute from './components/RoleRoute'
import AccountPage from './pages/AccountPage'
import AppointmentsPage from './pages/AppointmentsPage'
import ClinicPage from './pages/ClinicPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import PatientsPage from './pages/PatientsPage'
import RegisterPage from './pages/RegisterPage'
import SetupPage from './pages/SetupPage'
import './App.css'

const AuditPage = lazy(() => import('./pages/AuditPage'))
const BillingPage = lazy(() => import('./pages/BillingPage'))
const InvoicePrintPage = lazy(() => import('./pages/InvoicePrintPage'))
const StaffManagementPage = lazy(() => import('./pages/StaffManagementPage'))
const DepartmentManagementPage = lazy(() => import('./pages/DepartmentManagementPage'))
const ConsultationsPage = lazy(() => import('./pages/ConsultationsPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const DoctorDashboardPage = lazy(() => import('./pages/DoctorDashboardPage'))
const DoctorPatientRecordPage = lazy(() => import('./pages/DoctorPatientRecordPage'))
const DocumentsPage = lazy(() => import('./pages/DocumentsPage'))
const LaboratoryPage = lazy(() => import('./pages/LaboratoryPage'))
const NotificationsPage = lazy(() => import('./pages/NotificationsPage'))
const PrescriptionsPage = lazy(() => import('./pages/PrescriptionsPage'))
const PrescriptionPrintPage = lazy(() => import('./pages/PrescriptionPrintPage'))

function App() {
  const { user, logout } = useAuth()
  const [logoutError, setLogoutError] = useState('')

  async function handleSignOut() {
    setLogoutError('')
    try {
      await logout()
    } catch {
      setLogoutError('Signed out on this device, but the server could not revoke the refresh token.')
    }
  }

  return (
    <div className="app-shell">
      <header className={`topbar${user ? ' topbar-authenticated' : ''}`}>
        <NavLink className="brand" to="/">
          <span className="brand-mark" aria-hidden="true">M</span>
          <span>MediTrack</span>
        </NavLink>
        <nav aria-label="Main navigation">
          <NavLink end to="/">Overview</NavLink>
          {user ? (
            <>
              {user.role === 'billing' ? (
                <>
                  <NavLink to="/billing/dashboard">Dashboard</NavLink>
                  <NavLink to="/billing#invoices">Invoices</NavLink>
                  <NavLink to="/billing#payment-history">Payments</NavLink>
                  <NavLink to="/billing#pending-payments">Pending payments</NavLink>
                  <NavLink to="/billing#pending-prescriptions">Pending prescriptions</NavLink>
                  <NavLink to="/billing#payment-history">Payment history</NavLink>
                </>
              ) : user.role === 'receptionist' ? (
                <>
                  <NavLink to="/receptionist/dashboard">Dashboard</NavLink>
                  <NavLink to="/patients">Patients</NavLink>
                  <NavLink to="/appointments">Appointments</NavLink>
                  <NavLink to="/clinic">Doctors</NavLink>
                  <NavLink to="/appointments#queue">Queue</NavLink>
                  <NavLink to="/billing">Billing</NavLink>
                  <NavLink to="/notifications">Notifications</NavLink>
                  <NavLink to="/account">Profile</NavLink>
                </>
              ) : (
                <>
                  {(user.role === 'admin' || user.role === 'receptionist' || user.role === 'patient') && <NavLink to="/patients">{user.role === 'patient' ? 'My profile' : 'Patients'}</NavLink>}
                  {(user.role === 'admin' || user.role === 'receptionist' || user.role === 'doctor' || user.role === 'patient') && <NavLink to="/clinic">{user.role === 'patient' ? 'Doctors' : user.role === 'doctor' ? 'My availability' : 'Clinic'}</NavLink>}
                  <NavLink to={`/${user.role}/dashboard`}>Dashboard</NavLink>
                  <NavLink to="/appointments">Appointments</NavLink>
                  {(user.role === 'admin' || user.role === 'doctor' || user.role === 'patient') && <NavLink to="/consultations">Consultations</NavLink>}
                  {(user.role === 'admin' || user.role === 'doctor' || user.role === 'patient') && <NavLink to="/prescriptions">Prescriptions</NavLink>}
                  {(user.role === 'admin' || user.role === 'doctor' || user.role === 'patient') && <NavLink to="/laboratory">Laboratory</NavLink>}
                  {(user.role === 'admin' || user.role === 'doctor' || user.role === 'receptionist' || user.role === 'patient') && <NavLink to="/documents">Documents</NavLink>}
                  {(user.role === 'admin' || user.role === 'receptionist' || user.role === 'patient') && <NavLink to="/billing">Billing</NavLink>}
                  {user.role === 'admin' && <NavLink to="/admin/staff">Staff management</NavLink>}
                  {user.role === 'admin' && <NavLink to="/admin/departments">Departments</NavLink>}
                </>
              )}
              <NavLink to="/notifications">Notifications</NavLink>
              {user.role === 'admin' && <NavLink to="/audit">Activity</NavLink>}
              <NavLink to="/account">Account</NavLink>
              <button className="nav-button" onClick={handleSignOut}>Sign out</button>
            </>
          ) : (
            <>
              <NavLink to="/setup">How it works</NavLink>
              <NavLink to="/login">Sign in</NavLink>
              <NavLink to="/register">Register</NavLink>
            </>
          )}
        </nav>
      </header>
      {logoutError && <p className="logout-notice" role="alert">{logoutError}</p>}

      <main className="page-content">
        <Suspense fallback={<p className="route-message" role="status">Loading workspace…</p>}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/setup" element={<SetupPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/account" element={<AccountPage />} />
            <Route path="/appointments" element={<AppointmentsPage />} />
            <Route element={<RoleRoute allowedRoles={['admin', 'receptionist', 'patient']} />}>
              <Route path="/dashboard" element={<DashboardPage />} />
            </Route>
            <Route element={<RoleRoute allowedRoles={['admin']} />}>
              <Route path="/admin" element={<DashboardPage />} />
              <Route path="/admin/dashboard" element={<DashboardPage />} />
              <Route path="/admin/staff" element={<StaffManagementPage />} />
              <Route path="/admin/departments" element={<DepartmentManagementPage />} />
            </Route>
            <Route element={<RoleRoute allowedRoles={['doctor']} />}>
              <Route path="/doctor" element={<DoctorDashboardPage />} />
              <Route path="/doctor/dashboard" element={<DoctorDashboardPage />} />
              <Route path="/doctor/patients/:patientId" element={<DoctorPatientRecordPage />} />
            </Route>
            <Route element={<RoleRoute allowedRoles={['receptionist']} />}>
              <Route path="/receptionist" element={<DashboardPage />} />
              <Route path="/receptionist/dashboard" element={<DashboardPage />} />
            </Route>
            <Route element={<RoleRoute allowedRoles={['billing']} />}>
              <Route path="/billing/dashboard" element={<BillingPage />} />
            </Route>
            <Route element={<RoleRoute allowedRoles={['patient']} />}>
              <Route path="/patient" element={<DashboardPage />} />
              <Route path="/patient/dashboard" element={<DashboardPage />} />
            </Route>
            <Route path="/notifications" element={<NotificationsPage />} />
            <Route path="/clinic" element={<ClinicPage />} />
            <Route element={<RoleRoute allowedRoles={['admin', 'receptionist', 'patient']} />}>
              <Route path="/patients" element={<PatientsPage />} />
            </Route>
            <Route element={<RoleRoute allowedRoles={['admin', 'doctor', 'patient']} />}>
              <Route path="/consultations" element={<ConsultationsPage />} />
              <Route path="/prescriptions" element={<PrescriptionsPage />} />
              <Route path="/laboratory" element={<LaboratoryPage />} />
            </Route>
            <Route element={<RoleRoute allowedRoles={['admin', 'doctor', 'billing', 'patient']} />}>
              <Route path="/prescriptions/:prescriptionId/print" element={<PrescriptionPrintPage />} />
            </Route>
            <Route element={<RoleRoute allowedRoles={['admin', 'doctor', 'receptionist', 'patient']} />}>
              <Route path="/documents" element={<DocumentsPage />} />
            </Route>
            <Route element={<RoleRoute allowedRoles={['admin', 'receptionist', 'billing', 'patient']} />}>
              <Route path="/billing" element={<BillingPage />} />
              <Route path="/billing/:invoiceId/print" element={<InvoicePrintPage />} />
            </Route>
            <Route element={<RoleRoute allowedRoles={['admin']} />}>
              <Route path="/audit" element={<AuditPage />} />
            </Route>
          </Route>
          <Route path="*" element={<section className="panel"><h1>Page not found</h1><p>Use the navigation above to return to MediTrack.</p></section>} />
        </Routes>
        </Suspense>
      </main>

      <footer className="footer">MediTrack · Clinic operations</footer>
    </div>
  )
}

export default App
