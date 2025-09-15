"""
고급 머신러닝 분석 모듈
scikit-learn 기반 예측 및 클러스터링 기능
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# scikit-learn 임포트
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import silhouette_score, classification_report, mean_squared_error
from sklearn.impute import SimpleImputer

# 시계열 분석
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.seasonal import seasonal_decompose
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

# 고급 시각화
import matplotlib
matplotlib.use('Agg')  # 비대화형 백엔드 사용으로 팝업 방지
import matplotlib.pyplot as plt
import seaborn as sns

class MLAnalyzer:
    """머신러닝 기반 고급 분석기"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.models = {}
        
    def analyze_data(self, data: pd.DataFrame, analysis_type: str, **kwargs) -> Dict[str, Any]:
        """
        데이터 분석 메인 함수
        
        Args:
            data: 분석할 데이터프레임
            analysis_type: 분석 유형 ('clustering', 'prediction', 'timeseries', 'anomaly', 'segmentation')
            **kwargs: 분석별 추가 파라미터
        """
        
        if data.empty:
            return {"error": "데이터가 없습니다."}
        
        try:
            if analysis_type == 'clustering':
                return self.customer_clustering(data, **kwargs)
            elif analysis_type == 'prediction':
                return self.sales_prediction(data, **kwargs)
            elif analysis_type == 'timeseries':
                return self.timeseries_analysis(data, **kwargs)
            elif analysis_type == 'anomaly':
                return self.anomaly_detection(data, **kwargs)
            elif analysis_type == 'segmentation':
                return self.market_segmentation(data, **kwargs)
            elif analysis_type == 'recommendation':
                return self.product_recommendation(data, **kwargs)
            else:
                return {"error": f"지원하지 않는 분석 유형: {analysis_type}"}
                
        except Exception as e:
            return {"error": f"분석 중 오류 발생: {str(e)}"}
    
    def customer_clustering(self, data: pd.DataFrame, n_clusters: int = 5, sample_size: int = None) -> Dict[str, Any]:
        """고객 클러스터링 분석 (K-means)"""
        
        # 샘플 크기 제한 적용
        if sample_size and len(data) > sample_size:
            data = data.sample(n=sample_size, random_state=42)
        
        # 수치형 컬럼만 선택 (datetime 제외)
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        # datetime 컬럼 제거
        datetime_cols = data.select_dtypes(include=['datetime64', 'datetime']).columns
        data_for_analysis = data.drop(columns=datetime_cols, errors='ignore')
        
        if len(numeric_cols) < 2:
            return {"error": "클러스터링을 위한 충분한 수치 데이터가 없습니다."}
        
        # 결측치 처리 (수치형 데이터만)
        imputer = SimpleImputer(strategy='mean')
        data_clean = pd.DataFrame(
            imputer.fit_transform(data_for_analysis[numeric_cols]), 
            columns=numeric_cols
        )
        
        # 데이터 정규화
        data_scaled = self.scaler.fit_transform(data_clean)
        
        # K-means 클러스터링
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(data_scaled)
        
        # 실루엣 스코어 계산
        silhouette_avg = silhouette_score(data_scaled, clusters)
        
        # 클러스터별 통계
        data_clean['cluster'] = clusters
        cluster_stats = data_clean.groupby('cluster').agg(['mean', 'count']).round(2)
        
        # PCA로 2D 시각화 데이터 생성
        if len(numeric_cols) > 2:
            pca = PCA(n_components=2)
            data_pca = pca.fit_transform(data_scaled)
            explained_variance = pca.explained_variance_ratio_
        else:
            data_pca = data_scaled[:, :2]
            explained_variance = [1.0, 0.0]
        
        # 클러스터 중심점
        centers_scaled = kmeans.cluster_centers_
        if len(numeric_cols) > 2:
            centers_pca = pca.transform(centers_scaled)
        else:
            centers_pca = centers_scaled[:, :2]
        
        return {
            "analysis_type": "customer_clustering",
            "n_clusters": n_clusters,
            "silhouette_score": float(silhouette_avg),
            "cluster_stats": cluster_stats.to_dict(),
            "clusters": clusters.tolist(),
            "visualization_data": {
                "points": data_pca.tolist(),
                "clusters": clusters.tolist(),
                "centers": centers_pca.tolist(),
                "explained_variance": explained_variance.tolist()
            },
            "insights": self._generate_clustering_insights(data_clean, clusters, silhouette_avg),
            "recommendations": self._generate_clustering_recommendations(data_clean, clusters)
        }
    
    def sales_prediction(self, data: pd.DataFrame, target_col: str = 'total_amount', days_ahead: int = 30, sample_size: int = None) -> Dict[str, Any]:
        """매출 예측 분석 (Random Forest)"""
        
        # 샘플 크기 제한 적용
        if sample_size and len(data) > sample_size:
            data = data.sample(n=sample_size, random_state=42)
        
        if target_col not in data.columns:
            # 가능한 타겟 컬럼 찾기
            possible_targets = ['total_amount', 'amount', 'sales', 'revenue', 'price']
            target_col = None
            for col in possible_targets:
                if col in data.columns:
                    target_col = col
                    break
            
            if target_col is None:
                return {"error": "예측할 수 있는 수치 컬럼을 찾을 수 없습니다."}
        
        # 피처 엔지니어링
        features_data = self._create_features_for_prediction(data, target_col)
        
        if features_data.empty:
            return {"error": "예측을 위한 충분한 데이터가 없습니다."}
        
        # 타겟과 피처 분리
        X = features_data.drop(columns=[target_col])
        y = features_data[target_col]
        
        # 결측치 처리
        X = X.fillna(X.mean())
        
        # 훈련/테스트 분할
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Random Forest 모델 훈련
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        rf_model.fit(X_train, y_train)
        
        # 예측 및 성능 평가
        y_pred = rf_model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        
        # 피처 중요도
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': rf_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # 미래 예측 (단순화)
        future_predictions = self._generate_future_predictions(rf_model, X, days_ahead)
        
        return {
            "analysis_type": "sales_prediction",
            "target_column": target_col,
            "model_performance": {
                "rmse": float(rmse),
                "mean_target": float(y.mean()),
                "accuracy_percentage": max(0, 100 - (rmse / y.mean() * 100))
            },
            "feature_importance": feature_importance.head(10).to_dict('records'),
            "predictions": {
                "actual": y_test.tolist()[:20],
                "predicted": y_pred.tolist()[:20]
            },
            "future_forecast": future_predictions,
            "insights": self._generate_prediction_insights(feature_importance, rmse, y.mean()),
            "recommendations": self._generate_prediction_recommendations(feature_importance)
        }
    
    def timeseries_analysis(self, data: pd.DataFrame, date_col: str = None, value_col: str = None, sample_size: int = None) -> Dict[str, Any]:
        """시계열 분석"""
        
        # 샘플 크기 제한 적용
        if sample_size and len(data) > sample_size:
            data = data.sample(n=sample_size, random_state=42)
        
        # 날짜 컬럼 찾기
        if date_col is None:
            date_columns = ['created_at', 'order_date', 'date', 'timestamp']
            for col in date_columns:
                if col in data.columns:
                    date_col = col
                    break
        
        if date_col is None or date_col not in data.columns:
            return {"error": "날짜 컬럼을 찾을 수 없습니다."}
        
        # 값 컬럼 찾기
        if value_col is None:
            value_columns = ['total_amount', 'amount', 'sales', 'count']
            for col in value_columns:
                if col in data.columns:
                    value_col = col
                    break
        
        if value_col is None:
            return {"error": "분석할 수치 컬럼을 찾을 수 없습니다."}
        
        try:
            # 데이터 전처리
            ts_data = data[[date_col, value_col]].copy()
            ts_data[date_col] = pd.to_datetime(ts_data[date_col])
            ts_data = ts_data.sort_values(date_col)
            
            # 일별 집계
            daily_data = ts_data.groupby(ts_data[date_col].dt.date)[value_col].sum().reset_index()
            daily_data.columns = ['date', 'value']
            daily_data['date'] = pd.to_datetime(daily_data['date'])
            daily_data = daily_data.set_index('date')
            
            # 기본 통계
            trend = self._calculate_trend(daily_data['value'])
            seasonality = self._detect_seasonality(daily_data['value'])
            
            # 이동평균
            daily_data['ma_7'] = daily_data['value'].rolling(window=7).mean()
            daily_data['ma_30'] = daily_data['value'].rolling(window=30).mean()
            
            # 변화율
            daily_data['pct_change'] = daily_data['value'].pct_change()
            
            result = {
                "analysis_type": "timeseries_analysis",
                "date_range": {
                    "start": daily_data.index.min().isoformat(),
                    "end": daily_data.index.max().isoformat(),
                    "days": len(daily_data)
                },
                "trend": trend,
                "seasonality": seasonality,
                "statistics": {
                    "mean": float(daily_data['value'].mean()),
                    "std": float(daily_data['value'].std()),
                    "min": float(daily_data['value'].min()),
                    "max": float(daily_data['value'].max())
                },
                "time_series_data": {
                    "dates": daily_data.index.strftime('%Y-%m-%d').tolist(),
                    "values": daily_data['value'].tolist(),
                    "ma_7": daily_data['ma_7'].dropna().tolist(),
                    "ma_30": daily_data['ma_30'].dropna().tolist()
                },
                "insights": self._generate_timeseries_insights(daily_data, trend, seasonality),
                "recommendations": self._generate_timeseries_recommendations(trend, seasonality)
            }
            
            # ARIMA 예측 (가능한 경우)
            if STATSMODELS_AVAILABLE and len(daily_data) > 30:
                try:
                    arima_forecast = self._arima_forecast(daily_data['value'])
                    result["arima_forecast"] = arima_forecast
                except:
                    result["arima_forecast"] = None
            
            return result
            
        except Exception as e:
            return {"error": f"시계열 분석 중 오류: {str(e)}"}
    
    def anomaly_detection(self, data: pd.DataFrame, method: str = 'isolation', sample_size: int = None) -> Dict[str, Any]:
        """이상치 탐지"""
        
        # 샘플 크기 제한 적용
        if sample_size and len(data) > sample_size:
            data = data.sample(n=sample_size, random_state=42)
        
        # 수치형 컬럼만 선택 (datetime 제외)
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        # datetime 컬럼 제거
        datetime_cols = data.select_dtypes(include=['datetime64', 'datetime']).columns
        data_for_analysis = data.drop(columns=datetime_cols, errors='ignore')
        
        if len(numeric_cols) == 0:
            return {"error": "이상치 탐지를 위한 수치 데이터가 없습니다."}
        
        # 결측치 처리 (수치형 데이터만)
        data_clean = data_for_analysis[numeric_cols].fillna(data_for_analysis[numeric_cols].mean())
        
        if method == 'isolation':
            from sklearn.ensemble import IsolationForest
            
            # Isolation Forest
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            anomalies = iso_forest.fit_predict(data_clean)
            anomaly_scores = iso_forest.decision_function(data_clean)
            
        elif method == 'statistical':
            # 통계적 방법 (Z-score)
            z_scores = np.abs((data_clean - data_clean.mean()) / data_clean.std())
            anomalies = (z_scores > 3).any(axis=1).astype(int)
            anomalies = np.where(anomalies == 1, -1, 1)  # -1: 이상치, 1: 정상
            anomaly_scores = -z_scores.max(axis=1)  # 가장 큰 Z-score
        
        else:
            return {"error": f"지원하지 않는 이상치 탐지 방법: {method}"}
        
        # 이상치 분석
        anomaly_indices = np.where(anomalies == -1)[0]
        normal_indices = np.where(anomalies == 1)[0]
        
        anomaly_data = data.iloc[anomaly_indices]
        normal_data = data.iloc[normal_indices]
        
        return {
            "analysis_type": "anomaly_detection",
            "method": method,
            "total_samples": len(data),
            "anomalies_count": len(anomaly_indices),
            "anomaly_rate": float(len(anomaly_indices) / len(data) * 100),
            "anomaly_indices": anomaly_indices.tolist(),
            "anomaly_scores": anomaly_scores.tolist(),
            "anomaly_samples": anomaly_data.head(10).to_dict('records'),
            "normal_stats": normal_data[numeric_cols].describe().to_dict(),
            "anomaly_stats": anomaly_data[numeric_cols].describe().to_dict() if len(anomaly_data) > 0 else {},
            "insights": self._generate_anomaly_insights(len(anomaly_indices), len(data), method),
            "recommendations": self._generate_anomaly_recommendations(len(anomaly_indices), len(data))
        }
    
    # 헬퍼 메서드들
    def _create_features_for_prediction(self, data: pd.DataFrame, target_col: str) -> pd.DataFrame:
        """예측을 위한 피처 생성"""
        features = data.copy()
        
        # 날짜 기반 피처
        date_cols = ['created_at', 'order_date', 'date']
        for col in date_cols:
            if col in features.columns:
                try:
                    features[col] = pd.to_datetime(features[col])
                    features[f'{col}_year'] = features[col].dt.year
                    features[f'{col}_month'] = features[col].dt.month
                    features[f'{col}_day'] = features[col].dt.day
                    features[f'{col}_weekday'] = features[col].dt.dayofweek
                    features = features.drop(columns=[col])
                except:
                    # 날짜 변환 실패시 컬럼 제거
                    features = features.drop(columns=[col], errors='ignore')
        
        # datetime 타입 컬럼 모두 제거
        datetime_cols = features.select_dtypes(include=['datetime64', 'datetime']).columns
        features = features.drop(columns=datetime_cols, errors='ignore')
        
        # 카테고리 변수 인코딩
        categorical_cols = features.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if features[col].nunique() < 100:  # 카테고리가 너무 많지 않은 경우만
                try:
                    features[col] = pd.Categorical(features[col]).codes
                except:
                    features = features.drop(columns=[col], errors='ignore')
            else:
                features = features.drop(columns=[col])
        
        # ID 컬럼 제거
        id_cols = [col for col in features.columns if '_id' in col.lower()]
        features = features.drop(columns=id_cols, errors='ignore')
        
        # 수치형 데이터만 남기기
        numeric_cols = features.select_dtypes(include=[np.number]).columns
        features = features[numeric_cols]
        
        return features
    
    def _calculate_trend(self, series: pd.Series) -> Dict[str, Any]:
        """트렌드 계산"""
        if len(series) < 2:
            return {"direction": "unknown", "slope": 0, "r_squared": 0}
        
        x = np.arange(len(series))
        y = series.values
        
        # 선형 회귀
        slope, intercept = np.polyfit(x, y, 1)
        
        # R-squared
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
        
        return {
            "direction": direction,
            "slope": float(slope),
            "r_squared": float(r_squared)
        }
    
    def _detect_seasonality(self, series: pd.Series) -> Dict[str, Any]:
        """계절성 감지"""
        if len(series) < 14:  # 최소 2주 데이터 필요
            return {"detected": False, "period": None, "strength": 0}
        
        # 자기상관 계산 (단순화)
        try:
            # 주별 패턴 확인 (7일)
            if len(series) >= 14:
                weekly_corr = series.corr(series.shift(7))
                if not np.isnan(weekly_corr) and weekly_corr > 0.3:
                    return {"detected": True, "period": 7, "strength": float(weekly_corr)}
            
            return {"detected": False, "period": None, "strength": 0}
        except:
            return {"detected": False, "period": None, "strength": 0}
    
    def _generate_future_predictions(self, model, X: pd.DataFrame, days_ahead: int) -> List[Dict]:
        """미래 예측 생성 (단순화)"""
        # 최근 데이터 패턴을 바탕으로 미래 예측
        last_row = X.iloc[-1:].copy()
        predictions = []
        
        for i in range(min(days_ahead, 30)):  # 최대 30일까지
            pred = model.predict(last_row)[0]
            predictions.append({
                "day": i + 1,
                "predicted_value": float(pred)
            })
        
        return predictions
    
    def _arima_forecast(self, series: pd.Series, steps: int = 7) -> Dict[str, Any]:
        """ARIMA 모델을 사용한 예측"""
        try:
            # 간단한 ARIMA(1,1,1) 모델
            model = ARIMA(series, order=(1, 1, 1))
            fitted_model = model.fit()
            
            # 예측
            forecast = fitted_model.forecast(steps=steps)
            conf_int = fitted_model.get_forecast(steps=steps).conf_int()
            
            return {
                "forecast": forecast.tolist(),
                "confidence_interval": {
                    "lower": conf_int.iloc[:, 0].tolist(),
                    "upper": conf_int.iloc[:, 1].tolist()
                }
            }
        except:
            return None
    
    # 인사이트 생성 메서드들
    def _generate_clustering_insights(self, data: pd.DataFrame, clusters: np.ndarray, silhouette_score: float) -> List[str]:
        """클러스터링 인사이트"""
        insights = []
        n_clusters = len(np.unique(clusters))
        
        insights.append(f"고객을 {n_clusters}개 그룹으로 세분화했습니다.")
        insights.append(f"클러스터링 품질 점수: {silhouette_score:.2f} (1에 가까울수록 좋음)")
        
        # 가장 큰 클러스터
        cluster_counts = pd.Series(clusters).value_counts()
        largest_cluster = cluster_counts.index[0]
        insights.append(f"가장 큰 고객 그룹은 {largest_cluster}번 그룹으로 전체의 {cluster_counts.iloc[0]/len(clusters)*100:.1f}%를 차지합니다.")
        
        return insights
    
    def _generate_clustering_recommendations(self, data: pd.DataFrame, clusters: np.ndarray) -> List[str]:
        """클러스터링 추천사항"""
        return [
            "각 고객 그룹별로 차별화된 마케팅 전략을 수립하세요.",
            "가장 큰 그룹에 집중하여 매출 증대를 노리세요.",
            "작은 그룹들은 프리미엄 고객일 가능성이 있으니 특별 관리하세요."
        ]
    
    def _generate_prediction_insights(self, feature_importance: pd.DataFrame, rmse: float, mean_target: float) -> List[str]:
        """예측 인사이트"""
        insights = []
        
        accuracy = max(0, 100 - (rmse / mean_target * 100))
        insights.append(f"예측 정확도: {accuracy:.1f}%")
        
        if len(feature_importance) > 0:
            top_feature = feature_importance.iloc[0]
            insights.append(f"가장 중요한 예측 요인: {top_feature['feature']}")
        
        return insights
    
    def _generate_prediction_recommendations(self, feature_importance: pd.DataFrame) -> List[str]:
        """예측 추천사항"""
        recommendations = [
            "예측 모델을 정기적으로 업데이트하여 정확도를 유지하세요.",
            "중요 요인들을 모니터링하여 비즈니스 전략에 반영하세요."
        ]
        
        if len(feature_importance) > 0:
            top_feature = feature_importance.iloc[0]['feature']
            recommendations.append(f"{top_feature} 관련 데이터 품질을 높이면 예측 성능이 개선됩니다.")
        
        return recommendations
    
    def _generate_timeseries_insights(self, data: pd.DataFrame, trend: Dict, seasonality: Dict) -> List[str]:
        """시계열 인사이트"""
        insights = []
        
        insights.append(f"전체 기간 동안 {trend['direction']} 추세를 보입니다.")
        
        if seasonality['detected']:
            insights.append(f"{seasonality['period']}일 주기의 계절성이 감지되었습니다.")
        else:
            insights.append("뚜렷한 계절성은 발견되지 않았습니다.")
        
        # 변동성 분석
        cv = data['value'].std() / data['value'].mean()
        if cv > 0.3:
            insights.append("데이터의 변동성이 큽니다.")
        else:
            insights.append("데이터가 상대적으로 안정적입니다.")
        
        return insights
    
    def _generate_timeseries_recommendations(self, trend: Dict, seasonality: Dict) -> List[str]:
        """시계열 추천사항"""
        recommendations = []
        
        if trend['direction'] == 'increasing':
            recommendations.append("긍정적인 성장 추세입니다. 현재 전략을 유지하세요.")
        elif trend['direction'] == 'decreasing':
            recommendations.append("하락 추세입니다. 개선 전략이 필요합니다.")
        
        if seasonality['detected']:
            recommendations.append("계절성을 고려한 재고 관리 및 마케팅 계획을 수립하세요.")
        
        return recommendations
    
    def _generate_anomaly_insights(self, anomaly_count: int, total_count: int, method: str) -> List[str]:
        """이상치 인사이트"""
        rate = anomaly_count / total_count * 100
        
        insights = [
            f"{method} 방법으로 전체 데이터의 {rate:.1f}%에서 이상치를 발견했습니다.",
            f"총 {anomaly_count}개의 이상 패턴이 감지되었습니다."
        ]
        
        if rate > 10:
            insights.append("이상치 비율이 높습니다. 데이터 품질을 점검해보세요.")
        elif rate < 1:
            insights.append("데이터가 매우 일관적입니다.")
        
        return insights
    
    def _generate_anomaly_recommendations(self, anomaly_count: int, total_count: int) -> List[str]:
        """이상치 추천사항"""
        rate = anomaly_count / total_count * 100
        
        recommendations = [
            "발견된 이상치들을 개별적으로 검토하여 원인을 파악하세요.",
            "반복적인 이상치 패턴이 있다면 비즈니스 프로세스를 점검하세요."
        ]
        
        if rate > 5:
            recommendations.append("이상치 탐지 시스템을 구축하여 실시간 모니터링하세요.")
        
        return recommendations
    
    def market_segmentation(self, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """시장 세분화 분석"""
        return {"error": "시장 세분화 기능은 개발 중입니다."}
    
    def product_recommendation(self, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """상품 추천 분석"""
        return {"error": "상품 추천 기능은 개발 중입니다."}