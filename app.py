import streamlit as st
import google.generativeai as genai
import requests
import datetime
import pytz
from PIL import Image

# --- CONFIGURATION ---
st.set_page_config(page_title="Ohr HaTorah v2.4", page_icon="🕎", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.title("🕎 Ohr HaTorah")
    # UPDATED LABEL HERE:
    st.markdown("**The Digital Beit Midrash Companion**")
    
    st.caption("v2.4 | Powered by Gemini 2.0")
    
    if 'GEMINI_API_KEY' in st.secrets:
        api_key = st.secrets['GEMINI_API_KEY']
    else:
        api_key = st.text_input("Enter Google API Key", type="password")

    st.divider()
    zip_code = st.text_input("Zip Code (US Only)", value="11213")
    if st.button("Update Location"):
        st.rerun()
    
    st.divider()
    mode = st.radio("Mode:", ["Chavruta Chat", "Siddur Builder", "Scholar's Eye (OCR)"])

# --- ZMANIM LOGIC ---
def get_zmanim_data(zip_c):
    try:
        today = datetime.date.today().isoformat()
        # 1. Times
        zman_resp = requests.get(f"https://www.hebcal.com/zmanim?cfg=json&zip={zip_c}&date={today}").json()
        times = zman_resp.get("times", {})
        
        # 2. Parasha
        cal_resp = requests.get("https://www.hebcal.com/shabbat?cfg=json&geonameid=281184&M=on").json()
        parsha = next((i['title'] for i in cal_resp['items'] if i['category'] == 'parashat'), "Unknown")
        
        return {
            "netz": times.get("sunrise", "N/A")[11:16],
            "shma": times.get("sof_zman_shma", "N/A")[11:16],
            "shkia": times.get("sunset", "N/A")[11:16],
            "parsha": parsha,
            "link": f"https://www.sefaria.org/topics/{parsha.replace(' ', '-')}"
        }
    except:
        return None

if zip_code:
    data = get_zmanim_data(zip_code)
    c1, c2, c3 = st.columns(3)
    if data:
        c1.info(f"📅 **Parsha:** [{data['parsha']}]({data['link']})")
        c2.warning(f"☀️ Netz: {data['netz']} | ⏰ Shma: {data['shma']} | 🌙 Shkia: {data['shkia']}")
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
    
    # TRY GEMINI 2.0 FLASH FIRST
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp", 
            system_instruction=SYSTEM_INSTRUCTIONS
        )
    except:
        # FALLBACK TO 1.5 PRO IF 2.0 FAILS
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro", 
            system_instruction=SYSTEM_INSTRUCTIONS
        )

# --- MODES ---
if mode == "Chavruta Chat":
    st.header("📚 Chavruta Chat")
    if "messages" not in st.session_state: st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                chat = model.start_chat(history=[{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.messages[:-1]])
                response = chat.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "model", "content": response.text})
            except Exception as e:
                st.error(f"Connection Error: {e}")

elif mode == "Siddur Builder":
    st.header("🕍 Custom Siddur")
    c1, c2 = st.columns(2)
    nusach = c1.selectbox("Nusach", ["Sephardi (Edot HaMizrach)", "Ashkenaz"])
    prayer = c2.selectbox("Prayer", ["Shema", "Amidah", "Kaddish", "Asher Yatzar"])
    if st.button("Generate"):
        with st.spinner("Writing..."):
            st.markdown(model.generate_content(f"Write '{prayer}' in Nusach '{nusach}'. Hebrew with English translation.").text)

elif mode == "Scholar's Eye (OCR)":
    st.header("👁️ Scholar's Eye")
    if
