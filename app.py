import streamlit as st
from openai import OpenAI
import logging
import time
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get secrets from Streamlit's secrets management
api_key = st.secrets["openai"]["api_key"]
assistant_id = st.secrets["assistant"]["id"]
vector_store_id = st.secrets["vector_store"]["id"]

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# List of monks and their icons
monks = {
    "스님AI": "🧘",
    "금강경 선생님": "🌸",
    "선명상 전문가": "☯️",
    "MZ스님": "📿",
}

# Set up Streamlit page
st.set_page_config(page_title="불교 스님 AI", page_icon="🧘", layout="wide")

# Add custom CSS for KakaoTalk-like design
kakao_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    
    body {
        font-family: 'Noto Sans KR', sans-serif;
        background-color: #9bbbd4;
        color: #000000;
    }
    .stApp {
        max-width: 100%;
        padding: 0;
    }
    .main-container {
        max-width: 100%;
        padding: 0;
        background-color: #9bbbd4;
    }
    .chat-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background-color: #a1c0d5;
        color: #000000;
        padding: 10px 20px;
        font-weight: bold;
        font-size: 18px;
        z-index: 1000;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
    }
    .chat-container {
        display: flex;
        flex-direction: column;
        padding: 70px 10px 70px 10px;
        overflow-y: auto;
        height: calc(100vh - 140px);
    }
    .stChatMessage {
        background-color: transparent !important;
        border-radius: 0 !important;
        padding: 10px 0 !important;
        margin: 5px 0 !important;
        max-width: 100% !important;
        width: auto !important;
        box-shadow: none !important;
    }
    .stChatMessage.user {
        text-align: right;
    }
    .stChatMessage.assistant {
        text-align: left;
    }
    .message-bubble {
        display: inline-block;
        max-width: 70%;
        padding: 8px 12px;
        border-radius: 15px;
        font-size: 14px;
        line-height: 1.4;
    }
    .user .message-bubble {
        background-color: #fef01b;
        border-top-right-radius: 0;
    }
    .assistant .message-bubble {
        background-color: #ffffff;
        border-top-left-radius: 0;
    }
    .stTextInput {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 10px;
        background-color: #eaeaea;
    }
    .stTextInput > div {
        background-color: #ffffff;
        border-radius: 20px;
        padding: 5px 15px;
    }
    .stTextInput input {
        background-color: transparent;
        border: none;
        padding: 10px 0;
    }
    button {
        border-radius: 50%;
        width: 40px;
        height: 40px;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #fef01b;
        color: #000000;
        border: none;
        font-size: 20px;
    }
    .loading-dots::after {
        content: '...';
        animation: pulse 1.5s infinite;
        display: inline-block;
    }
    @keyframes pulse {
        0% { opacity: 0.5; }
        50% { opacity: 1; }
        100% { opacity: 0.5; }
    }
</style>
"""
st.markdown(kakao_css, unsafe_allow_html=True)

# Sidebar for monk selection (hidden on mobile)
selected_monk = st.sidebar.radio("대화할 스님을 선택하세요", list(monks.keys()))

# Chat header
st.markdown(f'<div class="chat-header">{selected_monk}와의 대화</div>', unsafe_allow_html=True)

# Initialize session state for messages and thread IDs
if "messages" not in st.session_state:
    st.session_state.messages = {monk: [] for monk in monks}
if "thread_id" not in st.session_state:
    st.session_state.thread_id = {monk: None for monk in monks}

# Function to create a new thread
def create_thread():
    try:
        thread = client.beta.threads.create()
        return thread.id
    except Exception as e:
        logger.error(f"Thread creation failed: {str(e)}")
        return None

# Function to remove citation markers from the text
def remove_citation_markers(text):
    return re.sub(r'【\d+:\d+†source】', '', text)

# Initialize thread if not already initialized
if st.session_state.thread_id[selected_monk] is None:
    st.session_state.thread_id[selected_monk] = create_thread()

# Display chat messages
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
for message in st.session_state.messages[selected_monk]:
    with st.chat_message(message["role"], avatar=monks[selected_monk] if message["role"] == "assistant" else None):
        st.markdown(f'<div class="message-bubble">{message["content"]}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Handle user input
if prompt := st.chat_input(f"{selected_monk}에게 질문하세요"):
    st.session_state.messages[selected_monk].append({"role": "user", "content": prompt})
    
    try:
        # Send message to assistant
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id[selected_monk],
            role="user",
            content=f"사용자가 {selected_monk}와 대화하고 있습니다: {prompt}"
        )

        # Create a run
        run_params = {
            "thread_id": st.session_state.thread_id[selected_monk],
            "assistant_id": assistant_id,
        }

        # Add file_search tool if vector_store_id is available
        if vector_store_id:
            run_params["tools"] = [{"type": "file_search"}]

        logger.info(f"Creating run with params: {run_params}")
        run = client.beta.threads.runs.create(**run_params)

        # Wait for the response and display
        with st.chat_message("assistant", avatar=monks[selected_monk]):
            message_placeholder = st.empty()

            # Display "Generating response" message with loading animation
            message_placeholder.markdown("""
            <div class="message-bubble" style="display: flex; align-items: center;">
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
                        message_placeholder.markdown(f'<div class="message-bubble">{full_response}▌</div>', unsafe_allow_html=True)

                    message_placeholder.markdown(f'<div class="message-bubble">{full_response}</div>', unsafe_allow_html=True)
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

# Button to reset the chat (hidden on mobile)
if st.sidebar.button("대화 초기화"):
    st.session_state.messages[selected_monk] = []
    st.session_state.thread_id[selected_monk] = create_thread()
    st.rerun()  # Use st.rerun() instead of st.experimental_rerun()