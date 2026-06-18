import streamlit as st
import lib.fun_lib as fl
import lib.emotion as em

st.set_page_config(
    page_title="마음 봄",
    page_icon="🌱",
    layout="centered"
)

## GPT API 호출 session 만들기
if "init_report_done" not in st.session_state:
    st.session_state.init_report_done = False

## GTP API에 의해 만들어진 데이터
if "report" not in st.session_state:
    st.session_state.report = None

# 구글 시트에서 데이터 가져와서 캐시에 넣고 60초 동안 지속
# 새로운 마음 기록후에는 cache clear시킴
@st.cache_data(ttl=60)
def load_emotion_log_cached():
    return fl.load_emotion_log()

st.title("🌱 마음 봄")
st.caption("오늘의 마음을 기록하고, 천천히 돌보는 감정 케어")

tab1, tab2 = st.tabs(["💭 마음의 고백","🌈 감정 보듬기"])
with tab1:
    with st.container(border=True):
        st.subheader("오늘, 당신의 마음은 어떤가요?")
        st.write("매일 나의 마음을 기록해 보세요.")
        st.markdown(fl.step_css, unsafe_allow_html=True)
        cols = st.columns([0.1,10,0.4])
        with cols[1]:
            mind_text = st.text_area(
                "![sprout](app/static/sprout.svg) 당신의 감정을 알고 싶어요.",
                placeholder="나의 감정은?"
            )    

        cols = st.columns([1,8,1])
        with cols[1]:
            write_mind = st.button("마음 기록하기", key="mind_btn", use_container_width=True)
        if mind_text.strip() == "":
            st.warning("마음을 한 문장으로 적어주세요.")
        elif write_mind and mind_text!="":
            success = fl.save_emotion_log(mind_text,em.predict_emotion(mind_text, top_k=1))
            # 기록 저장 후 캐시 삭제 - 다시 가져오기
            if success:
                st.cache_data.clear() # google sheet에서 데이터를 다시 받아 올 수 있도록 cache 삭제
                st.session_state.init_report_done = False # 데이터 입력 후 gpt다시 불러오기
        # 전체 목록 가져오기
        df = load_emotion_log_cached()
        st.markdown(fl.mind_text_list(df),unsafe_allow_html=True)

with tab2:
    with st.container(border=True):
        st.subheader("나의 감정 보듬기")
        st.caption("차곡차곡 모인 지난 감정을 보살피며 점진적인 성장을 확인하세요.")
        st.markdown(fl.step_css, unsafe_allow_html=True)

        st.write("![sprout](app/static/tree.svg) 마음 기후 분포 (최대 30일)")
        # df = load_emotion_log_cached()
        # st.write(df)
        if not df.empty:
            # st.write(df)
            summary = {}
            caution_cnt = 0
            positive_cnt = 0
            percent = 0
            cnt = 0
            str_html = ""
            total_cnt = int(df.shape[0])
            summary["total_count"] = total_cnt
            
            recent_text = df.sort_values(by="regist_dt",ascending=False)["text"].head(1).iloc[0]
            df_emotion = df.groupby("emotion1")["emotion2"].count()
            max_emotion = df_emotion.idxmax()
            for key,item in fl.emotion.items():
                if total_cnt == 0:
                    cnt,percent = 0
                    summary["top_emotion"] = ""
                    summary["top_ratio"] = 0
                    summary["positive_ratio"] = 0
                    summary["caution_ratio"] = 0
                    summary["total_count"] = 0
                else:         
                    if df_emotion.index.str.contains(key).sum() > 0:
                        cnt = df_emotion[key]
                        percent = int((cnt / total_cnt)*100)
                        # 가장 많이 적립된 감정이 여러개 일 수도 있지만 그중 하나만
                        if max_emotion == key:
                            summary["top_emotion"] = max_emotion
                            summary["top_ratio"] = percent
                        if key == "기쁨":
                            positive_cnt += cnt
                        else:
                            caution_cnt += cnt                                                        
                    else:
                        cnt,percent = 0,0                 

                summary["positive_ratio"] = (positive_cnt / total_cnt)*100
                summary["caution_ratio"] = (caution_cnt / total_cnt)*100    
                str_html += f"""<div class="emotion-item">
    <div class="emotion-row">
    <span class="emotion-label">
    <span class="emotion-icon">{item}</span>
    {key}
    </span>
    <span id="pct" class="emotion-percent">{percent}%</span>
    </div>
    <div class="emotion-track">
    <div id="bar" class="emotion-bar" style="width:{percent}%"></div>
    </div>
    </div>"""
            st.markdown(str_html,unsafe_allow_html=True)
            #################

            #### init_report_done = False 인 경우, gpt api호출
            if not st.session_state.init_report_done:
                data = fl.generate_emotion_report_with_gpt(summary,recent_text,30)
                st.session_state.report = data
                st.session_state.init_report_done = True 
            
            #### st.session_state.report 에 데이터가 있는 경우 출력
            if st.session_state.report:
                st.markdown(fl.letter_box(st.session_state.report),unsafe_allow_html=True)