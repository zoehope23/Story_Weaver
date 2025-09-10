import streamlit as st
import requests
import json
import base64
import wave
import io
import time

# Use Streamlit's session state to manage variables
if 'story' not in st.session_state:
    st.session_state.story = ""
if 'is_listening' not in st.session_state:
    st.session_state.is_listening = False
if 'voice_input' not in st.session_state:
    st.session_state.voice_input = ""

# Placeholders for the API key and app ID, which are automatically provided
__app_id = 'default-app-id'
__firebase_config = '{}'
__initial_auth_token = None
api_key = "" # Leave this as-is, it will be automatically filled by the environment

# --- CSS for a cozy, bedtime story theme ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Lobster&family=Patrick+Hand&display=swap');
    
    body {
        background-color: #F0F8FF; /* AliceBlue */
    }
    .main-header {
        text-align: center;
        font-family: 'Lobster', cursive;
        color: #4682B4; /* SteelBlue */
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    .main-subheader {
        text-align: center;
        color: #708090; /* SlateGray */
        font-family: 'Patrick Hand', cursive;
    }
    .stButton>button {
        font-family: 'Patrick Hand', cursive;
        font-size: 18px;
        padding: 12px 30px;
        border-radius: 25px;
        border: 2px solid #B0C4DE; /* LightSteelBlue */
        background-color: #ADD8E6; /* LightBlue */
        color: #4682B4;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stButton>button:hover {
        background-color: #B0C4DE;
        color: #4682B4;
        transform: translateY(-2px);
    }
    .stTextInput, .stTextArea, .stSelectbox {
        border-radius: 15px;
        border: 1px solid #B0C4DE;
        background-color: #F8F8FF;
    }
    .story-container {
        padding: 25px;
        border-radius: 20px;
        background-color: #E6E6FA; /* Lavender */
        border: 2px solid #B0C4DE;
        margin-top: 30px;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .story-text {
        font-family: 'Patrick Hand', cursive;
        font-size: 22px;
        line-height: 1.8;
        color: #333;
    }
    .spinner {
        text-align: center;
    }
    .speaker-button-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 20px;
    }
    .speaker-icon {
        cursor: pointer;
        transition: transform 0.2s;
        margin-right: 10px;
    }
    .speaker-icon:hover {
        transform: scale(1.1);
    }
    .moon-icon {
        display: block;
        margin: auto;
        animation: moon-float 5s ease-in-out infinite;
    }
    @keyframes moon-float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
        100% { transform: translateY(0px); }
    }
</style>
""", unsafe_allow_html=True)

# --- Python function to create a WAV file from PCM data ---
def pcm_to_wav(pcm_data, sample_rate=16000, channels=1, bits_per_sample=16):
    """Converts PCM audio data to a WAV file in memory."""
    wav_file = io.BytesIO()
    with wave.open(wav_file, 'wb') as wav_writer:
        wav_writer.setnchannels(channels)
        wav_writer.setsampwidth(bits_per_sample // 8)
        wav_writer.setframerate(sample_rate)
        wav_writer.writeframes(pcm_data)
    wav_file.seek(0)
    return wav_file

# --- Function to generate the story using the Gemini API ---
def generate_story(genre, characters, age_group, tips):
    """Generates a story based on user input using the Gemini LLM."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"
    
    # Construct a comprehensive prompt for the model
    prompt = f"""
    You are a professional story writer specializing in short, age-appropriate bedtime stories for children. Your task is to craft a creative and gentle story.
    The story should be suitable for the specified age group and incorporate the provided characters and genre.

    **Genre:** {genre}
    **Characters:** {characters}
    **Age Group:** {age_group}
    **Additional Tips/Requests:** {tips}

    Please write a calming and clear story, perfect for reading aloud before bed.
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        story_content = data['candidates'][0]['content']['parts'][0]['text']
        st.session_state.story = story_content
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred while generating the story: {e}")
        st.session_state.story = ""
    except (KeyError, IndexError) as e:
        st.error(f"Could not parse the API response. Please try again. Error: {e}")
        st.session_state.story = ""

# --- Function to convert story text to speech using the Gemini TTS API ---
def text_to_speech(text):
    """Converts text to audio and plays it."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    # Choosing a gentle, easy-going voice for a bedtime story
                    "prebuiltVoiceConfig": {"voiceName": "Zubenelgenubi"}
                }
            }
        },
        "model": "gemini-2.5-flash-preview-tts"
    }

    try:
        st.info("Generating audio, please wait...")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        audio_data_base64 = data['candidates'][0]['content']['parts'][0]['inlineData']['data']
        audio_data = base64.b64decode(audio_data_base64)
        
        # Convert raw PCM data to WAV format
        wav_bytes = pcm_to_wav(audio_data).getvalue()
        
        st.audio(wav_bytes, format='audio/wav')
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred during text-to-speech conversion: {e}")
    except (KeyError, IndexError) as e:
        st.error(f"Could not parse the TTS API response. Error: {e}")

