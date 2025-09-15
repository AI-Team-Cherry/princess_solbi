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

// 자연어 쿼리 요청 타입
export interface NaturalLanguageQueryRequest {
  query: string;
  ai_mode: boolean;
  collection?: string;
}

// 자연어 쿼리 응답 타입
export interface NaturalLanguageQueryResponse {
  success: boolean;
  query?: {
    collection: string;
    operation: string;
    filter: any;
    options?: any;
    pipeline?: any[];
  };
  results?: any[];
  error?: string;
  natural_language: string;
  parsed_elements?: {
    collection: string | null;
    filters: any;
    projection: any;
    sort: any;
    limit: number | null;
    aggregation: any[];
  };
}

// 자연어 검색 서비스
class NaturalLanguageSearchService {
  /**
   * 자연어를 MongoDB 쿼리로 변환
   */
  async convertQuery(request: NaturalLanguageQueryRequest): Promise<NaturalLanguageQueryResponse> {
    try {
      const response = await api.post('/nl/convert-query', request);
      return response.data;
    } catch (error: any) {
      console.error('쿼리 변환 오류:', error);
      throw new Error(
        error.response?.data?.detail || '쿼리 변환 중 오류가 발생했습니다.'
      );
    }
  }

  /**
   * 자연어 검색 실행
   */
  async search(request: NaturalLanguageQueryRequest): Promise<NaturalLanguageQueryResponse> {
    try {
      const response = await api.post('/nl/search', request);
      return response.data;
    } catch (error: any) {
      console.error('자연어 검색 오류:', error);
      throw new Error(
        error.response?.data?.detail || '검색 중 오류가 발생했습니다.'
      );
    }
  }

  /**
   * 자연어 예시 제공
   */
  getExamples(): string[] {
    return [
      "이번 달 부정적인 리뷰를 출력해줘",
      "지난주 긍정적인 리뷰 10개 보여줘",
      "오늘 등록된 리뷰 개수",
      "최근 평점이 낮은 리뷰 분석해줘",
      "이번 달 상품별 리뷰 개수",
      "부정적인 리뷰의 평균 평점",
      "어제 등록된 주문 목록",
      "이번 주 매출 총액"
    ];
  }

  /**
   * 쿼리 결과를 사용자 친화적으로 포맷팅
   */
  formatResults(response: NaturalLanguageQueryResponse): {
    summary: string;
    details: string;
    count: number;
  } {
    if (!response.success || !response.results) {
      return {
        summary: "검색 결과가 없습니다.",
        details: response.error || "알 수 없는 오류가 발생했습니다.",
        count: 0
      };
    }

    const count = response.results.length;
    const query = response.query;
    
    let summary = "";
    let details = "";

    // 연산 타입에 따른 요약
    if (query?.operation === "aggregate") {
      summary = `집계 결과: ${count}개 그룹`;
      if (response.results[0]?.total) {
        details = `총 ${response.results[0].total}개의 문서`;
      } else if (response.results[0]?.average) {
        details = `평균값: ${response.results[0].average.toFixed(2)}`;
      }
    } else {
      summary = `검색 결과: ${count}개 문서`;
      if (query?.options?.sort) {
        const sortField = Object.keys(query.options.sort)[0];
        const sortOrder = query.options.sort[sortField] === -1 ? "최신순" : "오래된순";
        details = `${sortField} ${sortOrder} 정렬`;
      }
    }

    // 필터 정보 추가
    if (query?.filter && Object.keys(query.filter).length > 0) {
      const filterKeys = Object.keys(query.filter).join(", ");
      details += details ? ` | 필터: ${filterKeys}` : `필터: ${filterKeys}`;
    }

    return { summary, details, count };
  }

  /**
   * 결과를 테이블 형식으로 변환
   */
  convertToTableData(results: any[]): {
    columns: string[];
    rows: any[];
  } {
    if (!results || results.length === 0) {
      return { columns: [], rows: [] };
    }

    // 첫 번째 문서에서 컬럼 추출
    const firstDoc = results[0];
    const columns = Object.keys(firstDoc).filter(key => key !== '_id');

    // 행 데이터 변환
    const rows = results.map(doc => {
      const row: any = {};
      columns.forEach(col => {
        let value = doc[col];
        
        // 날짜 포맷팅
        if (value && typeof value === 'string' && value.match(/^\d{4}-\d{2}-\d{2}/)) {
          value = new Date(value).toLocaleString('ko-KR');
        }
        
        // 객체나 배열은 JSON 문자열로 변환
        if (typeof value === 'object' && value !== null) {
          value = JSON.stringify(value, null, 2);
        }
        
        row[col] = value;
      });
      return row;
    });

    return { columns, rows };
  }
}

export const naturalLanguageSearchService = new NaturalLanguageSearchService();
export default naturalLanguageSearchService;