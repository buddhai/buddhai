import streamlit as st
from openai import OpenAI
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit secrets에서 설정한 시크릿 값을 사용
api_key = st.secrets["openai"]["api_key"]
assistant_id = st.secrets["assistant"]["id"]
vector_store_id = st.secrets.get("vector_store", {}).get("id")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=api_key)

# ... (이전 코드 유지) ...

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
        run_params = {
            "thread_id": st.session_state.thread_id,
            "assistant_id": assistant_id,
        }
        if vector_store_id:
            run_params["tool_resources"] = {"file_search": {"vector_store_ids": [vector_store_id]}}

        logger.info(f"Creating run with params: {run_params}")
        run = client.beta.threads.runs.create(**run_params)

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

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        st.error(f"An error occurred: {str(e)}")

# ... (나머지 코드 유지) ...