# --- Front-end UI with Streamlit ---
st.markdown("""
<svg class="moon-icon" width="60" height="60" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2z" fill="#FFC107" stroke="#FFD700" stroke-width="1"/>
    <path d="M16 11c0-2.209-1.791-4-4-4s-4 1.791-4 4 1.791 4 4 4 4-1.791 4-4z" fill="#FFFACD" stroke="#FFD700" stroke-width="1"/>
    <circle cx="12" cy="12" r="3" fill="#ADD8E6"/>
</svg>
<h1 class='main-header'>Bedtime Story Creator</h1>
<h2 class='main-subheader'>Let's create a magical story together!</h2>
""", unsafe_allow_html=True)

st.write("Enter the details below to generate a unique story.")

# Input fields
characters = st.text_input("Characters (e.g., a sleepy bear, a talking star, a brave little mouse)", "")
genre = st.text_input("Genre (e.g., fantasy, adventure, a story about friendship)", "")
age_group = st.selectbox("Select Age Group", ["Children (5-10)", "Teens (11-18)", "Adults (18+)"], index=0)

with st.expander("Additional Tips & Voice Input"):
    # Text area for tips
    tips = st.text_area("Add any specific tips or details for the story:", height=100)

    # Voice Input section
    st.write("Use voice input to fill in the text field above.")
    
    # JavaScript component for voice input
    js_code = """
    <script>
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;

    const startListening = () => {
        recognition.start();
        document.getElementById('voice-status').innerText = 'Listening...';
        document.getElementById('voice-input-btn').style.backgroundColor = '#ADD8E6';
    };

    recognition.onresult = (event) => {
        const result = event.results[0][0].transcript;
        const textarea = window.parent.document.querySelector('textarea[aria-label="Add any specific tips or details for the story:"]');
        if (textarea) {
            textarea.value = result;
            textarea.dispatchEvent(new Event('change', { bubbles: true })); // Trigger a change event
        }
    };

    recognition.onend = () => {
        document.getElementById('voice-status').innerText = 'Done.';
        document.getElementById('voice-input-btn').style.backgroundColor = '';
    };

    recognition.onerror = (event) => {
        document.getElementById('voice-status').innerText = 'Error: ' + event.error;
    };
    </script>
    <button id="voice-input-btn" onclick="startListening()">Start Voice Input</button>
    <span id="voice-status"></span>
    """
    st.components.v1.html(js_code, height=100)

# Main action button
if st.button("Create Story"):
    if not characters and not genre:
        st.warning("Please enter at least characters and genre to create the story.")
    else:
        with st.spinner("Tucking the story into bed..."):
            generate_story(genre, characters, age_group, tips)

# Display the story and speaker button if a story exists
if st.session_state.story:
    st.markdown("<div class='story-container'>", unsafe_allow_html=True)
    st.markdown(f"<p class='story-text'>{st.session_state.story}</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Speaker icon button
    speaker_svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#4682B4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="speaker-icon">
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
    </svg>
    """
    
    st.markdown("<div class='speaker-button-container'>", unsafe_allow_html=True)
    if st.button("Tell me the story", key="play_audio"):
        text_to_speech(st.session_state.story)
    st.markdown("</div>", unsafe_allow_html=True)
