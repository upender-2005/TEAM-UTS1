import streamlit as st
import tempfile
import json

st.title("🤖 Voice ChatBot")

SMALL_MODEL = "llama3-8b"
SYSTEM_PROMPT = "Answer in English, concisely, with brief code when useful."

def init_history():
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hi! Ask me anything by typing or speaking."},
    ]

if "messages" not in st.session_state:
    init_history()



audio = st.audio_input("Record your voice")
if audio:
    st.success("🎤 Audio captured!")
    st.audio(audio)   # play back your voice
    # Instead of transcription, just type your question manually for now






# Show history
for m in st.session_state.messages:
    if m["role"] == "system":
        continue
    with st.chat_message(m["role"]):
        st.write(m["content"])

# --- Voice Input (new Streamlit API) ---
st.subheader("🎙️ Speak your question")
audio = st.audio_input("Record your voice")

voice_text = None
if audio:
    # Save audio file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio.read())
        audio_path = tmp.name

    # 🔊 Transcribe with Whisper (or another STT API)
    # Example: OpenAI Whisper
    import openai
    transcript = openai.audio.transcriptions.create(
        model="whisper-1",
        file=open(audio_path, "rb")
    )
    voice_text = transcript.text

# --- Text Input ---
prompt = st.chat_input("Type your question…")

if voice_text:
    prompt = voice_text

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # --- Query Snowflake Cortex ---
    cnx = st.connection("snowflake")
    session = cnx.session()
    history = st.session_state.messages[-10:]

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            result = session.sql("""
                SELECT SNOWFLAKE.CORTEX.COMPLETE(
                    ?, 
                    PARSE_JSON(?), 
                    OBJECT_CONSTRUCT(
                        'temperature', 0.2,
                        'max_tokens', 400,
                        'guardrails', TRUE
                    )
                ) AS resp
            """, params=[SMALL_MODEL, json.dumps(history)]).collect()[0]["RESP"]

            try:
                obj = json.loads(result)
                if "choices" in obj:
                    choice = obj["choices"][0]
                    if "message" in choice:
                        reply = choice["message"]["content"]
                    elif "text" in choice:
                        reply = choice["text"]
                    else:
                        reply = str(choice)
                else:
                    reply = result
            except Exception:
                reply = result

            st.write(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})

            # --- Voice Output (TTS) ---
            tts_url = f"https://api.streamelements.com/kappa/v2/speech?voice=Brian&text={reply}"
            st.audio(tts_url)

# --- Sidebar ---
with st.sidebar:
    st.subheader("⚙️ Model & Settings")
    st.caption("Using Snowflake Cortex COMPLETE under the hood.")
    st.markdown(f"- Model: {SMALL_MODEL}  \n- temperature: 0.2  \n- max_tokens: 400  \n- guardrails: on")
    if st.button("🧹 Clear chat", type="secondary"):
        init_history()
        st.rerun()
