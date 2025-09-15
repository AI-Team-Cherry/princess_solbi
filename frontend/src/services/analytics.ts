import axios from 'axios';
import { Analysis, AnalysisResult, QueryRequest, SharedAnalysis, ApiResponse } from '../types';

// 백엔드 API URL (환경 변수 또는 기본값)
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 인증 토큰을 요청에 자동으로 추가
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 응답 인터셉터 (토큰 만료 처리 등)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 토큰 만료 시 로그아웃 처리
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 자연어 쿼리 처리
export const submitQuery = async (request: QueryRequest): Promise<AnalysisResult> => {
  try {
    const response = await api.post('/query', {
      query: request.query,
      use_ai_mode: true, // 무조건 AI 모드 사용
      save_analysis: true,
      tags: request.tags || []
    });

    const data = response.data;
    
    // FastAPI 응답을 프론트엔드 타입으로 변환
    return {
      visualization: data.visualizations && data.visualizations[0] ? data.visualizations[0] : null,
      analysis: data.insights.join('\n\n'),
      data: data.data_count > 0 ? [{ count: data.data_count, query: request.query }] : [],
      model_status: {
        status: "ready",
        model: "Dynamic MongoDB Analyzer",
        type: "local"
      },
      prediction_basis: `${data.data_count}건의 데이터를 기반으로 한 동적 스키마 분석`
    };
  } catch (error: any) {
    console.error('Query submission error:', error);
    
    // 에러 처리 - 목업 데이터 반환
    return {
      visualization: null,
      analysis: `쿼리 처리 중 오류가 발생했습니다: ${error.response?.data?.detail || error.message}`,
      data: [],
      model_status: {
        status: "error",
        model: "Dynamic MongoDB Analyzer",
        type: "local"
      },
      prediction_basis: "오류로 인해 분석을 완료할 수 없습니다."
    };
  }
};

// 분석 저장
export const saveAnalysis = async (analysisData: {
  query: string;
  result: AnalysisResult;
  title?: string;
  description?: string;
  tags?: string[];
  isPublic?: boolean;
}): Promise<Analysis> => {
  try {
    // 분석이 이미 저장되었을 수도 있으므로 별도 저장 API는 구현하지 않음
    // submitQuery에서 이미 save_analysis: true로 저장됨
    
    return {
      id: 'analysis-' + Date.now(),
      userId: '1',
      query: analysisData.query,
      result: analysisData.result,
      createdAt: new Date(),
      updatedAt: new Date(),
      isPublic: analysisData.isPublic || false,
      tags: analysisData.tags || [],
      title: analysisData.title,
      description: analysisData.description
    };
  } catch (error) {
    console.error('Save analysis error:', error);
    throw error;
  }
};

// 내 분석 목록 조회
export const getMyAnalyses = async (page: number = 1, limit: number = 10): Promise<{
  analyses: Analysis[];
  total: number;
  page: number;
  totalPages: number;
}> => {
  try {
    const skip = (page - 1) * limit;
    const response = await api.get(`/analyses/my?skip=${skip}&limit=${limit}`);
    
    const data = response.data;
    const analyses = data.analyses.map((item: any) => ({
      id: item.id,
      userId: item.user_id,
      query: item.query,
      result: {
        analysis: item.result.insights?.join('\n\n') || '분석 결과 없음',
        data: item.result.data || []
      },
      createdAt: new Date(item.created_at),
      updatedAt: new Date(item.updated_at),
      isPublic: item.is_shared || false,
      tags: item.tags || [],
      title: item.query,
      description: ''
    }));

    return {
      analyses,
      total: data.total,
      page: Math.floor(data.skip / data.limit) + 1,
      totalPages: Math.ceil(data.total / data.limit)
    };
  } catch (error) {
    console.error('Get my analyses error:', error);
    
    // 에러 시 빈 결과 반환
    return {
      analyses: [],
      total: 0,
      page: 1,
      totalPages: 1
    };
  }
};

// 분석 상세 조회
export const getAnalysisById = async (id: string): Promise<Analysis> => {
  try {
    const response = await api.get(`/analyses/${id}`);
    const item = response.data;
    
    return {
      id: item.id,
      userId: item.user_id,
      query: item.query,
      result: {
        analysis: item.result.insights?.join('\n\n') || '분석 결과 없음',
        data: item.result.data || [],
        visualization: item.result.visualizations?.[0] || null
      },
      createdAt: new Date(item.created_at),
      updatedAt: new Date(item.updated_at),
      isPublic: item.is_shared || false,
      tags: item.tags || [],
      title: item.query,
      description: ''
    };
  } catch (error) {
    console.error('Get analysis by ID error:', error);
    throw error;
  }
};

