# ============================================================
# 학습된 LoRA 감정 분류 모델로 문장 감정 예측하기
# ============================================================
import os
import json
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel


# 기본 모델 이름
BASE_MODEL_NAME = "klue/roberta-base"
# 학습 결과 저장 폴더
MODEL_DIR = "./lora_model"

# 사용할 장치 설정
device = "cuda" if torch.cuda.is_available() else "cpu"
# ============================================================
# 1. 라벨 정보 불러오기
# ============================================================
with open(os.path.join(MODEL_DIR, "label_map.json"), "r", encoding="utf-8") as f:
    label_map = json.load(f)

# json으로 저장하면 key가 문자열이 되므로 int로 다시 변환합니다.
id2label = {int(k): v for k, v in label_map["id2label"].items()}
label2id = label_map["label2id"]
num_labels = len(id2label)
# ============================================================
# 2. 토크나이저와 모델 불러오기
# ============================================================
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
# 먼저 기본 분류 모델을 불러옵니다.
base_model = AutoModelForSequenceClassification.from_pretrained(
    BASE_MODEL_NAME,
    num_labels=num_labels,
    id2label=id2label,
    label2id=label2id
)

# 그 위에 학습된 LoRA adapter를 붙입니다.
model = PeftModel.from_pretrained(base_model, MODEL_DIR)
model.to(device)
model.eval()

# ============================================================
# 3. 감정 예측 함수
# ============================================================
def predict_emotion(text: str, top_k: int = 3):
    """
    입력 문장에 대해 감정을 예측합니다.

    top_k:
        가장 가능성이 높은 감정 몇 개를 보여줄지 결정합니다.
    """

    # 문장을 토큰화합니다.
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=128
    )

    # GPU 또는 CPU로 이동
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # 예측
    with torch.no_grad():
        outputs = model(**inputs)

    # logits을 확률로 변환
    probs = torch.softmax(outputs.logits, dim=-1)[0]

    # 확률이 높은 상위 top_k개 추출
    top_probs, top_indices = torch.topk(probs, k=top_k)

    results = []

    for prob, idx in zip(top_probs, top_indices):
        label_name = id2label[int(idx)]
        results.append(
            {
                "emotion": label_name,
                "score": float(prob)
            }
        )

    return results
# ============================================================
# 4. 테스트
# ============================================================
if __name__ == "__main__":
    # while True:
    text = input("\n감정을 분석할 문장을 입력하세요. 종료하려면 q 입력: ")
    result = predict_emotion(text, top_k=3)
    print("\n예측 결과")
    for item in result:
        print(f"- {item['emotion']} : {item['score']:.4f}")