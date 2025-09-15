"""
GPT 기반 Reflection 구조 분석기
생성 > 반성 > 재생성을 최대 10번 반복하여 완벽한 보고서 생성
"""

import os
import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import openai
import pandas as pd
from pydantic import BaseModel, Field

class ReflectionStep(BaseModel):
    """Reflection 단계를 나타내는 모델"""
    step: int
    generation: str
    reflection: str
    score: float = Field(ge=0, le=10)
    improvements: List[str] = []

class AnalysisResult(BaseModel):
    """최종 분석 결과 모델"""
    question: str
    final_report: str
    reflection_steps: List[ReflectionStep]
    total_steps: int
    execution_time: float
    final_score: float
    data_summary: str

class GPTReflectionAnalyzer:
    """GPT 기반 Reflection 분석기"""
    
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.max_reflections = 10
        self.target_score = 9.0
        
    def analyze_with_reflection(self, question: str, data: pd.DataFrame) -> AnalysisResult:
        """Reflection 구조로 분석 수행"""
        start_time = time.time()
        
        # 데이터 요약 생성
        data_summary = self._create_data_summary(data)
        
        # Reflection 단계들
        reflection_steps = []
        current_generation = ""
        
        print(f"🚀 GPT Reflection 분석 시작: {question}")
        print("=" * 80)
        
        for step in range(1, self.max_reflections + 1):
            print(f"\n📝 Step {step}: 분석 생성 중...")
            
            # 1단계: 분석 생성
            if step == 1:
                current_generation = self._generate_initial_analysis(question, data_summary)
            else:
                # 이전 반성을 바탕으로 개선된 분석 생성
                previous_reflection = reflection_steps[-1].reflection
                previous_improvements = reflection_steps[-1].improvements
                current_generation = self._improve_analysis(
                    question, data_summary, current_generation, 
                    previous_reflection, previous_improvements
                )
            
            print(f"✅ 분석 생성 완료 ({len(current_generation)}자)")
            
            # 2단계: 반성 및 평가
            print(f"🤔 Step {step}: 반성 및 평가 중...")
            reflection_result = self._reflect_on_analysis(current_generation, question)
            
            # ReflectionStep 객체 생성
            step_result = ReflectionStep(
                step=step,
                generation=current_generation,
                reflection=reflection_result["reflection"],
                score=reflection_result["score"],
                improvements=reflection_result["improvements"]
            )
            
            reflection_steps.append(step_result)
            
            print(f"📊 Step {step} 완료 - 점수: {reflection_result['score']}/10")
            print(f"📋 개선점: {len(reflection_result['improvements'])}개")
            
            # 목표 점수 달성 시 종료
            if reflection_result["score"] >= self.target_score:
                print(f"🎉 목표 점수 달성! ({reflection_result['score']}/10)")
                break
                
            # 최대 단계 도달 시 경고
            if step == self.max_reflections:
                print(f"⚠️ 최대 반복 횟수 도달 ({self.max_reflections}회)")
        
        execution_time = time.time() - start_time
        
        # 최종 결과 구성
        final_result = AnalysisResult(
            question=question,
            final_report=current_generation,
            reflection_steps=reflection_steps,
            total_steps=len(reflection_steps),
            execution_time=execution_time,
            final_score=reflection_steps[-1].score,
            data_summary=data_summary
        )
        
        print(f"\n🏁 Reflection 분석 완료!")
        print(f"📈 최종 점수: {final_result.final_score}/10")
        print(f"⏱️ 실행 시간: {execution_time:.2f}초")
        print(f"🔄 총 반복 횟수: {final_result.total_steps}회")
        
        return final_result
    
    def _create_data_summary(self, data: pd.DataFrame) -> str:
        """데이터 요약 생성"""
        if data.empty:
            return "분석할 데이터가 없습니다."
        
        summary_parts = []
        summary_parts.append(f"총 {len(data)}개의 데이터 포인트")
        
        # 숫자형 컬럼 요약
        numeric_cols = data.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            if col != '_id':
                mean_val = data[col].mean()
                max_val = data[col].max()
                min_val = data[col].min()
                summary_parts.append(f"{col}: 평균 {mean_val:.2f}, 최대 {max_val:.2f}, 최소 {min_val:.2f}")
        
        # 카테고리별 요약
        if '_id' in data.columns and len(data) > 0:
            summary_parts.append(f"주요 카테고리: {', '.join(data['_id'].head(5).tolist())}")
        
        return " | ".join(summary_parts)
    
    def _generate_initial_analysis(self, question: str, data_summary: str) -> str:
        """초기 분석 생성"""
        prompt = f"""당신은 무신사 이커머스 데이터 분석 전문가입니다.
주어진 질문에 대해 포괄적이고 전문적인 분석 보고서를 작성해주세요.

질문: {question}
데이터 요약: {data_summary}

다음 구조로 상세한 보고서를 작성해주세요:

## 1. 경영진 요약 (500자 이상)
- 핵심 발견사항과 비즈니스 임팩트
- 즉시 실행 가능한 액션 아이템
- 예상 효과와 ROI

## 2. 데이터 분석 결과 (1500자 이상)
- 주요 지표 분석
- 패턴 및 트렌드 식별
- 통계적 인사이트
- 비교 분석 결과

## 3. 원인 분석 (1000자 이상)
- 현상의 근본 원인
- 영향 요인 분석
- 시장 환경 고려사항
- 고객 행동 분석

## 4. 비즈니스 영향 분석 (800자 이상)
- 매출/수익성 영향
- 고객 만족도 영향
- 브랜드 이미지 영향
- 운영 효율성 영향

## 5. 실행 계획 (1000자 이상)
- 단기 대응 방안 (1-3개월)
- 중기 전략 (3-12개월)  
- 장기 비전 (1-3년)
- 구체적 실행 단계

## 6. 리스크 관리 (400자 이상)
- 예상 리스크
- 완화 전략
- 모니터링 방법

## 7. 성과 측정 (300자 이상)
- 핵심 KPI
- 측정 주기
- 목표 수치

총 5000자 이상으로 작성하고, 구체적 수치와 실행 가능한 권장사항을 포함하세요.
무신사의 비즈니스 특성을 반영하여 실무적 가치가 높은 내용으로 구성하세요."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"분석 생성 중 오류가 발생했습니다: {str(e)}"
    
    def _reflect_on_analysis(self, analysis: str, question: str) -> Dict[str, Any]:
        """분석에 대한 반성 및 평가"""
        reflection_prompt = f"""다음은 "{question}"에 대한 분석 보고서입니다.
