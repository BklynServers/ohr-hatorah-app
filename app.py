import streamlit as st
import google.generativeai as genai
import requests
import datetime
from PIL import Image

# --- CONFIGURATION ---
st.set_page_config(page_title="Ohr HaTorah Research", page_icon="🕎", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .source-box {
        background-color: #fcf8e3; 
        border: 1px solid #faebcc; 
        padding: 15px; 
        border-radius: 5px; 
        max-height: 500px; 
        overflow-y: scroll;
        font-family: 'Ezra SIL', 'SBL Hebrew', serif;
    }
    .hebrew { direction: rtl; font-size: 1.2em; font-weight: bold; }
    .english { font-size: 1em; color: #555; }
    .stButton>button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.title("🕎 Ohr HaTorah")
    st.caption("Research Terminal v4.1")
    
    if 'GEMINI_API_KEY' in st.secrets:
        api_key = st.secrets['GEMINI_API_KEY']
    else:
        api_key = st.text_input("Enter Google API Key", type="password")

    st.divider()
    
    mode = st.radio("Select Tool:", ["Sugya Search (Lexis Mode)", "Scholar's Eye (OCR)", "Siddur Builder"])
    
    st.divider()
    
    zip_code = st.text_input("Zip Code (Zmanim)", value="11213")
    if zip_code and st.button("Update"):
        st.rerun()

# --- HELPER: SEFARIA SEARCH ---
def search_sefaria_text(ref):
    url = f"https://www.sefaria.org/api/texts/{ref}?context=0"
    try:
        response = requests.get(url).json()
        hebrew = response.get('he', 'Text not found.')
        english = response.get('text', 'Translation not found.')
        return hebrew, english, response.get('ref', ref)
    except:
        return None, None, None

# --- AI CONFIGURATION (FIXED) ---
if api_key:
    genai.configure(api_key=api_key)
    
    # We use a TRY/EXCEPT block to find a working model
    # We prefer 2.0 Flash (Smart/Fast), fallback to 1.5 Flash (Reliable)
    SYSTEM_PROMPT = """
    You are the 'Ohr HaTorah' Research Engine.
    1. Role: Analyze Torah texts like a legal scholar.
    2. Tone: Professional, Academic, and Reverent.
    3. Format: Use structured tables and bullet points.
    """
    
    try:
        # Try the experimental 2.0 model first
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp", system_instruction=SYSTEM_PROMPT)
    except:
        # Fallback to standard 1.5 Flash
        model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)

# --- MAIN INTERFACE ---

# === MODE 1: SUGYA SEARCH ===
if mode == "Sugya Search (Lexis Mode)":
    st.header("🔎 Sugya Research Terminal")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_ref = st.text_input("Enter Source (e.g., 'Berakhot 2a', 'Rambam Deot 1:1')")
    with col2:
        fetch_btn = st.button("Retrieve Text")

    if "current_he" not in st.session_state:
        st.session_state.current_he = ""
        st.session_state.current_en = ""
        st.session_state.current_ref = ""

    if fetch_btn and search_ref:
        he, en, ref_title = search_sefaria_text(search_ref)
        if he:
            st.session_state.current_he = he
            st.session_state.current_en = en
            st.session_state.current_ref = ref_title
        else:
            st.error("Source not found in the Digital Library.")

    if st.session_state.current_ref:
        st.divider()
        st.subheader(f"📜 Text: {st.session_state.current_ref}")
        
        left_col, right_col = st.columns(2)
        
        with left_col:
            st.info("📖 Source Text (Mekorot)")
            display_he = st.session_state.current_he
            display_en = st.session_state.current_en
            
            if isinstance(display_he, list): display_he = " ".join([str(x) for x in display_he])
            if isinstance(display_en, list): display_en = " ".join([str(x) for x in display_en])
                
            st.markdown(f"<div class='source-box'><div class='hebrew'>{display_he}</div><hr><div class='english'>{display_en}</div></div>", unsafe_allow_html=True)

        with right_col:
            st.success("🤖 AI Legal Analyst")
            analysis_type = st.selectbox("Select Analysis Type:", ["Summarize", "Halachic Conclusion", "Comparison", "Free Chat"])
            
            if st.button("Analyze Text"):
                with st.spinner("Analyzing..."):
                    try:
                        prompt = f"Analyze this text ({st.session_state.current_ref}):\n{display_he}\nTask: {analysis_type}"
                        response = model.generate_content(prompt)
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"AI Error: {e}")

# === MODE 2: SCHOLAR'S EYE (OCR) ===
elif mode == "Scholar's Eye (OCR)":
    st.header("👁️ Scholar's Eye")
    img_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])
    if img_file:
        img = Image.open(img_file)
        st.image(img, width=400)
        if st.button("Transcribe"):
            with st.spinner("Scanning..."):
                try:
                    response = model.generate_content(["Transcribe and explain:", img])
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"AI Error: {e}")

# === MODE 3: SIDDUR BUILDER ===
elif mode == "Siddur Builder":
    st.header("🕍 Custom Siddur Generator")
    nusach = st.selectbox("Nusach", ["Sephardi", "Ashkenaz", "Ari"])
    prayer = st.selectbox("Prayer", ["Ashrei", "Amidah", "Aleinu"])
    if st.button("Generate"):
        with st.spinner("Writing..."):
            try:
                # SAFE GENERATION BLOCK
                response = model.generate_content(f"Write '{prayer}' in Nusach '{nusach}'.")
                st.markdown(response.text)
            except Exception as e:
                # If 2.0 fails, catch it here
                st.error(f"Error generating prayer. Try refreshing or checking API key. Details: {e}")