// 공유 분석 목록 조회
export const getSharedAnalyses = async (
  category?: string,
  search?: string,
  page: number = 1,
  limit: number = 10
): Promise<{
  analyses: SharedAnalysis[];
  total: number;
  page: number;
  totalPages: number;
}> => {
  try {
    const skip = (page - 1) * limit;
    const response = await api.get(`/analyses/shared?skip=${skip}&limit=${limit}`);
    
    const data = response.data;
    const analyses = data.analyses.map((item: any) => ({
      id: item.id,
      originalAnalysisId: item.id,
      sharedBy: {
        id: item.user_id,
        employeeId: item.user_id,
        name: item.user_name || 'Unknown',
        department: item.user_department || 'Unknown',
        role: 'user'
      },
      sharedAt: new Date(item.created_at),
      usageCount: Math.floor(Math.random() * 20), // 임시 값
      rating: 4.0 + Math.random(), // 임시 값
      category: 'general',
      query: item.query,
      tags: item.tags || []
    }));

    return {
      analyses,
      total: data.total,
      page: Math.floor(data.skip / data.limit) + 1,
      totalPages: Math.ceil(data.total / data.limit)
    };
  } catch (error) {
    console.error('Get shared analyses error:', error);
    
    return {
      analyses: [],
      total: 0,
      page: 1,
      totalPages: 1
    };
  }
};

// 분석 공유
export const shareAnalysis = async (analysisId: string): Promise<SharedAnalysis> => {
  try {
    await api.put(`/analyses/${analysisId}`, { is_shared: true });
    
    return {
      id: 'shared-' + Date.now(),
      originalAnalysisId: analysisId,
      sharedBy: {
        id: '1',
        employeeId: 'current-user',
        name: '현재사용자',
        department: '영업부서',
        role: 'user'
      },
      sharedAt: new Date(),
      usageCount: 0,
      rating: 5.0,
      category: 'general'
    };
  } catch (error) {
    console.error('Share analysis error:', error);
    throw error;
  }
};

// 공유 분석 적용
export const applySharedAnalysis = async (sharedAnalysisId: string): Promise<Analysis> => {
  try {
    // 공유 분석을 기반으로 새로운 분석 생성
    const sharedAnalysis = await getAnalysisById(sharedAnalysisId);
    
    // 동일한 쿼리로 새로운 분석 실행
    const result = await submitQuery({ query: sharedAnalysis.query });
    
    return {
      id: 'applied-' + Date.now(),
      userId: '1',
      query: sharedAnalysis.query + ' (공유 분석 적용)',
      result: result,
      createdAt: new Date(),
      updatedAt: new Date(),
      isPublic: false,
      tags: [...(sharedAnalysis.tags || []), '공유', '적용'],
      title: '공유 분석 적용: ' + sharedAnalysis.query
    };
  } catch (error) {
    console.error('Apply shared analysis error:', error);
    throw error;
  }
};

// 분석 삭제
export const deleteAnalysis = async (id: string): Promise<void> => {
  try {
    await api.delete(`/analyses/${id}`);
  } catch (error) {
    console.error('Delete analysis error:', error);
    throw error;
  }
};

// 분석 업데이트
export const updateAnalysis = async (id: string, updates: Partial<Analysis>): Promise<Analysis> => {
  try {
    const updateData: any = {};
    
    if (updates.tags !== undefined) updateData.tags = updates.tags;
    if (updates.isPublic !== undefined) updateData.is_shared = updates.isPublic;
    
    await api.put(`/analyses/${id}`, updateData);
    
    // 업데이트된 분석 조회
    return await getAnalysisById(id);
  } catch (error) {
    console.error('Update analysis error:', error);
    throw error;
  }
};

// 대시보드 통계 조회
export const getDashboardStats = async (): Promise<any> => {
  try {
    const response = await api.get('/dashboard/stats');
    return response.data;
  } catch (error) {
    console.error('Get dashboard stats error:', error);
    
    // 에러 시 기본값 반환
    return {
      user_stats: {
        total_analyses: 0,
        shared_analyses: 0,
        department: 'Unknown',
        role: 'analyst'
      },
      recent_analyses: [],
      popular_analyses: []
    };
  }
};

// 스키마 정보 조회
export const getSchemaInfo = async (): Promise<any> => {
  try {
    const response = await api.get('/schema/info');
    return response.data;
  } catch (error) {
    console.error('Get schema info error:', error);
    return null;
  }
};

// 쿼리 제안 조회
export const getQuerySuggestions = async (): Promise<string[]> => {
  try {
    const response = await api.get('/queries/suggestions');
    return response.data.suggestions;
  } catch (error) {
    console.error('Get query suggestions error:', error);
    return [];
  }
};

// 스키마 새로고침 (관리자만)
export const refreshSchema = async (): Promise<any> => {
  try {
    const response = await api.post('/schema/refresh');
    return response.data;
  } catch (error) {
    console.error('Refresh schema error:', error);
    throw error;
  }
};