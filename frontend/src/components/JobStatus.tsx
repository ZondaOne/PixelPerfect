import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { JobResponseDTO, JobStatusEnum } from '../types';
import { getJobStatus } from '../services/apiService';
import { unlockPremiumQuality } from '../services/tokenService';
import { Clock, CheckCircle, XCircle, Loader2, Download, Unlock, Star, Sparkles, Scissors, Maximize, Expand, X, ArrowRight, Zap } from 'lucide-react';

interface JobStatusProps {
  jobId: string;
  initialImageUrl?: string;
  variant?: string;
  serviceType?: 'background-removal' | 'upscale' | 'enlarge' | 'object-removal';
  onJobCompleted?: (job: JobResponseDTO) => void;
  onContinueProcessing?: (selectedService: 'upscale' | 'object-removal', imageUrl: string) => void;
}

// Lazy load GSAP only when needed
const loadGSAP = () => import('gsap').then(module => module.gsap);

// Optimized global protection - only run once
let globalProtectionSetup = false;
const setupGlobalProtection = () => {
  if (globalProtectionSetup) return;
  globalProtectionSetup = true;

  // Use requestAnimationFrame for better performance
  let rafId: number;
  const detectDevTools = () => {
    if (window.outerHeight - window.innerHeight > 160 || window.outerWidth - window.innerWidth > 160) {
      document.body.innerHTML = `
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #000; color: #fff; display: flex; align-items: center; justify-content: center; z-index: 999999; font-family: Arial;">
          <div style="text-align: center;">
            <h1>🚫 Access Denied</h1>
            <p>Developer tools are not allowed on this page.</p>
            <p>Please close DevTools and refresh the page.</p>
          </div>
        </div>
      `;
      return;
    }
    rafId = requestAnimationFrame(detectDevTools);
  };
  detectDevTools();

  // Optimized event listeners with passive option
  const keydownHandler = (e: KeyboardEvent) => {
    if (e.key === 'F12' || 
        (e.ctrlKey && e.shiftKey && e.key === 'I') ||
        (e.ctrlKey && e.shiftKey && e.key === 'J') ||
        (e.ctrlKey && e.shiftKey && e.key === 'C') ||
        (e.ctrlKey && e.key === 'U') ||
        (e.ctrlKey && e.key === 'S') ||
        (e.ctrlKey && e.key === 'P')) {
      e.preventDefault();
      e.stopPropagation();
    }
  };

  document.addEventListener('keydown', keydownHandler, { passive: false });
  document.addEventListener('selectstart', (e) => e.preventDefault(), { passive: false });
  document.addEventListener('dragstart', (e) => e.preventDefault(), { passive: false });
  document.addEventListener('contextmenu', (e) => e.preventDefault(), { passive: false });

  // Reduce console clear frequency
  setInterval(() => {
    console.clear();
    console.log('%cStop!', 'color: red; font-size: 50px; font-weight: bold;');
    console.log('%cThis is a browser feature intended for developers. Content is protected.', 'color: red; font-size: 16px;');
  }, 5000); 
};

