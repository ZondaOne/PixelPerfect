import React, { useState, useRef, useEffect } from 'react';
import { gsap } from 'gsap';
import { Eye, EyeOff, Mail, Lock, Sparkles, User, ArrowRight, Shield } from 'lucide-react';
import { login, register, createGuestUser, storeUserData, resendVerificationEmail } from '../services/authService';
import logo from '../assets/logo.png';
import { GoogleLogin } from '@react-oauth/google';

const LoginPage: React.FC = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [hasAnimated, setHasAnimated] = useState(false);
  const [username, setUsername] = useState('');
  const [registrationSuccess, setRegistrationSuccess] = useState(false);
  const [registrationEmail, setRegistrationEmail] = useState('');
  const [emailVerificationPending, setEmailVerificationPending] = useState(false);

 const backgroundImages = [
  "https://i.imgur.com/86ij9Sd.jpeg",
  "https://i.imgur.com/HEhUJ5q.jpeg",
  "https://i.imgur.com/aXmHT1p.jpeg",
  "https://i.imgur.com/mCtgUAu.jpeg",
  "https://i.imgur.com/0YsUKZi.jpeg",
  "https://i.imgur.com/7572PnN.jpeg",
  "https://i.imgur.com/P14Jczs.jpeg"
];

const [selectedIndex, setSelectedIndex] = useState(0);

useEffect(() => {
  const interval = setInterval(() => {
    setSelectedIndex(prevIndex => (prevIndex + 1) % backgroundImages.length);
  }, 3000); 

  return () => clearInterval(interval);
}, []);

