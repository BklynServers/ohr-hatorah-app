import streamlit as st
import google.generativeai as genai
import requests
import datetime
import pytz
from PIL import Image

# --- CONFIGURATION ---
st.set_page_config(page_title="Ohr HaTorah v2.1", page_icon="🕎", layout="wide")

# --- SIDEBAR: SETTINGS & TOOLS ---
with st.sidebar:
    st.title("🕎 Ohr HaTorah")
    st.markdown("**The Sephardic Digital Beit Midrash**")
    
    # 1. API Key Check
    if 'GEMINI_API_KEY' in st.secrets:
        api_key = st.secrets['GEMINI_API_KEY']
    else:
        api_key = st.text_input("Enter Google API Key", type="password")

    st.divider()
    
    # 2. Location for Zmanim
    st.subheader("📍 Location (Zmanim)")
    zip_code = st.text_input("Zip Code (US Only)", value="11213")
    
    st.divider()
    
    # 3. Mode Selector
    mode = st.radio("Select Mode:", ["Chavruta Chat (Study)", "Siddur Builder", "Scholar's Eye (OCR)"])

# --- MODULE 1: ZMANIM DASHBOARD ---
def get_zmanim(zip_c):
    # Fetch from Hebcal
    today = datetime.date.today().isoformat()
    url = f"https://www.hebcal.com/zmanim?cfg=json&zip={zip_c}&date={today}"
    try:
        resp = requests.get(url).json()
        return resp
    except:
        return None

def get_calendar():
    # Fetch Parsha & Daf Yomi
    url = "https://www.hebcal.com/shabbat?cfg=json&geonameid=3448439&M=on" # Jerusalem default
    try:
        data = requests.get(url).json()
        parsha = next((item['title'] for item in data['items'] if item['category'] == 'parashat'), "Unknown")
        return parsha
    except:
        return "Unknown"

# Display Dashboard
if zip_code:
    col1, col2, col3 = st.columns(3)
    zmanim_data = get_zmanim(zip_code)
    parsha_name = get_calendar()
    
    with col1:
        st.info(f"📅 **Parsha:** {parsha_name}")
    with col2:
        if zmanim_data:
            shma = zmanim_data.get("times", {}).get("sof_zman_shma", "")[:5]
            candles = zmanim_data.get("times", {}).get("candles", "")[:5]
            st.warning(f"⏰ **Sof Zman Shema:** {shma}")
    with col3:
        st.success(f"📖 **Daily Tehillim:** Ch. {datetime.date.today().day}")

st.divider()

# --- SETUP AI MODEL (THE BRAIN) ---
# We hardwire Hebrew/Spanish fluency and Sephardic identity here.
SYSTEM_INSTRUCTIONS = """
You are **Ohr HaTorah**, a wise Sephardic Torah Scholar and Study Partner (Chavruta).

### IDENTITY & LANGUAGE
1.  **Multilingual:** You are strictly fluent in **Hebrew (Ivrit)**, **English**, and **Spanish**.
    * If the user speaks Hebrew, answer in high-level Hebrew.
    * If the user speaks Spanish, answer in Spanish.
2.  **Tradition:** You follow the **Sephardic Mesorah** (Rambam, Shulchan Aruch/Bet Yosef, Rav Ovadia Yosef).
3.  **Terminology:** Never use Ashkenazi pronunciation (e.g., say "Shabbat" not "Shabbos", "Chavruta" not "Chavrusa").

### MODES OF OPERATION
1.  **Chavruta Chat:**
    * Cite sources clearly (Chapter/Verse).
    * Use the Sefaria API logic if asked to check a text.
    * Adhere to the hierarchy: Tanakh -> Gemara -> Rishonim -> Acharonim.
2.  **Siddur Builder:**
    * Output liturgical text accurately.
    * Pay attention to Nusach (Edot HaMizrach vs Ashkenaz).
3.  **Scholar's Eye (OCR):**
    * When given an image, transcribe the text exactly (Hebrew/Rashi script).
    * Translate it.
    * Explain the context.
"""

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", # Flash is required for OCR (Images)
        system_instruction=SYSTEM_INSTRUCTIONS
    )

# --- MODULE 2: MODES ---

# MODE A: CHAVRUTA CHAT
if mode == "Chavruta Chat (Study)":
    st.header("📚 Chavruta Chat")
    st.caption("Ask in Hebrew, English, or Spanish.")
    
    # Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question... / שאל שאלה... / Hacé una pregunta..."):
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
                st.error(f"Error: {e}")

# MODE B: SIDDUR BUILDER
elif mode == "Siddur Builder":
    st.header("🕍 Custom Siddur / סידור מותאם אישית")
    
    c1, c2, c3 = st.columns(3)
    nusach = c1.selectbox("Nusach / נוסח", ["Sephardi (Edot HaMizrach)", "Ashkenaz", "Ari (Chabad)", "Baladi (Teiman)"])
    lang = c2.selectbox("Language / שפה", ["Hebrew Only", "Hebrew/English", "Hebrew/Spanish", "Hebrew/Russian"])
    prayer = c3.selectbox("Prayer / תפילה", ["Ashrei", "Shema", "Amidah (Weekday)", "Aleinu", "Birkat Hamazon", "Kaddish"])
    
    if st.button("Generate Prayer / צור תפילה"):
        with st.spinner("Writing holy text..."):
            prompt = f"Write the prayer '{prayer}' in Nusach '{nusach}'. Output format: {lang}. If translation is needed, provide linear translation. Ensure strict accuracy."
            response = model.generate_content(prompt)
            st.markdown(response.text)

# MODE C: SCHOLAR'S EYE (OCR)
elif mode == "Scholar's Eye (OCR)":
    st.header("👁️ Scholar's Eye / עין הסופר")
    st.markdown("Upload a photo of any text (Gemara, handwritten letter, Pashkevil).")
    
    uploaded_file = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg", "webp"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Text", width=400)
        
        if st.button("Decipher & Explain"):
            with st.spinner("Analyzing..."):
                prompt = "Look at this image. 1. Transcribe the Hebrew/Yiddish/Ladino text exactly. 2. Translate it to English (and Spanish if relevant). 3. Explain the context."
                response = model.generate_content([prompt, image])
                st.markdown(response.text)

else:
    st.info("Please enter your API Key in the sidebar.")
