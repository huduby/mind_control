import streamlit as st
import pandas as pd
from datetime  import datetime
from pathlib import Path
import requests
from openai import OpenAI
import json

emotion = {"기쁨":"🌞","당황":"☁️","분노":"⚡","불안":"🌫️","상처":"💨","슬픔":"🌧️"}
        
def mind_text_list(df_list):
    str_html = ""
    if df_list.empty:
        str_html = f"""<div class="recent-box">
<div class="recent-head">
<span>🕊️</span>
<strong>최근 마음 기록</strong>
</div>
<div class="recent-list">
<div class="recent-item">
<div class="recent-emoji">💬</div>
<div class="recent-body">
    <p>아직 등록을 하지 않으셨군요.</p>
</div>
"""
    else:
        str_html = f"""<div class="recent-box">
<div class="recent-head">
<span>🕊️</span>
<strong>최근 마음 기록</strong>
</div><div class="recent-list">"""
        if df_list.shape[0] > 5:
            rows = 5
        else:
            rows = df_list.shape[0]
        df_list = df_list.sort_values(by="regist_dt",ascending=False).head(rows)
        for i in range(rows):
            regist_dt = df_list.iloc[i,0]
            text = df_list.iloc[i,1]
            em = df_list.iloc[i,2]
            str_html += f"""<div class="recent-item">
<div class="recent-emoji">{emotion[em]}</div>
<div class="recent-body">
<div class="recent-top">
<span class="recent-date">{regist_dt[:10]}</span>
<span class="recent-emotion">{em}</span>
</div>
<p>{text}</p>
</div>
</div>"""
    str_html += """</div>
</div>"""
    return str_html

def letter_box(str_json):
    data = json.loads(str_json)
    
    title = data["title"]
    message = data["message"]
    suggestion = data["suggestion"]

    str_html = f"""<div class="empathy-card">
<div class="mind-name">
<span class="mind-icon">🌿</span>
<span class="mind-label">오늘 마음의 이름</span>
</div>

<h3 class="mind-title">{title}</h3>

<p class="mind-message">
{message}
</p>

<p class="mind-suggestion">
{suggestion}
</p>
</div>"""
    return str_html

# openAI api에서 감정 리포트 가져오기
def generate_emotion_report_with_gpt(summary, recent_texts,N=7):
    print("GPT API 실행")
    client = OpenAI(api_key=st.secrets["openai"]["api_key"])

    prompt = f"""
최근 {N}일 감정 기록 요약입니다.

총 기록 수: {summary["total_count"]}개,
가장 많이 나타난 감정: {summary["top_emotion"]},
대표 감정 비율: {summary["top_ratio"]:.1f}%,
기쁨 비율: {summary["positive_ratio"]:.1f}%,
주의 감정 비율: {summary["caution_ratio"]:.1f}%,

최근 작성 문장 일부:
{recent_texts}

아래 조건에 맞춰 한국어로 감정 리포트를 작성해 주세요.

작성 규칙:
- 한국어로 작성
- 청소년 감정 기록 앱에 들어갈 문장처럼 따뜻하고 다정하게 작성
- 의학적 진단, 치료, 우울증 판정처럼 말하지 않기
- "너는 ~ 상태야"처럼 단정하지 않기
- "보여요", "느껴질 수 있어요", "함께 있었던 것 같아요" 같은 부드러운 표현 사용
- 숫자, 퍼센트, 기록 개수는 절대 문장에 직접 쓰지 않기
- "비율", "통계", "전체", "대표 감정" 같은 분석 보고서 표현 쓰지 않기
- 감정을 좋고 나쁨으로 판단하지 않기
- 최근 감정 흐름을 날씨, 계절, 마음의 온도 같은 부드러운 이미지로 표현해도 좋음
- 전체 문장은 짧고 편안하게 작성
- 결과는 반드시 JSON 형식으로 출력

출력 형식:
{{
  "title": "짧은 제목",
  "message": "최근 감정 흐름에 대한 따뜻한 해석. 2문장 이내.",
  "suggestion": "오늘 바로 해볼 수 있는 작은 실천 제안. 1문장."
}}
"""
    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )
    return response.output_text

# 구글 sheet 데이터 읽어오기
def load_emotion_log():
    url = st.secrets["google_sheet"]["app_script_url"]
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"데이터 불러오기 실패: {response.status_code}")
            # print(response.text)
            return pd.DataFrame()
        result = response.json()
        if len(result) == 0:
            print("Apps Script에서 오류가 발생했습니다.")
            return pd.DataFrame()
        else:            
            data = result.get("data", [])
            # print(data)
            if len(data) == 0:
                return pd.DataFrame()
            df = pd.DataFrame(data)
            return df

    except Exception as e:
        st.error("구글 시트 데이터를 불러오는 중 오류가 발생했습니다.")
        st.exception(e)
        return ""
    
# 구글 sheet로 데이터 저장
def save_emotion_log(txt, lora_data, weather=""):
    url = st.secrets["google_sheet"]["app_script_url"]

    # lora_data 형태 정리
    if isinstance(lora_data, str):
        emotion_text = lora_data
    elif isinstance(lora_data, list):
        emotion_text = lora_data[0]["emotion"]
    elif isinstance(lora_data, dict):
        emotion_text = lora_data["emotion"]
    else:
        st.error("lora_data 형식이 올바르지 않습니다.")
        return False

    # 감정 분리
    emotions = emotion_text.split("_")
    emotion1 = emotions[0] if len(emotions) > 0 else ""
    emotion2 = emotions[1] if len(emotions) > 1 else ""
    
    data = {
        "regist_dt": datetime.now().strftime("%Y-%m-%d"),
        "text": txt,
        "emotion1": emotion1,
        "emotion2": emotion2
    }

    try:
        response = requests.post(url, json=data, timeout=10)
        # st.write(response.text)
        if response.status_code == 200:
            return True
        else:
            st.error(f"저장 실패: {response.status_code}")
            st.write(response.text)
            return False

    except Exception as e:
        st.error("구글 시트 저장 중 오류가 발생했습니다.")
        st.exception(e)
        return False

