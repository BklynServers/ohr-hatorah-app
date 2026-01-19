import streamlit as st
import google.generativeai as genai
import requests
import datetime
from PIL import Image

# --- CONFIGURATION ---
st.set_page_config(page_title="Ohr HaTorah Research", page_icon="🕎", layout="wide")

# --- CUSTOM CSS (FOR THE LEXIS/OTZAR LOOK) ---
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
    st.caption("Research Terminal v4.0")
    
    # 1. API KEY (BYOK Model for Cost Control)
    if 'GEMINI_API_KEY' in st.secrets:
        api_key = st.secrets['GEMINI_API_KEY']
    else:
        api_key = st.text_input("Enter Google API Key", type="password")

    st.divider()
    
    # 2. RESEARCH TOOLS
    mode = st.radio("Select Tool:", ["Sugya Search (Lexis Mode)", "Scholar's Eye (OCR)", "Siddur Builder"])
    
    st.divider()
    
    # 3. ZMANIM WIDGET (Minimalist)
    zip_code = st.text_input("Zip Code (Zmanim)", value="11213")
    if zip_code and st.button("Update"):
        st.rerun()

# --- HELPER: SEFARIA SEARCH (THE LIBRARY) ---
def search_sefaria_text(ref):
    # This fetches the ACTUAL text from Sefaria's database
    url = f"https://www.sefaria.org/api/texts/{ref}?context=0"
    try:
        response = requests.get(url).json()
        hebrew = response.get('he', 'Text not found.')
        english = response.get('text', 'Translation not found.')
        return hebrew, english, response.get('ref', ref)
    except:
        return None, None, None

# --- AI CONFIGURATION ---
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro", # Use PRO for deep analysis
        system_instruction="""
        You are the 'Ohr HaTorah' Research Engine.
        1. **Role:** Analyze Torah texts like a legal scholar (LexisNexis style).
        2. **Method:** When a user provides a text, analyze the Pshat, Remez, Drash, and Sod (if applicable).
        3. **Tone:** Professional, Academic, and Reverent.
        4. **Format:** Use structured tables and bullet points.
        """
    )

# --- MAIN INTERFACE ---

# === MODE 1: SUGYA SEARCH (THE LEXIS EXPERIENCE) ===
if mode == "Sugya Search (Lexis Mode)":
    st.header("🔎 Sugya Research Terminal")
    
    # 1. SEARCH BAR
    col1, col2 = st.columns([3, 1])
    with col1:
        search_ref = st.text_input("Enter Source (e.g., 'Berakhot 2a', 'Rambam Deot 1:1', 'Genesis 1:1')")
    with col2:
        fetch_btn = st.button("Retrieve Text")

    if "current_he" not in st.session_state:
        st.session_state.current_he = ""
        st.session_state.current_en = ""
        st.session_state.current_ref = ""

    # 2. RETRIEVE TEXT
    if fetch_btn and search_ref:
        he, en, ref_title = search_sefaria_text(search_ref)
        if he:
            st.session_state.current_he = he
            st.session_state.current_en = en
            st.session_state.current_ref = ref_title
        else:
            st.error("Source not found in the Digital Library.")

    # 3. SPLIT SCREEN WORKSPACE
    if st.session_state.current_ref:
        st.divider()
        st.subheader(f"📜 Text: {st.session_state.current_ref}")
        
        left_col, right_col = st.columns(2)
        
        # LEFT: THE "OTZAR" (Raw Text)
        with left_col:
            st.info("📖 Source Text (Mekorot)")
            
            # Formatting complex text lists
            display_he = st.session_state.current_he
            display_en = st.session_state.current_en
            
            # Handle if text is list or string
            if isinstance(display_he, list):
                display_he = " ".join([str(x) for x in display_he])
            if isinstance(display_en, list):
                display_en = " ".join([str(x) for x in display_en])
                
            st.markdown(f"<div class='source-box'><div class='hebrew'>{display_he}</div><hr><div class='english'>{display_en}</div></div>", unsafe_allow_html=True)

        # RIGHT: THE "LEXIS" (AI Analysis)
        with right_col:
            st.success("🤖 AI Legal Analyst")
            
            # Preset Prompts
            analysis_type = st.selectbox("Select Analysis Type:", [
                "Summarize & Key Points",
                "Halachic Conclusion (Maskana)",
                "Comparison (Rashi vs. Tosafot Logic)",
                "Modern Application",
                "Free Chat"
            ])
            
            if st.button("Analyze Text"):
                with st.spinner("Analyzing..."):
                    prompt = f"""
                    Analyze this text: {st.session_state.current_ref}
                    Text Content: {display_he} \n {display_en}
                    
                    Task: Perform a '{analysis_type}'.
                    If Halacha, cite the Shulchan Aruch rulings related to this.
                    If Gemara, explain the Shakla v'Tarya (flow of logic).
                    """
                    response = model.generate_content(prompt)
                    st.markdown(response.text)

# === MODE 2: SCHOLAR'S EYE (OCR) ===
elif mode == "Scholar's Eye (OCR)":
    st.header("👁️ Scholar's Eye (Image Scan)")
    st.caption("Upload a page from a Sefer (like Otzar HaChochma) to analyze it.")
    
    img_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])
    if img_file:
        img = Image.open(img_file)
        st.image(img, width=400)
        
        if st.button("Transcribe & Explain"):
            with st.spinner("Scanning..."):
                prompt = "Transcribe this Hebrew/Aramaic text exactly. Then provide a translation and a summary of the topic discussing."
                response = model.generate_content([prompt, img])
                st.markdown(response.text)

# === MODE 3: SIDDUR BUILDER ===
elif mode == "Siddur Builder":
    st.header("🕍 Custom Siddur Generator")
    nusach = st.selectbox("Nusach", ["Sephardi", "Ashkenaz", "Ari"])
    prayer = st.selectbox("Prayer", ["Ashrei", "Amidah", "Aleinu"])
    if st.button("Generate"):
        st.markdown(model.generate_content(f"Write '{prayer}' in Nusach '{nusach}'.").text)
