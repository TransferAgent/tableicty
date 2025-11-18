import { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';

interface RenderWithProvidersOptions extends Omit<RenderOptions, 'wrapper'> {
  initialRoute?: string;
}

export function renderWithProviders(
  ui: ReactElement,
  {
    initialRoute = '/',
    ...renderOptions
  }: RenderWithProvidersOptions = {}
) {
  const router = createMemoryRouter(
    [
      {
        path: '*',
        element: (
          <AuthProvider>
            {ui}
          </AuthProvider>
        ),
      },
    ],
    {
      initialEntries: [initialRoute],
    }
  );

  const result = render(<RouterProvider router={router} />, renderOptions);

  return {
    ...result,
    router,
  };
}

export * from '@testing-library/react';
