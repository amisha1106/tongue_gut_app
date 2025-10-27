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
        <p style='text-align:center; font-size:14px; color:#d63384; margin-top:10px;'>
        <b>💡 Pro Tip:</b> Challenge your friends to see who has the healthiest gut! 🏆
        </p>
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
        You are a professional AI tongue health analyst with a fun personality.
        Analyze this tongue image and respond EXACTLY in this format:

        Category: [one of: healthy, white, yellow, purple, deep red, indigo violet, unusual]
        Confidence: [number between 0-100]
        Key Observations: [1-2 lines on color, coating, cracks, and moisture]
        Gut Health Score: [number between 0-100]
        Insights: [brief friendly message with light humor]
        Tips: [2-3 short, witty suggestions - make them fun but helpful!]

        Be consistent with the format and add personality to make it engaging!
        """
        resp1 = model.generate_content([main_prompt, cropped_img])
        text1 = resp1.text.strip()

        # 🧹 Step 1: Standardize section headings
        # 🧹 Step 1: Standardize section headings
        text1 = re.sub(r'(?i)(?<=Category)[:\-]?', ':', text1)
        text1 = re.sub(r'(?i)(?<=Confidence)[:\-]?', ':', text1)
        text1 = re.sub(r'(?i)(?<=Key Observations)[:\-]?', ':', text1)
        text1 = re.sub(r'(?i)(?<=Gut Health Score)[:\-]?', ':', text1)
        text1 = re.sub(r'(?i)(?<=Insights)[:\-]?', ':', text1)
        text1 = re.sub(r'(?i)(?<=Tips)[:\-]?', ':', text1)
        
        # ✨ Step 2: Insert section headers with emojis
        text1 = re.sub(r'(?i)\s*(Category:)', r'\n\n🩺 \1', text1)
        text1 = re.sub(r'(?i)\s*(Confidence:)', r'\n\n🩺 \1', text1)
        text1 = re.sub(r'(?i)\s*(Key Observations:)', r'\n\n🩺 \1', text1)
        text1 = re.sub(r'(?i)\s*(Gut Health Score:)', r'\n\n🩺 \1', text1)
        text1 = re.sub(r'(?i)\s*(Insights:)', r'\n\n💡 \1', text1)
        text1 = re.sub(r'(?i)\s*(Tips:)', r'\n\n🌿 \1', text1)
        
        # 🌿 Step 3: Format bullets cleanly (contextual emojis + clean spacing)
        def add_contextual_emoji(bullet_text):
            """Add relevant emoji depending on keyword"""
            t = bullet_text.lower()
            if "tongue" in t or "brush" in t or "scrape" in t:
                emoji = "🪥"
            elif "probiotic" in t or "gut" in t:
                emoji = "🧫"
            elif "drink" in t or "water" in t or "hydrate" in t:
                emoji = "💧"
            else:
                emoji = "🌸"
            return f"    {emoji} {bullet_text.strip()}"
        
        # Normalize list markers
        text1 = re.sub(r'[\*•]+\s*', r'\n• ', text1)
        text1 = re.sub(r'(?i)(\d+\.\s*)', r'\n• ', text1)
        text1 = re.sub(r'(\n\s*•\s*){2,}', r'\n• ', text1)
        
        # Split and format lines
        lines = text1.split("\n")
        formatted_lines = []
        tips_section = False
        
        for line in lines:
            if re.search(r'(?i)🌿\s*Tips:', line):
                tips_section = True
                formatted_lines.append(line)
                continue
        
            if line.strip().startswith("•"):
                formatted_lines.append(add_contextual_emoji(line.replace("•", "").strip()))
            else:
                formatted_lines.append(line)
        
        text1 = "\n".join(formatted_lines)
        
        # 🧾 Step 4: Remove stray HTML safely
        text1 = re.sub(r'<[^>]+>', '', text1)
        
        # 🧼 Step 5: Final cleanup
        text1 = re.sub(r'\n{3,}', '\n\n', text1).strip()
        
        # 🚫 Step 6: Remove duplicate summary lines
        text1 = re.sub(r'🩺\s*Category:[^\n]*', '', text1)
        text1 = re.sub(r'🩺\s*Confidence:[^\n]*', '', text1)
        text1 = re.sub(r'🩺\s*Gut Health Score:[^\n]*', '', text1)
        text1 = re.sub(r'\n{2,}', '\n\n', text1).strip()
        
        # ✅ FINAL CLEANUP: aggressively remove all leftover HTML tags + invisible Unicode
        text1 = re.sub(r'<[^>]*>', '', text1)  # remove any tag like <div>, </div>, <p>, etc.
        text1 = re.sub(r'&nbsp;|&lt;|&gt;|&amp;', '', text1)  # remove HTML entities
        text1 = re.sub(r'[\u200b\u200c\u200d\uFEFF\xa0]', '', text1)  # remove invisible chars
        text1 = text1.strip()



        # ---------- Stage 4: Extract values with improved regex ----------
        # Extract confidence
        conf = re.search(r'(?:confidence|Confidence)[:\s]+(\d{1,3})', text1, re.IGNORECASE)
        conf_val = int(conf.group(1)) if conf else 75

        # Check for low confidence and refine if needed
        if conf_val < 75 or "uncertain" in text1.lower():
            refine_prompt = main_prompt + "\nYou seemed uncertain before. Re-analyze carefully with higher confidence and ensure consistency."
            resp2 = model.generate_content([refine_prompt, cropped_img])
            text2 = resp2.text.strip()
            conf2 = re.search(r'(?:confidence|Confidence)[:\s]+(\d{1,3})', text2, re.IGNORECASE)
            conf_val2 = int(conf2.group(1)) if conf2 else 75
            if conf_val2 > conf_val:
                text1 = text2
                conf_val = conf_val2

        # Extract category
        categories = ["healthy", "white", "yellow", "purple", "deep red", "indigo violet", "unusual"]
        cat = "unclassified"
        cat_match = re.search(r'(?:category|Category)[:\s]+([^\n]+)', text1, re.IGNORECASE)
        if cat_match:
            cat_text = cat_match.group(1).lower().strip()
            for c in categories:
                if c in cat_text:
                    cat = c.replace(" ", "_")
                    break

        # Extract gut score
        gut_score = None
        # Try multiple patterns
        m = re.search(r'(?:gut health score|Gut Health Score)[:\s]+(\d{1,3})', text1, re.IGNORECASE)
        if m:
            gut_score = int(m.group(1))
        else:
            m2 = re.search(r'(\d{1,3})\s*/\s*100', text1)
            if m2:
                gut_score = int(m2.group(1))

        if gut_score is None or not (0 <= gut_score <= 100):
            gut_score = 65

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

        # ---------- Stage 6: Determine rank and badge ----------
        if gut_score >= 90:
            rank = "Gut Guru 🧘‍♀️"
            badge = "🏆"
            message = "You're basically a gut health superhero!"
        elif gut_score >= 80:
            rank = "Digestive Champion 💪"
            badge = "🥇"
            message = "Your gut game is strong! Keep it up!"
        elif gut_score >= 70:
            rank = "Gut Guardian 🛡️"
            badge = "🥈"
            message = "You're on the right track! A little more TLC needed."
        elif gut_score >= 60:
            rank = "Belly Buddy 🤝"
            badge = "🥉"
            message = "Your gut needs some extra love and care."
        elif gut_score >= 50:
            rank = "Tummy Trainee 📚"
            badge = "🎖️"
            message = "Time to level up your gut health game!"
        else:
            rank = "Gut Newbie 🌱"
            badge = "⭐"
            message = "Don't worry, every expert was once a beginner!"

        gut_level = (
            "🌟 Excellent Gut Vibes!"
            if gut_score > 85
            else ("😎 Balanced but Room to Improve!" if gut_score > 60 else "⚠️ Gut May Need Some Love!")
        )

        # ---------- Stage 7: Display results with scorecard ----------
        st.success("✅ Analysis Complete!")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(
                f"""
                <div style="background-color:rgba(255,240,245,0.95);padding:20px;border-radius:15px;border:3px solid #ffb6c1;">
                <h3 style='color:#d63384;'>🧠 Your Gut Health Report</h3>
                <p style='color:#000;'><b>Category:</b> {cat.replace('_',' ').title()}</p>
                <p style='color:#000;'><b>Confidence:</b> {conf_val}%</p>
                <p style='color:#000;'><b>Gut Score:</b> {gut_score}/100</p>
                <p style='color:#000;'><b>Status:</b> {gut_level}</p>
                <hr>
                <div style='color:#333;'>{text1}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        with col2:
            st.markdown(
                f"""
                <div style="background-color:#fff0f6;padding:20px;border-radius:15px;border:3px solid #ffb6c1;text-align:center;">
                <h2 style='color:#d63384; margin-top:0;'>🏅 Your Rank</h2>
                <div style='font-size:60px; margin:10px 0;'>{badge}</div>
                <h3 style='color:#d63384; margin:10px 0;'>{rank}</h3>
                <p style='color:#333; font-size:14px;'>{message}</p>
                <hr style='border:1px solid #ffd6e9;'>
                <div style='background: linear-gradient(90deg, #d63384, #ff69b4); color:white; padding:10px; border-radius:8px; margin-top:15px;'>
                <b style='font-size:24px;'>{gut_score}</b><br>
                <span style='font-size:12px;'>POINTS</span>
                </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        # ---------- Stage 8: Share and compare section ----------
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="background-color:#ffeef8; padding:20px; border-radius:12px; border:2px solid #ffd6e9; text-align:center;">
            <h4 style='color:#d63384; margin-top:0;'>🎯 Challenge Your Squad!</h4>
            <p style='color:#333; font-size:15px;'>
            You scored <b style='color:#d63384;'>{gut_score}/100</b>! 
            Think your friends can beat that? Share this app and start a gut health competition! 🏆
            </p>
            <p style='color:#666; font-size:13px; margin-top:10px;'>
            💡 <i>Pro tip: The person with the lowest score buys dinner... preferably something probiotic-rich! 😄</i>
            </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

else:
    st.info("👆 Upload a clear tongue image to start the analysis.")











