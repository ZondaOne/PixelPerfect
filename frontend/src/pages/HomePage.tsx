import React, { useEffect, useRef, useState } from 'react';
import Layout from '../components/Layout';
import Navbar from '../components/Navbar';
import AnimatedGradientMesh from '../components/AnimatedGradientMesh';
import AnimatedNetMesh from '../components/AnimatedNetMesh';
import { isAuthenticated } from '../services/authService';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { 
  Scissors, 
  Maximize, 
  Sparkles, 
  Expand, 
  Wand2, 
  FileImage, 
  ArrowRight, 
  Star, 
  Shield, 
  Zap, 
  Target,
  Check,
  ChevronDown
} from 'lucide-react';
import logo from '../assets/logo.png';
import { motion } from 'framer-motion';
import DragDropUploader from '../components/DragDropUploader';
import { useNavigate } from 'react-router-dom';

gsap.registerPlugin(ScrollTrigger);

const HomePage: React.FC = () => {
  const [showContent] = useState(true);
  const [openFAQ, setOpenFAQ] = useState<number | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [isAnimating, setIsAnimating] = useState(true);
  
  const heroRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);
  const logoRef = useRef<HTMLImageElement>(null);
  const servicesRef = useRef<HTMLDivElement>(null);
  const pipelineRef = useRef<HTMLDivElement>(null);
  const partnersRef = useRef<HTMLDivElement>(null);
  const audienceRef = useRef<HTMLDivElement>(null);
  const whyChooseRef = useRef<HTMLDivElement>(null);
  const pricingRef = useRef<HTMLDivElement>(null);
  const faqRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const handleFileSelect = (file: File) => {
  setUploadedFile(file);
  const url = URL.createObjectURL(file);
  setPreviewUrl(url);

  const reader = new FileReader();
  reader.onload = (e) => {
    if (e.target?.result) {
      // Guardar la imagen como base64 para que persista al navegar
      localStorage.setItem('uploadedImageData', e.target.result as string);
      localStorage.setItem('uploadedImageName', file.name);
      
      // Pequeño delay para mejor UX antes de navegar
      setTimeout(() => {
        navigate('/background-removal');
      }, 500);
    }
  };
  reader.readAsDataURL(file);
};

