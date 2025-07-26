# app.py
import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

# --- Configuration ---
# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# Configure the generative AI model
# Add a check to ensure the app doesn't crash if the API key is missing
try:
    if API_KEY:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        model = None
except Exception as e:
    st.error(f"Error configuring Generative AI: {e}")
    model = None
    st.stop()

# --- Helper Functions ---
def get_pdf_text(pdf_file):
    """Extracts text from an uploaded PDF file."""
    try:
        # Open the PDF file from the uploaded bytes
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text += page.get_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF file: {e}")
        return None

def get_gemini_response(resume_text, jd_text):
    """Generates a response from the Gemini model based on a prompt."""
    
    # The detailed prompt instructing the AI
    prompt = f"""
    You are an expert AI Career Advisor. Your task is to analyze a candidate's resume against a job description and provide a detailed, structured analysis in JSON format.

    **Resume Text:**
    ---
    {resume_text}
    ---

    **Job Description Text:**
    ---
    {jd_text}
    ---

    **Instructions:**
    1.  **Analyze Both Documents:** Carefully read the resume to understand the candidate's skills, experience, and education. Read the job description to identify the key requirements, responsibilities, and desired qualifications.
    2.  **Calculate Match Score:** Provide a "match_score" from 0 to 100, representing how well the resume aligns with the job description. A higher score means a better match.
    3.  **Summarize Candidate Profile:** Write a brief "candidate_summary" of the candidate's profile in relation to the job.
    4.  **Identify Skill Gaps:** Create a list of "missing_skills". Each item in the list should be an object with the skill name, its importance (High, Medium, Low), and an explanation of why it's needed for the job.
    5.  **Provide Resume Recommendations:** Offer specific, actionable "resume_recommendations" to improve the resume's alignment with the job description.
    6.  **Give Career Advice:** Provide personalized "career_advice" to help the candidate bridge any gaps and be a better fit for this or similar roles.
    7.  **Overall Feedback:** Give a concluding "feedback" statement.

    **Output Format:**
    Return ONLY a valid JSON object with the following structure. Do not include any other text or markdown formatting before or after the JSON.
    {{
      "match_score": <number>,
      "candidate_summary": "<string>",
      "missing_skills": [
        {{
          "skill": "<string>",
          "importance": "<High/Medium/Low>",
          "explanation": "<string>"
        }}
      ],
      "resume_recommendations": ["<string>", "<string>", ...],
      "career_advice": "<string>",
      "feedback": "<string>"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean up the response to ensure it's valid JSON
        # The model sometimes wraps the JSON in ```json ... ```
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_response)
    except Exception as e:
        st.error(f"An error occurred while communicating with the AI model: {e}")
        raw_response_text = "No response received"
        if 'response' in locals() and hasattr(response, 'text'):
            raw_response_text = response.text
        st.error(f"Raw AI Response that caused error:\n{raw_response_text}")
        return None

# --- Streamlit App UI ---
st.set_page_config(page_title="AI Career Advisor", layout="wide")

# Custom CSS for a clean, professional, high-contrast UI
st.markdown("""
<style>
    /* General App Background */
    .stApp {
        background-color: #1e1e2f;
        color: #f5f5f5;
    }

    /* Content Area */
    .st-emotion-cache-1y4p8pa {
        max-width: 1100px;
        padding: 2rem 3rem;
        color: #f5f5f5;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
    }

    /* Paragraphs and Text */
    .stMarkdown, .st-emotion-cache-16idsys p {
        color: #e0e0e0 !important;
    }

    .stTextArea textarea {
    border: 1px solid #555;
    border-radius: 8px;
    background-color: #2a2a3b;
    color: #f5f5f5;
    caret-color: #00ffe7 !important; /* Neon-ish cyan caret for visibility */
}

    /* Placeholder text */
    textarea::placeholder {
        color: #00b4d8 !important;
        opacity: 0.7;
    }

    /* Cursor visibility on focus */
    .stTextArea textarea:focus {
        outline: none !important;
        border-color: #00b4d8 !important;
        box-shadow: 0 0 5px #00b4d8;
    }

    /* Loading (waiting) cursor when busy */
    body:has(.stSpinner) {
        cursor: wait !important;
    }

    /* Buttons */
    .stButton>button {
        background-color: #0077b6;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 12px 25px;
        transition: background-color 0.3s ease;
        box-shadow: 0 4px 14px rgba(0, 119, 182, 0.4);
    }

    .stButton>button:hover {
        background-color: #023e8a;
    }

    /* Metric Styling */
    .stMetric {
        background-color: #2c2c3c;
        border-left: 5px solid #00b4d8;
        padding: 1.2rem;
        border-radius: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.4);
    }

    .stMetric [data-testid="stMetricValue"] {
        color: #f5f5f5 !important;
    }

    .stMetric [data-testid="stMetricLabel"] {
        color: #a0aec0 !important;
    }

    /* Alert Boxes */
    .stAlert {
        border-radius: 8px;
        border-width: 1px;
        border-style: solid;
        padding: 1rem;
    }

    /* Warnings - Missing Skills */
    .st-emotion-cache-l99sz1 {
        background-color: #3b2f1e;
        border-color: #facc15;
        color: #ffe58f !important;
    }

    /* Info - Career Advice */
    .st-emotion-cache-j6nner {
        background-color: #1e3a8a;
        border-color: #60a5fa;
        color: #dbeafe !important;
    }

    /* Success - Feedback */
    .st-emotion-cache-ocqkz7 {
        background-color: #14532d;
        border-color: #4ade80;
        color: #d1fae5 !important;
    }

    /* Expander JSON Box */
    .st-expander {
        background-color: #2a2a3b !important;
        color: #f5f5f5 !important;
        border: 1px solid #444;
    }
