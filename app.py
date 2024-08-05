import streamlit as st
from anthropic import Anthropic
import logging
import time

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit secrets에서 설정한 시크릿 값을 사용
api_key = st.secrets["anthropic"]["api_key"]

# Anthropic 클라이언트 초기화
client = Anthropic(api_key=api_key)

# 스님 목록과 아이콘 (변경 없음)
monks = {
    "스님AI": "🧘",
    "불교 경전 선생님": "📚",
    "선명상 전문가": "🧘‍♂️",
    "MZ스님": "🙏"
}

# 사용자 아이콘 설정 (변경 없음)
user_icon = "🧑🏻‍💻"

# Streamlit 페이지 설정 (변경 없음)
st.set_page_config(page_title="불교 스님 AI", page_icon="🧘", layout="wide")


# 커스텀 CSS 추가
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Myeongjo&display=swap');

    body {
        font-family: 'Nanum Myeongjo', serif;
        background-color: #f5f0e8;
        color: #333;
    }

    .main-container {
        max-width: 800px;
        margin: auto;
        padding: 20px;
        background-color: #fff9e6;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .stRadio > label {
        font-size: 1.1rem;
        padding: 8px 15px;
        border-radius: 20px;
        background-color: #f0e6d2;
        transition: all 0.3s;
    }

    .stRadio > label:hover {
        background-color: #e6d8b5;
    }

    .element-container .stChatMessage {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin-bottom: 0 !important;
    }

    .stTextInput > div > div > input {
        font-size: 1rem;
        padding: 10px 15px;
        border-radius: 20px;
        border: 1px solid #d1c3a6;
    }

    .stButton > button {
        font-size: 1rem;
        padding: 8px 16px;
        border-radius: 20px;
        background-color: #FEC78B;
        color: white;
        transition: all 0.3s;
    }

    .stButton > button:hover {
        background-color: #6d563d;
        transform: translateY(-2px);
    }

    .stApp {
        max-width: 900px;
        margin: 0 auto;
        padding: 20px;
    }

    .stMarkdown {
        font-size: 16px;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# 상단 메뉴바에 스님 선택 옵션을 라디오 버튼으로 추가 (변경 없음)
selected_monk = st.radio("대화할 스님을 선택하세요", list(monks.keys()), horizontal=True)

# 제목과 초기화 버튼을 하나의 컨테이너에 배치 (변경 없음)
col1, col2 = st.columns([3, 1])
with col1:
    st.title(f"{monks[selected_monk]} {selected_monk}와의 대화")
with col2:
    if st.button("대화 초기화", key="reset_button"):
        st.session_state.messages[selected_monk] = []
        st.rerun()

# 세션 상태 초기화 (thread_id 제거)
if "messages" not in st.session_state:
    st.session_state.messages = {monk: [] for monk in monks}

# 기본 안내 메시지 추가 (변경 없음)
if not st.session_state.messages[selected_monk]:
    st.info(f"안녕하세요! {selected_monk}와의 대화를 시작합니다. 어떤 질문이 있으신가요?")

# 채팅 메시지 표시 (변경 없음)
for message in st.session_state.messages[selected_monk]:
    avatar = monks[selected_monk] if message["role"] == "assistant" else user_icon
    with st.chat_message(message["role"], avatar=avatar):
        bg_color = '#e6f3ff' if message["role"] == "user" else '#f9f9f9'
        border_color = '#b8d3ff' if message["role"] == "user" else '#e0e0e0'
        st.markdown(f"<div style='background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 10px; padding: 15px; margin-bottom: 20px;'>{message['content']}</div>", unsafe_allow_html=True)

# 사용자 입력 처리
prompt = st.chat_input(f"{selected_monk}에게 질문하세요")
if prompt:
    st.session_state.messages[selected_monk].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=user_icon):
        st.markdown(f"<div style='background-color: #e6f3ff; border: 1px solid #b8d3ff; border-radius: 10px; padding: 15px; margin-bottom: 20px;'>{prompt}</div>", unsafe_allow_html=True)

    try:
        # Claude에 메시지 전송 및 응답 받기
        with st.chat_message("assistant", avatar=monks[selected_monk]):
            message_placeholder = st.empty()
            message_placeholder.markdown("답변을 생성 중...")
            
            full_response = ""
            
            # 이전 대화 내용을 포함하여 메시지 생성
            messages = [{"role": "system", f"content": f"당신은 {selected_monk}입니다. 불교의 가르침에 따라 답변해주세요."}]
            for msg in st.session_state.messages[selected_monk]:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            # Claude API 호출
            with client.messages.stream(
                model="claude-3.5-sonnet-20240229",
                max_tokens=1000,
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    message_placeholder.markdown(f"<div style='background-color: #f9f9f9; border: 1px solid #e0e0e0; border-radius: 10px; padding: 15px; margin-bottom: 20px;'>{full_response}▌</div>", unsafe_allow_html=True)
                    time.sleep(0.02)
                
            message_placeholder.markdown(f"<div style='background-color: #f9f9f9; border: 1px solid #e0e0e0; border-radius: 10px; padding: 15px; margin-bottom: 20px;'>{full_response}</div>", unsafe_allow_html=True)

        st.session_state.messages[selected_monk].append({"role": "assistant", "content": full_response})

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        st.error(f"오류가 발생했습니다: {str(e)}")

# 스크롤을 최신 메시지로 이동 (변경 없음)
st.markdown('<script>window.scrollTo(0, document.body.scrollHeight);</script>', unsafe_allow_html=True)