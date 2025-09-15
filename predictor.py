#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
예측 모듈 - 허깅페이스 모델 사용
"""

import torch
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from tqdm.auto import tqdm

from config import LABEL_NAMES, FASHION_ASPECTS

class ThreeClassPredictor:
    """3클래스 감정 예측기"""
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
        self.model.eval()

    def predict(self, text, aspect="전체"):
        """텍스트의 감정을 예측 (부정/중립/긍정)"""
        if not text or pd.isna(text):
            return {
                "prediction": "중립",
                "confidence": 0.33,
                "probabilities": {
                    "부정": 0.33,
                    "중립": 0.34,
                    "긍정": 0.33
                }
            }

        input_text = f"[{aspect}] {str(text)}"

        device = next(self.model.parameters()).device
        inputs = self.tokenizer(
            input_text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        ).to(device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)
            pred_class = torch.argmax(probs, dim=-1).item()
            confidence = probs[0][pred_class].item()

        return {
            "prediction": LABEL_NAMES[pred_class],
            "confidence": confidence,
            "probabilities": {
                "부정": probs[0][0].item(),
                "중립": probs[0][1].item(),
                "긍정": probs[0][2].item()
            }
        }

def load_huggingface_model(model_name):
    """허깅페이스 모델 로드"""
    print(f"🔄 허깅페이스 모델 로딩: {model_name}")
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        
        # GPU 설정
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model = model.to(device)
        model.eval()
        
        print("✅ 모델 로딩 완료!")
        return model, tokenizer
    except Exception as e:
        print(f"❌ 모델 로딩 실패: {e}")
        return None, None

def find_relevant_aspects_with_model(text, predictor, confidence_threshold=0.55):
    """
    학습된 모델을 사용해서 텍스트에서 관련 있는 속성들을 자동으로 찾기
    키워드 없이 모델이 알아서 판단
    """
    if not text or pd.isna(text):
        return {}

    relevant_aspects = {}

    # 각 속성에 대해 모델로 예측해보기
    for aspect in FASHION_ASPECTS:
        try:
            result = predictor.predict(text, aspect=aspect)
            confidence = result['confidence']

            # 임계값 이상이면 해당 속성이 관련있다고 판단
            if confidence >= confidence_threshold:
                relevant_aspects[aspect] = {
                    'prediction': result['prediction'],
                    'confidence': confidence,
                    'probabilities': result['probabilities']
                }
        except:
            continue

    return relevant_aspects

def test_3class_custom(model_name, text):
    """커스텀 텍스트 3클래스 테스트"""
    model, tokenizer = load_huggingface_model(model_name)
    if not model:
        return

    predictor = ThreeClassPredictor(model, tokenizer)
    result = predictor.predict(text)

    print(f"📝 입력: {text}")
    print(f"🎯 예측: {result['prediction']} (신뢰도: {result['confidence']:.3f})")
    print(f"📊 확률분포:")
    for label, prob in result['probabilities'].items():
        bar = "█" * int(prob * 20)
        print(f"  {label}: {prob:.3f} {bar}")