import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useTenant } from '../../contexts/TenantContext';
import { LayoutDashboard, User, FileText, Receipt, FileCheck, LogOut, Shield, Settings, CreditCard } from 'lucide-react';

export function DashboardLayout() {
  const { user, logout } = useAuth();
  const { currentTenant, currentRole, isAdmin } = useTenant();
  const navigate = useNavigate();
  const location = useLocation();

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
                <h1 className="text-xl font-bold text-indigo-600">tableicty</h1>
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
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
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
            <div className="flex items-center">
              <div className="mr-4 text-sm text-gray-700">
                {user?.first_name} {user?.last_name}
              </div>
              <button
                onClick={handleLogout}
                className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
