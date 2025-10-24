import streamlit as st
import os
import io
import re
import firebase_admin
from firebase_admin import credentials, storage
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
from streamlit_cropper import st_cropper
from datetime import datetime

# ============================
# 🔹 Load API keys and config
# ============================
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
firebase_key_path = os.getenv("FIREBASE_CREDENTIALS")

if not gemini_key:
    st.error("❌ GEMINI_API_KEY not found in .env file")
    st.stop()

if not firebase_key_path or not os.path.exists(firebase_key_path):
    st.error("❌ Firebase key file missing or path invalid")
    st.stop()

# Configure Gemini
genai.configure(api_key=gemini_key)

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_key_path)
    firebase_admin.initialize_app(cred, {
        "storageBucket": "gibud-f7cc9.appspot.com"
    })

bucket = storage.bucket()

# ============================
# 🌈 Streamlit UI Setup - Pinkish White Theme
# ============================
st.set_page_config(page_title="Gut & Tongue Analyzer", layout="centered", page_icon="👅")

# 💅 Custom CSS: Pinkish-white background with excellent text visibility
st.markdown("""
<style>
    /* Main background - soft pinkish white */
    .stApp {
        background: linear-gradient(135deg, #fff0f5, #ffe4e9, #fff5f8, #ffeef4);
        background-attachment: fixed;
    }
    
    /* All text elements - dark for maximum readability */
    h1, h2, h3, h4, h5, h6, p, li, span, div, label {
        color: #2c2c2c !important;
    }
    
    /* Stronger text contrast for body text */
    .stMarkdown, .stText {
        color: #1a1a1a !important;
    }
    
    /* File uploader styling */
    div[data-testid="stFileUploader"] {
        background-color: rgba(255, 255, 255, 0.9) !important;
        border-radius: 15px;
        padding: 20px;
        border: 2px dashed #ffb6c1;
    }
    
    div[data-testid="stFileUploader"] label {
        color: #333333 !important;
        font-weight: 600;
    }
    
    /* File uploader drag-drop area */
    div[data-testid="stFileUploader"] section {
        background-color: rgba(255, 240, 245, 0.95) !important;
        border: 2px dashed #ffb6c1 !important;
        border-radius: 12px;
    }
    
    /* File uploader button */
    div[data-testid="stFileUploader"] button {
        background-color: #ffb6c1 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px;
        font-weight: 600;
    }
    
    div[data-testid="stFileUploader"] button:hover {
        background-color: #ff99b9 !important;
    }
    
    /* File name display */
    div[data-testid="stFileUploader"] span {
        color: #1a1a1a !important;
    }
    
    /* Small text in uploader */
    div[data-testid="stFileUploader"] small {
        color: #555555 !important;
    }
    
    /* Button styling - pink theme */
    .stButton>button {
        background: linear-gradient(135deg, #ff9fb9, #ffb6c1);
        color: #ffffff !important;
        border: none;
        border-radius: 12px;
        padding: 0.7em 1.5em;
        font-weight: bold;
        font-size: 16px;
        box-shadow: 0 4px 8px rgba(255, 182, 193, 0.3);
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #ff87a5, #ff99b9);
        box-shadow: 0 6px 12px rgba(255, 182, 193, 0.5);
        transform: translateY(-2px);
    }
    
    /* Success/Error messages */
    .stSuccess, .stError, .stWarning, .stInfo {
        color: #1a1a1a !important;
    }
    
    /* Spinner text */
    .stSpinner > div {
        color: #2c2c2c !important;
    }
    
    /* Image captions */
    .stImage figcaption {
        color: #444444 !important;
        font-weight: 500;
    }
    
    /* Input fields */
    input, textarea, select {
        background-color: rgba(255, 255, 255, 0.8) !important;
        color: #1a1a1a !important;
        border: 1px solid #ffb6c1 !important;
    }
    
    /* Cropper container */
    .streamlit-cropper {
        background-color: rgba(255, 255, 255, 0.6);
        border-radius: 10px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ============================
# 🌟 Header
# ============================
st.markdown("""
<h1 style='text-align:center; color:#d63384; text-shadow: 1px 1px 2px rgba(255,255,255,0.5);'>
    👅 Gut-o-Meter
</h1>
<p style='text-align:center; font-size:18px; color:#333333; font-weight: 500;'>
    Get your <b style='color:#d63384;'>Tongue Analysis</b> + a <b style='color:#d63384;'>Gut Health Score</b> 🧠✨
</p>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background-color:#ffeef8; padding:20px; border-radius:12px; border:2px solid #ffd6e9; box-shadow: 0 2px 8px rgba(255, 182, 193, 0.15);">
<h4 style='color:#d63384; margin-top:0;'>🧾 Quick Steps:</h4>
<ol style="font-size:15px; color:#333333; line-height:1.8;">
<li>📸 Upload a <b>clear image of your tongue</b> (avoid filters or edits).</li>
<li>⏰ For best results, take the photo <b>in the morning before brushing, eating, or drinking</b> — this shows your tongue's natural color and coating.</li>
<li>✂️ Crop if needed (keep only the tongue area visible).</li>
<li>🚀 Hit "Analyze My Gut Health" and let the AI work its magic!</li>
</ol>
</div>
""", unsafe_allow_html=True)

# ============================
# 📸 Upload + Crop
# ============================
st.markdown("<br>", unsafe_allow_html=True)
uploaded_file = st.file_uploader("📸 Upload your tongue image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="📂 Your uploaded image", use_container_width=True)

    st.markdown("""
    <h3 style='color:#d63384; margin-top: 30px;'>✂️ Optional: Crop your tongue image</h3>
    <p style='color:#555555; font-style: italic;'>(Focus on the tongue area for best results 👅)</p>
    """, unsafe_allow_html=True)
    
    cropped_img = st_cropper(
        image, 
        realtime_update=True, 
        box_color="#ff007f", 
        aspect_ratio=None
    )

    # Fun analyze button
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_button = st.button("🔍 Analyze My Gut Health (Let's Go!)")

    if analyze_button:
        st.markdown("""
        <h2 style='text-align:center; color:#d63384;'>
            🤖 Analyzing your tongue... 🧘‍♀️🧠
        </h2>
        """, unsafe_allow_html=True)
        
        with st.spinner("Consulting the ancient AI of gut wisdom..."):
            try:
                # Gemini Model - Using correct model name
                model = genai.GenerativeModel("gemini-2.0-flash-exp")

                prompt = """
                    You are a friendly but knowledgeable AI health assistant with a touch of humor. Analyze the provided tongue image and generate a structured report that is informative, accurate, and fun.

                    Your output should include:

                    🩺 Tongue Category:
                    Classify the tongue into one of: healthy, white, yellow, purple, deep red, unusual, or indigo violet. You may add a tiny playful comment like 'looking royal today!' or 'a little mysterious!'.

                    📊 Gut Score (0–100):
                    Estimate a realistic gut health score (integer) based on the tongue's color, texture, and coating. Format it as "XX/100" and include a short, light-hearted sentence explaining why you gave that score. Example: "78/100 – Gut is decent, but it may be plotting a little rebellion!"

                    💬 Tongue Talk – Color & Texture:
                    Describe the tongue's appearance (color, coating, texture, cracks, moisture) in clear, simple language. Keep it friendly and maybe add a fun little observation, e.g., 'smooth like butter' or 'has some character'.

                    🌿 Gut Health Insights:
                    Provide a brief, informative comment about the user's gut health with a sprinkle of humor. Example: "Your gut is generally behaving well, though it might be sneaking a cookie behind your back!"

                    💡 Tips for a Healthier Gut & Tongue:
                    Give 2–3 simple, safe, and practical suggestions to improve tongue and gut health (diet, hydration, lifestyle). You can add light humor like 'drink water like your plants are watching'.

                    Formatting rules:
                    - Use section headings with emojis as shown.
                    - Keep paragraphs short (2–3 lines).
                    - Be friendly, accurate, and encouraging.
                    - Make it fun but not silly; avoid slang or negativity.
                    - Avoid medical jargon that could confuse a normal reader.
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

                # Extract Gut Score using multiple patterns
                gut_score = None
                
                # Pattern 1: XX/100
                gut_score_match = re.search(r'(\d{1,3})\s*/\s*100', result_text)
                if gut_score_match:
                    gut_score = int(gut_score_match.group(1))
                
                # Pattern 2: Score: XX or Score of XX
                if not gut_score:
                    score_match = re.search(r'score[:\s]+(\d{1,3})', result_text, re.IGNORECASE)
                    if score_match:
                        gut_score = int(score_match.group(1))

                # Determine gut status from score or keywords
                if gut_score and 0 <= gut_score <= 100:
                    if gut_score > 85:
                        gut_level = "🌟 Excellent Gut Vibes!"
                    elif gut_score > 60:
                        gut_level = "😎 Balanced but Room to Improve!"
                    else:
                        gut_level = "⚠️ Gut May Need Some Love!"
                else:
                    # Fallback: look for descriptive cues
                    if "excellent" in result_text.lower() or "very healthy" in result_text.lower():
                        gut_level = "🌟 Excellent Gut Vibes!"
                        gut_score = 90
                    elif "healthy" in result_text.lower() or "good" in result_text.lower():
                        gut_level = "😎 Balanced but Room to Improve!"
                        gut_score = 75
                    elif "moderate" in result_text.lower() or "average" in result_text.lower():
                        gut_level = "😎 Balanced but Room to Improve!"
                        gut_score = 65
                    else:
                        gut_level = "⚠️ Gut May Need Some Love!"
                        gut_score = 55

                # Upload to Firebase Storage (silently in background)
                try:
                    img_bytes = io.BytesIO()
                    cropped_img.save(img_bytes, format="PNG")
                    img_bytes.seek(0)

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    blob_path = f"{predicted_category}/{timestamp}_{uploaded_file.name}"
                    blob = bucket.blob(blob_path)
                    blob.upload_from_file(img_bytes, content_type="image/png")
                    # Not making public - privacy first!
                except Exception as fb_error:
                    # Silently log the error but don't show to user
                    print(f"Firebase upload error: {fb_error}")

                # ============================
                # 🎉 Display Results
                # ============================
                st.success(f"✅ Analysis Complete!")

                st.markdown(f"""
                <div style="background-color:rgba(255, 240, 245, 0.95); padding:25px; border-radius:15px; margin-top:25px; border:3px solid #ffb6c1; box-shadow: 0 4px 12px rgba(255,182,193,0.3);">
                    <h3 style='color:#d63384; margin-top:0;'>🧠 Your Gut Health Report</h3>
                    <p style='color:#333333;'><b style='color:#d63384;'>Category:</b> 
                        <span style='font-weight:600; color:#2c2c2c;'>{predicted_category.replace('_', ' ').title()}</span>
                    </p>
                    <p style='color:#333333;'><b style='color:#d63384;'>Gut Health Score:</b> 
                        <span style="font-size:28px; color:#ff1493; font-weight:bold;">{gut_score}/100</span> 🎯
                    </p>
                    <p style='color:#333333;'><b style='color:#d63384;'>Status:</b> 
                        <span style='font-weight:600; color:#2c2c2c;'>{gut_level}</span>
                    </p>
                    <hr style='border-color:#ffb6c1;'>
                    <h4 style='color:#d63384;'>🩺 AI Tongue & Gut Insights:</h4>
                    <div style='color:#1a1a1a; line-height:1.8; font-size:15px;'>{result_text}</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("""
                <div style="background-color:rgba(255, 243, 205, 0.9); padding:20px; border-radius:12px; margin-top:25px; border:2px solid #ffc107;">
                    <h4 style='color:#d63384; margin-top:0;'>⚠️ Important Disclaimer</h4>
                    <p style='color:#1a1a1a; line-height:1.6;'>
                        This is an AI-powered analysis for <b>educational purposes only</b>. 
                        It should not be used as a substitute for professional medical advice, diagnosis, or treatment.
                        <br><br>
                        <b>Always consult a qualified healthcare professional</b> for any health concerns or before making any decisions related to your health.
                    </p>
                </div>
                """, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"💥 Oops! Something went wrong during analysis: {str(e)}")
                st.info("💡 Try uploading a clearer image or check your internet connection.")

else:
    st.markdown("""
    <div style='text-align:center; padding:40px; background-color:rgba(255,255,255,0.6); border-radius:15px; border:2px dashed #ffb6c1; margin-top:20px;'>
        <h3 style='color:#d63384;'>👆 Upload an image to get started!</h3>
        <p style='color:#555555;'>Your tongue analysis awaits... 😊</p>
    </div>
    """, unsafe_allow_html=True)