import streamlit as st
import requests
import base64
from datetime import datetime
from pathlib import Path
from audio_recorder_streamlit import audio_recorder
import time
from voice_assistant_chatbot.routes.voice_routes import AudioQuerySchema
import os
from application import process_audio_query


# Page configuration
st.set_page_config(
    page_title="🕌 Voice Assistant",
    page_icon="🕌",
    layout="centered"
)

# Simple, clean CSS
st.markdown("""
<style>
    .main {
        padding: 0 !important;
    }
    
    .block-container {
        padding: 2rem 1rem !important;
        max-width: 500px !important;
        margin: 0 auto;
    }
    
    /* Voice assistant container */
    .voice-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 30px;
        padding: 3rem 2rem;
        color: white;
        text-align: center;
        margin: 2rem 0;
    }
    
    .voice-title {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    
    .voice-subtitle {
        font-size: 1.5rem;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    .status-text {
        font-size: 1.2rem;
        margin: 2rem 0;
        opacity: 0.9;
    }
    
    /* Response styling */
    .response-container {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        margin: 2rem 0;
        color: #2c3e50;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .question-text {
        font-style: italic;
        color: #7f8c8d;
        margin-bottom: 1.5rem;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 10px;
        border-left: 4px solid #3498db;
    }
    
    .response-text {
        font-size: 1.1rem;
        line-height: 1.6;
        color: #2c3e50;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Center audio recorder */
    .stAudioRecorder {
        display: flex;
        justify-content: center;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)




def send_voice_query(audio_file_path: str) -> dict:
    """Send voice query to backend"""

    try:
        path = AudioQuerySchema(file_path=audio_file_path)
        url = "http://127.0.0.1:8000/audio_query"  # Adjust if backend is hosted elsewhere
        
        payload = {"file_path": audio_file_path}
        
        # response = process_audio_query(path)
        response = requests.post(url, json=payload, timeout=120)
        
        if response.status_code == 200:
            return response.json()
            
        else:
            return {"status": "error", "message": f"Server error: {response.status_code}"}
        
    except Exception as e:
        return {"status": "error", "message": f"Connection error: {str(e)}"}



def save_audio_file(audio_bytes, dir_path: str = "recordings") -> str | None:
    """Save audio bytes to file_path"""
    
    try:
        output_dir = Path(dir_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        os.makedirs(dir_path, exist_ok=True)
    
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"voice_query_{timestamp}.wav"
        file_path = output_dir / filename

        with open(file_path, 'wb') as f:
            f.write(audio_bytes)
        
        return str(file_path)
    
    except Exception as e:
        st.error(f"Error saving audio file: {str(e)}")
        return None
    


# ---- Initialize session state ----
def initialize_session_state():
    if "current_response" not in st.session_state:
        st.session_state.current_response = None
    if "current_audio" not in st.session_state:
        st.session_state.current_audio = None
    if "just_processed" not in st.session_state:
        st.session_state.just_processed = False
    if "new_question_clicked" not in st.session_state:   # ✅ Add this line
        st.session_state.new_question_clicked = False


def main():
    # Header
    initialize_session_state()
    st.markdown("""
    <div class="voice-container">
        <div class="voice-title">🕌</div>
        <h2 class="voice-subtitle">Islamic Voice Assistant</h2>
        <div class="status-text">🎤 Tap the microphone and ask your Islamic question</div>
    </div>
    """, unsafe_allow_html=True)

    # Audio recorder (silence cutoff = 6 sec)
    audio_bytes = audio_recorder(
        text="🎙️ Record Question",
        recording_color="#e74c3c",
        neutral_color="#3498db",
        icon_name="microphone",
        icon_size="32px",
        pause_threshold=6.0
    )

    # Process audio (only once per recording and not after "New Question")
    if audio_bytes and not st.session_state.current_response and not st.session_state.new_question_clicked:
        with st.spinner("🔄 Be Patient.. Processing your question..."):
            file_path = save_audio_file(audio_bytes)

            if file_path:
                try:
                    result = send_voice_query(file_path)
                except Exception as e:
                    st.error(f"❌ Frontend failed calling backend: {e}")
                    st.stop()
            else:
                st.error("❌ Audio save failed")
                st.stop()

            if result.get("success") is True:
                st.session_state.current_response = {
                    "query_text": result.get("query_text", ""),
                    "response": result.get("response", ""),
                    "timestamp": datetime.now().strftime("%I:%M %p")
                }

                try:
                    audio_path = result.get("voice_responses_dir")
                    with open(audio_path, "rb") as f:
                        st.session_state.current_audio = f.read()

                    st.audio(st.session_state.current_audio, format="audio/wav")

                except Exception as e:
                    st.error(f"❌ Audio file issue: {e} | Path tried: {audio_path}")

                st.success("✅ Question processed successfully!")
                st.session_state.just_processed = True
                st.rerun()

            else:
                st.error(f"❌ {result.get('message', 'Unknown error')}")

    # Reset new_question flag after rerun
    if st.session_state.get("new_question_clicked", False):
        st.session_state.new_question_clicked = False

    # Display response
    if st.session_state.current_response:
        response = st.session_state.current_response

        st.markdown(f"""
        <div class="response-container">
            <h4>👤 Your Question ({response['timestamp']}):</h4>
            <div class="question-text">"{response['query_text']}"</div>

            <h4>🤖 Islamic Assistant:</h4>
            
        </div>
        """, unsafe_allow_html=True)

        # Audio response
        if st.session_state.current_audio:
            try:
                if isinstance(st.session_state.current_audio, str):
                    audio_data = base64.b64decode(st.session_state.current_audio)
                    st.audio(audio_data, format="audio/mp3")
                else:
                    st.audio(st.session_state.current_audio, format="audio/mp3")
            except Exception as e:
                st.error(f"Could not play audio response: {e}")

        # Action buttons
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🆕 New Question"):
                st.session_state.current_response = None
                st.session_state.current_audio = None
                st.session_state.just_processed = False
                st.session_state.new_question_clicked = True
                st.rerun()

        with col2:
            if st.button("🔄 Replay Audio"):
                if st.session_state.current_audio:
                    st.rerun()
                else:
                    st.warning("No audio available")

        with col3:
            if st.button("📋 Copy Text"):
                st.code(response['response'])


if __name__ == "__main__":
    main()
