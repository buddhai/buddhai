import streamlit as st
from openai import OpenAI
import logging
import time
import re
from typing_extensions import override
from openai import AssistantEventHandler

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit secrets에서 설정한 시크릿 값을 사용
api_key = st.secrets["openai"]["api_key"]
assistant_id = st.secrets["assistant"]["id"]
vector_store_id = st.secrets["vector_store"].get("id")  # .get() 메소드 사용

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

# (이전의 CSS 스타일 설정 유지)

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
    with st.chat_message(message["role"], avatar=monks.get(selected_monk) if message["role"] == "assistant" else "👤"):
        st.markdown(message["content"])

# EventHandler 클래스 정의
class StreamHandler(AssistantEventHandler):
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.full_response = ""

    @override
    def on_text_created(self, text) -> None:
        self.full_response = ""

    @override
    def on_text_delta(self, delta, snapshot):
        self.full_response += delta.value
        self.placeholder.markdown(self.full_response + "▌", unsafe_allow_html=True)

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
        }

        # Vector store ID가 있으면 file_search 도구 추가
        if vector_store_id:
            run_params["tools"] = [{"type": "file_search"}]

        logger.info(f"Creating run with params: {run_params}")

        with st.chat_message("assistant", avatar=monks.get(selected_monk)):
            message_placeholder = st.empty()
            stream_handler = StreamHandler(message_placeholder)

            # "답변을 생성하는 중..." 메시지와 로딩 애니메이션 표시
            message_placeholder.markdown("""
            <div style="display: flex; align-items: center;">
                <div class="loading-spinner"></div>
                답변을 생성하는 중...
            </div>
            """, unsafe_allow_html=True)

            with client.beta.threads.runs.stream(
                **run_params,
                event_handler=stream_handler,
            ) as stream:
                stream.until_done()

            # 최종 응답 표시
            full_response = remove_citation_markers(stream_handler.full_response)
            message_placeholder.markdown(full_response, unsafe_allow_html=True)

        st.session_state.messages[selected_monk].append({"role": "assistant", "content": full_response})

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        st.error(f"오류가 발생했습니다: {str(e)}")

# 채팅 초기화 버튼
if st.sidebar.button("대화 초기화"):
    st.session_state.messages[selected_monk] = []
    st.session_state.thread_id[selected_monk] = create_thread()
    st.experimental_rerun()