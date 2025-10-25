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
# 🔹 Load API keys and Firebase config from Streamlit Secrets
# ============================

# Gemini API key
gemini_key = st.secrets.get("GEMINI_API_KEY")
if not gemini_key:
    st.error("❌ GEMINI_API_KEY not found in Streamlit secrets")
    st.stop()

# Firebase credentials (make a mutable copy)
firebase_creds_dict = dict(st.secrets.get("FIREBASE"))
firebase_creds_dict["private_key"] = firebase_creds_dict["private_key"].replace("\\n", "\n")

# ============================
# 🔹 Configure Gemini
# ============================
genai.configure(api_key=gemini_key)

# ============================
# 🔹 Initialize Firebase
# ============================
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_creds_dict)
    firebase_admin.initialize_app(cred, {
        "storageBucket": "gibud-f7cc9.appspot.com"
    })

bucket = storage.bucket()

# ============================
# 🌈 Streamlit UI Setup - Pinkish White Theme
# ============================
st.set_page_config(page_title="Gut & Tongue Analyzer", layout="centered", page_icon="👅")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #fff0f5, #ffe4e9, #fff5f8, #ffeef4); background-attachment: fixed; }
    h1,h2,h3,h4,h5,h6,p,li,span,div,label { color:#2c2c2c !important; }
    .stMarkdown,.stText { color:#1a1a1a !important; }
    div[data-testid="stFileUploader"] { background-color: rgba(255,255,255,0.9)!important; border-radius:15px; padding:20px; border:2px dashed #ffb6c1; }
    div[data-testid="stFileUploader"] label { color:#333 !important; font-weight:600; }
    div[data-testid="stFileUploader"] section { background-color: rgba(255,240,245,0.95)!important; border:2px dashed #ffb6c1!important; border-radius:12px; }
    div[data-testid="stFileUploader"] button { background-color:#ffb6c1!important; color:#fff!important; border:none!important; border-radius:8px; font-weight:600; }
    div[data-testid="stFileUploader"] button:hover { background-color:#ff99b9!important; }
    div[data-testid="stFileUploader"] span { color:#1a1a1a!important; }
    div[data-testid="stFileUploader"] small { color:#555!important; }
    .stButton>button { background: linear-gradient(135deg,#ff9fb9,#ffb6c1); color:#fff!important; border:none; border-radius:12px; padding:0.7em 1.5em; font-weight:bold; font-size:16px; box-shadow:0 4px 8px rgba(255,182,193,0.3); transition:all 0.3s ease; }
    .stButton>button:hover { background:linear-gradient(135deg,#ff87a5,#ff99b9); box-shadow:0 6px 12px rgba(255,182,193,0.5); transform:translateY(-2px); }
    .stSuccess,.stError,.stWarning,.stInfo { color:#1a1a1a!important; }
    .stSpinner>div { color:#2c2c2c!important; }
    .stImage figcaption { color:#444; font-weight:500; }
    input,textarea,select { background-color: rgba(255,255,255,0.8)!important; color:#1a1a1a!important; border:1px solid #ffb6c1!important; }
    .streamlit-cropper { background-color: rgba(255,255,255,0.6); border-radius:10px; padding:10px; }
</style>
""", unsafe_allow_html=True)

# ============================
# 🌟 Header
# ============================
st.markdown("""
<h1 style='text-align:center; color:#d63384; text-shadow: 1px 1px 2px rgba(255,255,255,0.5);'>
    👅 Gut-o-Meter
</h1>
<p style='text-align:center; font-size:18px; color:#333; font-weight:500;'>
    Get your <b style='color:#d63384;'>Tongue Analysis</b> + a <b style='color:#d63384;'>Gut Health Score</b> 🧠✨
</p>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background-color:#ffeef8; padding:20px; border-radius:12px; border:2px solid #ffd6e9; box-shadow: 0 2px 8px rgba(255,182,193,0.15);">
<h4 style='color:#d63384; margin-top:0;'>🧾 Quick Steps:</h4>
<ol style="font-size:15px; color:#333; line-height:1.8;">
<li>📸 Upload a <b>clear image of your tongue</b> (avoid filters or edits).</li>
<li>⏰ For best results, take the photo <b>in the morning before brushing, eating, or drinking</b>.</li>
<li>✂️ Crop if needed (keep only the tongue area visible).</li>
<li>🚀 Hit "Analyze My Gut Health" and let the AI work its magic!</li>
</ol>
</div>
""", unsafe_allow_html=True)

# ============================
# 📸 Upload + Crop + Validation + Analysis
# ============================
st.markdown("<br>", unsafe_allow_html=True)
uploaded_file = st.file_uploader("📸 Upload your tongue image", type=["jpg","jpeg","png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="📂 Your uploaded image", use_container_width=True)

    st.markdown("""
    <h3 style='color:#d63384; margin-top:30px;'>✂️ Optional: Crop your tongue image</h3>
    <p style='color:#555; font-style:italic;'>(Focus on the tongue area for best results 👅)</p>
    """, unsafe_allow_html=True)

    cropped_img = st_cropper(image, realtime_update=True, box_color="#ff007f", aspect_ratio=None)

    st.markdown("<br>", unsafe_allow_html=True)
    analyze_button = st.button("🔍 Analyze My Gut Health (Let's Go!)")

    if analyze_button:
        st.markdown("<h2 style='text-align:center; color:#d63384;'>🤖 Validating image... 👀</h2>", unsafe_allow_html=True)

        with st.spinner("Checking if this image contains a tongue..."):
            try:
                verifier = genai.GenerativeModel("gemini-2.0-flash-exp")
                verify_prompt = """
                You are an image validator. Analyze the image and respond with ONLY one word:
                - "yes" if the image clearly shows a human tongue,
                - "no" if it shows a face, body, scenery, object, or anything else.

                Do not explain. Just respond with 'yes' or 'no'.
                """
                verify_response = verifier.generate_content([verify_prompt, cropped_img])
                verify_result = verify_response.text.strip().lower()

                if "no" in verify_result:
                    st.error("🚫 This image doesn’t seem to contain a tongue.")
                    st.markdown("""
                    <div style="background-color:#fff5f5; padding:15px; border-radius:10px; border:2px solid #ffb6c1;">
                        <p style='color:#333;'>
                        Please upload a <b>clear image of your tongue</b> only.<br>
                        Avoid selfies, full-face photos, or other body parts.<br><br>
                        📸 <i>Tip:</i> Stick out your tongue in good lighting and keep your mouth relaxed.
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.stop()

            except Exception as e:
                st.warning(f"⚠️ Image validation failed: {str(e)}")
                st.info("Proceeding cautiously... results may be less accurate.")

        # ✅ Proceed only if it's a valid tongue image
        st.markdown("<h2 style='text-align:center; color:#d63384;'>🤖 Analyzing your tongue... 🧘‍♀️🧠</h2>", unsafe_allow_html=True)

        with st.spinner("Consulting the ancient AI of gut wisdom..."):
            try:
                model = genai.GenerativeModel("gemini-2.0-flash-exp")

                prompt = """
                    You are a friendly but knowledgeable AI health assistant with a touch of humor. Analyze the provided tongue image and generate a structured report that is informative, accurate, and fun.

                    Your output should include:

                    🩺 Tongue Category:
                    Classify the tongue into one of: healthy, white, yellow, purple, deep red, unusual, or indigo violet. Add a small playful remark.

                    📊 Gut Score (0–100):
                    Estimate a realistic gut health score with a fun short explanation.

                    💬 Tongue Talk – Color & Texture:
                    Describe the tongue's color, coating, texture, cracks, and moisture briefly.

                    🌿 Gut Health Insights:
                    Offer a light, informative insight about gut health based on the tongue.

                    💡 Tips for a Healthier Gut & Tongue:
                    Give 2–3 safe and practical suggestions with mild humor.

                    Keep paragraphs short and friendly. Avoid medical jargon or negativity.
                """

                response = model.generate_content([prompt, cropped_img])
                result_text = response.text

                # Detect color category
                categories = ["healthy", "white", "yellow", "purple", "deep red", "deep_red", "unusual", "indigo violet", "indigo_violet"]
                predicted_category = "unclassified"
                for c in categories:
                    pattern = c.lower().replace("_", "[ _-]")
                    if re.search(f"\\b{pattern}\\b", result_text.lower()):
                        predicted_category = c.replace(" ", "_")
                        break

                # Extract Gut Score
                gut_score = None
                match = re.search(r'(\d{1,3})\s*/\s*100', result_text)
                if match:
                    gut_score = int(match.group(1))
                else:
                    match2 = re.search(r'score[:\s]+(\d{1,3})', result_text, re.IGNORECASE)
                    if match2:
                        gut_score = int(match2.group(1))

                if gut_score and 0 <= gut_score <= 100:
                    if gut_score > 85:
                        gut_level = "🌟 Excellent Gut Vibes!"
                    elif gut_score > 60:
                        gut_level = "😎 Balanced but Room to Improve!"
                    else:
                        gut_level = "⚠️ Gut May Need Some Love!"
                else:
                    gut_level = "⚠️ Gut May Need Some Love!" if gut_score is None else gut_level

                # ✅ Upload only valid images to Firebase
                try:
                    img_bytes = io.BytesIO()
                    cropped_img.save(img_bytes, format="PNG")
                    img_bytes.seek(0)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    blob_path = f"{predicted_category}/{timestamp}_{uploaded_file.name}"
                    blob = bucket.blob(blob_path)
                    blob.upload_from_file(img_bytes, content_type="image/png")
                except Exception as fb_error:
                    st.warning(f"⚠️ Firebase upload skipped: {fb_error}")

                # Display Results
                st.success("✅ Analysis Complete!")
                st.markdown(f"""
                <div style="background-color:rgba(255,240,245,0.95); padding:25px; border-radius:15px; margin-top:25px; border:3px solid #ffb6c1; box-shadow:0 4px 12px rgba(255,182,193,0.3);">
                    <h3 style='color:#d63384; margin-top:0;'>🧠 Your Gut Health Report</h3>
                    <p style='color:#333;'><b style='color:#d63384;'>Category:</b> {predicted_category.replace('_',' ').title()}</p>
                    <p style='color:#333;'><b style='color:#d63384;'>Gut Health Score:</b> <span style="font-size:28px; color:#ff1493; font-weight:bold;">{gut_score}/100</span> 🎯</p>
                    <p style='color:#333;'><b style='color:#d63384;'>Status:</b> {gut_level}</p>
                    <hr style='border-color:#ffb6c1;'>
                    <h4 style='color:#d63384;'>🩺 AI Tongue & Gut Insights:</h4>
                    <div style='color:#1a1a1a; line-height:1.8; font-size:15px;'>{result_text}</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("""
                <div style="background-color:rgba(255,243,205,0.9); padding:20px; border-radius:12px; margin-top:25px; border:2px solid #ffc107;">
                    <h4 style='color:#d63384; margin-top:0;'>⚠️ Important Disclaimer</h4>
                    <p style='color:#1a1a1a; line-height:1.6;'>
                        This AI analysis is for <b>educational and wellness purposes only</b>.
                        Please consult a healthcare professional for medical advice.
                    </p>
                </div>
                """, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"💥 Oops! Something went wrong: {str(e)}")
                st.info("💡 Try a clearer image or check your internet connection.")

else:
    st.markdown("""
    <div style='text-align:center; padding:40px; background-color:rgba(255,255,255,0.6); border-radius:15px; border:2px dashed #ffb6c1; margin-top:20px;'>
        <h3 style='color:#d63384;'>👆 Upload an image to get started!</h3>
        <p style='color:#555;'>Your tongue analysis awaits... 😊</p>
    </div>
    """, unsafe_allow_html=True)
