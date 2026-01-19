import streamlit as st
import google.generativeai as genai
import requests
import datetime
import pytz
from PIL import Image

# --- CONFIGURATION ---
st.set_page_config(page_title="Ohr HaTorah v2.5", page_icon="🕎", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.title("🕎 Ohr HaTorah")
    st.markdown("**The Digital Beit Midrash Companion**")
    st.caption("v2.5 | Powered by Gemini 2.0")
    
    # API Key Check
    if 'GEMINI_API_KEY' in st.secrets:
        api_key = st.secrets['GEMINI_API_KEY']
    else:
        api_key = st.text_input("Enter Google API Key", type="password")

    st.divider()
    
    # Location Logic
    zip_code = st.text_input("Zip Code (US Only)", value="11213")
    if st.button("Update Location"):
        st.rerun()
    
    st.divider()
    
    # Mode Selector
    mode = st.radio("Mode:", ["Chavruta Chat", "Siddur Builder", "Scholar's Eye (OCR)"])

# --- ZMANIM FUNCTION ---
def get_zmanim_data(zip_c):
    try:
        today = datetime.date.today().isoformat()
        # 1. Times
        zman_resp = requests.get(f"https://www.hebcal.com/zmanim?cfg=json&zip={zip_c}&date={today}").json()
        times = zman_resp.get("times", {})
        
        # 2. Parasha
        cal_resp = requests.get("https://www.hebcal.com/shabbat?cfg=json&geonameid=281184&M=on").json()
        # Safe extraction of Parasha
        parsha = "Unknown"
        for item in cal_resp.get('items', []):
            if item.get('category') == 'parashat':
                parsha = item.get('title')
                break
        
        return {
            "netz": times.get("sunrise", "N/A")[11:16],
            "shma": times.get("sof_zman_shma", "N/A")[11:16],
            "shkia": times.get("sunset", "N/A")[11:16],
            "parsha": parsha,
            "link": f"https://www.sefaria.org/topics/{parsha.replace(' ', '-')}"
        }
    except Exception as e:
        return None

# --- DISPLAY DASHBOARD ---
if zip_code:
    data = get_zmanim_data(zip_code)
    c1, c2, c3 = st.columns(3)
    if data:
        c1.info(f"📅 **Parsha:** [{data['parsha']}]({data['link']})")
        c2.warning(f"☀️ Netz: {data['netz']} | ⏰ Shma: {data['shma']} | 🌙 Shkia: {data['shkia']}")
        
        # Tehillim Link
        day = datetime.date.today().day
        c3.success(f"📖 **Tehillim:** [Chapter {day}](https://www.sefaria.org/Psalms.{day})")

st.divider()

# --- AI CONFIGURATION ---
SYSTEM_INSTRUCTIONS = """
You are **Ohr HaTorah**.
1. **Identity:** Sephardic Torah Scholar. Fluent in Hebrew/English/Spanish.
2. **Sources:** Strict adherence to Mesorah (Rambam/Bet Yosef).
3. **Citation:** Always cite chapter and verse.
"""

if api_key:
    genai.configure(api_key=api_key)
    
    # Fallback Logic for Models
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp", 
            system_instruction=SYSTEM_INSTRUCTIONS
        )
    except:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro", 
            system_instruction=SYSTEM_INSTRUCTIONS
        )

# --- MODE 1: CHAVRUTA CHAT ---
if mode == "Chavruta Chat":
    st.header("📚 Chavruta Chat")
    
    # Initialize History
    if "messages" not in st.session_state: 
        st.session_state.messages = []
    
    # Show History
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): 
            st.markdown(m["content"])

    # Input Logic
    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): 
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            try:
                chat = model.start_chat(history=[{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages[:-1]])
                response = chat.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "model", "content": response.text})
            except Exception as e:
                st.error(f"Connection Error: {e}")

# --- MODE 2: SIDDUR BUILDER ---
elif mode == "Siddur Builder":
    st.header("🕍 Custom Siddur")
    c1, c2 = st.columns(2)
    nusach = c1.selectbox("Nusach", ["Sephardi (Edot HaMizrach)", "Ashkenaz"])
    prayer = c2.selectbox("Prayer", ["Shema", "Amidah", "Kaddish", "Asher Yatzar"])
    
    if st.button("Generate"):
        with st.spinner("Writing..."):
            try:
                resp = model.generate_content(f"Write '{prayer}' in Nusach '{nusach}'. Hebrew with English translation.")
                st.markdown(resp.text)
            except Exception as e:
                st.error(f"Error: {e}")

# --- MODE 3: OCR ---
elif mode == "Scholar's Eye (OCR)":
    st.header("👁️ Scholar's Eye")
    
    img_file = st.file_uploader("Upload Text Image", type=["png", "jpg", "jpeg", "webp"])
    if img_file:
        img = Image.open(img_file)
        st.image(img, width=300)
        
        if st.button("Decipher"):
            with st.spinner("Reading..."):
                try:
                    resp = model.generate_content(["Transcribe and explain this Jewish text:", img])
                    st.markdown(resp.text)
                except Exception as e:
                    st.error(f"Error: {e}")
