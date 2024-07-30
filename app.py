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
st.set_page_config(page_title="불교 스님 AI", page_icon="🧘", layout="centered")

# 커스텀 CSS 추가
st.markdown("""
<style>
    /* 전체 페이지 스타일 */
    .stApp {
        background-color: #f5f5f5;
        display: flex;
        justify-content: center;
        align-items: flex-start;
        padding-top: 20px;
    }

    /* 메인 컨테이너 스타일 */
    .main-container {
        width: 375px;
        margin: 0 auto;
        padding: 20px;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        display: flex;
        flex-direction: column;
        height: calc(100vh - 40px);
        max-height: 800px;
    }

    /* 채팅 메시지 스타일 */
    .stChatMessage {
        border-radius: 20px;
        padding: 12px 18px;
        margin: 8px 0;
        max-width: 80%;
        clear: both;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
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

    /* 채팅 영역 스타일 */
    .chat-area {
        flex: 1;
        overflow-y: auto;
        padding-bottom: 20px;
    }

    /* 입력 필드 스타일 */
    .stTextInput {
        position: sticky;
        bottom: 20px;
        width: 100%;
        padding: 15px;
        background-color: white;
        border-radius: 30px;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    }

    /* 스크롤바 스타일 */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }

    /* 반응형 디자인 */
    @media (max-width: 768px) {
        .main-container {
            padding: 10px;
        }
        .stChatMessage {
            max-width: 90%;
        }
    }

    /* 로딩 애니메이션 */
    @keyframes pulse {
        0% { opacity: 0.5; }
        50% { opacity: 1; }
        100% { opacity: 0.5; }
    }
    .loading-dots::after {
        content: '...';
        animation: pulse 1.5s infinite;
        display: inline-block;
    }

    /* 제목과 초기화 버튼 컨테이너 */
    .title-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
    }

    /* 초기화 버튼 스타일 */
    .reset-button {
        padding: 5px 10px;
        background-color: #f44336;
        color: white;
        border: none;
        border-radius: 5px;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

# 상단 메뉴바에 스님 선택 옵션을 라디오 버튼으로 추가
selected_monk = st.radio("대화할 스님을 선택하세요", list(monks.keys()), horizontal=True)

# 메인 영역 설정
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# 제목과 초기화 버튼을 하나의 컨테이너에 배치
st.markdown('<div class="title-container">', unsafe_allow_html=True)
st.markdown(f"<h1>{selected_monk}와의 대화</h1>", unsafe_allow_html=True)

# 대화 초기화 버튼
if st.button("대화 초기화", key="reset_button"):
    st.session_state.messages[selected_monk] = []
    st.session_state.thread_id[selected_monk] = create_thread()
    st.experimental_rerun()

st.markdown('</div>', unsafe_allow_html=True)

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

# 채팅 영역
st.markdown('<div class="chat-area">', unsafe_allow_html=True)

# 채팅 메시지 표시
for message in st.session_state.messages[selected_monk]:
    with st.chat_message(message["role"], avatar=monks[selected_monk] if message["role"] == "assistant" else "👤"):
        st.markdown(message["content"])

st.markdown('</div>', unsafe_allow_html=True)  # 채팅 영역 닫기

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
        run = client.beta.threads.runs.create(**run_params)

        # 응답 대기 및 표시
        with st.chat_message("assistant", avatar=monks[selected_monk]):
            message_placeholder = st.empty()
            
            # "답변을 생성 중" 메시지와 로딩 애니메이션 표시
            message_placeholder.markdown("""
            <div style="display: flex; align-items: center;">
                <span>답변을 생성 중</span><span class="loading-dots"></span>
            </div>
            """, unsafe_allow_html=True)
            
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

st.markdown('</div>', unsafe_allow_html=True)  # 메인 컨테이너 닫기