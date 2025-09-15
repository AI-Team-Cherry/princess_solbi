import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// API 클라이언트 설정
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터: 토큰 자동 추가
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// ML 분석 요청 타입
export interface MLAnalysisRequest {
  analysis_type: 'clustering' | 'prediction' | 'timeseries' | 'anomaly' | 'segmentation';
  collection_name: string;
  parameters?: Record<string, any>;
  save_analysis?: boolean;
  tags?: string[];
}

// ML 분석 결과 타입
export interface MLAnalysisResult {
  id?: string;
  analysis_type: string;
  collection: string;
  data_count: number;
  ml_result: {
    analysis_type: string;
    [key: string]: any;
  };
  visualizations: Array<{
    mark: any;
    data: any;
    encoding: any;
    title: string;
    width: number;
    height: number;
  }>;
  created_at: string;
}

// ML 분석 방법 타입
export interface MLMethod {
  name: string;
  description: string;
  parameters: Record<string, {
    type: string;
    default?: any;
    description: string;
    options?: string[];
  }>;
}

// ML 컬렉션 정보 타입
export interface MLCollection {
  name: string;
  document_count: number;
  numeric_fields: string[];
  sample_fields: string[];
}

// ML 분석 서비스
class MLAnalyticsService {
  /**
   * ML 분석 실행
   */
  async performAnalysis(request: MLAnalysisRequest): Promise<MLAnalysisResult> {
    try {
      const response = await api.post('/ml/analyze', request);
      return response.data;
    } catch (error: any) {
      console.error('ML 분석 오류:', error);
      throw new Error(
        error.response?.data?.detail || 'ML 분석 중 오류가 발생했습니다.'
      );
    }
  }

  /**
   * 지원하는 ML 분석 방법 목록 조회
   */
  async getMLMethods(): Promise<Record<string, MLMethod>> {
    try {
      const response = await api.get('/ml/methods');
      return response.data.methods;
    } catch (error: any) {
      console.error('ML 방법 목록 조회 오류:', error);
      throw new Error(
        error.response?.data?.detail || 'ML 방법 목록을 가져오는 중 오류가 발생했습니다.'
      );
    }
  }

  /**
   * ML 분석 가능한 컬렉션 목록 조회
   */
  async getMLCollections(): Promise<MLCollection[]> {
    try {
      const response = await api.get('/ml/collections');
      return response.data.collections;
    } catch (error: any) {
      console.error('ML 컬렉션 목록 조회 오류:', error);
      throw new Error(
        error.response?.data?.detail || 'ML 컬렉션 목록을 가져오는 중 오류가 발생했습니다.'
      );
    }
  }

  /**
   * 고객 클러스터링 분석
   */
  async performClustering(
    collectionName: string,
    nClusters: number = 5,
    sampleSize: number = 1000
  ): Promise<MLAnalysisResult> {
    return this.performAnalysis({
      analysis_type: 'clustering',
      collection_name: collectionName,
      parameters: {
        n_clusters: nClusters,
        sample_size: sampleSize,
      },
      tags: ['clustering', 'customer-segmentation'],
    });
  }

  /**
   * 매출 예측 분석
   */
  async performPrediction(
    collectionName: string,
    targetCol?: string,
    daysAhead: number = 30,
    sampleSize: number = 1000
  ): Promise<MLAnalysisResult> {
    const parameters: Record<string, any> = {
      days_ahead: daysAhead,
      sample_size: sampleSize,
    };
    
    if (targetCol) {
      parameters.target_col = targetCol;
    }

    return this.performAnalysis({
      analysis_type: 'prediction',
      collection_name: collectionName,
      parameters,
      tags: ['prediction', 'sales-forecast'],
    });
  }

  /**
   * 시계열 분석
   */
  async performTimeSeriesAnalysis(
    collectionName: string,
    dateCol?: string,
    valueCol?: string,
    sampleSize: number = 1000
  ): Promise<MLAnalysisResult> {
    const parameters: Record<string, any> = {
      sample_size: sampleSize,
    };
    
    if (dateCol) {
      parameters.date_col = dateCol;
    }
    
    if (valueCol) {
      parameters.value_col = valueCol;
    }

    return this.performAnalysis({
      analysis_type: 'timeseries',
      collection_name: collectionName,
      parameters,
      tags: ['timeseries', 'trend-analysis'],
    });
  }

  /**
   * 이상치 탐지 분석
   */
  async performAnomalyDetection(
    collectionName: string,
    method: 'isolation' | 'statistical' = 'isolation',
    sampleSize: number = 1000
  ): Promise<MLAnalysisResult> {
    return this.performAnalysis({
      analysis_type: 'anomaly',
      collection_name: collectionName,
      parameters: {
        method,
        sample_size: sampleSize,
      },
      tags: ['anomaly-detection', 'outliers'],
    });
  }

  /**
   * 분석 결과 해석 도우미
   */
  interpretResult(result: MLAnalysisResult): {
    summary: string;
    insights: string[];
    recommendations: string[];
  } {
    const { analysis_type, ml_result } = result;
    
    switch (analysis_type) {
      case 'clustering':
        return {
          summary: `${ml_result.n_clusters}개 고객 그룹으로 세분화되었습니다. 실루엣 점수: ${ml_result.silhouette_score?.toFixed(2)}`,
          insights: ml_result.insights || [],
          recommendations: ml_result.recommendations || [],
        };
      
      case 'prediction':
        return {
          summary: `매출 예측 모델의 정확도: ${ml_result.model_performance?.accuracy_percentage?.toFixed(1)}%`,
          insights: ml_result.insights || [],
          recommendations: ml_result.recommendations || [],
        };
      
      case 'timeseries':
        return {
          summary: `${ml_result.date_range?.days || 0}일간의 시계열 분석 완료. 트렌드: ${ml_result.trend?.direction || 'unknown'}`,
          insights: ml_result.insights || [],
          recommendations: ml_result.recommendations || [],
        };
      
      case 'anomaly':
        return {
          summary: `전체 데이터의 ${ml_result.anomaly_rate?.toFixed(1)}%에서 이상치가 발견되었습니다.`,
          insights: ml_result.insights || [],
          recommendations: ml_result.recommendations || [],
        };
      
      default:
        return {
          summary: '분석이 완료되었습니다.',
          insights: ml_result.insights || [],
          recommendations: ml_result.recommendations || [],
        };
    }
  }

  /**
   * 분석 유형별 추천 매개변수
   */
  getRecommendedParameters(analysisType: string, collectionInfo: MLCollection): Record<string, any> {
    switch (analysisType) {
      case 'clustering':
        const estimatedClusters = Math.min(Math.max(Math.floor(Math.sqrt(collectionInfo.document_count / 100)), 3), 10);
        return {
          n_clusters: estimatedClusters,
          sample_size: Math.min(collectionInfo.document_count, 1000),
        };
      
      case 'prediction':
        return {
          target_col: collectionInfo.numeric_fields[0] || 'total_amount',
          days_ahead: 30,
          sample_size: Math.min(collectionInfo.document_count, 1000),
        };
      
      case 'timeseries':
        return {
          date_col: 'created_at',
          value_col: collectionInfo.numeric_fields[0] || 'total_amount',
          sample_size: Math.min(collectionInfo.document_count, 2000),
        };
      
      case 'anomaly':
        return {
          method: 'isolation',
          sample_size: Math.min(collectionInfo.document_count, 1000),
        };
      
      default:
        return {};
    }
  }
}

export const mlAnalyticsService = new MLAnalyticsService();
export default mlAnalyticsService;