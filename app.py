import streamlit as st
from openai import OpenAI
import os

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

    # Assistant에 메시지 전송 및 응답 생성
    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt
    )
    run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=assistant_id,
        tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}}
    )

    # 응답 대기 및 표시
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        while run.status != "completed":
            run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )
            if run.status == "completed":
                messages = client.beta.threads.messages.list(thread_id=st.session_state.thread_id)
                full_response = messages.data[0].content[0].text.value
                message_placeholder.markdown(full_response)
                break

    st.session_state.messages.append({"role": "assistant", "content": full_response})

# 채팅 초기화 버튼
if st.button("대화 초기화"):
    st.session_state.messages = []
    st.session_state.thread_id = create_thread()
    st.experimental_rerun()