const selectedImage = backgroundImages[selectedIndex];

  // Refs for animation
  const heroRef = useRef<HTMLDivElement>(null);
  const uploaderRef = useRef<HTMLDivElement>(null);
  const featuresRef = useRef<HTMLDivElement>(null);
  const formContentRef = useRef<HTMLDivElement>(null);
  const onForgotPassword = () => {
  
    window.location.href = '/AuthForm';
  };

  // Animation effect that only runs once
  useEffect(() => {
    if (!hasAnimated) {
      // Set initial states immediately to prevent flash
      if (heroRef.current && uploaderRef.current && featuresRef.current) {
        gsap.set([heroRef.current, uploaderRef.current, featuresRef.current], {
          opacity: 0,
          y: 40,
          scale: 0.95,
          filter: 'blur(8px)'
        });

        // Create entrance animation
        const tl = gsap.timeline({ delay: 0.1 });
        
        tl.to(heroRef.current, {
          opacity: 1,
          y: 0,
          scale: 1,
          filter: 'blur(0px)',
          duration: 1.4,
          ease: "power4.out"
        })
        .to(uploaderRef.current, {
          opacity: 1,
          y: 0,
          scale: 1,
          filter: 'blur(0px)',
          duration: 1.2,
          ease: "power3.out"
        }, "-=0.9")
        .to(featuresRef.current, {
          opacity: 1,
          y: 0,
          scale: 1,
          filter: 'blur(0px)',
          duration: 0.8,
          ease: "power2.out"
        }, "-=0.3");

        setHasAnimated(true);
      }
    }
  }, [hasAnimated]);

  // Subtle animation for form content when switching between login/signup
  useEffect(() => {
    if (hasAnimated && formContentRef.current) {
      gsap.fromTo(formContentRef.current, 
        { opacity: 0.7, y: 10 },
        { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }
      );
    }
  }, [isLogin, hasAnimated]);


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setRegistrationSuccess(false);
    setEmailVerificationPending(false);

    try {
      if (isLogin) {
        const response = await login({email, password });
        storeUserData(response);
        window.location.href = '/';
      } else {
        const response = await register({displayName: username, email, password });
        setRegistrationSuccess(true);
        setRegistrationEmail(email);
      }
    } catch (err: any) {
      // Handle email verification error specifically
      if (err.type === 'EMAIL_NOT_VERIFIED') {
        setEmailVerificationPending(true);
        setRegistrationEmail(err.email);
        setError(err.message);
      } else {
        setError(err.message || 'An error occurred');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResendVerification = async () => {
    setLoading(true);
    setError('');
    
    try {
      await resendVerificationEmail(registrationEmail);
      setError('Verification email sent! Please check your inbox.');
    } catch (err: any) {
      setError(err.message || 'Failed to resend verification email');
    } finally {
      setLoading(false);
    }
  };

  const handleGuestLogin = async () => {
    setLoading(true);
    try {
      const response = await createGuestUser();
      storeUserData(response);
      window.location.href = '/';
    } catch (err: any) {
      setError(err.message || 'Failed to create guest user');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async (credentialResponse: any) => {
  console.log('Google login response:', credentialResponse);
  
  if (!credentialResponse.credential) {
    setError('No credential received from Google');
    return;
  }

  setLoading(true);
  setError('');

  try {
    // Llamar a tu endpoint backend
    const response = await fetch('https://backend-1li0.onrender.com/api/v1/auth/login-with-google', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        credential: credentialResponse.credential
      })
    });

    if (!response.ok) {
      const errorData = await response.text();
      throw new Error(errorData || 'Google login failed');
    }

    const data = await response.json();
    console.log('Backend response:', data);

    // Guardar los datos del usuario (igual que en login normal)
    storeUserData(data);
    
    // Redirigir a la página principal
    window.location.href = '/';
    
  } catch (err: any) {
    console.error('Google login error:', err);
    setError(err.message || 'Google login failed');
  } finally {
    setLoading(false);
  }
};

  return (
  <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 relative">
  
  {/* Hero Image Section */}
  <div className="absolute left-0 top-0 bottom-0 right-[500px] hidden lg:block">
    {selectedImage && (
      <img 
        src={selectedImage}
        alt="Hero Background"
        className="w-full h-full object-cover"
      />
    )}
    
    <div className="absolute inset-0 bg-gradient-to-r from-black/10 to-black/30"></div>

    <p className="absolute bottom-4 left-4 text-white text-sm z-10">
      This image was generated by PixelPerfect Gen-AI.
    </p>
  </div>

  
  <div className="h-screen flex items-stretch justify-end relative z-10">
    <div className="w-[500px] h-full flex items-stretch justify-center bg-white">

          {/* Login Form */}
          <div ref={uploaderRef} className="w-full max-w-lg">
      <div className="bg-white p-6 shadow-lg border border-gray-200 h-full flex flex-col justify-center">
        
        {/* Content wrapper */}
        <div className="relative z-10">
          
          {/* Logo and Header */}
          <div ref={formContentRef} className="text-center mb-4">
            <img 
              src={logo} 
              alt="Logo" 
              className="w-12 h-12 mx-auto mb-3"
            />
            <h2 className="text-xl font-medium text-gray-800 mb-1">
              {isLogin ? 'Sign In' : 'Create Account'}
            </h2>
          </div>

          {/* Error Message */}
          {error && !registrationSuccess && !emailVerificationPending && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg mb-4 text-center text-sm">
              {error}
            </div>
          )}

          {/* Registration Success Message */}
          {registrationSuccess && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-3 py-2 rounded-lg mb-4 text-center text-sm">
              <div className="flex items-center justify-center gap-2 mb-1">
                <Mail size={14} />
                <span className="font-medium">Registration Successful!</span>
              </div>
              <p>Check your email ({registrationEmail}) and click the verification link.</p>
              <button
                onClick={handleResendVerification}
                disabled={loading}
                className="mt-1 text-green-600 hover:text-green-800 font-medium text-sm underline"
              >
                Didn't receive the email? Resend
              </button>
            </div>
          )}

          {/* Email Verification Pending Message */}
          {emailVerificationPending && (
            <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 px-3 py-2 rounded-lg mb-4 text-center text-sm">
              <div className="flex items-center justify-center gap-2 mb-1">
                <Mail size={14} />
                <span className="font-medium">Verification Required</span>
              </div>
              <p>Verify your email ({registrationEmail}) to continue.</p>
              <button
                onClick={handleResendVerification}
                disabled={loading}
                className="mt-1 text-yellow-600 hover:text-yellow-800 font-medium text-sm underline"
              >
                Resend verification email
              </button>
            </div>
          )}

          <div className="space-y-2 mb-4">
          <GoogleLogin
          onSuccess={handleGoogleLogin}
          onError={() => {
            console.log('Google Login Failed');
            setError('Google login failed');
          }}
          theme="outline"
          size="large"
          width="100%"
        />

            <button 
              onClick={() => setIsLogin(!isLogin)}
              className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors duration-200"
            >
              <Mail className="w-4 h-4 text-gray-600" />
              <span className="text-gray-700 font-medium text-sm">Continue with Email</span>
            </button>
          </div>

          {/* Email Form */}
          <form onSubmit={handleSubmit} className="space-y-3 mb-4">
            {!isLogin && (
              <div>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 text-sm"
                  placeholder="Username"
                  required
                />
              </div>
            )}

            <div>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 text-sm"
                placeholder="Email"
                required
              />
            </div>

            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2.5 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 text-sm"
                placeholder="Password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2.5 px-4 rounded-lg font-medium transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              {loading ? (
                <div className="flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Processing...
                </div>
              ) : (
                isLogin ? 'Sign In' : 'Create Account'
              )}
            </button>
          </form>

          {/* Notifications checkbox */}
          <div className="flex items-start gap-2 mb-4">
            <input
              type="checkbox"
              id="notifications"
              className="mt-0.5 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="notifications" className="text-xs text-gray-600 leading-relaxed">
              I don't want to receive promotional email notifications.
            </label>
          </div>

          {/* Guest Login */}
          <button
            onClick={handleGuestLogin}
            disabled={loading}
            className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 py-2.5 px-4 rounded-lg font-medium transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed mb-4 text-sm"
          >
            <div className="flex items-center justify-center gap-2">
              <User size={16} />
              Continue as Guest
            </div>
          </button>

          {/* Terms and Privacy */}
          <p className="text-center text-xs text-gray-500 mb-3">
            By registering you agree to our{' '}
            <a href="#" className="text-blue-600 hover:underline">Terms of Use</a>
            {' '}and{' '}
            <a href="#" className="text-blue-600 hover:underline">Privacy Policy</a>.
          </p>

          {/* Switch Login/Register */}
          <div className="text-center mb-3">
            <span className="text-gray-600 text-sm">
              {isLogin ? "Don't have an account?" : "Already have an account?"}
            </span>
            <button
              onClick={() => setIsLogin(!isLogin)}
              className="text-blue-600 hover:underline font-medium text-sm ml-1"
            >
              {isLogin ? 'Create Account' : 'Sign In'}
            </button>
          </div>

          {isLogin && (
            <div className="text-center mb-3">
              <button 
                onClick={onForgotPassword}
                className="text-blue-600 hover:underline text-sm"
              >
                Forgot your password?
              </button>
            </div>
          )}

          {/* Cookie Settings */}
          <div className="text-center">
            <button className="text-blue-600 hover:underline text-sm">
              Cookie Settings
            </button>
          </div>
        </div>
      </div>
    </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;