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
    "진우스님": "🧘",
    "꽃스님": "🌸",
    "혜민스님": "☯️",
    "법정스님": "📿",
    "성륜스님": "🕉️"
}

# Set up Streamlit page
st.set_page_config(page_title="불교 스님 AI", page_icon="🧘", layout="wide")

# Add Tailwind CSS
tailwind_css = """
<link href="https://unpkg.com/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
<style>
    .stApp {
        width: 100%;
        padding: 1rem;
        box-sizing: border-box;
        background-color: #f5f5f5;
    }
    .main-container {
        width: 100%;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        min-height: 60vh;
    }
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
    .stTextInput {
        position: fixed;
        bottom: 50%;
        left: 50%;
        transform: translate(-50%, 50%);
        width: calc(100% - 40px);
        max-width: 800px;
        padding: 15px;
        background-color: white;
        border-radius: 30px;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    }
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
    @media (max-width: 768px) {
        .main-container {
            padding: 10px;
        }
        .stChatMessage {
            max-width: 90%;
        }
    }
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
</style>
"""
st.markdown(tailwind_css, unsafe_allow_html=True)

# Sidebar for monk selection
selected_monk = st.sidebar.radio("대화할 스님을 선택하세요", list(monks.keys()))

# Main title
st.title(f"{selected_monk}와의 대화")

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
for message in st.session_state.messages[selected_monk]:
    with st.chat_message(message["role"], avatar=monks[selected_monk] if message["role"] == "assistant" else "👤"):
        st.markdown(message["content"])

# Handle user input
if prompt := st.chat_input(f"{selected_monk}에게 질문하세요"):
    st.session_state.messages[selected_monk].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

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

# Button to reset the chat
if st.sidebar.button("대화 초기화"):
    st.session_state.messages[selected_monk] = []
    st.session_state.thread_id[selected_monk] = create_thread()
    st.experimental_rerun()
