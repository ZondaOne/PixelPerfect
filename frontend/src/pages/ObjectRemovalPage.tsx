import React, { useState } from 'react';
import { Sparkles, Upload, CheckCircle, Star, MousePointer, Wand2, Zap, Target, Shield } from 'lucide-react';
import Layout from '../components/Layout';
import Navbar from '../components/Navbar';
import ObjectRemoval from '../components/ObjectRemover';
import JobStatus from '../components/JobStatus';
import { JobTypeEnum } from '../types';
import DragDropUploader from '../components/DragDropUploader';
import BeforeAfterSlider from '../components/BeforeAfterSlider';
import AnimatedGradientMesh from '../components/AnimatedGradientMesh';
import { uploadImageAndCreateJob } from '../services/apiService';
import { useServiceAnimation } from '../hooks/useServiceAnimation';

export interface ObjectRemovalConfig {
  method: 'BOUNDING_BOX' | 'PRECISE_MASK';
  coordinates?: {x: number, y: number, width: number, height: number};
  quality?: 'FREE' | 'PREMIUM';
  mask?: ImageData;
  detectionSettings?: {
    sensitivity: number;
    edgeThreshold: number;
    smoothing: number;
  };
}


interface ImageDimensions {
  original: { width: number; height: number };
  preview: { width: number; height: number };
}

