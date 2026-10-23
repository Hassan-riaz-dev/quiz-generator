import json
import os

import streamlit as st
from groq import Groq

# ---------- Page config ----------
st.set_page_config(page_title="AI Quiz Generator", page_icon="🧠", layout="centered")

# ---------- Black theme (CSS) ----------
st.markdown(
    """
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #0d0d0d; }
    h1, h2, h3, h4, p, label, span, div { color: #FFFFFF; }
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #1a1a1a !important; color: #FFFFFF !important;
    }
    .stButton > button {
        background-color: #00C853; color: #000000; font-weight: 700;
        border: none; border-radius: 8px; padding: 0.5rem 1.2rem;
    }
    .stButton > button:hover { background-color: #00E676; color: #000000; }
    .q-card {
        background-color: #111111; border: 1px solid #2a2a2a;
        border-radius: 12px; padding: 14px 18px; margin-top: 18px;
    }
    .correct { color: #00E676; font-weight: 600; }
    .wrong { color: #FF5252; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

MODEL = "openai/gpt-oss-120b"


# ---------- Helpers ----------
def get_api_key() -> str:
    """Key priority: Streamlit secrets -> environment variable -> sidebar input."""
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY", "")


def generate_quiz(api_key: str, topic: str, num_q: int, difficulty: str) -> list:
    client = Groq(api_key=api_key)

    system_prompt = (
        "You are a quiz generator. Reply ONLY with valid JSON in this exact format:\n"
        '{"questions": [{"question": "...", "options": ["A text", "B text", "C text", "D text"], '
        '"answer_index": 0, "hint": "a short helpful hint that does NOT reveal the answer", '
        '"explanation": "one or two lines explaining the correct answer"}]}\n'
        "Rules: exactly 4 options per question, answer_index is 0-3, no extra text."
    )
    user_prompt = (
        f"Create {num_q} multiple choice questions on the topic: {topic}. "
        f"Difficulty: {difficulty}."
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    return data["questions"]


# ---------- UI ----------
st.title("🧠 AI Quiz Generator")
st.caption("Topic likho, quiz banao, hints lo, aur end pe answers dekho.")

with st.sidebar:
    st.header("⚙️ Settings")
    api_key = get_api_key()
    if not api_key:
        api_key = st.text_input("Groq API Key", type="password")
    else:
        st.success("API key loaded ✅")
    num_q = st.slider("Number of questions", 3, 15, 5)
    difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"], index=1)

topic = st.text_input("Quiz topic / prompt", placeholder="e.g. Python basics, Pakistan history, Machine Learning")

if st.button("Generate Quiz 🚀"):
    if not api_key:
        st.error("Pehle Groq API key daalo (sidebar mein).")
    elif not topic.strip():
        st.warning("Topic likho pehle.")
    else:
        with st.spinner("Quiz ban raha hai..."):
            try:
                st.session_state.quiz = generate_quiz(api_key, topic, num_q, difficulty)
                st.session_state.submitted = False
                # purane answers clear karo
                for k in [k for k in st.session_state if k.startswith("q_")]:
                    del st.session_state[k]
            except Exception as e:
                st.error(f"Error: {e}")

quiz = st.session_state.get("quiz")

if quiz:
    for i, q in enumerate(quiz):
        st.markdown(f'<div class="q-card"><b>Q{i + 1}. {q["question"]}</b></div>', unsafe_allow_html=True)
        with st.expander("💡 Hint"):
            st.write(q.get("hint", "No hint available."))
        st.radio(
            "Choose your answer:",
            q["options"],
            index=None,
            key=f"q_{i}",
            disabled=st.session_state.get("submitted", False),
        )

    if not st.session_state.get("submitted", False):
        if st.button("Submit Quiz ✅"):
            st.session_state.submitted = True
            st.rerun()

    # ---------- Results + answers at the end ----------
    if st.session_state.get("submitted", False):
        score = 0
        st.markdown("---")
        st.header("📊 Results & Answers")

        for i, q in enumerate(quiz):
            correct = q["options"][q["answer_index"]]
            chosen = st.session_state.get(f"q_{i}")
            is_right = chosen == correct
            score += int(is_right)

            st.markdown(f"**Q{i + 1}. {q['question']}**")
            if is_right:
                st.markdown(f'<span class="correct">✔ Your answer: {chosen}</span>', unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<span class="wrong">✘ Your answer: {chosen or "Not answered"}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(f'<span class="correct">Correct answer: {correct}</span>', unsafe_allow_html=True)
            st.caption(f"📘 {q.get('explanation', '')}")

        st.subheader(f"🏆 Score: {score} / {len(quiz)}")
        if score == len(quiz):
            st.balloons()

        if st.button("🔄 New Quiz"):
            st.session_state.quiz = None
            st.session_state.submitted = False
            st.rerun()
