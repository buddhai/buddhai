import streamlit as st
from openai import OpenAI
import logging
import time

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit secrets에서 설정한 시크릿 값을 사용
api_key = st.secrets["openai"]["api_key"]
assistant_id = st.secrets["assistant"]["id"]
vector_store_id = st.secrets["vector_store"]["id"]


# OpenAI 클라이언트 초기화
client = OpenAI(api_key=api_key)

# Streamlit 페이지 설정
st.set_page_config(page_title="진우스님AI", page_icon="🧘")
st.title("진우스님AI와의 대화")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

# Thread 생성 함수
def create_thread():
    thread = client.beta.threads.create()
    return thread.id

# Thread 초기화
if st.session_state.thread_id is None:
    st.session_state.thread_id = create_thread()

# 채팅 메시지 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("진우스님AI에게 질문하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        # Assistant에 메시지 전송
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt
        )

        # run 생성
        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=assistant_id,
        )

        # 응답 대기 및 표시 (streaming)
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            while run.status != "completed":
                run = client.beta.threads.runs.retrieve(
                    thread_id=st.session_state.thread_id,
                    run_id=run.id
                )
                if run.status == "completed":
                    messages = client.beta.threads.messages.list(
                        thread_id=st.session_state.thread_id
                    )
                    new_message = messages.data[0].content[0].text.value
                    
                    # Simulate streaming by showing the response word by word
                    for word in new_message.split():
                        full_response += word + " "
                        time.sleep(0.05)  # Adjust the speed as needed
                        message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
                    break
                elif run.status == "failed":
                    st.error("응답 생성에 실패했습니다. 다시 시도해 주세요.")
                    break
                else:
                    time.sleep(0.5)  # Wait before checking again

        st.session_state.messages.append({"role": "assistant", "content": full_response})

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        st.error(f"오류가 발생했습니다: {str(e)}")

# 채팅 초기화 버튼
if st.button("대화 초기화"):
    st.session_state.messages = []
    st.session_state.thread_id = create_thread()
    st.experimental_rerun()