const JobStatus: React.FC<JobStatusProps> = ({ 
  jobId, 
  initialImageUrl, 
  serviceType = 'background-removal', 
  onJobCompleted,
  onContinueProcessing
}) => {
  const [job, setJob] = useState<JobResponseDTO | null>(null);
  const [error, setError] = useState('');
  const [unlocking, setUnlocking] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const processedCanvasRef = useRef<HTMLCanvasElement>(null);
  const originalCanvasRef = useRef<HTMLCanvasElement>(null);
  const [progress, setProgress] = useState(0);
  const [isDevToolsOpen, setIsDevToolsOpen] = useState(false);
  const [gsapLoaded, setGsapLoaded] = useState(false);
  
  // Continue Processing Modal State
  const [showContinueModal, setShowContinueModal] = useState(false);
  const [selectedService, setSelectedService] = useState<'upscale' | 'object-removal' | null>(null);
  const [isModalAnimating, setIsModalAnimating] = useState(false);

  // Optimized devtools detection with debounce
  useEffect(() => {
    setupGlobalProtection();
    
    let timeoutId: NodeJS.Timeout;
    const detectDevTools = () => {
      const threshold = 160;
      const isOpen = window.outerHeight - window.innerHeight > threshold || 
                     window.outerWidth - window.innerWidth > threshold;
      
      if (isOpen !== isDevToolsOpen) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => setIsDevToolsOpen(isOpen), 100);
      }
    };

    const interval = setInterval(detectDevTools, 500);
    return () => {
      clearInterval(interval);
      clearTimeout(timeoutId);
    };
  }, [isDevToolsOpen]);

  // Optimized canvas rendering with memoization
  const renderImageToCanvas = useCallback((canvas: HTMLCanvasElement, src: string) => {
    if (!canvas || !src) return;
    
    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;
    
    const img = new Image();
    img.onload = () => {
      requestAnimationFrame(() => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        
        // Optimized watermark
        ctx.globalAlpha = 0.01;
        ctx.fillStyle = 'white';
        ctx.font = '20px Arial';
        ctx.fillText('Protected Content', 10, 30);
        ctx.globalAlpha = 1;
      });
    };
    
    img.crossOrigin = 'anonymous';
    img.src = src;
  }, []);

  // Lazy load images
  useEffect(() => {
    if (originalCanvasRef.current && initialImageUrl) {
      const timeoutId = setTimeout(() => {
        renderImageToCanvas(originalCanvasRef.current!, initialImageUrl);
      }, 0);
      return () => clearTimeout(timeoutId);
    }
  }, [initialImageUrl, renderImageToCanvas]);

  useEffect(() => {
    if (processedCanvasRef.current && job?.thumbnailUrl) {
      renderImageToCanvas(processedCanvasRef.current, job.thumbnailUrl);
    }
  }, [job?.thumbnailUrl, renderImageToCanvas]);

  // Memoized event handlers
  const preventRightClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const preventDragStart = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const preventSelection = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
  }, []);

  const preventInspect = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'F12' || 
        (e.ctrlKey && e.shiftKey && e.key === 'I') ||
        (e.ctrlKey && e.shiftKey && e.key === 'C') ||
        (e.ctrlKey && e.key === 'U') ||
        (e.ctrlKey && e.key === 'S')) {
      e.preventDefault();
    }
  }, []);

  // Continue Processing Modal Functions
  const handleShowContinueModal = useCallback(() => {
    setShowContinueModal(true);
    setSelectedService(null);
  }, []);

  const handleCloseContinueModal = useCallback(() => {
    setIsModalAnimating(true);
    setTimeout(() => {
      setShowContinueModal(false);
      setIsModalAnimating(false);
      setSelectedService(null);
    }, 200);
  }, []);

  // Available services for continue processing
  const availableServices = useMemo(() => {
    const services = [
      {
        id: 'upscale' as const,
        title: 'Upscale Image',
        description: 'Enhance resolution and quality with AI',
        icon: Maximize,
        gradient: 'from-blue-500 to-indigo-600',
        bgGradient: 'from-blue-50 to-indigo-50',
        disabled: serviceType === 'upscale',
        href: '/upscale'
      },
      {
        id: 'object-removal' as const,
        title: 'Remove Objects',
        description: 'Remove unwanted objects from your image',
        icon: Sparkles,
        gradient: 'from-purple-500 to-violet-600',
        bgGradient: 'from-purple-50 to-violet-50',
        disabled: serviceType === 'object-removal',
        href: '/object-removal'
      }
    ];
    
    const filtered = services.filter(service => !service.disabled);
    console.log('🛠️ Available services:', filtered);
    
    return filtered;
  }, [serviceType]);

  // FIXED Continue Processing Handler
  const handleContinueProcessing = useCallback(() => {
    console.log('🔥 STARTING handleContinueProcessing');
    console.log('📊 Current state:', {
      selectedService,
      jobExists: !!job,
      onContinueProcessingExists: !!onContinueProcessing,
      availableServices: availableServices.map(s => ({ id: s.id, href: s.href }))
    });

    // Validation checks
    if (!selectedService) {
      console.error('❌ No selectedService');
      alert('Please select a service to continue');
      return;
    }

    if (!job) {
      console.error('❌ No job');
      alert('No job data available');
      return;
    }

    // Find service first
    const service = availableServices.find(s => s.id === selectedService);
    console.log('🔍 Service found:', service);

    if (!service) {
      console.error('❌ Service not found');
      alert('Selected service not available');
      return;
    }

    // Get image URL
    const imageUrl = job.isPremiumQuality ? (job.processedImageUrl || job.thumbnailUrl) : job.thumbnailUrl;
    console.log('🖼️ Image URL:', imageUrl);

    const encodedImageUrl = imageUrl ? encodeURIComponent(imageUrl) : '';
    const serviceWithImage = {
    ...service,
    href: `${service.href}?preloadImage=${encodedImageUrl}`
  };
    console.log('🔗 Updated service URL:', serviceWithImage.href);

    // If onContinueProcessing callback exists, call it
    if (onContinueProcessing) {
      console.log('📞 Calling onContinueProcessing callback...');
      try {
        onContinueProcessing(selectedService, imageUrl!);
        console.log('✅ onContinueProcessing callback executed successfully');
      } catch (error) {
        console.error('❌ Error in onContinueProcessing callback:', error);
      }
    }

    // Close modal first
    console.log('🚪 Closing modal...');
    setShowContinueModal(false);
    setSelectedService(null);
    setIsModalAnimating(false);

    // Perform redirect with multiple fallbacks
    
    console.log('🌐 Attempting redirect to:', service.href);
    
    // Use setTimeout to ensure modal state updates complete
    setTimeout(() => {
      try {
        // Method 1: Standard redirect
        console.log('🚀 Redirecting with window.location.href...');
        window.open(serviceWithImage.href, '_self');
      } catch (error) {
        console.error('❌ window.location.href failed:', error);
        
        // Method 2: Using location.assign
        try {
          console.log('🔄 Trying window.location.assign...');
          window.location.assign(service.href);
        } catch (error2) {
          console.error('❌ window.location.assign failed:', error2);
          
          // Method 3: Using location.replace
          try {
            console.log('🔄 Trying window.location.replace...');
            window.location.replace(service.href);
          } catch (error3) {
            console.error('❌ window.location.replace failed:', error3);
            
            // Method 4: Create and click a link
            try {
              console.log('🔗 Creating link element...');
              const link = document.createElement('a');
              link.href = service.href;
              link.target = '_self';
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
            } catch (error4) {
              console.error('❌ Link click failed:', error4);
              
              // Final fallback: Show user a message
              alert(`Please navigate to: ${service.href}`);
              console.log('🆘 All redirect methods failed, showing user message');
            }
          }
        }
      }
    }, 100);

  }, [selectedService, job, onContinueProcessing, availableServices]);

  // Optimized download function
  const downloadImage = useCallback(async (imageUrl: string, fileName: string = 'image.png'): Promise<void> => {
    try {
      if (!imageUrl || imageUrl.trim() === '') {
        throw new Error('URL empty');
      }

      const response = await fetch(imageUrl, {
        method: 'GET',
        headers: {
          'Accept': 'image/*',
          'Cache-Control': 'no-cache',
        },
        mode: 'cors', 
        credentials: 'omit'
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status} - ${response.statusText}`);
      }

      const contentType = response.headers.get('content-type');
      
      if (!contentType || !contentType.startsWith('image/')) {
        throw new Error(`Invalid content: ${contentType}`);
      }

      const blob = await response.blob();

      if (blob.size === 0) {
        throw new Error('Empty file received');
      }
      
      const fileExtension = contentType.split('/')[1] || 'png';
      const finalFileName = fileName.includes('.') ? fileName : `${fileName}.${fileExtension}`;
      
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = finalFileName;
      link.style.display = 'none';

      document.body.appendChild(link);
      
      setTimeout(() => {
        link.click();
        
        setTimeout(() => {
          if (document.body.contains(link)) {
            document.body.removeChild(link);
          }
          URL.revokeObjectURL(blobUrl);
        }, 100);
      }, 10);
      
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        setError('Could not connect to server');
      } else if (error instanceof Error) {
        setError(`Download error: ${error.message}`);
      } else {
        setError('Unknown error occurred');
      }
    }
  }, []);

  // Memoized service configuration
  const serviceConfig = useMemo(() => {
    const configs = {
      'background-removal': {
        icon: Scissors,
        accentColor: 'from-rose-500 to-pink-600',
        ringColor: 'ring-rose-500/20',
        bgGradient: 'from-rose-50 to-pink-50',
        phrases: {
          processing: ['Removing background with precision...', 'Making backgrounds disappear...', 'Cutting through the noise...'],
          completed: ['Background removed successfully!', 'Clean result achieved.', 'Background eliminated.']
        }
      },
      'upscale': {
        icon: Maximize,
        accentColor: 'from-blue-500 to-indigo-600',
        ringColor: 'ring-blue-500/20',
        bgGradient: 'from-blue-50 to-indigo-50',
        phrases: {
          processing: ['Enhancing image quality...', 'Upscaling with AI precision...', 'Improving resolution...'],
          completed: ['Image enhanced successfully!', 'Quality improvement complete.', 'Resolution upgraded.']
        }
      },
      'enlarge': {
        icon: Expand,
        accentColor: 'from-green-500 to-emerald-600',
        ringColor: 'ring-green-500/20',
        bgGradient: 'from-green-50 to-emerald-50',
        phrases: {
          processing: ['Enlarging image dimensions...', 'Expanding image boundaries...', 'Increasing image size...'],
          completed: ['Image enlarged successfully!', 'Size increase complete.', 'Dimensions expanded.']
        }
      },
      'object-removal': {
        icon: Sparkles,
        accentColor: 'from-purple-500 to-violet-600',
        ringColor: 'ring-purple-500/20',
        bgGradient: 'from-purple-50 to-violet-50',
        phrases: {
          processing: ['Removing unwanted objects...', 'Cleaning up the image...', 'Erasing distractions...'],
          completed: ['Objects removed successfully!', 'Image cleaned perfectly.', 'Unwanted elements erased.']
        }
      }
    };
    return configs[serviceType];
  }, [serviceType]);

  const getRandomPhrase = useCallback((type: 'processing' | 'completed') => {
    const phrases = serviceConfig.phrases[type];
    return phrases[Math.floor(Math.random() * phrases.length)];
  }, [serviceConfig.phrases]);

  // Optimized job polling with exponential backoff
  useEffect(() => {
    let interval: NodeJS.Timeout;
    let pollCount = 0;
    
    const pollJobStatus = async () => {
      try {
        const response = await getJobStatus(jobId);
        setJob(response);

        if (response.status === JobStatusEnum.COMPLETED || response.status === JobStatusEnum.FAILED) {
          if (response.status === JobStatusEnum.COMPLETED && onJobCompleted) {
            onJobCompleted(response);
          }
          clearInterval(interval);
          return;
        }

        // Exponential backoff for polling
        pollCount++;
        const nextInterval = Math.min(1000 + (pollCount * 500), 5000);
        clearInterval(interval);
        interval = setTimeout(pollJobStatus, nextInterval);
        
      } catch (err: any) {
        setError(err.message || 'Failed to get job status');
        clearInterval(interval);
      }
    };

    pollJobStatus();

    return () => clearInterval(interval);
  }, [jobId, onJobCompleted]);

  // Lazy load GSAP and entrance animation
  useEffect(() => {
    if (containerRef.current && !gsapLoaded) {
      loadGSAP().then(gsap => {
        setGsapLoaded(true);
        gsap.fromTo(containerRef.current, 
          { opacity: 0, y: 40, scale: 0.95 },
          { opacity: 1, y: 0, scale: 1, duration: 0.8, ease: "power3.out" }
        );
        
        containerRef.current?.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'center' 
        });
      }).catch(() => {
        setGsapLoaded(true);
        if (containerRef.current) {
          containerRef.current.style.opacity = '1';
          containerRef.current.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
          });
        }
      });
    }
  }, [gsapLoaded]);

  const handleUnlockPremium = useCallback(async () => {
    if (!job || unlocking) return;

    setUnlocking(true);
    try {
      await unlockPremiumQuality(job.jobId);
      const updatedJob = await getJobStatus(job.jobId);
      setJob(updatedJob);
    } catch (err: any) {
      setError(err.message || 'Failed to unlock premium quality');
    } finally {
      setUnlocking(false);
    }
  }, [job, unlocking]);

  // Memoized status checks
  const isProcessing = useMemo(() => {
    return job?.status === JobStatusEnum.PENDING || 
           job?.status === JobStatusEnum.QUEUED || 
           job?.status === JobStatusEnum.PROCESSING;
  }, [job?.status]);

  const isCompleted = useMemo(() => job?.status === JobStatusEnum.COMPLETED, [job?.status]);
  const isFailed = useMemo(() => job?.status === JobStatusEnum.FAILED, [job?.status]);

  const statusConfig = useMemo(() => {
    const ServiceIcon = serviceConfig.icon;
    switch (job?.status) {
      case JobStatusEnum.COMPLETED:
        return { 
          text: getRandomPhrase('completed'), 
          icon: CheckCircle, 
          color: 'text-green-600',
          bgColor: 'bg-green-100',
          pulse: false
        };
      case JobStatusEnum.FAILED:
        return { 
          text: 'Process failed. Please try again.', 
          icon: XCircle, 
          color: 'text-red-600',
          bgColor: 'bg-red-100',
          pulse: false
        };
      case JobStatusEnum.PROCESSING:
        return { 
          text: getRandomPhrase('processing'), 
          icon: ServiceIcon, 
          color: 'text-slate-600',
          bgColor: `bg-gradient-to-r ${serviceConfig.accentColor}`,
          pulse: true
        };
      default:
        return { 
          text: 'Preparing for processing...', 
          icon: Clock, 
          color: 'text-slate-500',
          bgColor: 'bg-slate-100',
          pulse: false
        };
    }
  }, [job?.status, serviceConfig, getRandomPhrase]);

  const StatusIcon = statusConfig.icon;

  // Optimized processing animation
  useEffect(() => {
    if (!isProcessing || !gsapLoaded) {
      setProgress(0);
      return;
    }

    let timeElapsed = 0;
    const interval = setInterval(() => {
      timeElapsed += 300;
      
      setProgress((prev) => {
        if (prev >= 70) return Math.min(prev + Math.random() * 0.5, 85);
        if (prev >= 50) return prev + Math.random() * 1;
        return prev + Math.random() * 3;
      });
    }, 300);

    return () => clearInterval(interval);
  }, [isProcessing, gsapLoaded]);

  // Early return for dev tools
  if (isDevToolsOpen) {
    return (
      <div className="fixed inset-0 bg-black text-white flex items-center justify-center z-50">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4">🚫 Access Denied</h1>
          <p className="text-xl mb-2">Developer tools are not allowed on this page.</p>
          <p className="text-lg">Please close DevTools and refresh the page.</p>
        </div>
      </div>
    );
  }

  // Early return for errors
  if (error) {
    return (
      <div 
        ref={containerRef} 
        className="w-full max-w-lg mx-auto select-none"
        onContextMenu={preventRightClick}
        onKeyDown={preventInspect}
        tabIndex={0}
        style={{ 
          userSelect: 'none',
          WebkitUserSelect: 'none',
          MozUserSelect: 'none',
          msUserSelect: 'none'
        }}
      >
        <div className="bg-white/95 backdrop-blur-3xl rounded-3xl p-8 shadow-2xl border border-white/30 ring-1 ring-slate-900/5 transition-all duration-300">
          <div className="text-center space-y-4">
            <div className="w-16 h-16 bg-red-100 rounded-2xl flex items-center justify-center mx-auto">
              <XCircle className="text-red-600" size={32} />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-slate-900 mb-2">Something went wrong!</h3>
              <p className="text-sm text-slate-600 leading-relaxed">{error}</p>
              <p className="text-xs text-slate-500 mt-2">Please try again later.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div 
        ref={containerRef} 
        className="w-full max-w-lg mx-auto select-none"
        onContextMenu={preventRightClick}
        onKeyDown={preventInspect}
        tabIndex={0}
        style={{ 
          userSelect: 'none',
          WebkitUserSelect: 'none',
          MozUserSelect: 'none',
          msUserSelect: 'none',
          opacity: gsapLoaded ? 1 : 0
        }}
      >
        <div className="bg-white/95 backdrop-blur-3xl rounded-3xl p-8 shadow-2xl border border-white/30 ring-1 ring-slate-900/5 transition-all duration-300 hover:shadow-3xl relative z-50">
          
          {/* Image Container */}
          <div ref={imageRef} className="relative mb-8">
            <div className="aspect-[4/3] bg-slate-50 rounded-2xl overflow-hidden relative ring-1 ring-slate-900/5 shadow-inner">
            
              <div 
                className="absolute inset-0 z-10 bg-transparent"
                onContextMenu={preventRightClick}
                onDragStart={preventDragStart}
                onMouseDown={preventSelection}
                style={{ 
                  userSelect: 'none',
                  WebkitUserSelect: 'none',
                  MozUserSelect: 'none',
                  msUserSelect: 'none'
                }}
              />
              
              {/* Original Image */}
              <canvas
                ref={originalCanvasRef}
                className={`w-full h-full object-contain transition-all duration-700 select-none ${isCompleted ? 'opacity-0 scale-105' : 'opacity-100 scale-100'}`}
                onContextMenu={preventRightClick}
                onDragStart={preventDragStart}
                onMouseDown={preventSelection}
                style={{ 
                  userSelect: 'none',
                  WebkitUserSelect: 'none',
                  MozUserSelect: 'none',
                  msUserSelect: 'none',
                  pointerEvents: 'none'
                }}
              />
              
              {/* Processing Overlay */}
              <div 
                ref={overlayRef}
                className={`absolute inset-0 backdrop-blur-sm flex flex-col items-center justify-center transition-all duration-500 bg-black/20 z-20 ${isProcessing ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
              >
                <div className={`w-20 h-20 rounded-2xl flex items-center justify-center mb-6 ${statusConfig.bgColor} ${statusConfig.pulse ? 'animate-pulse' : ''}`}>
                  <StatusIcon className="text-white" size={32} />
                </div>
                <div className="text-center text-white">
                  <p className="font-semibold text-lg mb-2">{statusConfig.text}</p>
                  <p className="text-sm opacity-90">This usually takes 15-30 seconds</p>
                </div>
                
                <div className="w-80 h-1 bg-white/20 rounded-full mt-6 overflow-hidden">
                  <div 
                    className="h-full bg-white rounded-full transition-all duration-300 ease-out"
                    style={{ 
                      width: `${progress}%`,
                      transform: `translateX(-${100 - progress}%)`,
                      animation: 'slideIn 0.3s ease-out'
                    }}
                  />
                </div>
              </div>
              
              {/* Processed Image */}
              <canvas
                ref={processedCanvasRef}
                className={`absolute inset-0 w-full h-full object-cover transition-all duration-1000 select-none ${isCompleted ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}
                onContextMenu={preventRightClick}
                onDragStart={preventDragStart}
                onMouseDown={preventSelection}
                style={{ 
                  userSelect: 'none',
                  WebkitUserSelect: 'none',
                  MozUserSelect: 'none',
                  msUserSelect: 'none',
                  pointerEvents: 'none'
                }}
              />
              
              {/* Completion Celebration Overlay */}
              {isCompleted && (
                <div className="absolute top-4 right-4 bg-green-500 text-white px-3 py-1 rounded-full text-sm font-medium shadow-lg z-40">
                  ✨ Complete!
                </div>
              )}
            </div>
          </div>

          {/* Status Section */}
          <div className="space-y-6">
            <div className="text-center">
              <div className={`inline-flex items-center gap-3 px-4 py-2 rounded-full ${statusConfig.bgColor} ${serviceConfig.ringColor} ring-1`}>
                <StatusIcon className={`${statusConfig.color} ${statusConfig.pulse ? 'animate-pulse' : ''}`} size={20} />
                <span className="font-medium text-slate-900">{statusConfig.text}</span>
              </div>
              {job && (
                <p className="text-xs text-slate-500 mt-2">Job {job.jobId.slice(0, 8)}</p>
              )}
            </div>

            {/* Completed Actions */}
            {isCompleted && job && (
              <div className="space-y-4">
                {/* Premium Unlock */}
                {!job.isPremiumQuality && (
                  <div className={`bg-gradient-to-r ${serviceConfig.bgGradient} border border-black/5 p-6 rounded-2xl`}>
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-sm">
                        <Star className="text-amber-500" size={24} />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-slate-900 mb-1">Upgrade Your Result</h4>
                        <p className="text-sm text-slate-600">Unlock full resolution and premium quality</p>
                      </div>
                      <button
                        onClick={handleUnlockPremium}
                        disabled={unlocking}
                        className={`flex items-center gap-2 bg-gradient-to-r ${serviceConfig.accentColor} text-white px-6 py-3 rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all duration-300 disabled:opacity-60 hover:scale-[1.02] active:scale-[0.98] ring-1 ring-white/20`}
                      >
                        {unlocking ? (
                          <Loader2 className="animate-spin" size={16} />
                        ) : (
                          <>
                            <Unlock size={16} />
                            <span>{job.tokenCost || 1} token{(job.tokenCost || 1) > 1 ? 's' : ''}</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )}

                <div className="space-y-3">
                  {/* Continue Processing Button */}
                  <button
                    onClick={handleShowContinueModal}
                    className="w-full flex items-center justify-center gap-3 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white px-8 py-4 rounded-2xl font-semibold transition-all duration-300 shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] ring-1 ring-amber-500/20"
                  >
                    <Zap size={20} />
                    <span>Continue Processing</span>
                    <ArrowRight size={16} />
                  </button>

                  {/* Thumbnail Download Button */}
                  {job.thumbnailUrl && (
                    <button
                      onClick={() => downloadImage(job.thumbnailUrl!, 'PixelPerfect_Image')}
                      className="w-full flex items-center justify-center gap-3 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white px-8 py-4 rounded-2xl font-semibold transition-all duration-300 shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] ring-1 ring-blue-500/20"
                    >
                      <Download size={20} />
                      <span>Download Preview (Free)</span>
                    </button>
                  )}
                  
                  {/* Full Quality Download Button */}
                  {job.isPremiumQuality && job.processedImageUrl && (
                    <button
                      onClick={() => downloadImage(job.processedImageUrl!, 'full-quality-image_pixel_perfect')}
                      className="w-full flex items-center justify-center gap-3 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white px-8 py-4 rounded-2xl font-semibold transition-all duration-300 shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] ring-1 ring-green-500/20"
                    >
                      <Download size={20} />
                      <span>Download Full Quality</span>
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Continue Processing Modal */}
      {showContinueModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
          <div 
            className={`bg-white/95 backdrop-blur-3xl rounded-3xl p-8 shadow-2xl border border-white/30 ring-1 ring-slate-900/5 max-w-md w-full mx-4 transition-all duration-300 ${
              isModalAnimating ? 'scale-95 opacity-0' : 'scale-100 opacity-100'
            }`}
            onContextMenu={preventRightClick}
            onKeyDown={preventInspect}
            tabIndex={0}
            style={{ 
              userSelect: 'none',
              WebkitUserSelect: 'none',
              MozUserSelect: 'none',
              msUserSelect: 'none'
            }}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-r from-amber-500 to-orange-600 rounded-xl flex items-center justify-center">
                  <Zap className="text-white" size={20} />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-slate-900">Continue Processing</h3>
                  <p className="text-sm text-slate-600">Take your image to the next level</p>
                </div>
              </div>
              <button
                onClick={handleCloseContinueModal}
                className="w-8 h-8 bg-slate-100 hover:bg-slate-200 rounded-full flex items-center justify-center transition-colors duration-200"
              >
                <X size={16} className="text-slate-600" />
              </button>
            </div>

            {/* Processed Image Preview */}
            <div className="mb-6">
              <div className="aspect-[4/3] bg-slate-50 rounded-2xl overflow-hidden relative ring-1 ring-slate-900/5 shadow-inner">
                {job && job.thumbnailUrl && (
                  <div className="relative w-full h-full">
                    <img
                      src={job.thumbnailUrl}
                      alt="Result preview"
                      className="w-full h-full object-cover select-none"
                      onContextMenu={preventRightClick}
                      onDragStart={preventDragStart}
                      onMouseDown={preventSelection}
                      style={{ 
                        userSelect: 'none',
                        WebkitUserSelect: 'none',
                        MozUserSelect: 'none',
                        msUserSelect: 'none',
                        pointerEvents: 'none'
                      }}
                    />            
                    <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent pointer-events-none" />
                    <div className="absolute bottom-3 left-3 bg-white/90 backdrop-blur-sm px-3 py-1 rounded-full text-xs font-medium text-slate-700">
                      Current Result
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Service Selection */}
            <div className="space-y-3 mb-6">
              <p className="text-sm font-medium text-slate-700 mb-3">Choose your next enhancement:</p>
              {availableServices.map((service) => {
                const ServiceIcon = service.icon;
                const isSelected = selectedService === service.id;
                
                return (
                  <button
                    key={service.id}
                    onClick={() => {
                      console.log('🎯 Service selected:', service.id);
                      setSelectedService(service.id);
                    }}
                    className={`w-full p-4 rounded-2xl border-2 transition-all duration-300 text-left ${
                      isSelected 
                        ? `border-transparent bg-gradient-to-r ${service.gradient} text-white shadow-lg`
                        : 'border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                        isSelected 
                          ? 'bg-white/20' 
                          : `bg-gradient-to-r ${service.bgGradient}`
                      }`}>
                        <ServiceIcon 
                          className={isSelected ? 'text-white' : 'text-slate-600'} 
                          size={24} 
                        />
                      </div>
                      <div className="flex-1">
                        <h4 className={`font-semibold mb-1 ${
                          isSelected ? 'text-white' : 'text-slate-900'
                        }`}>
                          {service.title}
                        </h4>
                        <p className={`text-sm ${
                          isSelected ? 'text-white/90' : 'text-slate-600'
                        }`}>
                          {service.description}
                        </p>
                      </div>
                      {isSelected && (
                        <div className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center">
                          <CheckCircle className="text-white" size={16} />
                        </div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Modal Actions */}
            <div className="flex gap-3">
              <button
                onClick={handleCloseContinueModal}
                className="flex-1 px-6 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-medium transition-colors duration-200"
              >
                Cancel
              </button>
              <button
                onClick={handleContinueProcessing}
                disabled={!selectedService}
                className={`flex-1 px-6 py-3 rounded-xl font-semibold transition-all duration-300 flex items-center justify-center gap-2 ${
                  selectedService
                    ? 'bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-[0.98]'
                    : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                }`}
              >
                <span>Continue</span>
                <ArrowRight size={16} />
              </button>
            </div>

            {/* Info Note */}
            <div className="mt-4 p-3 bg-blue-50 rounded-xl">
              <p className="text-xs text-blue-800">
                💡 Your processed image will be used as input for the next enhancement
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default JobStatus;