useEffect(() => {
  return () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
  };
}, [previewUrl]);
  // E-commerce focused services
  const services = [
    {
      href: "/background-removal",
      icon: Scissors,
      title: "Product Background Removal",
      description: "Remove backgrounds from product photos instantly",
      tokens: "Free"
    },
    {
      href: "/enlarge",
      icon: Expand,
      title: "Smart Product Expansion",
      description: "AI-powered canvas expansion for lifestyle shots",
      tokens: "1 token"
    },
    {
      href: "/upscale",
      icon: Maximize,
      title: "High-Resolution Upscaling",
      description: "Enhance product images up to 4K resolution",
      tokens: "Free"
    },
    {
      href: "/object-removal",
      icon: Sparkles,
      title: "Defect & Object Removal",
      description: "Remove scratches, dust, and unwanted objects",
      tokens: "Free"
    },
    {
      href: "/image-generation",
      icon: Wand2,
      title: "Product Variations Generator",
      description: "Create product mockups and variations",
      tokens: "1 token"
    },
    {
      href: "#",
      icon: FileImage,
      title: "Batch Processing",
      description: "Process hundreds of products at once",
      tokens: "Coming Soon",
      comingSoon: true
    }
  ];

  // E-commerce pipeline steps
  const pipelineSteps = [
    {
      title: "Raw Product Photo",
      description: "Original product image with cluttered background",
      tech: "Input Processing",
      metrics: {
        quality: "Standard",
        conversion: "2.1%",
        engagement: "Low"
      }
    },
    {
      title: "Background Removed",
      description: "Clean, professional product isolation",
      tech: "AI Background Removal",
      metrics: {
        quality: "Professional",
        conversion: "4.2%",
        engagement: "Medium"
      }
    },
    {
      title: "AI Enhanced & Upscaled",
      description: "Crystal clear 4K resolution with enhanced details",
      tech: "Neural Upscaling",
      metrics: {
        quality: "Premium",
        conversion: "7.8%",
        engagement: "High"
      }
    }
  ];

  // E-commerce partners
  const partners = [
    "Shopify Plus",
    "Amazon Sellers",
    "Etsy Stores",
    "WooCommerce",
    "BigCommerce",
    "Magento",
    "eBay Pro",
    "Walmart Marketplace"
  ];

  // E-commerce audience
  const audience = [
    {
      title: "For Online Retailers",
      description: "Transform your product catalog with professional-grade images that drive conversions and reduce returns.",
      iconBg: "bg-gradient-to-br from-blue-50 to-blue-100",
      iconColor: "text-blue-600",
      borderColor: "border-blue-200/50",
      lines: [
        { width: "w-8", color: "bg-blue-300", delay: "0s" },
        { width: "w-6", color: "bg-blue-400", delay: "0.5s" },
        { width: "w-4", color: "bg-blue-500", delay: "1s" }
      ]
    },
    {
      title: "For Marketplace Sellers", 
      description: "Stand out on Amazon, eBay, and Etsy with stunning product images that meet platform requirements.",
      iconBg: "bg-gradient-to-br from-emerald-50 to-emerald-100",
      iconColor: "text-emerald-600",
      borderColor: "border-emerald-200/50",
      lines: [
        { width: "w-6", color: "bg-emerald-300", delay: "0s" },
        { width: "w-8", color: "bg-emerald-400", delay: "0.3s" },
        { width: "w-5", color: "bg-emerald-500", delay: "0.6s" }
      ]
    },
    {
      title: "For Brands & Agencies",
      description: "Scale your product photography workflow with API integration and batch processing capabilities.",
      iconBg: "bg-gradient-to-br from-purple-50 to-purple-100",
      iconColor: "text-purple-600",
      borderColor: "border-purple-200/50",
      lines: [
        { width: "w-7", color: "bg-purple-300", delay: "0s" },
        { width: "w-5", color: "bg-purple-400", delay: "0.4s" },
        { width: "w-9", color: "bg-purple-500", delay: "0.8s" }
      ]
    }
  ];

  // E-commerce focused features
  const whyFeatures = [
    {
      icon: Shield,
      title: "E-commerce Security",
      description: "Your product images are processed securely and never stored permanently. GDPR compliant."
    },
    {
      icon: Zap,
      title: "Lightning Fast Processing",
      description: "Process thousands of product images in minutes. Perfect for large catalogs and flash sales."
    },
    {
      icon: Target,
      title: "Conversion Optimized",
      description: "Professional-grade results that increase click-through rates and reduce return rates."
    }
  ];

  // E-commerce pricing
  const pricingPlans = [
    {
      name: "Starter Store",
      price: "$0",
      period: "forever",
      description: "Perfect for small online stores",
      features: [
        "50 product images per month",
        "Background removal (unlimited)",
        "Image upscaling (unlimited)",
        "Object removal (unlimited)",
        "Email support"
      ],
      cta: "Start Free",
      popular: false
    },
    {
      name: "Growing Business",
      price: "$29",
      period: "month",
      description: "For expanding e-commerce stores",
      features: [
        "1,000 product images per month",
        "All image processing tools",
        "Priority processing queue",
        "Batch upload (up to 100)",
        "API access",
        "Phone & chat support"
      ],
      cta: "Start Free Trial",
      popular: true
    },
    {
      name: "Enterprise",
      price: "$99",
      period: "month",
      description: "For large catalogs and agencies",
      features: [
        "Unlimited product images",
        "Advanced batch processing",
        "Custom integrations",
        "Dedicated account manager",
        "White-label options",
        "99.9% SLA guarantee"
      ],
      cta: "Contact Sales",
      popular: false
    }
  ];

  // E-commerce FAQ
  const faqs = [
    {
      question: "How does AI product image processing improve sales?",
      answer: "Professional product images with clean backgrounds and high resolution increase customer trust, reduce bounce rates, and can improve conversion rates by 30-40%. Clear, detailed images also reduce return rates."
    },
    {
      question: "Can I process images in bulk for my entire catalog?",
      answer: "Yes! Our batch processing feature allows you to upload and process hundreds of product images simultaneously. Enterprise plans include unlimited batch processing."
    },
    {
      question: "Are the processed images optimized for e-commerce platforms?",
      answer: "Absolutely. Our AI automatically optimizes images for major platforms like Amazon, Shopify, eBay, and Etsy, ensuring they meet size, format, and quality requirements."
    },
    {
      question: "How quickly can I process my product images?",
      answer: "Most images are processed in under 10 seconds. For bulk processing, our enterprise solution can handle thousands of images per hour."
    },
    {
      question: "Do you offer API integration for my e-commerce platform?",
      answer: "Yes, we provide RESTful APIs and direct integrations with popular e-commerce platforms. This allows automatic processing of new product uploads."
    },
    {
      question: "What happens to my original product images?",
      answer: "Your original images are securely processed and immediately deleted after processing. We never store or use your product images for training."
    }
  ];

  

  // Animation effects
  useEffect(() => {
    if (!showContent) return;

    // Hero animations
    const tl = gsap.timeline();
    
    gsap.set([logoRef.current, titleRef.current, subtitleRef.current, ctaRef.current], {
      opacity: 0,
      y: 40,
      scale: 0.95
    });

    tl.to(logoRef.current, {
      opacity: 1,
      scale: 1,
      y: 0,
      duration: 1.2,
      ease: "power3.out"
    })
    .to(titleRef.current, {
      opacity: 1,
      y: 0,
      scale: 1,
      duration: 1.4,
      ease: "power3.out"
    }, "-=0.8")
    .to(subtitleRef.current, {
      opacity: 1,
      y: 0,
      scale: 1,
      duration: 1.2,
      ease: "power3.out"
    }, "-=1.0")
    .to(ctaRef.current, {
      opacity: 1,
      y: 0,
      scale: 1,
      duration: 1,
      ease: "power3.out"
    }, "-=0.8");

    // Floating logo animation
    gsap.to(logoRef.current, {
      y: -8,
      duration: 3,
      repeat: -1,
      yoyo: true,
      ease: "power2.inOut",
      delay: 1.5
    });

    // Scroll-triggered animations for sections
    const sections = [servicesRef, pipelineRef, partnersRef, audienceRef, whyChooseRef, pricingRef, faqRef];
    
    sections.forEach((ref) => {
      if (ref.current) {
        gsap.fromTo(ref.current.children, 
          {
            opacity: 0,
            y: 30
          },
          {
            opacity: 1,
            y: 0,
            duration: 0.8,
            ease: "power3.out",
            stagger: 0.1,
            scrollTrigger: {
              trigger: ref.current,
              start: "top 85%",
              toggleActions: "play none none reverse"
            }
          }
        );
      }
    });

  }, [showContent]);

  // Infinite scroll animation style
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes infiniteScroll {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
      }
      .animate-infinite-scroll {
        animation: infiniteScroll 25s linear infinite;
      }
      .animate-infinite-scroll:hover {
        animation-play-state: paused;
      }
    `;
    document.head.appendChild(style);
    
    return () => {
      document.head.removeChild(style);
    };
  }, []);

  if (!isAuthenticated()) {
    return (
      <Layout>
        <Navbar />
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center px-6">
          <div className="max-w-md w-full">
            <div className="bg-white/80 backdrop-blur-xl rounded-3xl p-8 shadow-2xl border border-white/50">
              <div className="text-center mb-8">
                <img
                  src={logo}
                  alt="Pixel Perfect AI"
                  className="w-16 h-16 mx-auto mb-6 drop-shadow-lg"
                />
                <h1 className="text-2xl font-medium text-slate-900 mb-3 tracking-tight">
                  Welcome to PixelPerfect E-commerce AI
                </h1>
                <p className="text-slate-600 text-sm leading-relaxed">
                  Professional product image processing powered by cutting-edge AI technology.
                </p>
              </div>
              <a
                href="/login"
                className="w-full bg-slate-900 hover:bg-slate-800 text-white py-3 px-6 rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
              >
                <Star size={16} />
                Get Started
                <ArrowRight size={16} />
              </a>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <AnimatedGradientMesh variant="default" intensity="subtle" />
      <AnimatedNetMesh intensity="subtle" />
      <Navbar />

      {/* Hero Section */}
      <div ref={heroRef} className="min-h-screen flex items-center justify-center px-6 py-20">
        <div className="max-w-4xl mx-auto text-center">
          
          {/* Simple logo badge */}
          <div className="inline-flex items-center gap-3 px-4 py-2 bg-white/80 backdrop-blur-sm rounded-full border border-slate-200/50 mb-12 opacity-0" ref={logoRef}>
            <img
              src={logo}
              alt="Pixel Perfect AI"
              className="w-6 h-6"
            />
            <span className="text-sm font-medium text-slate-600">
              PixelPerfect E-commerce AI
            </span>
          </div>

          {/* Clean, impactful title */}
          <h1
            ref={titleRef}
            className="text-6xl md:text-8xl font-light text-slate-900 mb-8 leading-tight tracking-tight opacity-0"
          >
            Transform your
            <br />
            <span className="font-medium">product catalog</span>
          </h1>

          {/* Simple subtitle */}
          <p
            ref={subtitleRef}
            className="text-xl text-slate-600 mb-16 max-w-2xl mx-auto leading-relaxed opacity-0"
          >
            Professional AI image processing for e-commerce. 
            Remove backgrounds, upscale resolution, boost conversions. 
            All in seconds.
          </p>

          {/* Clean CTA buttons */}
          <div
            ref={ctaRef}
            className="flex flex-col sm:flex-row gap-4 justify-center items-center opacity-0"
          >
            <a
              href="/background-removal"
              className="bg-slate-900 hover:bg-slate-800 text-white px-8 py-4 rounded-2xl font-medium transition-all duration-200 shadow-lg hover:shadow-xl flex items-center gap-3"
            >
              Process first product free
              <ArrowRight size={18} />
            </a>

            <a
              href="#pipeline"
              className="bg-white/80 backdrop-blur-sm border border-slate-200 hover:border-slate-300 text-slate-700 px-8 py-4 rounded-2xl font-medium transition-all duration-200"
            >
              See the difference
            </a>
          </div>
        </div>
      </div>

      <div ref={pipelineRef} id="pipeline" className="py-24 bg-gradient-to-b from-slate-50 to-white">
  <div className="max-w-7xl mx-auto px-6">
    <div className="text-center mb-20">
      <h2 className="text-4xl md:text-5xl font-semibold text-slate-900 mb-6 tracking-tight">
        AI Processing Pipeline
      </h2>
      <p className="text-xl text-slate-600 max-w-3xl mx-auto leading-relaxed">
        Our advanced AI technology transforms ordinary product photos into high-converting, professional images that drive sales.
      </p>
    </div>

    {pipelineSteps.map((step, index) => {
  const isEven = index % 2 === 0;
  const isTransparentStep = index === 1;

  return (
   <motion.div
  key={index}
  initial={{ opacity: 0, x: isEven ? -100 : 100 }}
  whileInView={{ opacity: 1, x: 0 }}
  viewport={{ once: true, amount: 0.4 }}
  transition={{ duration: 0.7, ease: 'easeOut' }}
  className={`flex flex-col-reverse lg:flex-row ${!isEven ? 'lg:flex-row-reverse' : ''} items-center gap-16`}
>
  <div className="w-full lg:w-1/2">
    <div className="bg-white/30 backdrop-blur-2xl p-10 rounded-3xl border border-white/20 shadow-[0_10px_40px_rgba(0,0,0,0.1)]">
      <div className="text-sm text-blue-600 font-semibold mb-3 uppercase tracking-wider">
        {step.tech}
      </div>
      <h3 className="text-2xl font-semibold text-slate-900 mb-4">{step.title}</h3>
      <p className="text-slate-600 leading-relaxed mb-6">{step.description}</p>

      <div className="grid grid-cols-3 gap-4 pt-6 border-t border-white/20">
        <div className="text-center">
          <div className="font-semibold text-slate-900 text-lg">{step.metrics.quality}</div>
          <div className="text-slate-500 text-sm">Quality</div>
        </div>
        <div className="text-center">
          <div className="font-semibold text-slate-900 text-lg">{step.metrics.conversion}</div>
          <div className="text-slate-500 text-sm">Conversion</div>
        </div>
        <div className="text-center">
          <div className="font-semibold text-slate-900 text-lg">{step.metrics.engagement}</div>
          <div className="text-slate-500 text-sm">Engagement</div>
        </div>
      </div>
    </div>
  </div>

  <div className="w-full lg:w-1/2 relative rounded-3xl overflow-hidden 
                  border border-white/30 bg-white/30 backdrop-blur-2xl
                  shadow-[0_10px_40px_rgba(0,0,0,0.1)] flex justify-center items-center p-6">
    {isTransparentStep && (
      <div
        className="absolute inset-0 z-0"
        style={{
          backgroundImage: `linear-gradient(45deg, #e2e8f0 25%, transparent 25%), 
                            linear-gradient(-45deg, #e2e8f0 25%, transparent 25%), 
                            linear-gradient(45deg, transparent 75%, #e2e8f0 75%), 
                            linear-gradient(-45deg, transparent 75%, #e2e8f0 75%)`,
          backgroundSize: '20px 20px',
          backgroundPosition: '0 0, 0 10px, 10px -10px, -10px 0px',
        }}
      />
    )}

    <img
      src={
        index === 0
          ? "https://images.unsplash.com/photo-1696603971992-5c7aa2a3f290?q=80&w=1600&auto=format&fit=crop"
          : "https://res.cloudinary.com/drzokg7bb/image/upload/v1753560508/pixelperfect/processed/ff08b7bb-1108-4563-80d5-2f3082cf17de_bg_removed.png"
      }
      alt={`Step ${index + 1}`}
      className={`relative z-10 rounded-3xl max-h-[350px] ${
        index === 0 ? 'object-cover' : 'object-contain'
      }`}
      style={{ maxWidth: '100%', margin: '0 auto', display: 'block' }}
    />

    {(index === 0 || index === 2) && (
      <div className="absolute top-4 right-4 z-20">
        <span className={`px-4 py-2 text-sm font-medium rounded-full shadow-md backdrop-blur-xl border border-white/30 ${
          index === 0 ? 'bg-orange-100/80 text-orange-700' : 'bg-green-100/80 text-green-700'
        }`}>
          {index === 0 ? 'Original' : 'Enhanced'}
        </span>
      </div>
    )}
  </div>
