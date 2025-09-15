#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
허깅페이스 모델 사용 예제
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from predictor import ThreeClassPredictor

# 허깅페이스 모델 정보
MODEL_NAME = "solbi12/ecommers_fasion_fine_tuned_3class_model"
LABEL_NAMES = ["부정", "중립", "긍정"]

def load_huggingface_model():
    """허깅페이스에서 모델 로드"""
    print(f"🔄 허깅페이스 모델 로딩: {MODEL_NAME}")
    
    try:
        # 토크나이저와 모델 로드
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        
        # GPU 설정
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model = model.to(device)
        model.eval()
        
        print("✅ 모델 로딩 완료!")
        return model, tokenizer
    except Exception as e:
        print(f"❌ 모델 로딩 실패: {e}")
        return None, None

def predict_sentiment(text, model, tokenizer):
    """텍스트 감정 분석"""
    if not text:
        return {
            "prediction": "중립",
            "confidence": 0.33,
            "probabilities": {
                "부정": 0.33,
                "중립": 0.34,
                "긍정": 0.33
            }
        }

    # 입력 텍스트 전처리
    input_text = f"[전체] {str(text)}"
    
    # 토크나이징
    device = next(model.parameters()).device
    inputs = tokenizer(
        input_text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True
    ).to(device)

    # 예측
    with torch.no_grad():
        outputs = model(**inputs)
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

def test_huggingface_model():
    """허깅페이스 모델 테스트"""
    print("🚀 허깅페이스 모델 테스트 시작!")
    
    # 모델 로드
    model, tokenizer = load_huggingface_model()
    if not model:
        return
    
    # 테스트 텍스트들
    test_texts = [
        "배송이 빠르고 품질도 좋아요",
        "사이즈가 너무 커서 아쉬워요", 
        "색상이 예쁘고 디자인도 마음에 들어요",
        "가격 대비 품질이 그저 그래요",
        "착용감이 편하고 스타일도 좋아요",
        "정말 만족스러운 구매였어요",
        "기대했던 것보다 별로예요"
    ]
    
    print(f"\n📊 {len(test_texts)}개 텍스트에 대한 감정 분석 결과:")
    print("=" * 80)
    
    for i, text in enumerate(test_texts, 1):
        result = predict_sentiment(text, model, tokenizer)
        
        print(f"\n{i}. 텍스트: {text}")
        print(f"   예측: {result['prediction']} (신뢰도: {result['confidence']:.3f})")
        print(f"   확률: 부정 {result['probabilities']['부정']:.3f}, "
              f"중립 {result['probabilities']['중립']:.3f}, "
              f"긍정 {result['probabilities']['긍정']:.3f}")
        
        # 시각적 바 차트
        max_prob = max(result['probabilities'].values())
        for label, prob in result['probabilities'].items():
            bar = "█" * int(prob * 20)
            print(f"   {label}: {prob:.3f} {bar}")

def interactive_test():
    """대화형 테스트"""
    print("🚀 허깅페이스 모델 대화형 테스트!")
    print("종료하려면 'quit' 또는 'exit'를 입력하세요.")
    print("=" * 50)
    
    # 모델 로드
    model, tokenizer = load_huggingface_model()
    if not model:
        return
    
    while True:
        try:
            text = input("\n📝 분석할 텍스트를 입력하세요: ").strip()
            
            if text.lower() in ['quit', 'exit', '종료']:
                print("👋 프로그램을 종료합니다.")
                break
                
            if not text:
                print("❌ 텍스트를 입력해주세요.")
                continue
            
            result = predict_sentiment(text, model, tokenizer)
            
            print(f"\n🎯 결과:")
            print(f"   예측: {result['prediction']} (신뢰도: {result['confidence']:.3f})")
            print(f"   확률 분포:")
            for label, prob in result['probabilities'].items():
                bar = "█" * int(prob * 20)
                print(f"     {label}: {prob:.3f} {bar}")
                
        except KeyboardInterrupt:
            print("\n👋 프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"❌ 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_test()
    else:
        test_huggingface_model()
