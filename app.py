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
    .stApp {
        background-color: #f5f5f5;
    }
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stChatMessage {
        padding: 12px 18px;
        margin: 8px 0;
        border-radius: 20px;
        max-width: 80%;
        clear: both;
    }
    .stChatMessage.user {
        background-color: #e6f3ff;
        float: right;
        border-bottom-right-radius: 0;
    }
    .stChatMessage.assistant {
        background-color: #f0f7e6;
        float: left;
        border-bottom-left-radius: 0;
    }
    .chat-input {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        width: calc(100% - 40px);
        max-width: 760px;
    }
    .title-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
    }
    .stButton>button {
        background-color: #f44336;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# 상단 메뉴바에 스님 선택 옵션을 라디오 버튼으로 추가
selected_monk = st.radio("대화할 스님을 선택하세요", list(monks.keys()), horizontal=True)

# 채팅 컨테이너 시작
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

# 제목과 초기화 버튼을 하나의 컨테이너에 배치
col1, col2 = st.columns([3, 1])
with col1:
    st.title(f"{selected_monk}와의 대화")
with col2:
    if st.button("대화 초기화"):
        st.session_state.messages[selected_monk] = []
        st.session_state.thread_id[selected_monk] = None
        st.experimental_rerun()

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

# 채팅 컨테이너 닫기
st.markdown('</div>', unsafe_allow_html=True)

# 사용자 입력 처리
prompt = st.chat_input(f"{selected_monk}에게 질문하세요", key="chat_input")
if prompt:
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
        run = client.beta.threads.runs.create(**run_params)

        # 응답 대기 및 표시
        with st.chat_message("assistant", avatar=monks[selected_monk]):
            message_placeholder = st.empty()
            message_placeholder.markdown("답변을 생성 중...")
            
            full_response = ""
            
            while run.status not in ["completed", "failed"]:
                run = client.beta.threads.runs.retrieve(
                    thread_id=st.session_state.thread_id[selected_monk],
                    run_id=run.id
                )
                if run.status == "completed":
                    messages = client.beta.threads.messages.list(thread_id=st.session_state.thread_id[selected_monk])
                    new_message = messages.data[0].content[0].text.value
                    new_message = remove_citation_markers(new_message)
                    
                    # Stream response
                    for char in new_message:
                        full_response += char
                        time.sleep(0.02)
                        message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
                    break
                elif run.status == "failed":
                    st.error("응답 생성에 실패했습니다. 다시 시도해 주세요.")
                    logger.error(f"Run failed: {run.last_error}")
                    break
                else:
                    time.sleep(0.5)

        st.session_state.messages[selected_monk].append({"role": "assistant", "content": full_response})

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        st.error(f"오류가 발생했습니다: {str(e)}")

# 스크롤을 최신 메시지로 이동
st.markdown('<script>window.scrollTo(0, document.body.scrollHeight);</script>', unsafe_allow_html=True)