</motion.div>


  );
})}

  </div>
</div>

   {/* Try It Yourself Section */}
<div className="py-24 bg-gradient-to-b from-white to-slate-50">
  <div className="max-w-4xl mx-auto px-6">
    <div className="text-center mb-16">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8 }}
      >
        <h2 className="text-4xl md:text-5xl font-semibold text-slate-900 mb-6 tracking-tight">
          Try it yourself
        </h2>
        <p className="text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
          Upload any product image and see our AI magic in action. 
          Experience professional-grade processing in seconds.
        </p>
      </motion.div>
    </div>

    <motion.div
      initial={{ opacity: 0, y: 50 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.8, delay: 0.2 }}
      className="bg-white/60 backdrop-blur-xl rounded-3xl p-8 md:p-12 shadow-[0_20px_60px_rgba(0,0,0,0.1)] border border-white/30"
    >
      <div className="max-w-2xl mx-auto">
        <DragDropUploader
          onFileSelect={handleFileSelect}
          accept="image/*"
          maxSize={10}
          preview={previewUrl}
          className="w-full"
        />
        
        {/* Additional info */}
        {/* Upload status or CTA */}
        <div className="mt-8 text-center">
          {uploadedFile ? (
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-full text-sm font-medium border border-blue-200 animate-pulse">
              <div className="w-4 h-4 border-2 border-blue-600/30 border-t-blue-600 rounded-full animate-spin" />
              Redirecting to editor...
            </div>
          ) : (
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-50 text-green-700 rounded-full text-sm font-medium border border-green-200">
              <Sparkles size={16} />
              Free background removal • No signup required
            </div>
          )}
        </div>

        {/* Processing steps preview */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-4">
              <FileImage className="w-6 h-6 text-blue-600" />
            </div>
            <h4 className="font-semibold text-slate-900 mb-2">Upload</h4>
            <p className="text-sm text-slate-600">Drag, drop, or paste your product image</p>
          </div>
          
          <div className="text-center">
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Wand2 className="w-6 h-6 text-purple-600" />
            </div>
            <h4 className="font-semibold text-slate-900 mb-2">Process</h4>
            <p className="text-sm text-slate-600">AI removes background instantly</p>
          </div>
          
          <div className="text-center">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Star className="w-6 h-6 text-green-600" />
            </div>
            <h4 className="font-semibold text-slate-900 mb-2">Download</h4>
            <p className="text-sm text-slate-600">Get your professional result</p>
          </div>
        </div>
      </div>
    </motion.div>

    {/* Trust indicators */}
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.8, delay: 0.4 }}
      className="mt-16 text-center"
    >
      <div className="flex flex-wrap justify-center items-center gap-8 text-slate-500">
        <div className="flex items-center gap-2">
          <Shield size={16} />
          <span className="text-sm">Secure processing</span>
        </div>
        <div className="flex items-center gap-2">
          <Zap size={16} />
          <span className="text-sm">Under 10 seconds</span>
        </div>
        <div className="flex items-center gap-2">
          <Check size={16} />
          <span className="text-sm">No watermarks</span>
        </div>
      </div>
    </motion.div>
  </div>
