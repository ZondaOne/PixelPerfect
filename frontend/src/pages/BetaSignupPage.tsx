import React, { useState } from 'react';
import { Star, ArrowRight, Mail, Sparkles, CheckCircle } from 'lucide-react';
import AnimatedGradientMesh from '../components/AnimatedGradientMesh';
import AnimatedNetMesh from '../components/AnimatedNetMesh';
import logo from '../assets/logo.png';

const BetaSignupPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  if (!email) return;

  setIsLoading(true);

  try {
    const response = await fetch('https://backend-1li0.onrender.com/waitlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });

    let data: any = {};
    const text = await response.text(); 
    if (text) {
      data = JSON.parse(text);
    }

    if (!response.ok) {
      throw new Error(data.error || 'Failed to join waitlist');
    }

    setIsSubmitted(true);
  } catch (err: any) {
    alert(err.message);
  } finally {
    setIsLoading(false);
  }
};



  const handleSkipDebug = () => {
    window.location.href = '/';
  };

  if (isSubmitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center px-6 relative overflow-hidden">
        <AnimatedGradientMesh variant="default" intensity="subtle" />
        <AnimatedNetMesh intensity="subtle" />
        
        <div className="max-w-md w-full relative z-10">
          <div className="bg-white/80 backdrop-blur-xl rounded-3xl p-8 shadow-2xl border border-white/50">
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              
              <h1 className="text-2xl font-medium text-slate-900 mb-3 tracking-tight">
                You're on the list!
              </h1>
              
              <p className="text-slate-600 text-sm leading-relaxed mb-6">
                Thank you for joining our beta waitlist. We'll notify you as soon as we launch.
              </p>
              
              <button
                onClick={handleSkipDebug}
                className="w-full bg-slate-900 hover:bg-slate-800 text-white py-3 px-6 rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
              >
                <Star size={16} />
                Continue to App
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center px-6 relative overflow-hidden">
      <AnimatedGradientMesh variant="default" intensity="subtle" />
      <AnimatedNetMesh intensity="subtle" />
      
      <div className="max-w-md w-full relative z-10">
        <div className="bg-white/80 backdrop-blur-xl rounded-3xl p-8 shadow-2xl border border-white/50">
          <div className="text-center mb-8">
            <img
              src={logo}
              alt="Pixel Perfect AI"
              className="w-16 h-16 mx-auto mb-6 drop-shadow-lg"
            />
            
            <div className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-100 to-purple-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium mb-4">
              <Sparkles size={14} />
              Early Access
            </div>
            
            <h1 className="text-2xl font-medium text-slate-900 mb-3 tracking-tight">
              Join the Beta
            </h1>
            
            <p className="text-slate-600 text-sm leading-relaxed">
              Be among the first to experience the future of AI-powered image processing.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-2">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-slate-400" />
                </div>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-white/70 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 backdrop-blur-sm"
                  placeholder="Enter your email"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={!email || isLoading}
              className="w-full bg-slate-900 hover:bg-slate-800 disabled:bg-slate-400 text-white py-3 px-6 rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2 shadow-lg hover:shadow-xl disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Adding you to the list...
                </>
              ) : (
                <>
                  <Star size={16} />
                  Join Beta Waitlist
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-200/60">
            <button
              onClick={handleSkipDebug}
              className="w-full text-slate-500 hover:text-slate-700 text-sm font-medium transition-colors duration-200"
            >
              Skip for now (Debug Mode)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BetaSignupPage;