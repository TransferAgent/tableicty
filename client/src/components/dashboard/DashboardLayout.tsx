import { useState } from 'react';
import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useTenant } from '../../contexts/TenantContext';
import { LayoutDashboard, User, FileText, Receipt, FileCheck, LogOut, Shield, Settings, CreditCard, Menu, X, Users, PieChart } from 'lucide-react';

export function DashboardLayout() {
  const { user, logout } = useAuth();
  const { currentTenant, currentRole, isAdmin } = useTenant();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const navItems = [
    { path: '/dashboard', label: 'Portfolio', icon: LayoutDashboard },
    { path: '/dashboard/profile', label: 'Profile', icon: User },
    { path: '/dashboard/security', label: 'Security', icon: Shield },
    { path: '/dashboard/transactions', label: 'Transactions', icon: FileText },
    { path: '/dashboard/tax-documents', label: 'Tax Documents', icon: Receipt },
    { path: '/dashboard/certificates', label: 'Certificates', icon: FileCheck },
  ];

  if (isAdmin) {
    navItems.push({ path: '/dashboard/shareholders', label: 'Shareholders', icon: Users });
    navItems.push({ path: '/dashboard/cap-table', label: 'Cap Table', icon: PieChart });
    navItems.push({ path: '/dashboard/admin', label: 'Admin', icon: Settings });
    navItems.push({ path: '/dashboard/billing', label: 'Billing', icon: CreditCard });
  }

  const roleLabels: Record<string, string> = {
    'PLATFORM_ADMIN': 'Platform Admin',
    'TENANT_ADMIN': 'Admin',
    'TENANT_STAFF': 'Staff',
    'SHAREHOLDER': 'Shareholder',
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <Link to="/dashboard" className="text-xl font-bold text-indigo-600 hover:text-indigo-700 transition-colors">
                  tableicty
                </Link>
                {currentTenant && (
                  <div className="ml-4 flex items-center gap-2 pl-4 border-l border-gray-200">
                    <span className="text-sm font-medium text-gray-700">{currentTenant.name}</span>
                    {currentRole && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                        {roleLabels[currentRole] || currentRole}
                      </span>
                    )}
                  </div>
                )}
              </div>
              <div className="hidden md:ml-6 md:flex md:space-x-8">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-indigo-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`}
                    >
                      <Icon className="w-4 h-4 mr-2" />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
            <div className="flex items-center gap-3 flex-shrink-0">
              <span className="hidden lg:block text-sm text-gray-700 whitespace-nowrap">
                {user?.first_name} {user?.last_name}
              </span>
              <button
                onClick={handleLogout}
                className="hidden sm:inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 whitespace-nowrap"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </button>
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="md:hidden inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
              >
                {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="md:hidden border-t border-gray-200">
            <div className="pt-2 pb-3 space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center px-4 py-2 text-base font-medium ${
                      isActive
                        ? 'bg-indigo-50 border-l-4 border-indigo-500 text-indigo-700'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-800'
                    }`}
                  >
                    <Icon className="w-5 h-5 mr-3" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
            <div className="pt-4 pb-3 border-t border-gray-200">
              <div className="px-4 mb-3">
                <p className="text-sm font-medium text-gray-700">
                  {user?.first_name} {user?.last_name}
                </p>
                <p className="text-xs text-gray-500">{user?.email}</p>
              </div>
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleLogout();
                }}
                className="flex w-full items-center px-4 py-2 text-base font-medium text-red-600 hover:bg-red-50"
              >
                <LogOut className="w-5 h-5 mr-3" />
                Logout
              </button>
            </div>
          </div>
        )}
      </nav>
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