</div>

      {/* Services Section */}
      <div ref={servicesRef} id="services" className="py-20 bg-slate-50/50 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-light text-slate-900 mb-4 tracking-tight">
              E-commerce AI Tools
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto font-light">
              Everything you need to create a professional product catalog that converts.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {services.map((service, index) => (
              <a
                key={service.href}
                href={service.href}
                className={`group relative bg-white/90 backdrop-blur-sm border border-slate-200/50 rounded-2xl overflow-hidden transition-all duration-300 hover:shadow-xl hover:border-slate-300/50 hover:-translate-y-1 ${service.comingSoon ? 'cursor-default opacity-70' : ''}`}
              >
                {service.comingSoon && (
                  <div className="absolute top-4 right-4 bg-slate-100 text-slate-500 text-xs font-medium px-3 py-1 rounded-full z-10">
                    Coming Soon
                  </div>
                )}

                <div className="relative w-full h-48 overflow-hidden" style={{
                  background: `linear-gradient(135deg, 
                    ${index === 0 ? '#fee2e2 0%, #fecaca 50%, #fca5a5 100%' : ''}
                    ${index === 1 ? '#dbeafe 0%, #bfdbfe 50%, #93c5fd 100%' : ''}
                    ${index === 2 ? '#d1fae5 0%, #a7f3d0 50%, #6ee7b7 100%' : ''}
                    ${index === 3 ? '#e0e7ff 0%, #c7d2fe 50%, #a5b4fc 100%' : ''}
                    ${index === 4 ? '#fce7f3 0%, #fbcfe8 50%, #f9a8d4 100%' : ''}
                    ${index === 5 ? '#f3f4f6 0%, #e5e7eb 50%, #d1d5db 100%' : ''}
                  )`
                }}>
                  <div className="absolute inset-0 bg-white/20 group-hover:bg-white/30 transition-colors duration-300"></div>
                  
                  <div className="relative h-full flex items-center justify-center">
                    <div className="w-20 h-20 bg-white/90 backdrop-blur-sm rounded-3xl flex items-center justify-center shadow-lg group-hover:shadow-xl group-hover:scale-110 transition-all duration-300">
                      <service.icon className="text-slate-800" size={32} />
                    </div>
                  </div>
                  
                  {/* Animated dots pattern */}
                  <div className="absolute top-4 left-4 flex gap-1">
                    <div className="w-2 h-2 bg-white/40 rounded-full animate-pulse"></div>
                    <div className="w-2 h-2 bg-white/40 rounded-full animate-pulse" style={{animationDelay: '0.5s'}}></div>
                    <div className="w-2 h-2 bg-white/40 rounded-full animate-pulse" style={{animationDelay: '1s'}}></div>
                  </div>
                  
                  {/* Subtle geometric pattern */}
                  <div className="absolute bottom-4 right-4 opacity-20">
                    <div className="w-8 h-8 transform rotate-45 border border-white/60"></div>
                  </div>
                </div>

                <div className="p-6 bg-white">
                  <h3 className="text-lg font-medium text-slate-900 mb-2">
                    {service.title}
                  </h3>
                  
                  <p className="text-slate-600 text-sm leading-relaxed mb-4">
                    {service.description}
                  </p>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 text-sm font-medium">
                      {service.tokens}
                    </span>
                    {!service.comingSoon && (
                      <ArrowRight
                        size={16}
                        className="text-slate-400 group-hover:text-slate-900 group-hover:translate-x-1 transition-all duration-300"
                      />
                    )}
                  </div>
                </div>
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* Partners Section */}
      <div ref={partnersRef} className="py-24 bg-white overflow-hidden relative">
        <div className="text-center mb-20">
          <h3 className="text-2xl font-light text-slate-800 mb-4 tracking-tight">
            Trusted by E-commerce Leaders
          </h3>
          <div className="w-16 h-0.5 bg-gradient-to-r from-transparent via-slate-300 to-transparent mx-auto"></div>
        </div>
        
        <div className="flex items-center gap-20 animate-infinite-scroll">
          {[...partners, ...partners].map((partner, index) => (
            <div
              key={index}
              className="text-slate-700 hover:text-slate-900 transition-colors duration-300 cursor-default whitespace-nowrap flex-shrink-0 group"
            >
              <div className="text-2xl font-light tracking-wide group-hover:scale-105 transition-transform duration-300">
                {partner}
              </div>
            </div>
          ))}
        </div>
        
        {/* Enhanced gradient overlays */}
        <div className="absolute inset-y-0 left-0 w-40 bg-gradient-to-r from-white via-white/70 to-transparent pointer-events-none z-10"></div>
        <div className="absolute inset-y-0 right-0 w-40 bg-gradient-to-l from-white via-white/70 to-transparent pointer-events-none z-10"></div>
      </div>

      {/* Audience Section */}
      <div ref={audienceRef} className="py-20 bg-slate-50/50 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-light text-slate-900 mb-4 tracking-tight">
              Built for E-commerce Success
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto font-light">
              Whether you're selling on your own store or major marketplaces.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {audience.map((item, index) => (
              <div 
                key={index}
                className={`group relative bg-white backdrop-blur-sm border ${item.borderColor} rounded-2xl p-8 hover:shadow-xl hover:-translate-y-1 transition-all duration-500`}
              >
                {/* Abstract Icon */}
                <div className={`w-16 h-16 ${item.iconBg} rounded-2xl mb-6 relative overflow-hidden`}>
                  {/* Animated lines pattern */}
                  <div className="absolute inset-0 flex flex-col justify-center items-center gap-1">
                    {item.lines.map((line, lineIndex) => (
                      <div 
                        key={lineIndex}
                        className={`${line.width} h-0.5 ${line.color} rounded-full opacity-60 group-hover:opacity-100 transition-opacity duration-300`}
                        style={{ animationDelay: line.delay }}
                      />
                    ))}
                  </div>
                  
                  {/* Subtle glow effect */}
                  <div className="absolute inset-0 bg-white/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                </div>
                
                <h3 className="text-xl font-medium text-slate-900 mb-4 tracking-tight">
                  {item.title}
                </h3>
                <p className="text-slate-600 leading-relaxed">
                  {item.description}
                </p>
                
                {/* Subtle accent line */}
                <div className={`w-12 h-0.5 ${item.lines[0].color} rounded-full mt-6 opacity-30 group-hover:opacity-60 group-hover:w-16 transition-all duration-300`}></div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Why Choose PixelPerfect */}
      <div ref={whyChooseRef} className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-light text-slate-900 mb-4 tracking-tight">
              Why E-commerce Brands Choose Us
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto font-light">
              Built specifically for online retail success.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {whyFeatures.map((feature, index) => (
              <div
                key={index}
                className="text-center group"
              >
                <div className="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg group-hover:shadow-xl transition-shadow duration-300">
                  <feature.icon className="text-slate-700" size={24} />
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

      {/* Pricing Section */}
      <div ref={pricingRef} className="py-20 bg-slate-50/50 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-light text-slate-900 mb-4 tracking-tight">
              E-commerce Plans That Scale
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto font-light">
              From startup stores to enterprise catalogs. Start free, scale as you grow.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {pricingPlans.map((plan, index) => (
              <div
                key={index}
                className={`relative bg-white border rounded-2xl p-8 transition-all duration-300 hover:shadow-xl hover:-translate-y-1 ${
                  plan.popular 
                    ? 'border-slate-900 shadow-lg' 
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <span className="bg-slate-900 text-white px-4 py-1 rounded-full text-sm font-medium">
                      Most Popular
                    </span>
                  </div>
                )}

                <div className="text-center mb-8">
                  <h3 className="text-xl font-medium text-slate-900 mb-2">
                    {plan.name}
                  </h3>
                  <div className="mb-4">
                    <span className="text-4xl font-light text-slate-900">
                      {plan.price}
                    </span>
                    <span className="text-slate-600">/{plan.period}</span>
                  </div>
                  <p className="text-slate-600">
                    {plan.description}
                  </p>
                </div>

                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-center gap-3">
                      <Check size={16} className="text-green-500 flex-shrink-0" />
                      <span className="text-slate-600">{feature}</span>
                    </li>
                  ))}
                </ul>

                <button
                  className={`w-full py-3 px-6 rounded-xl font-medium transition-all duration-200 ${
                    plan.popular
                      ? 'bg-slate-900 text-white hover:bg-slate-800'
                      : 'bg-slate-100 text-slate-900 hover:bg-slate-200'
                  }`}
                >
                  {plan.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* FAQ Section */}
      <div ref={faqRef} className="py-20 bg-white">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-light text-slate-900 mb-4 tracking-tight">
              E-commerce FAQ
            </h2>
            <p className="text-lg text-slate-600 font-light">
              Everything you need to know about AI product image processing.
            </p>
          </div>

          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <div
                key={index}
                className="bg-slate-50/50 border border-slate-200/50 rounded-2xl overflow-hidden"
              >
                <button
                  className="w-full p-6 text-left flex items-center justify-between hover:bg-slate-50 transition-colors duration-200"
                  onClick={() => setOpenFAQ(openFAQ === index ? null : index)}
                >
                  <span className="text-lg font-medium text-slate-900">
                    {faq.question}
                  </span>
                  <ChevronDown
                    size={20}
                    className={`text-slate-400 transition-transform duration-200 ${
                      openFAQ === index ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                
                {openFAQ === index && (
                  <div className="px-6 pb-6">
                    <p className="text-slate-600 leading-relaxed">
                      {faq.answer}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Final CTA */}
      <div className="py-20 bg-slate-50/50 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl md:text-4xl font-light text-slate-900 mb-6 tracking-tight">
            Ready to Transform Your Product Catalog?
          </h2>
          <p className="text-lg text-slate-600 mb-8 font-light">
            Join thousands of e-commerce stores who trust PixelPerfect AI for professional product images.
          </p>
          <a
            href="/background-removal"
            className="inline-flex items-center gap-3 bg-slate-900 hover:bg-slate-800 text-white px-8 py-4 rounded-2xl font-medium transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105"
          >
            Start Processing Products Now
            <ArrowRight size={20} />
          </a>
        </div>
      </div>

    </Layout>
  );
};

export default HomePage;