# -----------------------------
# 기본 css 설정
# -----------------------------
step_css = """
<style>
.block-container {
max-width: 720px;
}
.stButton > button {
width: 100%;
height: 70px;
border-radius: 5px;
border: 1px solid #eeeeee;
background-color: #ffffff;
color: #666666;
font-size: 14px;
line-height: 1.5;
transition: all 0.2s ease;
}

.stButton > button:hover {
border-color: #6ee7b7;
background-color: #ecfdf5;
color: #047857;
}

.st-key-write_btn button,
.st-key-release_btn button,
.st-key-comfort_btn button,
.st-key-garden_btn button {
height: 46px;
border: 1px solid #e7e5e4;
background-color: #ffffff;
color: #78716c;
font-size: 14px;
font-weight: 600;
}
.st-key-write_btn button:hover,
.st-key-release_btn button:hover,
.st-key-comfort_btn button:hover,
.st-key-garden_btn button:hover {
border-color: #10b981;
background-color: #ecfdf5;
color: #047857;
}
.st-key-mind_btn button {
width:500px;
height: 50px;
border-radius: 10px;
border: 1px solid white;
background-color: orange;
color: white;
font-size: 14px;
font-weight: bold;
paddiing-left:200px;
}
.st-key-mind_btn button:hover {
border:white;
background-color: #FFF4E6;
color: #FF9E00;
}
div.stButton > button {
display: flex;
align-items: center;
gap: 10px;
padding: 14px 20px;
font-size: 18px;
border-radius: 14px;
}

div.stButton > button img {
width: 20px !important;
height: 20px !important;
max-height: 20px !important;
}

.emotion-list {
display: flex;
flex-direction: column;
gap: 10px;
width: 80%;
margin:10px;
}

.emotion-item {
width: 80%;
margin-left:40px;
}

.emotion-row {
display: flex;
justify-content: space-between;
align-items: center;
margin-bottom: 4px;
font-size: 15px;
font-weight: 600;
color: #57534e;
}

.emotion-label {
display: flex;
align-items: center;
gap: 5px;
}

.emotion-icon {
font-size: 15px;
}

.emotion-percent {
font-size: 15px;
color: #57534e;
}

.emotion-track {
width: 100%;
height: 8px;
background-color: #f5f5f4;
border-radius: 999px;
overflow: hidden;
margin-bottom:10px
}

.emotion-bar {
height: 100%;
border-radius: 999px;
transition: width 1s ease;
background-color: #fbbf24;
}

.empathy-card {
width: calc(100% - 50px);
margin: 18px auto 18px;
box-sizing: border-box;

background: #fffdf9;
border: 1px solid #eadcc8;
border-radius: 18px;
padding: 22px 24px;
box-shadow: 0 6px 18px rgba(120, 90, 60, 0.08);
}

.mind-name {
display: flex;
align-items: center;
gap: 7px;
margin-bottom: 8px;
}

.mind-icon {
font-size: 17px;
}

.mind-label {
font-size: 12px;
font-weight: 600;
color: #8a6a43;
}

.mind-title {
margin: 0 0 16px;
font-size: 14px;
font-weight: 800;
color: #2f6b3f;
}

.mind-message {
margin: 0 0 18px;
font-size: 14px;
line-height: 1.8;
color: #57534e;
}

.mind-suggestion {
margin: 0;
padding-top: 14px;
border-top: 1px dashed #e8d8c2;

font-size: 14px;
line-height: 1.8;
font-weight: 700;
color: #44403c;
}

.recent-box {
width: calc(100% - 36px);
padding: 18px 20px;
background: #fffdf9;
border: 1px solid #eee2d2;
border-radius: 18px;
box-shadow: 0 5px 16px rgba(120, 90, 60, 0.07);
box-sizing: border-box;

height: auto;
overflow: visible;
margin:20px;
}

.recent-head {
display: flex;
align-items: center;
gap: 7px;
margin-bottom: 14px;
color: #5f4b32;
font-size: 14px;
}

.recent-head strong {
font-weight: 800;
}

.recent-list {
display: flex;
flex-direction: column;
gap: 10px;
}

.recent-item {
display: flex;
gap: 12px;
align-items: flex-start;
padding: 12px 14px;
background: #fafaf9;
border: 1px solid #f0eeee;
border-radius: 14px;
}

.recent-emoji {
width: 34px;
height: 34px;
border-radius: 50%;
background: #fff7e6;
display: flex;
align-items: center;
justify-content: center;
font-size: 17px;
flex-shrink: 0;
}

.recent-body {
flex: 1;
min-width: 0;
}

.recent-top {
display: flex;
justify-content: space-between;
align-items: center;
margin-bottom: 6px;
}

.recent-date {
font-size: 12px;
color: #a8a29e;
font-weight: 600;
}

.recent-emotion {
font-size: 12px;
color: #8a6a43;
font-weight: 700;
}

.recent-body p {
margin: 0;
font-size: 14px;
line-height: 1.6;
color: #44403c;
white-space: nowrap;
overflow: hidden;
text-overflow: ellipsis;
}
</style>       
"""