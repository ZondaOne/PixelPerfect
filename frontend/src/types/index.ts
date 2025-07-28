// src/types/index.ts - Updated with Style Transfer

export enum JobTypeEnum {
  BG_REMOVAL = 'BG_REMOVAL',
  UPSCALE = 'UPSCALE',
  ENLARGE = 'ENLARGE',
  IMAGE_GENERATION = 'IMAGE_GENERATION',
  OBJECT_REMOVAL = 'OBJECT_REMOVAL'
}

export enum JobStatusEnum {
  PENDING = 'PENDING',
  QUEUED = 'QUEUED',
  PROCESSING = 'PROCESSING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED',
  RETRYING = 'RETRYING',
  UPLOADING = 'UPLOADING'
}

export interface JobResponseDTO {
  jobId: string; 
  originalImageId: string;
  jobType: JobTypeEnum;
  status: JobStatusEnum;
  createdAt: string; 
  completedAt?: string;
  processedImageUrl?: string;
  thumbnailUrl?: string; 
  isPremiumQuality?: boolean; 
  tokenCost?: number; 
  tokenBalance?: number; 
  errorMessage?: string;
}

export interface ImageUploadRequestDTO {
  userId: string;
  jobType: JobTypeEnum;
  file: File; 
}

export interface GuestUserDTO {
  token: string;
  userId: string;
  displayName: string;
  isGuest: boolean;
  tokenBalance: number;
}

export interface TokenBalance {
  balance: number;
}

export interface TokenPurchase {
  amount: number;
}

// Style Transfer specific types
export interface StyleTransferConfig {
  style: string;
  prompt?: string;
  strength: number;
  quality: 'FREE' | 'PREMIUM';
}

export interface StyleOption {
  id: string;
  name: string;
  description: string;
  category: string;
  previewImage: string;
  prompt: string;
  popular?: boolean;
}

// Available art styles for style transfer
export const AVAILABLE_STYLES = [
  '3D_Chibi', 'American_Cartoon', 'Chinese_Ink', 'Clay_Toy', 'Fabric',
  'Ghibli', 'Irasutoya', 'Jojo', 'LEGO', 'Line', 'Macaron', 'Oil_Painting',
  'Origami', 'Paper_Cutting', 'Picasso', 'Pixel', 'Poly', 'Pop_Art',
  'Rick_Morty', 'Snoopy', 'Van_Gogh', 'Vector'
] as const;

export type StyleType = typeof AVAILABLE_STYLES[number];