import React, { useState, useEffect } from 'react';
import { Maximize, Upload, CheckCircle, Sparkles, Star, Zap, Target, Shield } from 'lucide-react';
import Layout from '../components/Layout';
import Navbar from '../components/Navbar';
import JobStatus from '../components/JobStatus';
import DragDropUploader from '../components/DragDropUploader';
import BeforeAfterSlider from '../components/BeforeAfterSlider';
import AnimatedGradientMesh from '../components/AnimatedGradientMesh';
import { JobTypeEnum } from '../types';
import { uploadImageAndCreateJob } from '../services/apiService';
import { useServiceAnimation } from '../hooks/useServiceAnimation';

const UpscalePage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [quality, setQuality] = useState<'FREE' | 'PREMIUM'>('FREE');


  // Agregar después de los useState
useEffect(() => {
  const urlParams = new URLSearchParams(window.location.search);
  const preloadImage = urlParams.get('preloadImage');
  
  if (preloadImage) {
    const imageUrl = decodeURIComponent(preloadImage);
    setPreview(imageUrl);
    
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      
      if (!ctx) {
        console.error('❌ Could not get canvas context');
        return;
      }
      
      canvas.width = img.width;
      canvas.height = img.height;
      
      // Asegurar que el canvas sea completamente transparente
      ctx.globalCompositeOperation = 'source-over';
      ctx.imageSmoothingEnabled = false; // Evitar suavizado que puede agregar colores
      
      // NO hacer clearRect, usar fillStyle transparente
      ctx.save();
      ctx.globalAlpha = 0;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.restore();
      
      // Dibujar imagen con máxima fidelidad
      ctx.globalAlpha = 1;
      ctx.drawImage(img, 0, 0, img.width, img.height, 0, 0, canvas.width, canvas.height);
      
      // Convertir directamente sin compresión
      canvas.toBlob((blob) => {
        if (blob) {
          const file = new File([blob], 'processed-image.png', { 
            type: 'image/png',
            lastModified: Date.now()
          });
          setSelectedFile(file);
          console.log('✅ Transparency-perfect image created');
        }
      }, 'image/png', 1.0);
    };
    
    img.onerror = () => setError('Error loading image. Please select manually.');
    img.crossOrigin = 'anonymous';
    img.src = imageUrl;
    
    window.history.replaceState({}, document.title, window.location.pathname);
  }
}, []);
  // Enhanced animation system
  const { heroRef, uploaderRef, configRef, workflowRef, featuresRef } = useServiceAnimation({
    serviceType: 'upscale',
    intensity: 'medium'
  });


  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setError('');

    const reader = new FileReader();
    reader.onload = () => {
      setPreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setError('');

    try {
      const jobConfig = {
        quality,
        scale: quality === 'PREMIUM' ? 4 : 2
      };

      const response = await uploadImageAndCreateJob(selectedFile, JobTypeEnum.UPSCALE, jobConfig);
      setCurrentJobId(response.jobId);

      // Reset form
      setSelectedFile(null);
      setPreview(null);
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleJobCompleted = () => {
    // Job completed
  };

  // Mock images for the slider
  const mockImages = [
    {
      before: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=300&h=300&fit=crop&q=50',
      after: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&h=600&fit=crop&q=90',
      title: '2x Upscaling',
      description: 'Enhanced resolution with preserved details and clarity'
    },
    {
      before: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=200&h=200&fit=crop&q=50',
      after: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&h=800&fit=crop&q=95',
      title: '4x Premium Upscaling',
      description: 'Professional quality enhancement for print and display'
    },
    {
      before: 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=250&h=250&fit=crop&q=60',
      after: 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=1000&h=1000&fit=crop&q=100',
      title: 'Detail Enhancement',
      description: 'AI-powered detail recovery and texture improvement'
    }
  ];

  const qualityOptions = [
    {
      type: 'FREE' as const,
      title: 'Standard Quality',
      description: 'Fast 2x upscaling with excellent quality for web use',
      scale: '2x',
      cost: 'FREE',
      features: ['2x resolution', 'Fast processing', 'Good for web use'],
      color: 'green'
    },
    {
      type: 'PREMIUM' as const,
      title: 'Premium Quality',
      description: 'Professional 4x upscaling with AI enhancement for print quality',
      scale: '4x',
      cost: '2 TOKENS',
      features: ['4x resolution', 'AI enhancement', 'Print quality'],
      color: 'orange'
    }
  ];

  

  return (
    <Layout>
      <AnimatedGradientMesh variant="upscale" intensity="subtle" />
      <Navbar />
      <div className="min-h-screen pt-20">
        <div className="max-w-4xl mx-auto py-12 px-6">

          {/* Hero Section */}
          <div ref={heroRef} className="text-center mb-16">
            <div className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-full font-medium text-sm mb-8">
              <Maximize size={16} />
              Image Upscaling
            </div>
            <h1 className="text-5xl md:text-6xl font-light text-slate-900 mb-6 leading-tight tracking-tight">
              Scale Beyond
              <br />
              <span className="font-medium italic bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 bg-clip-text text-transparent">
                Pixel Perfection
              </span>
            </h1>
            <p className="text-xl md:text-2xl text-slate-600 max-w-3xl mx-auto leading-relaxed font-light">
              Push the boundaries of resolution. Enhance without compromise.
              <br />
              <em className="text-slate-500">AI-powered upscaling that preserves every detail.</em>
            </p>
          </div>

          {/* Upload Section */}
          <div ref={uploaderRef} className="bg-white/60 backdrop-blur-xl p-8 md:p-12 rounded-3xl shadow-xl border border-slate-200/50 mb-8">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-gradient-to-br from-slate-100 to-slate-200 rounded-3xl flex items-center justify-center mx-auto mb-6">
                <Upload className="text-slate-700" size={24} />
              </div>
              <h3 className="text-3xl font-light text-slate-900 mb-3 tracking-tight">Upload Your Image</h3>
              <p className="text-slate-600 text-lg">Ready to supercharge your resolution?</p>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-2xl mb-8 text-center">
                {error}
              </div>
            )}

            <div className="space-y-8">
              <DragDropUploader
                onFileSelect={handleFileSelect}
                preview={preview}
                maxSize={10}
              />

              {selectedFile && (
                <div className="text-center bg-green-50 p-6 rounded-2xl border border-green-200">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <CheckCircle className="text-green-600" size={20} />
                    <strong className="text-green-800">Image Ready</strong>
                  </div>
                  <div className="text-slate-600">{selectedFile.name} ({Math.round(selectedFile.size / 1024)} KB)</div>
                </div>
              )}
            </div>
          </div>



          {/* Configuration Section */}
          {selectedFile && (
            <div ref={configRef} className="bg-white/60 backdrop-blur-xl p-8 md:p-12 rounded-3xl shadow-xl border border-slate-200/50 mb-8">
              <div className="text-center mb-12">
                <h3 className="text-3xl font-light text-slate-900 mb-3 tracking-tight">
                  <em className="italic text-slate-600">Choose</em> Your Scale
                </h3>
                <p className="text-slate-600 text-lg">Select the perfect upscaling level for your needs</p>
              </div>

              {/* Quality Selection */}
              <div className="mb-8">
                <h4 className="text-xl font-medium text-slate-900 mb-6 text-center">Upscaling Quality</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {qualityOptions.map((option) => (
                    <button
                      key={option.type}
                      onClick={() => setQuality(option.type)}
                      className={`group p-8 rounded-2xl border-2 text-left transition-all duration-300 ${quality === option.type
                        ? `border-${option.color}-500 bg-${option.color}-50 shadow-lg`
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-md'
                        }`}
                    >
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-colors duration-300 ${quality === option.type
                            ? option.color === 'green' ? 'bg-green-500 text-white' : 'bg-orange-500 text-white'
                            : 'bg-slate-100 text-slate-600 group-hover:bg-slate-200'
                            }`}>
                            {option.color === 'green' ? <Sparkles size={24} /> : <Star size={24} />}
                          </div>
                          <div>
                            <h5 className="font-medium text-slate-900">{option.title}</h5>
                            <div className="text-sm text-slate-600">{option.scale} resolution</div>
                          </div>
                        </div>
                        <div className={`px-3 py-1 rounded-full text-xs font-bold ${option.color === 'green'
                          ? 'bg-green-500 text-white'
                          : 'bg-orange-500 text-white'
                          }`}>
                          {option.cost}
                        </div>
                      </div>
                      <p className="text-sm text-slate-600 mb-4">{option.description}</p>
                      <div className="space-y-1">
                        {option.features.map((feature, index) => (
                          <div key={index} className="flex items-center gap-2 text-xs text-slate-500">
                            <div className="w-1 h-1 bg-slate-400 rounded-full" />
                            {feature}
                          </div>
                        ))}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={handleUpload}
                disabled={!selectedFile || loading}
                className="w-full bg-slate-900 hover:bg-slate-800 text-white py-6 px-8 rounded-2xl font-medium transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.02] text-lg"
              >
                <div className="flex items-center justify-center gap-3">
                  {loading ? (
                    <>
                      <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Enhancing Resolution...
                    </>
                  ) : (
                    <>
                      <Sparkles size={24} />
                      Upscale to {quality === 'PREMIUM' ? '4x' : '2x'}
                    </>
                  )}
                </div>
              </button>
            </div>
          )}

          {/* Before/After Examples */}
          <div className="mb-8">
            <BeforeAfterSlider images={mockImages} />
          </div>

          {/* Job Status Section */}
          {currentJobId && (
            <div className="mb-8">
              <JobStatus
                initialImageUrl={preview || ''}
                jobId={currentJobId}
                serviceType="upscale"
                onJobCompleted={handleJobCompleted}
              />
            </div>
          )}

          {/* How it Works Section */}
          <div ref={workflowRef} className="bg-white/60 backdrop-blur-xl p-8 md:p-12 rounded-3xl shadow-xl border border-slate-200/50 mb-8">
            <div className="text-center mb-16">
              <h3 className="text-4xl md:text-5xl font-light text-slate-900 mb-6 tracking-tight">
                <em className="italic font-medium bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 bg-clip-text text-transparent">Intelligent</em> Enhancement
              </h3>
              <p className="text-xl text-slate-600 max-w-2xl mx-auto font-light">
                Watch AI transform low resolution into crystal-clear detail
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">

              {/* Step 1 */}
              <div className="workflow-card text-center group opacity-0">
                <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:bg-slate-900 transition-colors duration-300 shadow-lg group-hover:shadow-xl">
                  <Upload className="text-slate-600 group-hover:text-white transition-colors duration-300" size={28} />
                </div>
                <h4 className="text-xl font-medium text-slate-900 mb-4">Image Analysis</h4>
                <p className="text-slate-600 leading-relaxed">
                  AI analyzes pixel patterns, textures, and edge details with surgical precision
                </p>
              </div>

              {/* Step 2 */}
              <div className="workflow-card text-center group opacity-0">
                <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:bg-slate-900 transition-colors duration-300 shadow-lg group-hover:shadow-xl">
                  <Target className="text-slate-600 group-hover:text-white transition-colors duration-300" size={28} />
                </div>
                <h4 className="text-xl font-medium text-slate-900 mb-4">Smart Enhancement</h4>
                <p className="text-slate-600 leading-relaxed">
                  Intelligent interpolation and detail enhancement using advanced neural networks
                </p>
              </div>

              {/* Step 3 */}
              <div className="workflow-card text-center group opacity-0">
                <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:bg-slate-900 transition-colors duration-300 shadow-lg group-hover:shadow-xl">
                  <Zap className="text-slate-600 group-hover:text-white transition-colors duration-300" size={28} />
                </div>
                <h4 className="text-xl font-medium text-slate-900 mb-4">Quality Optimization</h4>
                <p className="text-slate-600 leading-relaxed">
                  Final quality optimization and artifact removal for professional results
                </p>
              </div>
            </div>
          </div>

          {/* Features Section */}
          <div ref={featuresRef} className="bg-white/60 backdrop-blur-xl p-8 md:p-12 rounded-3xl shadow-xl border border-slate-200/50">
            <div className="text-center mb-16">
              <h3 className="text-4xl md:text-5xl font-light text-slate-900 mb-6 tracking-tight">
                Why Choose <em className="italic text-slate-600">Image Upscaling</em>
              </h3>
              <p className="text-xl text-slate-600 max-w-2xl mx-auto font-light">
                Professional-grade resolution enhancement with unmatched quality
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
              {[
                {
                  icon: Zap,
                  title: "Lightning Fast",
                  description: "Process and enhance images in seconds with our optimized AI infrastructure."
                },
                {
                  icon: Target,
                  title: "Detail Preserving",
                  description: "Advanced algorithms that preserve fine details while enhancing resolution."
                },
                {
                  icon: Shield,
                  title: "Privacy First",
                  description: "Your images are processed securely and never stored permanently."
                }
              ].map((feature) => (
                <div
                  key={feature.title}
                  className="text-center group"
                >
                  <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg group-hover:shadow-xl transition-shadow duration-300">
                    <feature.icon className="text-slate-700" size={28} />
                  </div>
                  <h3 className="text-xl font-medium text-slate-900 mb-4">
                    {feature.title}
                  </h3>
                  <p className="text-slate-600 leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default UpscalePage;