</style>
""", unsafe_allow_html=True)



st.title("🤖 AI Career Advisor")
st.write("Get a professional analysis of your resume. Upload your resume, paste the job description, and let the AI do the rest!")

# Check if API key is configured
if not API_KEY or not model:
    st.error("🔴 API Key not found or invalid! Please create a .env file in the same folder with your GOOGLE_API_KEY.")
    st.info("Example .env file content:\nGOOGLE_API_KEY=\"Your-Key-Here\"")
    st.stop()

# Layout with columns
col1, col2 = st.columns(2, gap="large")

with col1:
    st.header("📄 Your Resume")
    uploaded_resume = st.file_uploader("Upload your resume (PDF only)", type="pdf", label_visibility="collapsed")

with col2:
    st.header("📋 Job Description")
    job_description = st.text_area(
        "Paste the job description here", 
        height=320, 
        label_visibility="collapsed", 
        placeholder="Paste the job description here"
    )

# Analyze button
if st.button("Analyze ✨"):
    if uploaded_resume is not None and job_description:
        with st.spinner("Analyzing your documents... This may take a moment."):
            # Extract text from documents
            resume_text = get_pdf_text(uploaded_resume)
            
            if resume_text:
                # Get analysis from Gemini
                analysis_result = get_gemini_response(resume_text, job_description)

                if analysis_result:
                    st.success("Analysis Complete!")
                    st.balloons()

                    st.header("📊 Analysis Report")

                    # Match Score Metric
                    st.metric(
                        label="Resume Match Score",
                        value=f"{analysis_result.get('match_score', 'N/A')}%",
                        help="This score represents the alignment of your resume with the job description."
                    )
                    
                    st.subheader("👤 Candidate Summary")
                    st.write(analysis_result.get('candidate_summary', 'Not available.'))

                    st.subheader("⚠️ Missing Skills")
                    missing_skills = analysis_result.get('missing_skills', [])
                    if missing_skills:
                        for skill in missing_skills:
                            st.warning(f"**{skill.get('skill')}** ({skill.get('importance')} Importance): {skill.get('explanation')}")
                    else:
                        st.info("No significant skill gaps identified. Your skills are a great match!")

                    st.subheader("📝 Resume Recommendations")
                    recommendations = analysis_result.get('resume_recommendations', [])
                    if recommendations:
                        for rec in recommendations:
                            st.markdown(f"- {rec}")
                    
                    st.subheader("🚀 Career Advice")
                    st.info(analysis_result.get('career_advice', 'Not available.'))

                    st.subheader("💬 Overall Feedback")
                    st.success(analysis_result.get('feedback', 'Not available.'))

                    # Show the raw JSON response in an expander
                    with st.expander("Show Raw JSON Output"):
                        st.json(analysis_result)
    else:
        st.error("Please upload a resume and paste a job description to proceed.")
