from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os
import logging
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # GUI 없는 환경을 위한 설정
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import io
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.metrics import accuracy_score, classification_report, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
import warnings
warnings.filterwarnings('ignore')
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)

# MongoDB 연결
MONGODB_URI = os.getenv("MONGODB_URI") or os.getenv("MONGODB_URL")
DB_NAME = os.getenv("DB_NAME") or os.getenv("DATABASE_NAME", "musinsa_db")
MODEL_ID = os.getenv("MODEL_ID", "kakaocorp/kanana-nano-2.1b-instruct")

if not MONGODB_URI:
    MONGODB_URI = "mongodb+srv://musinsa:musinsa@cluster0.ed1m1eg.mongodb.net/musinsa?retryWrites=true&w=majority&appName=Cluster0"
    logger.warning("Using default MongoDB URI")

client = AsyncIOMotorClient(MONGODB_URI)
db: AsyncIOMotorDatabase = client[DB_NAME]

# 라우터 생성
router = APIRouter(prefix="/api", tags=["nl2analysis"])

# Pydantic 모델들
class NL2AnalysisRequest(BaseModel):
    dataset_id: str = Field(..., description="분석할 데이터셋 ID")
    query: str = Field(..., min_length=1, description="한국어 분석 요청")

# 분석 실행기 클래스
class AnalysisExecutor:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
        
    def create_analysis_prompt(self, query: str, data_info: Dict[str, Any]) -> str:
        """분석 요청을 위한 프롬프트 생성"""
        prompt = f"""너는 데이터 분석가다. 한국어 요청에 따라 분석 계획을 수립하라.

데이터 정보:
- 행 수: {data_info.get('row_count', 0)}
- 컬럼: {', '.join(data_info.get('columns', []))}
- 컬렉션: {data_info.get('collection', 'unknown')}

분석 요청: "{query}"

다음 중 적절한 분석 유형을 선택하고 실행 계획을 제시하라:
1. EDA (탐색적 데이터 분석): 기술통계, 분포 시각화, 상관관계 분석
2. ML_CLASSIFICATION: 분류 모델 (로지스틱 회귀, 랜덤 포레스트)
3. ML_REGRESSION: 회귀 모델 (선형 회귀, 랜덤 포레스트)
4. STATISTICAL: 기본 통계 분석 및 요약

응답 형식:
ANALYSIS_TYPE: [EDA/ML_CLASSIFICATION/ML_REGRESSION/STATISTICAL]
TARGET_COLUMN: [예측하고자 하는 컬럼명 또는 None]
FEATURES: [사용할 특성 컬럼들 또는 AUTO]
DESCRIPTION: [분석 내용 설명]

분석 계획:"""
        
        return prompt
    
    async def interpret_analysis_request(self, query: str, data_info: Dict[str, Any]) -> Dict[str, Any]:
        """자연어 분석 요청 해석"""
        query_lower = query.lower()
        
        # 키워드 기반 분석 유형 결정
        if any(word in query_lower for word in ["eda", "탐색", "분석", "시각화", "분포", "상관관계"]):
            analysis_type = "EDA"
        elif any(word in query_lower for word in ["분류", "예측", "로지스틱", "classification"]):
            analysis_type = "ML_CLASSIFICATION"
        elif any(word in query_lower for word in ["회귀", "예측", "regression", "linear"]):
            analysis_type = "ML_REGRESSION"
        else:
            analysis_type = "STATISTICAL"
        
        # 타겟 컬럼 추론
        target_column = None
        if "score" in data_info.get('columns', []) and any(word in query_lower for word in ["평점", "점수"]):
            target_column = "score"
        elif "price" in data_info.get('columns', []) and any(word in query_lower for word in ["가격", "매출"]):
            target_column = "price"
        elif "total_amount" in data_info.get('columns', []) and any(word in query_lower for word in ["매출", "금액"]):
            target_column = "total_amount"
        
        return {
            "analysis_type": analysis_type,
            "target_column": target_column,
            "features": "AUTO",
            "description": f"'{query}' 요청에 대한 {analysis_type} 분석"
        }
    
    async def execute_eda(self, df: pd.DataFrame, data_info: Dict[str, Any]) -> Dict[str, Any]:
        """탐색적 데이터 분석 실행"""
        try:
            results = {
                "summary": {},
                "charts": [],
                "insights": []
            }
            
            # 기술 통계
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                results["summary"]["numeric_stats"] = df[numeric_cols].describe().to_dict()
                
            # 문자형 컬럼 정보
            categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
            if categorical_cols:
                cat_info = {}
                for col in categorical_cols[:5]:  # 최대 5개만
                    cat_info[col] = {
                        "unique_count": df[col].nunique(),
                        "top_values": df[col].value_counts().head().to_dict()
                    }
                results["summary"]["categorical_stats"] = cat_info
            
            # 차트 생성
            charts = []
            
            # 1. 숫자형 컬럼 히스토그램
            if numeric_cols:
                fig, axes = plt.subplots(min(2, len(numeric_cols)), 2, figsize=(12, 8))
                if len(numeric_cols) == 1:
                    axes = [axes]
                    
                for i, col in enumerate(numeric_cols[:4]):  # 최대 4개
                    ax = axes.flat[i] if len(numeric_cols) > 1 else axes[0]
                    df[col].hist(bins=20, ax=ax, alpha=0.7)
                    ax.set_title(f'{col} 분포')
                    ax.set_xlabel(col)
                    ax.set_ylabel('빈도')
                
                plt.tight_layout()
                
                # base64 인코딩
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                buffer.seek(0)
                chart_base64 = base64.b64encode(buffer.getvalue()).decode()
                buffer.close()
                plt.close()
                
                charts.append({
                    "type": "histogram",
                    "title": "숫자형 변수 분포",
                    "data": f"data:image/png;base64,{chart_base64}"
                })
            
            # 2. 상관관계 히트맵
            if len(numeric_cols) > 1:
                plt.figure(figsize=(10, 8))
                correlation_matrix = df[numeric_cols].corr()
                sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0, square=True)
                plt.title('변수간 상관관계')
                
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                buffer.seek(0)
                chart_base64 = base64.b64encode(buffer.getvalue()).decode()
                buffer.close()
                plt.close()
                
                charts.append({
                    "type": "heatmap",
                    "title": "상관관계 히트맵",
                    "data": f"data:image/png;base64,{chart_base64}"
                })
            
            results["charts"] = charts
            
            # 인사이트 생성
            insights = []
            if numeric_cols:
                insights.append(f"숫자형 변수 {len(numeric_cols)}개 발견: {', '.join(numeric_cols)}")
                
            if categorical_cols:
                insights.append(f"범주형 변수 {len(categorical_cols)}개 발견: {', '.join(categorical_cols[:3])}...")
                
            results["insights"] = insights
            
            return results
            
        except Exception as e:
            logger.error(f"EDA execution error: {str(e)}")
            return {
                "summary": {"error": str(e)},
                "charts": [],
                "insights": [f"EDA 실행 중 오류 발생: {str(e)}"]
            }
    
    async def execute_ml_classification(self, df: pd.DataFrame, target_col: str) -> Dict[str, Any]:
        """분류 모델 실행"""
        try:
            if target_col not in df.columns:
                raise ValueError(f"Target column '{target_col}' not found")
            
            # 특성과 타겟 분리
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if target_col in numeric_cols:
                numeric_cols.remove(target_col)
            
            if not numeric_cols:
                raise ValueError("No numeric features available for classification")
            
            X = df[numeric_cols].fillna(0)
            y = df[target_col]
            
            # 타겟이 연속값이면 범주화
            if y.dtype in ['float64', 'int64'] and y.nunique() > 10:
                y = pd.cut(y, bins=3, labels=['Low', 'Medium', 'High'])
            
            # 레이블 인코딩
            le = LabelEncoder()
            y_encoded = le.fit_transform(y.astype(str))
            
            # 데이터 분할
            X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)
            
            # 모델 학습
            rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
            rf_model.fit(X_train, y_train)
            
            # 예측 및 평가
            y_pred = rf_model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            # 특성 중요도
            feature_importance = dict(zip(numeric_cols, rf_model.feature_importances_))
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            
            # 특성 중요도 차트
            plt.figure(figsize=(10, 6))
            features, importance = zip(*sorted_features[:10])  # 상위 10개
            plt.barh(range(len(features)), importance)
            plt.yticks(range(len(features)), features)
            plt.xlabel('중요도')
            plt.title('특성 중요도')
            plt.tight_layout()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            chart_base64 = base64.b64encode(buffer.getvalue()).decode()
            buffer.close()
            plt.close()
            
            return {
                "model_type": "Random Forest Classifier",
                "accuracy": round(accuracy, 4),
                "feature_importance": dict(sorted_features[:5]),
                "target_classes": le.classes_.tolist(),
                "charts": [{
                    "type": "feature_importance",
                    "title": "특성 중요도",
                    "data": f"data:image/png;base64,{chart_base64}"
                }],
                "insights": [
                    f"분류 정확도: {accuracy:.1%}",
                    f"가장 중요한 특성: {sorted_features[0][0]}",
                    f"사용된 특성 수: {len(numeric_cols)}"
                ]
            }
            
        except Exception as e:
            logger.error(f"ML Classification error: {str(e)}")
            return {
                "model_type": "Classification",
                "error": str(e),
                "charts": [],
                "insights": [f"분류 모델 실행 중 오류: {str(e)}"]
            }
    
    async def execute_ml_regression(self, df: pd.DataFrame, target_col: str) -> Dict[str, Any]:
        """회귀 모델 실행"""
        try:
            if target_col not in df.columns:
                raise ValueError(f"Target column '{target_col}' not found")
            
            # 특성과 타겟 분리
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if target_col in numeric_cols:
                numeric_cols.remove(target_col)
            
            if not numeric_cols:
                raise ValueError("No numeric features available for regression")
            
            X = df[numeric_cols].fillna(0)
            y = df[target_col].fillna(df[target_col].mean())
            
            # 데이터 분할
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # 모델 학습
            rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
            rf_model.fit(X_train, y_train)
            
            # 예측 및 평가
            y_pred = rf_model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # 특성 중요도
            feature_importance = dict(zip(numeric_cols, rf_model.feature_importances_))
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            
            # 예측 vs 실제값 차트
            plt.figure(figsize=(10, 6))
            plt.scatter(y_test, y_pred, alpha=0.5)
            plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
            plt.xlabel('실제값')
            plt.ylabel('예측값')
            plt.title('예측값 vs 실제값')
            plt.tight_layout()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            chart_base64 = base64.b64encode(buffer.getvalue()).decode()
            buffer.close()
            plt.close()
            
            return {
                "model_type": "Random Forest Regressor",
                "r2_score": round(r2, 4),
                "mse": round(mse, 4),
                "feature_importance": dict(sorted_features[:5]),
                "charts": [{
                    "type": "regression_plot",
                    "title": "예측값 vs 실제값",
                    "data": f"data:image/png;base64,{chart_base64}"
                }],
                "insights": [
                    f"R² 점수: {r2:.3f}",
                    f"평균제곱오차: {mse:.2f}",
                    f"가장 중요한 특성: {sorted_features[0][0]}"
                ]
            }
            
        except Exception as e:
            logger.error(f"ML Regression error: {str(e)}")
            return {
                "model_type": "Regression",
                "error": str(e),
                "charts": [],
                "insights": [f"회귀 모델 실행 중 오류: {str(e)}"]
            }
    
    async def execute_statistical_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """기본 통계 분석 실행"""
        try:
            results = {
                "basic_stats": {},
                "data_info": {},
                "charts": [],
                "insights": []
            }
            
            # 데이터 기본 정보
            results["data_info"] = {
                "rows": len(df),
                "columns": len(df.columns),
                "missing_values": df.isnull().sum().to_dict(),
                "data_types": df.dtypes.astype(str).to_dict()
            }
            
            # 기술 통계
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                results["basic_stats"] = df[numeric_cols].describe().to_dict()
            
            # 간단한 막대 차트 (범주형 변수)
            categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
            if categorical_cols:
                col = categorical_cols[0]  # 첫 번째 범주형 변수
                if df[col].nunique() <= 10:  # 카테고리가 너무 많지 않은 경우
                    value_counts = df[col].value_counts().head(10)
                    
                    plt.figure(figsize=(10, 6))
                    value_counts.plot(kind='bar')
                    plt.title(f'{col} 분포')
                    plt.xlabel(col)
                    plt.ylabel('개수')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    
                    buffer = io.BytesIO()
                    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                    buffer.seek(0)
                    chart_base64 = base64.b64encode(buffer.getvalue()).decode()
                    buffer.close()
                    plt.close()
                    
                    results["charts"].append({
                        "type": "bar_chart",
                        "title": f"{col} 분포",
                        "data": f"data:image/png;base64,{chart_base64}"
                    })
            
            # 인사이트 생성
            insights = []
            insights.append(f"총 {len(df)}개 행, {len(df.columns)}개 컬럼")
            
            missing_count = df.isnull().sum().sum()
            if missing_count > 0:
                insights.append(f"결측값 {missing_count}개 발견")
            else:
                insights.append("결측값 없음")
            
            if numeric_cols:
                insights.append(f"숫자형 변수 {len(numeric_cols)}개")
            
            if categorical_cols:
                insights.append(f"범주형 변수 {len(categorical_cols)}개")
            
            results["insights"] = insights
            
            return results
            
        except Exception as e:
            logger.error(f"Statistical analysis error: {str(e)}")
            return {
                "basic_stats": {"error": str(e)},
                "charts": [],
                "insights": [f"통계 분석 중 오류: {str(e)}"]
            }

