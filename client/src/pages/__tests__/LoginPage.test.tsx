import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../test/test-utils';
import { LoginPage } from '../LoginPage';
import { apiClient } from '../../api/client';

vi.mock('../../api/client', () => ({
  apiClient: {
    login: vi.fn(),
    getCurrentUser: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    loadTokens: vi.fn(),
    getTokens: vi.fn(() => ({ access: null, refresh: null })),
    clearTokens: vi.fn(),
  },
}));

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders login form', () => {
    renderWithProviders(<LoginPage />);
    
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('shows validation errors for empty fields', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);
    
    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /sign in/i });
    
    await user.clear(emailInput);
    await user.clear(passwordInput);
    await user.click(loginButton);
    
    expect(emailInput).toBeInvalid();
    expect(passwordInput).toBeInvalid();
  });

  it('handles successful login and redirects to dashboard', async () => {
    const user = userEvent.setup();
    const mockUser = {
      id: 123,
      email: 'test@example.com',
      first_name: 'John',
      last_name: 'Doe',
    };

    vi.mocked(apiClient.login).mockResolvedValue(undefined);
    vi.mocked(apiClient.getCurrentUser).mockResolvedValue(mockUser);

    const { router } = renderWithProviders(<LoginPage />);
    
    await user.type(screen.getByLabelText(/email address/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    
    await waitFor(() => {
      expect(apiClient.login).toHaveBeenCalledWith({
        username: 'test@example.com',
        password: 'password123'
      });
    });
    
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/dashboard');
    });
  });

  it('shows error message on failed login', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.login).mockRejectedValue({
      response: { data: { detail: 'Invalid credentials' } }
    });

    renderWithProviders(<LoginPage />);
    
    await user.type(screen.getByLabelText(/email address/i), 'wrong@example.com');
    await user.type(screen.getByLabelText(/password/i), 'wrongpass');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    
    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
    });
  });

  it('navigates to registration page when clicking register link', async () => {
    const user = userEvent.setup();
    const { router } = renderWithProviders(<LoginPage />);
    
    const registerLink = screen.getByText(/register here/i);
    await user.click(registerLink);
    
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/register');
    });
  });

  it('disables submit button while loading', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.login).mockImplementation(() => 
      new Promise(resolve => setTimeout(resolve, 1000))
    );

    renderWithProviders(<LoginPage />);
    
    await user.type(screen.getByLabelText(/email address/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    await user.click(submitButton);
    
    await waitFor(() => {
      expect(submitButton).toBeDisabled();
      expect(screen.getByText(/signing in/i)).toBeInTheDocument();
    });
  });
});
