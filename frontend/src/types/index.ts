// User types
export interface User {
  id: string;
  employeeId: string;
  name: string;
  department: string;
  role: 'user' | 'admin';
  lastLogin?: Date;
  createdAt?: Date;
  updatedAt?: Date;
}

// Analysis types
export interface Analysis {
  id: string;
  userId: string;
  query: string;
  result: AnalysisResult;
  createdAt: Date;
  updatedAt: Date;
  isPublic: boolean;
  tags: string[];
  title?: string;
  description?: string;
}

export interface AnalysisResult {
  visualization?: VegaLiteSpec | null;
  analysis: string;
  data: any[];
  model_status?: {
    status: string;
    model: string;
    type: string;
  };
  prediction_basis?: string;
  error?: string;
}

export interface VegaLiteSpec {
  $schema?: string;
  description?: string;
  data?: {
    values?: any[];
  };
  mark?: string;
  encoding?: {
    [key: string]: any;
  };
  [key: string]: any;
}

// Shared Analysis
export interface SharedAnalysis {
  id: string;
  originalAnalysisId: string;
  sharedBy: User;
  sharedAt: Date;
  usageCount: number;
  rating: number;
  category: string;
}

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface QueryRequest {
  query: string;
  use_ai_mode?: boolean;
  tags?: string[];
}

export interface LoginRequest {
  employeeId: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  token: string;
  refreshToken: string;
}