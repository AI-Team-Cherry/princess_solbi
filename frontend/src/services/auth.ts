import axios from 'axios';
import { LoginRequest, LoginResponse, User, ApiResponse } from '../types';

// 백엔드 API URL 업데이트
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

// 토큰 만료 처리
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // 토큰 만료 시 로그아웃 처리
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    
    return Promise.reject(error);
  }
);

// 로그인
export const login = async (credentials: LoginRequest): Promise<LoginResponse> => {
  try {
    console.log('API 호출 데이터:', {
      emp_no: credentials.employeeId,
      password: credentials.password
    });
    
    const response = await api.post('/auth/login', {
      emp_no: credentials.employeeId,
      password: credentials.password
    });
    
    const data = response.data;
    
    // 토큰과 사용자 정보 저장
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    
    return {
      token: data.access_token,
      refreshToken: '', // FastAPI에서는 별도 refresh token 없이 구현
      user: {
        id: data.user.employee_id,
        employeeId: data.user.employee_id,
        name: data.user.name,
        department: data.user.department,
        role: data.user.role,
        createdAt: new Date(),
        updatedAt: new Date()
      }
    };
  } catch (error: any) {
    console.error('Login error:', error);
    console.error('Response status:', error.response?.status);
    console.error('Response data:', error.response?.data);
    throw new Error(error.response?.data?.detail || '로그인에 실패했습니다.');
  }
};

// 로그아웃
export const logout = async (): Promise<void> => {
  try {
    await api.post('/auth/logout');
  } catch (error) {
    console.error('Logout API call failed:', error);
  } finally {
    // 로컬 스토리지 정리
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }
};

// 현재 사용자 정보 조회
export const getCurrentUser = async (): Promise<User> => {
  try {
    const response = await api.get('/auth/me');
    const userData = response.data;
    
    return {
      id: userData.employee_id,
      employeeId: userData.employee_id,
      name: userData.name,
      department: userData.department,
      role: userData.role,
      createdAt: new Date(),
      updatedAt: new Date()
    };
  } catch (error) {
    console.error('Get current user error:', error);
    throw error;
  }
};

// 회원가입 (관리자가 별도로 사용자 생성)
export const register = async (userData: {
  employeeId: string;
  password: string;
  name: string;
  department: string;
}): Promise<User> => {
  // FastAPI 백엔드에서는 별도 회원가입 API 없음 (관리자가 생성)
  throw new Error('회원가입은 관리자를 통해 진행해주세요.');
};

// 토큰 검증
export const verifyToken = async (): Promise<boolean> => {
  try {
    await getCurrentUser();
    return true;
  } catch {
    return false;
  }
};