const ObjectRemovalPage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [config, setConfig] = useState<ObjectRemovalConfig>({
    method: 'BOUNDING_BOX',
    quality: 'FREE'
  });
  

  const [imageDimensions, setImageDimensions] = useState<ImageDimensions | null>(null);

  // Enhanced animation system
  const { heroRef, uploaderRef, configRef, workflowRef, featuresRef } = useServiceAnimation({
    serviceType: 'object-removal',
    intensity: 'medium'
  });

  const handleFileSelect = (file: File) => {
    const isDifferentFile = !selectedFile || selectedFile.name !== file.name || selectedFile.size !== file.size;
    
    setSelectedFile(file);
    setError('');
 
    if (isDifferentFile) {
      setConfig({
        method: 'BOUNDING_BOX',
        quality: 'FREE'
      });
      setImageDimensions(null);
    }

    const reader = new FileReader();
    reader.onload = () => {
      const imageUrl = reader.result as string;
      setPreview(imageUrl);
      
   
      const img = new Image();
      img.onload = () => {
        setImageDimensions({
          original: { width: img.naturalWidth, height: img.naturalHeight },
          preview: { width: 0, height: 0 } 
        });
      };
      img.src = imageUrl;
    };
    reader.readAsDataURL(file);
  };

  const handleConfigChange = (newConfig: ObjectRemovalConfig, previewDimensions?: { width: number; height: number }) => {
    console.log('Config updated:', newConfig); 
    

    if (previewDimensions && imageDimensions) {
      setImageDimensions(prev => prev ? {
        ...prev,
        preview: previewDimensions
      } : null);
    }
    
    setConfig(newConfig);
  };

  const validateConfig = (): boolean => {
    if (config.method === 'BOUNDING_BOX' && !config.coordinates) {
      setError('Please select an area to remove using the bounding box tool');
      return false;
    }
    
    if (config.method === 'PRECISE_MASK' && !config.mask) {
      setError('Please draw a mask over the objects you want to remove');
      return false;
    }

    return true;
  };


  const scaleCoordinatesToOriginal = (previewCoords: {x: number, y: number, width: number, height: number}): {x: number, y: number, width: number, height: number} => {
    if (!imageDimensions) {
      console.warn('No image dimensions available, returning original coordinates');
      return previewCoords;
    }

    const { original, preview } = imageDimensions;
    
    if (preview.width === 0 || preview.height === 0) {
      console.warn('Preview dimensions are 0, returning original coordinates');
      return previewCoords;
    }

    const scaleX = original.width / preview.width;
    const scaleY = original.height / preview.height;

    const scaledCoords = {
      x: Math.round(previewCoords.x * scaleX),
      y: Math.round(previewCoords.y * scaleY),
      width: Math.round(previewCoords.width * scaleX),
      height: Math.round(previewCoords.height * scaleY)
    };

    console.log('Coordinate scaling:', {
      original: previewCoords,
      scaled: scaledCoords,
      imageDimensions,
      scales: { scaleX, scaleY }
    });

    return scaledCoords;
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    if (!validateConfig()) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      console.log('Uploading with config:', config); // Debug
      console.log('Image dimensions:', imageDimensions); // Debug
      
  
      const uploadConfig: any = {
        method: config.method,
        quality: config.quality || 'FREE',
      };

 
      if (config.coordinates) {
        uploadConfig.coordinates = scaleCoordinatesToOriginal(config.coordinates);
      }

  
      if (config.detectionSettings) {
        uploadConfig.detectionSettings = config.detectionSettings;
      }

      console.log('Final upload config:', {
        ...uploadConfig,
        mask: uploadConfig.mask ? `base64 string (${uploadConfig.mask.length} chars)` : undefined
      }); 

      const response = await uploadImageAndCreateJob(
        selectedFile, 
        JobTypeEnum.OBJECT_REMOVAL, 
        uploadConfig
      );
      
      console.log('Upload response:', response); // Debug
      setCurrentJobId(response.jobId);

      // Reset form
      setSelectedFile(null);
      setPreview(null);
      setConfig({
        method: 'BOUNDING_BOX',
        quality: 'FREE'
      });
      setImageDimensions(null);
    } catch (err: any) {
      console.error('Upload error:', err); // Debug
      console.error('Error details:', {
        message: err.message,
        status: err.status,
        response: err.response
      });
      

      if (err.response) {
        setError(`Server error: ${err.response.status} - ${err.response.statusText}`);
      } else if (err.message) {
        setError(err.message);
      } else {
        setError('Upload failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleJobCompleted = () => {
    // Job completed
    console.log('Job completed');
  };

  // Mock images for the slider
  const mockImages = [
    {
      before: 'https://i.imgur.com/djgBnnA.jpeg',
      after: 'https://i.imgur.com/aAyqjKV.jpeg',
      title: 'Tourist Removal',
      description: 'Remove unwanted people from your perfect landscape shots'
    },
    {
      before: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=600&h=600&fit=crop',
      after: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=600&h=600&fit=crop&blend=transparent',
      title: 'Object Cleanup',
      description: 'Clean removal of distracting objects with natural background fill'
    },
    {
      before: 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=600&h=600&fit=crop',
      after: 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=600&h=600&fit=crop&blend=nature',
      title: 'Seamless Restoration',
      description: 'Professional-grade object removal with intelligent background reconstruction'
    }
  ];

  const removalMethods = [
    {
      type: 'BOUNDING_BOX' as const,
      title: 'Smart Detection',
      description: 'AI automatically identifies and removes unwanted objects',
      icon: Wand2,
      features: ['Automatic object detection', 'One-click removal', 'Fast processing'],
    },
    {
      type: 'PRECISE_MASK' as const,
      title: 'Precise Selection',
      description: 'Manual selection for exact control over what gets removed',
      icon: MousePointer,
      features: ['Precise brush tool', 'Custom selection', 'Professional control'],
      badge: 'Coming Soon'
    }
  ];

  const qualityOptions = [
    {
      type: 'FREE' as const,
      title: 'Free Quality',
      description: 'Basic object removal with standard processing',
      cost: '0 TOKENS',
      color: 'blue'
    },
    {
      type: 'PREMIUM' as const,
      title: 'Premium Quality', 
      description: 'Professional-grade removal with advanced content-aware fill',
      cost: '5 TOKENS',
      color: 'purple'
    }
  ];

  // Verificar si la configuración está completa
  const isConfigComplete = () => {
    if (config.method === 'BOUNDING_BOX') {
      return config.coordinates !== undefined;
    }
    if (config.method === 'PRECISE_MASK') {
      return config.mask !== undefined;
    }
    return false;
  };

  return (
    <Layout>
      <AnimatedGradientMesh variant="object-removal" intensity="subtle" />
      <Navbar />
      <div className="min-h-screen pt-20">
        <div className="max-w-4xl mx-auto py-12 px-6">

          {/* Hero Section */}
          <div ref={heroRef} className="text-center mb-16">
            <div className="inline-flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-full font-medium text-sm mb-8">
              <Sparkles size={16} />
              Object Removal
            </div>
            <h1 className="text-5xl md:text-6xl font-light text-slate-900 mb-6 leading-tight tracking-tight">
              Erase the
              <br />
              <span className="font-medium italic bg-gradient-to-r from-violet-600 via-purple-600 to-fuchsia-600 bg-clip-text text-transparent">
                Unwanted
              </span>
            </h1>
            <p className="text-xl md:text-2xl text-slate-600 max-w-3xl mx-auto leading-relaxed font-light">
              Make distractions disappear. Perfect your composition.
              <br />
              <em className="text-slate-500">AI-powered object removal that leaves no trace.</em>
            </p>
          </div>

          {/* Upload Section */}
          <div ref={uploaderRef} className="bg-white/60 backdrop-blur-xl p-8 md:p-12 rounded-3xl shadow-xl border border-slate-200/50 mb-8">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-gradient-to-br from-slate-100 to-slate-200 rounded-3xl flex items-center justify-center mx-auto mb-6">
                <Upload className="text-slate-700" size={24} />
              </div>
              <h3 className="text-3xl font-light text-slate-900 mb-3 tracking-tight">Upload Your Image</h3>
              <p className="text-slate-600 text-lg">Ready to perfect your composition?</p>
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
                  <div className="text-slate-600">
                    {selectedFile.name} ({Math.round(selectedFile.size / 1024)} KB)
                    {imageDimensions && (
                      <div className="text-xs text-slate-500 mt-1">
                        Original: {imageDimensions.original.width}×{imageDimensions.original.height}px
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Object Removal Component */}
            {preview && (
              <div className="mt-8">
                <ObjectRemoval
                  config={config}
                  onChange={handleConfigChange}
                  imagePreview={preview}
                />
              </div>
            )}
          </div>

          {/* Configuration Section */}
          {selectedFile && (
            <div ref={configRef} className="bg-white/60 backdrop-blur-xl p-8 md:p-12 rounded-3xl shadow-xl border border-slate-200/50 mb-8">
              <div className="text-center mb-12">
                <h3 className="text-3xl font-light text-slate-900 mb-3 tracking-tight">
                  <em className="italic text-slate-600">Choose</em> Your Method
                </h3>
                <p className="text-slate-600 text-lg">Select how you want to remove unwanted objects</p>
              </div>

              {/* Removal Method Selection */}
              <div className="mb-12">
                <h4 className="text-xl font-medium text-slate-900 mb-6 text-center">Removal Method</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {removalMethods.map((method) => (
                    <button
                      key={method.type}
                      onClick={() => setConfig(prev => ({ ...prev, method: method.type }))}
                      disabled={method.badge === 'Coming Soon'}
                      className={`group p-8 rounded-2xl border-2 text-center transition-all duration-300 relative ${
                        config.method === method.type && method.badge !== 'Coming Soon'
                          ? 'border-slate-900 bg-slate-50 shadow-lg'
                          : method.badge === 'Coming Soon'
                            ? 'border-slate-200 bg-slate-50 opacity-60 cursor-not-allowed'
                            : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-md'
                      }`}
                    >
                      {method.badge && (
                        <div className="absolute top-4 right-4 bg-orange-500 text-white px-2 py-1 rounded-full text-xs font-bold">
                          {method.badge}
                        </div>
                      )}
                      <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4 transition-colors duration-300 ${
                        config.method === method.type && method.badge !== 'Coming Soon'
                          ? 'bg-slate-900 text-white'
                          : method.badge === 'Coming Soon'
                            ? 'bg-slate-200 text-slate-400'
                            : 'bg-slate-100 text-slate-600 group-hover:bg-slate-200'
                      }`}>
                        <method.icon size={24} />
                      </div>
                      <h5 className="font-medium text-slate-900 mb-2">{method.title}</h5>
                      <p className="text-sm text-slate-600 mb-4">{method.description}</p>
                      <div className="space-y-1">
                        {method.features.map((feature, index) => (
                          <div key={index} className="flex items-center justify-center gap-2 text-xs text-slate-500">
                            <div className="w-1 h-1 bg-slate-400 rounded-full" />
                            {feature}
                          </div>
                        ))}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Quality Selection */}
              <div className="mb-8">
                <h4 className="text-xl font-medium text-slate-900 mb-6 text-center">Quality Level</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {qualityOptions.map((option) => (
                    <button
                      key={option.type}
                      onClick={() => setConfig(prev => ({ ...prev, quality: option.type }))}
                      className={`group p-8 rounded-2xl border-2 text-left transition-all duration-300 ${
                        config.quality === option.type
                          ? `border-${option.color}-500 bg-${option.color}-50 shadow-lg`
                          : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-md'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-colors duration-300 ${
                            config.quality === option.type
                              ? option.color === 'blue' ? 'bg-blue-500 text-white' : 'bg-purple-500 text-white'
                              : 'bg-slate-100 text-slate-600 group-hover:bg-slate-200'
                          }`}>
                            {option.color === 'blue' ? <Sparkles size={24} /> : <Star size={24} />}
                          </div>
                          <div>
                            <h5 className="font-medium text-slate-900">{option.title}</h5>
                            <div className="text-sm text-slate-600">Advanced AI processing</div>
                          </div>
                        </div>
                        <div className={`px-3 py-1 rounded-full text-xs font-bold ${
                          option.color === 'blue'
                            ? 'bg-blue-500 text-white'
                            : 'bg-purple-500 text-white'
                        }`}>
                          {option.cost}
                        </div>
                      </div>
                      <p className="text-sm text-slate-600">{option.description}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Upload Button */}
              <button
                onClick={handleUpload}
                disabled={!selectedFile || loading || !isConfigComplete()}
                className="w-full bg-slate-900 hover:bg-slate-800 text-white py-6 px-8 rounded-2xl font-medium transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.02] text-lg"
              >
                <div className="flex items-center justify-center gap-3">
                  {loading ? (
                    <>
                      <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Removing Objects...
                    </>
                  ) : !isConfigComplete() ? (
                    <>
                      <Target size={24} />
                      Select Objects First
                    </>
                  ) : (
                    <>
                      <Sparkles size={24} />
                      Remove Objects
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
                serviceType="object-removal"
                onJobCompleted={handleJobCompleted}
              />
            </div>
          )}

          {/* How it Works Section */}
          <div ref={workflowRef} className="bg-white/60 backdrop-blur-xl p-8 md:p-12 rounded-3xl shadow-xl border border-slate-200/50 mb-8">
            <div className="text-center mb-16">
              <h3 className="text-4xl md:text-5xl font-light text-slate-900 mb-6 tracking-tight">
                <em className="italic font-medium bg-gradient-to-r from-violet-600 via-purple-600 to-fuchsia-600 bg-clip-text text-transparent">Smart</em> Removal
              </h3>
              <p className="text-xl text-slate-600 max-w-2xl mx-auto font-light">
                Watch AI seamlessly erase objects and restore backgrounds
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {/* Step 1 */}
              <div className="workflow-card text-center group opacity-0">
                <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:bg-slate-900 transition-colors duration-300 shadow-lg group-hover:shadow-xl">
                  <Upload className="text-slate-600 group-hover:text-white transition-colors duration-300" size={28} />
                </div>
                <h4 className="text-xl font-medium text-slate-900 mb-4">Object Detection</h4>
                <p className="text-slate-600 leading-relaxed">
                  AI scans your image to identify unwanted objects and their boundaries
                </p>
              </div>

              {/* Step 2 */}
              <div className="workflow-card text-center group opacity-0">
                <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:bg-slate-900 transition-colors duration-300 shadow-lg group-hover:shadow-xl">
                  <Target className="text-slate-600 group-hover:text-white transition-colors duration-300" size={28} />
                </div>
                <h4 className="text-xl font-medium text-slate-900 mb-4">Content Analysis</h4>
                <p className="text-slate-600 leading-relaxed">
                  Advanced algorithms analyze surrounding areas to understand background patterns
                </p>
              </div>

              {/* Step 3 */}
              <div className="workflow-card text-center group opacity-0">
                <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:bg-slate-900 transition-colors duration-300 shadow-lg group-hover:shadow-xl">
                  <Zap className="text-slate-600 group-hover:text-white transition-colors duration-300" size={28} />
                </div>
                <h4 className="text-xl font-medium text-slate-900 mb-4">Seamless Fill</h4>
                <p className="text-slate-600 leading-relaxed">
                  Objects are removed and replaced with natural background content that matches perfectly
                </p>
              </div>
            </div>
          </div>

          {/* Features Section */}
          <div ref={featuresRef} className="bg-white/60 backdrop-blur-xl p-8 md:p-12 rounded-3xl shadow-xl border border-slate-200/50">
            <div className="text-center mb-16">
              <h3 className="text-4xl md:text-5xl font-light text-slate-900 mb-6 tracking-tight">
                Why Choose <em className="italic text-slate-600">Object Removal</em>
              </h3>
              <p className="text-xl text-slate-600 max-w-2xl mx-auto font-light">
                Professional object removal with intelligent background restoration
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
              {[
                {
                  icon: Zap,
                  title: "Lightning Fast",
                  description: "Remove unwanted objects in seconds with our optimized AI infrastructure."
                },
                {
                  icon: Target,
                  title: "Pixel Perfect",
                  description: "Seamless object removal that leaves no traces or artifacts behind."
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

export default ObjectRemovalPage;