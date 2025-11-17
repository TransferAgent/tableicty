import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { apiClient } from '../api/client';
import type { User, LoginCredentials, RegisterData } from '../types';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    try {
      apiClient.loadTokens();
      const tokens = apiClient.getTokens();
      
      if (tokens.access) {
        const userData = await apiClient.getCurrentUser();
        setUser(userData);
      }
    } catch (error) {
      console.error('Failed to load user:', error);
      apiClient.clearTokens();
    } finally {
      setLoading(false);
    }
  };

  const login = async (credentials: LoginCredentials) => {
    await apiClient.login(credentials);
    const userData = await apiClient.getCurrentUser();
    setUser(userData);
  };

  const register = async (data: RegisterData) => {
    await apiClient.register(data);
    const userData = await apiClient.getCurrentUser();
    setUser(userData);
  };

  const logout = async () => {
    await apiClient.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