이 분석을 객관적으로 평가하고 개선점을 제시해주세요.

분석 보고서:
{analysis}

다음 기준으로 1-10점 사이에서 평가해주세요:
1. 분석의 완성도와 논리성
2. 실행 가능성과 구체성  
3. 비즈니스 가치와 실용성
4. 데이터 해석의 정확성
5. 권장사항의 명확성

평가 결과를 다음 JSON 형식으로 제공해주세요:
{{
    "score": 점수(1-10),
    "reflection": "분석에 대한 상세한 평가와 피드백 (1000자 이상)",
    "improvements": ["구체적 개선점1", "구체적 개선점2", "구체적 개선점3", ...]
}}

반드시 정확한 JSON 형식으로 응답해주세요."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": reflection_prompt}],
                max_tokens=2000,
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            
            # JSON 파싱 시도
            try:
                # JSON 블록 추출
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    content = content[start:end].strip()
                elif content.startswith("{") and content.endswith("}"):
                    content = content
                else:
                    # JSON이 아닌 경우 기본 구조 생성
                    raise ValueError("JSON 형식이 아님")
                
                result = json.loads(content)
                
                # 필수 키 확인 및 기본값 설정
                if "score" not in result:
                    result["score"] = 5.0
                if "reflection" not in result:
                    result["reflection"] = "평가를 생성할 수 없습니다."
                if "improvements" not in result:
                    result["improvements"] = ["구체적 개선점 필요"]
                
                # 점수 범위 확인
                result["score"] = max(1, min(10, float(result["score"])))
                
                return result
                
            except (json.JSONDecodeError, ValueError) as e:
                # JSON 파싱 실패 시 기본 반환값
                return {
                    "score": 5.0,
                    "reflection": f"반성 분석을 파싱할 수 없습니다: {str(e)}",
                    "improvements": ["JSON 형식 개선 필요", "구조화된 응답 필요"]
                }
                
        except Exception as e:
            return {
                "score": 5.0,
                "reflection": f"반성 생성 중 오류가 발생했습니다: {str(e)}",
                "improvements": ["오류 해결 필요"]
            }
    
    def _improve_analysis(self, question: str, data_summary: str, previous_analysis: str, 
                         reflection: str, improvements: List[str]) -> str:
        """이전 분석을 개선하여 새로운 분석 생성"""
        improvement_prompt = f"""다음은 "{question}"에 대한 이전 분석과 개선 피드백입니다.
피드백을 반영하여 더 나은 분석 보고서를 작성해주세요.

질문: {question}
데이터 요약: {data_summary}

이전 분석:
{previous_analysis}

개선 피드백:
{reflection}

구체적 개선점:
{', '.join(improvements)}

위 피드백을 모두 반영하여 다음 구조로 개선된 보고서를 작성해주세요:

## 1. 경영진 요약 (500자 이상)
## 2. 데이터 분석 결과 (1500자 이상)  
## 3. 원인 분석 (1000자 이상)
## 4. 비즈니스 영향 분석 (800자 이상)
## 5. 실행 계획 (1000자 이상)
## 6. 리스크 관리 (400자 이상)
## 7. 성과 측정 (300자 이상)

개선점을 적극 반영하여 더 완성도 높은 5000자 이상의 보고서를 작성하세요.
특히 지적된 부분을 중점적으로 개선하고, 더 구체적이고 실행 가능한 내용으로 보완하세요."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": improvement_prompt}],
                max_tokens=4000,
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"개선된 분석 생성 중 오류가 발생했습니다: {str(e)}"
    
    def format_result_for_display(self, result: AnalysisResult) -> Dict[str, Any]:
        """결과를 표시용으로 포맷팅"""
        return {
            "question": result.question,
            "final_report": result.final_report,
            "analysis_summary": {
                "total_steps": result.total_steps,
                "final_score": result.final_score,
                "execution_time": f"{result.execution_time:.2f}초",
                "report_length": f"{len(result.final_report)}자"
            },
            "reflection_history": [
                {
                    "step": step.step,
                    "score": step.score,
                    "improvements_count": len(step.improvements),
                    "reflection_preview": step.reflection[:200] + "..." if len(step.reflection) > 200 else step.reflection
                }
                for step in result.reflection_steps
            ],
            "data_summary": result.data_summary
        }