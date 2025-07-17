import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation, Navigate } from 'react-router-dom';

import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import BackgroundRemovalPage from './pages/BackgroundRemovalPage';
import UpscalePage from './pages/UpscalePage';
import EnlargePage from './pages/EnlargePage';
import ObjectRemovalPage from './pages/ObjectRemovalPage';
import ImageGenerationPage from './pages/ImageGenerationPage';
import ResetPasswordPage from './pages/ResetPassword';
import AuthForm from './pages/AuthForm';
import EmailVerificationPage from './pages/EmailVerificationPage';
import BetaSignupPage from './pages/BetaSignupPage';

import { isAuthenticated, setupAxiosInterceptors, createGuestUser } from './services/authService';

const AppWrapper = () => {
  const location = useLocation();

  const [isInitializing, setIsInitializing] = useState(true);
  const [authChecked, setAuthChecked] = useState(false);
  const [isAuthenticated_, setIsAuthenticated_] = useState(false);

  useEffect(() => {
    setupAxiosInterceptors();
  }, []);

  useEffect(() => {
    console.log('🔄 App.tsx useEffect triggered - initializing auth...');
    
    const initializeUser = async () => {
      if (isAuthenticated()) {
        console.log('✅ User already authenticated, skipping guest creation');
        setIsAuthenticated_(true);
        setIsInitializing(false);
        setAuthChecked(true);
        return;
      }

      try {
        console.log('❌ No authentication found, creating guest user...');
        const guestUser = await createGuestUser();
        console.log('✅ Guest user created successfully:', guestUser);
        setIsAuthenticated_(true);
        setAuthChecked(true);
      } catch (error) {
        console.error('❌ Failed to create guest user:', error);
        setIsAuthenticated_(false);
        setAuthChecked(true);
      } finally {
        setIsInitializing(false);
      }
    };

    initializeUser();
  }, []);

  const currentPath = location.pathname;

  // Rutas que NO requieren autenticación
  const publicRoutes = ['/login', '/AuthForm', '/verify-email', '/reset-password', '/beta-signup'];
  const isPublicRoute = publicRoutes.includes(currentPath);

  if (isInitializing || !authChecked) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900 mx-auto mb-4"></div>
          <p className="text-slate-600">Initializing...</p>
        </div>
      </div>
    );
  }

  // Solo redirigir a login si NO está autenticado Y NO está en una ruta pública
  if (!isAuthenticated_ && !isPublicRoute) {
    console.log('🔴 App.tsx: Not authenticated, redirecting to login');
    return <Navigate to="/login" replace />;
  }

  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/beta-signup" element={<BetaSignupPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/verify-email" element={<EmailVerificationPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/AuthForm" element={<AuthForm />} />
      <Route path="/background-removal" element={<BackgroundRemovalPage />} />
      <Route path="/upscale" element={<UpscalePage />} />
      <Route path="/enlarge" element={<EnlargePage />} />
      <Route path="/object-removal" element={<ObjectRemovalPage />} />
      <Route path="/image-generation" element={<ImageGenerationPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

const App = () => (
  <Router>
    <AppWrapper />
  </Router>
);

export default App;