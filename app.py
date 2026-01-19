import streamlit as st
import google.generativeai as genai
import requests
import re

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="Ohr HaTorah", page_icon="🕎")

# Sidebar for API Key (Secure)
with st.sidebar:
    st.title("🕎 Ohr HaTorah")
    st.markdown("Your AI Chavrusa for Halacha, Gemara, and Tanakh.")
    
    # Check for secrets first (Production), otherwise ask user (Local)
    if 'GEMINI_API_KEY' in st.secrets:
        api_key = st.secrets['GEMINI_API_KEY']
    else:
        api_key = st.text_input("Enter Google Gemini API Key", type="password")
        st.caption("Get a key at aistudio.google.com")

# --- SEFARIA FETCHING TOOL ---
def fetch_sefaria_text(citation):
    """Fetches text from Sefaria API to ground the AI's answers."""
    base_url = "https://www.sefaria.org/api/texts/"
    params = {"context": 0, "pad": 0, "vhe": 1, "ven": 1}
    try:
        response = requests.get(f"{base_url}{citation}", params=params)
        data = response.json()
        if "error" in data: return None
        
        # Clean HTML
        hebrew = re.sub(r'<[^>]+>', '', data.get("he", ""))
        english = re.sub(r'<[^>]+>', '', data.get("text", ""))
        return f"**SOURCE TEXT ({data['ref']}):**\n\n[Hebrew]: {hebrew}\n\n[English]: {english}"
    except:
        return None

# --- AI MODEL SETUP ---
SYSTEM_INSTRUCTIONS = """
You are **Ohr HaTorah**, an Orthodox Jewish study partner (Chavrusa).
1. **Source Everything:** Cite chapter/verse (e.g., Bereshit 1:1).
2. **Hierarchy:** Rishonim override Acharonim; Gemara overrides all.
3. **Tone:** Respectful, rational (Maimonidean), and clear.
4. **Tool Use:** If the user cites a specific text, ask if you should fetch the exact words.
5. **Disclaimer:** You are not a Posek. Do not give practical Halachic rulings for action.
"""

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_INSTRUCTIONS
    )

    # Initialize Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display Chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User Input
    if prompt := st.chat_input("Ask a question on Torah or Halacha..."):
        # 1. User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Check if we need to fetch text (Simple Keyword Check)
        # Advanced: You could make the AI decide this, but this is faster/cheaper.
        context_text = ""
        if "check" in prompt.lower() or "verify" in prompt.lower():
            # Extract potential citation (rough logic)
            with st.status("Consulting Sefaria Library..."):
                # This is a basic catch; in a full app we'd use function calling
                pass 
        
        # 3. AI Response
        with st.chat_message("assistant"):
            try:
                # Send full history to AI
                chat = model.start_chat(history=[
                    {"role": m["role"], "parts": [m["content"]]} 
                    for m in st.session_state.messages[:-1]
                ])
                response = chat.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "model", "content": response.text})
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info("Please enter your API Key in the sidebar to begin learning.")