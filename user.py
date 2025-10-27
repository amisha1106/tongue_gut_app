import streamlit as st
import io
import re
import firebase_admin
from firebase_admin import credentials, storage
import google.generativeai as genai
from PIL import Image
from streamlit_cropper import st_cropper
from datetime import datetime

# ============================
# 🎨 Custom Background Styling
# ============================
st.markdown(
    """
    <style>
    .stApp {
        background-color: #fff5f8;
    }
    .main {
        background-color: #fff5f8;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================
# 🔹 Load API keys and Firebase config
# ============================
gemini_key = st.secrets.get("GEMINI_API_KEY")
if not gemini_key:
    st.error("❌ GEMINI_API_KEY not found in Streamlit secrets")
    st.stop()

firebase_creds_dict = dict(st.secrets.get("FIREBASE"))
firebase_creds_dict["private_key"] = firebase_creds_dict["private_key"].replace("\\n", "\n")

genai.configure(api_key=gemini_key)

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_creds_dict)
    firebase_admin.initialize_app(cred, {"storageBucket": "gibud-f7cc9.appspot.com"})

bucket = storage.bucket()

# ============================
# 🩷 App Header + Info Box
# ============================
st.markdown(
    """ 
    <h1 style='text-align:center; color:#d63384; text-shadow: 1px 1px 2px rgba(255,255,255,0.5);'> 👅 Gut-o-Meter </h1> 
    <p style='text-align:center; font-size:18px; color:#333; font-weight:500;'> 
    Get your <b style='color:#d63384;'>Tongue Analysis</b> + a <b style='color:#d63384;'>Gut Health Score</b> 🧠✨ 
    </p> 
    """,
    unsafe_allow_html=True
)

st.markdown(
    """ 
    <div style="background-color:#ffeef8; padding:20px; border-radius:12px; border:2px solid #ffd6e9; 
    box-shadow: 0 2px 8px rgba(255,182,193,0.15);">
        <h4 style='color:#d63384; margin-top:0;'>🧾 Quick Steps:</h4>
        <ol style="font-size:15px; color:#333; line-height:1.8;">
            <li>📸 Upload a <b>clear image of your tongue</b> (avoid filters or edits).</li>
            <li>⏰ For best results, take the photo <b>in the morning before brushing, eating, or drinking</b>.</li>
            <li>✂️ Crop if needed (keep only the tongue area visible).</li>
            <li>🚀 Hit "Analyze My Gut Health" and let the AI work its magic!</li>
        </ol>
    </div>
    """,
    unsafe_allow_html=True
)

# ============================
# 📸 Upload + Crop
# ============================
uploaded_file = st.file_uploader("📸 Upload your tongue image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="📂 Uploaded image", use_container_width=True)
    cropped_img = st_cropper(image, realtime_update=True, box_color="#ff007f", aspect_ratio=None)
    analyze_button = st.button("🔍 Analyze My Gut Health")

    if analyze_button:
        model = genai.GenerativeModel("gemini-2.0-flash-exp")

        # ---------- Stage 1: Tongue detection ----------
        st.markdown("<h4 style='color:#d63384;'>🔍 Validating if it's a tongue...</h4>", unsafe_allow_html=True)
        verify_prompt = """
        You are a strict image validator.
        Return only one word:
        - "yes" if the image clearly shows a human tongue (full or major visible part),
        - "no" otherwise (face, teeth, lips, hand, scenery, unclear, etc.).
        """
        try:
            v_resp = model.generate_content([verify_prompt, cropped_img])
            v_text = v_resp.text.strip().lower()
        except Exception as e:
            st.error(f"⚠️ Validation failed: {e}")
            st.stop()

        if "no" in v_text:
            st.error("🚫 Not a valid tongue image.")
            st.info("Please upload a clear, well-lit tongue photo only.")
            st.stop()

        # ---------- Stage 2: Quality check ----------
        qc_prompt = """
        You are an image clarity inspector.
        Rate the clarity of the tongue image as:
        - "clear" if the tongue is well-lit, centered, and not covered by lips/teeth,
        - "unclear" if blurred, overexposed, too dark, or mostly mouth/face.
        Respond with one word only: clear / unclear.
        """
        qc_resp = model.generate_content([qc_prompt, cropped_img])
        qc_text = qc_resp.text.strip().lower()
        if "unclear" in qc_text:
            st.warning("⚠️ Tongue visibility unclear. Try retaking under better light.")
            st.stop()

        # ---------- Stage 3: Detailed two-pass analysis ----------
        st.markdown("<h4 style='color:#d63384;'>🤖 Analyzing tongue features...</h4>", unsafe_allow_html=True)

        main_prompt = """
        You are a professional AI tongue health analyst.
        Analyze this tongue image and respond in a short structured format:

        - Category: one of [healthy, white, yellow, purple, deep red, indigo violet, unusual]
        - Confidence (0–100): how sure you are
        - Key Observations: 1–2 lines on color, coating, cracks, and moisture
        - Gut Health Score (0–100): numeric
        - Insights: brief friendly message
        - Tips: 2 short suggestions

        Keep output concise and markdown-friendly.
        """
        resp1 = model.generate_content([main_prompt, cropped_img])
        text1 = resp1.text.strip()

        # Check for low confidence
        conf = re.search(r'confidence[:\s]+(\d{1,3})', text1, re.IGNORECASE)
        conf_val = int(conf.group(1)) if conf else 0

        if conf_val < 75 or "uncertain" in text1.lower():
            refine_prompt = main_prompt + "\nYou seemed uncertain before. Re-analyze carefully and ensure consistency."
            resp2 = model.generate_content([refine_prompt, cropped_img])
            text2 = resp2.text.strip()
            conf2 = re.search(r'confidence[:\s]+(\d{1,3})', text2, re.IGNORECASE)
            conf_val2 = int(conf2.group(1)) if conf2 else 0
            if conf_val2 > conf_val:
                text1 = text2
                conf_val = conf_val2

        # ---------- Stage 4: Extract values ----------
        categories = ["healthy", "white", "yellow", "purple", "deep red", "indigo violet", "unusual"]
        cat = "unclassified"
        for c in categories:
            if re.search(rf"\b{c}\b", text1.lower()):
                cat = c.replace(" ", "_")
                break

        gut_score = None
        m = re.search(r'(\d{1,3})\s*/\s*100', text1)
        if m:
            gut_score = int(m.group(1))
        else:
            m2 = re.search(r'score[:\s]+(\d{1,3})', text1, re.IGNORECASE)
            if m2:
                gut_score = int(m2.group(1))

        if gut_score is None or not (0 <= gut_score <= 100):
            gut_score = 60

        # ---------- Stage 5: Firebase upload (only if valid & confident) ----------
        if conf_val >= 70 and cat != "unclassified":
            try:
                img_bytes = io.BytesIO()
                cropped_img.save(img_bytes, format="PNG")
                img_bytes.seek(0)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = f"{cat}/{ts}_{uploaded_file.name}"
                blob = bucket.blob(path)
                blob.upload_from_file(img_bytes, content_type="image/png")
            except Exception as fb_err:
                st.warning(f"⚠️ Upload skipped: {fb_err}")
        else:
            st.info("🧠 AI uncertain — image not stored for quality assurance.")

        # ---------- Stage 6: Display results ----------
        gut_level = (
            "🌟 Excellent Gut Vibes!"
            if gut_score > 85
            else ("😎 Balanced but Room to Improve!" if gut_score > 60 else "⚠️ Gut May Need Some Love!")
        )

        st.success("✅ Analysis Complete!")
        st.markdown(
            f"""
            <div style="background-color:rgba(255,240,245,0.95);padding:20px;border-radius:15px;border:3px solid #ffb6c1;">
            <h3 style='color:#d63384;'>🧠 Your Gut Health Report</h3>
            <p><b>Category:</b> {cat.replace('_',' ').title()}</p>
            <p><b>Confidence:</b> {conf_val}%</p>
            <p><b>Gut Score:</b> {gut_score}/100</p>
            <p><b>Status:</b> {gut_level}</p>
            <hr>
            <div style='color:#333;'>{text1}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
else:
    st.info("👆 Upload a clear tongue image to start the analysis.")
