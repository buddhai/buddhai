import streamlit as st
from openai import OpenAI
import logging
import time
import re

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit secrets에서 설정한 시크릿 값을 사용
api_key = st.secrets["openai"]["api_key"]
assistant_id = st.secrets["assistant"]["id"]
vector_store_id = st.secrets["vector_store"]["id"]

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=api_key)

# 스님 목록과 아이콘
monks = {
    "진우스님": "🧘",
    "꽃스님": "🌸",
    "혜민스님": "☯️",
    "법정스님": "📿",
    "성륜스님": "🕉️"
}

# Streamlit 페이지 설정
st.set_page_config(page_title="불교 스님 AI", page_icon="🧘", layout="wide")

# 커스텀 CSS 추가
st.markdown("""
<style>
    .stChatMessage {
        background-color: #f0f0f0;
        border-radius: 15px;
        padding: 10px;
        margin: 5px 0;
    }
    .stChatMessage.user {
        background-color: #e6f3ff;
    }
    .stChatMessage.assistant {
        background-color: #f0f7e6;
    }
    .stApp {
        background-image: linear-gradient(to bottom, #ffffff, #f0f0f0);
    }
</style>
""", unsafe_allow_html=True)

# 사이드바에 스님 선택 옵션을 라디오 버튼으로 추가
selected_monk = st.sidebar.radio("대화할 스님을 선택하세요", list(monks.keys()))

# 메인 영역 설정
st.title(f"{selected_monk}과의 대화")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = {monk: [] for monk in monks}
if "thread_id" not in st.session_state:
    st.session_state.thread_id = {monk: None for monk in monks}

# Thread 생성 함수
def create_thread():
    try:
        thread = client.beta.threads.create()
        return thread.id
    except Exception as e:
        logger.error(f"Thread creation failed: {str(e)}")
        return None

# 인용 마커 제거 함수
def remove_citation_markers(text):
    return re.sub(r'【\d+:\d+†source】', '', text)

# Thread 초기화
if st.session_state.thread_id[selected_monk] is None:
    st.session_state.thread_id[selected_monk] = create_thread()

# 채팅 메시지 표시
for message in st.session_state.messages[selected_monk]:
    with st.chat_message(message["role"], avatar=monks[selected_monk] if message["role"] == "assistant" else "👤"):
        st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input(f"{selected_monk}에게 질문하세요"):
    st.session_state.messages[selected_monk].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    try:
        # Assistant에 메시지 전송
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id[selected_monk],
            role="user",
            content=f"사용자가 {selected_monk}와 대화하고 있습니다: {prompt}"
        )

        # run 생성
        run_params = {
            "thread_id": st.session_state.thread_id[selected_monk],
            "assistant_id": assistant_id,
            "stream": True  # 스트리밍 모드 활성화
        }

        # Vector store ID가 있으면 file_search 도구 추가
        if vector_store_id:
            run_params["tools"] = [{"type": "file_search"}]

        logger.info(f"Creating run with params: {run_params}")
        run = client.beta.threads.runs.create(**run_params)

        # 응답 대기 및 표시
        with st.chat_message("assistant", avatar=monks[selected_monk]):
            message_placeholder = st.empty()
            full_response = ""
            
            for chunk in client.beta.threads.runs.stream(
                thread_id=st.session_state.thread_id[selected_monk],
                run_id=run.id
            ):
                if chunk.event == "message_delta":
                    if chunk.data.delta.content:
                        full_response += chunk.data.delta.content
                        message_placeholder.markdown(remove_citation_markers(full_response) + "▌")
                elif chunk.event == "run_completed":
                    message_placeholder.markdown(remove_citation_markers(full_response))
                    break

        st.session_state.messages[selected_monk].append({"role": "assistant", "content": full_response})

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        st.error(f"오류가 발생했습니다: {str(e)}")

# 채팅 초기화 버튼
if st.sidebar.button("대화 초기화"):
    st.session_state.messages[selected_monk] = []
    st.session_state.thread_id[selected_monk] = create_thread()
    st.experimental_rerun()