# 분석 실행기 인스턴스
analysis_executor = AnalysisExecutor()

# API 엔드포인트들
@router.post("/nl2analysis")
async def execute_nl_analysis(request: NL2AnalysisRequest):
    """자연어 분석 요청 실행"""
    try:
        logger.info(f"NL2Analysis request: dataset_id={request.dataset_id}, query={request.query}")
        
        # 데이터셋 조회
        dataset = await db.saved_datasets.find_one({"dataset_id": request.dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="데이터셋을 찾을 수 없습니다")
        
        # 데이터셋을 DataFrame으로 변환
        preview_data = dataset.get("preview", [])
        if not preview_data:
            raise HTTPException(status_code=400, detail="데이터셋이 비어있습니다")
        
        df = pd.DataFrame(preview_data)
        
        # 데이터 정보 수집
        data_info = {
            "row_count": len(df),
            "columns": df.columns.tolist(),
            "collection": dataset.get("source", {}).get("collection", "unknown")
        }
        
        # 자연어 요청 해석
        analysis_plan = await analysis_executor.interpret_analysis_request(request.query, data_info)
        
        # 분석 실행
        if analysis_plan["analysis_type"] == "EDA":
            analysis_result = await analysis_executor.execute_eda(df, data_info)
        elif analysis_plan["analysis_type"] == "ML_CLASSIFICATION":
            target_col = analysis_plan.get("target_column")
            if not target_col:
                # 기본 타겟 컬럼 선택
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                target_col = numeric_cols[0] if numeric_cols else None
            
            if target_col:
                analysis_result = await analysis_executor.execute_ml_classification(df, target_col)
            else:
                raise HTTPException(status_code=400, detail="분류할 타겟 컬럼을 찾을 수 없습니다")
        
        elif analysis_plan["analysis_type"] == "ML_REGRESSION":
            target_col = analysis_plan.get("target_column")
            if not target_col:
                # 기본 타겟 컬럼 선택
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                target_col = numeric_cols[0] if numeric_cols else None
            
            if target_col:
                analysis_result = await analysis_executor.execute_ml_regression(df, target_col)
            else:
                raise HTTPException(status_code=400, detail="예측할 타겟 컬럼을 찾을 수 없습니다")
        
        else:  # STATISTICAL
            analysis_result = await analysis_executor.execute_statistical_analysis(df)
        
        return {
            "success": True,
            "dataset_id": request.dataset_id,
            "analysis_type": analysis_plan["analysis_type"],
            "query_interpretation": analysis_plan["description"],
            "results": analysis_result,
            "data_info": data_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"NL2Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"분석 실행 중 오류 발생: {str(e)}")

@router.get("/nl2analysis/examples")
async def get_nl2analysis_examples():
    """자연어 분석 요청 예시 제공"""
    return {
        "examples": [
            {
                "query": "이 데이터셋 EDA 해줘",
                "description": "기본적인 탐색적 데이터 분석 수행"
            },
            {
                "query": "평점 예측 모델 만들어줘",
                "description": "평점을 타겟으로 하는 분류/회귀 모델 학습"
            },
            {
                "query": "로지스틱 회귀로 분류해줘",
                "description": "로지스틱 회귀를 사용한 분류 모델"
            },
            {
                "query": "기본 통계 분석해줘",
                "description": "기술통계 및 기본 시각화 제공"
            },
            {
                "query": "상관관계 분석하고 시각화해줘",
                "description": "변수간 상관관계 분석 및 히트맵 생성"
            }
        ]
    }