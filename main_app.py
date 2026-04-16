import streamlit as st
import datetime
import random

# ------------------- PAGE CONFIG -------------------
st.set_page_config(
    page_title="Our Shared Space",
    page_icon="🤝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ------------------- FRIENDLY, CLEAN CSS -------------------
st.markdown("""
<style>
    /* Import clean, friendly fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Poppins:wght@500;700&display=swap');

    /* Overall background - soft neutral */
    .stApp {
        background: linear-gradient(145deg, #f0f4f8 0%, #d9e2ec 100%);
    }

    /* Main content card */
    .main > div {
        padding: 2rem 3rem;
        border-radius: 24px;
        background-color: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(6px);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.5);
    }

    /* Headers */
    h1, h2, h3 {
        font-family: 'Poppins', sans-serif !important;
        color: #1e293b !important;
    }

    h1 {
        font-weight: 700;
    }

    /* Body text */
    body, p, div, .stMarkdown, .stText {
        font-family: 'Inter', sans-serif !important;
        color: #334155;
    }

    /* Buttons */
    .stButton > button {
        background-color: #3b82f6;
        color: white;
        border-radius: 40px;
        border: none;
        padding: 8px 20px;
        font-weight: 500;
        font-family: 'Inter', sans-serif;
        box-shadow: 0 2px 6px rgba(59, 130, 246, 0.2);
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #2563eb;
        transform: translateY(-1px);
        box-shadow: 0 6px 12px rgba(59, 130, 246, 0.25);
    }

    /* Input fields */
    .stTextInput > div > div > input {
        border-radius: 40px;
        border: 1.5px solid #cbd5e1;
        background-color: white;
    }

    /* Checkbox / task items */
    .stCheckbox {
        background-color: #f8fafc;
        padding: 8px 16px;
        border-radius: 40px;
        margin-bottom: 6px;
        border: 1px solid #e2e8f0;
    }

    /* Success / info boxes */
    .stAlert {
        border-radius: 20px;
        background-color: rgba(255,255,255,0.9);
        border-left: 5px solid #3b82f6;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ------------------- HARDCODED CREDENTIALS -------------------
CREDENTIALS = {
    "user": "friendship123",   # Your login
    "maham": "buddies4ever"    # Maham's login (username case-sensitive: maham)
}

# ------------------- SESSION STATE INIT -------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "tasks" not in st.session_state:
    # Shared task list: each task is dict with text, completed, added_by
    st.session_state.tasks = []
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of (sender, text, timestamp)

# ------------------- LOGIN FORM -------------------
def login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🤝 Our Shared Space</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 1.1rem;'>Just for the two of us.</p>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("👤 Username (user / maham)").lower().strip()
            password = st.text_input("🔑 Password", type="password")
            submit = st.form_submit_button("🚪 Enter")
            if submit:
                if username in CREDENTIALS and password == CREDENTIALS[username]:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("❌ Incorrect username or password.")

# ------------------- MAIN APP (AFTER LOGIN) -------------------
def main_app():
    username = st.session_state.username
    display_name = "you" if username == "user" else "Maham"

    # Sidebar with user info and logout
    with st.sidebar:
        st.markdown(f"### 👋 Hello, {display_name}!")
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
        st.markdown("---")
        st.markdown("⭐ *Good friends are like stars. You don't always see them, but you know they're there.*")

    # Welcome message
    if username == "maham":
        st.markdown("<h2 style='text-align: center;'>👋 Hey Maham! Great to see you here.</h2>", unsafe_allow_html=True)
    else:
        st.markdown("<h2 style='text-align: center;'>👋 Welcome back! Ready for another good day?</h2>", unsafe_allow_html=True)

    st.markdown("---")

    # ---------- FEATURE 1: SHARED TO-DO LIST ----------
    st.markdown("### ✅ Our Shared To‑Do List")
    st.caption("Add tasks, check them off. We both see the same list.")

    # Display existing tasks
    if st.session_state.tasks:
        for i, task in enumerate(st.session_state.tasks):
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                checked = st.checkbox("", value=task["completed"], key=f"task_{i}", label_visibility="collapsed")
                if checked != task["completed"]:
                    st.session_state.tasks[i]["completed"] = checked
                    st.rerun()
            with col2:
                added_by = " (you)" if task["added_by"] == username else " (Maham)"
                if task["completed"]:
                    st.markdown(f"<span style='text-decoration: line-through; color: #64748b;'>{task['text']}{added_by}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"{task['text']}<span style='font-size:0.8rem; color: #64748b;'>{added_by}</span>", unsafe_allow_html=True)
    else:
        st.info("No tasks yet. Add one below!")

    # Add new task
    with st.form("add_task_form", clear_on_submit=True):
        new_task = st.text_input("➕ New task...", placeholder="e.g., Plan weekend hangout")
        submitted = st.form_submit_button("Add Task")
        if submitted and new_task.strip():
            st.session_state.tasks.append({
                "text": new_task.strip(),
                "completed": False,
                "added_by": username
            })
            st.rerun()

    # Option to clear completed tasks
    if st.button("🧹 Clear completed tasks"):
        st.session_state.tasks = [t for t in st.session_state.tasks if not t["completed"]]
        st.rerun()

    st.markdown("---")

    # ---------- FEATURE 2: FRIEND NOTES (MESSAGE BOARD) ----------
    st.markdown("### 💬 Notes for Each Other")
    st.caption("Leave a quick message. It stays here until you delete it.")

    # Display messages
    if st.session_state.messages:
        for msg in reversed(st.session_state.messages[-10:]):  # Show last 10
            sender_display = "You" if msg["sender"] == username else "Maham"
            time_str = msg["timestamp"].strftime("%b %d, %I:%M %p")
            st.markdown(f"""
            <div style='background: #e2e8f0; padding: 12px 18px; border-radius: 20px; margin-bottom: 10px;'>
                <span style='font-weight: 600;'>{sender_display}</span> <span style='font-size:0.8rem; color: #475569;'>({time_str})</span><br>
                <span>{msg["text"]}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No messages yet. Say hi!")

    # Send new message
    with st.form("message_form", clear_on_submit=True):
        msg_text = st.text_input("✏️ Write a note...", placeholder="Hey, want to grab coffee tomorrow?")
        send = st.form_submit_button("Send")
        if send and msg_text.strip():
            st.session_state.messages.append({
                "sender": username,
                "text": msg_text.strip(),
                "timestamp": datetime.datetime.now()
            })
            st.rerun()

    st.markdown("---")

    # ---------- FEATURE 3: DAILY QUOTE / FUN FACT ----------
    st.markdown("### 🌟 Today's Spark")
    quotes = [
        "Friendship is the only cement that will ever hold the world together. – Woodrow Wilson",
        "A real friend is one who walks in when the rest of the world walks out. – Walter Winchell",
        "Good friends are hard to find, harder to leave, and impossible to forget.",
        "Friends are the family we choose for ourselves.",
        "There's nothing better than a friend, unless it's a friend with chocolate.",
        "Life was meant for good friends and great adventures.",
        "A friend is someone who knows all about you and still loves you. – Elbert Hubbard",
        "True friends are never apart, maybe in distance but never in heart.",
    ]
    if st.button("🎲 Show me something"):
        quote = random.choice(quotes)
        st.markdown(f"""
        <div style='background: #dbeafe; padding: 20px; border-radius: 20px; text-align: center; margin: 15px 0;'>
            <span style='font-size: 1.3rem;'>“{quote}”</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("<p style='color: #64748b;'>Click the button for a friendly thought.</p>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<p style='text-align: center; opacity: 0.7;'>Built for two friends. 👯</p>", unsafe_allow_html=True)

# ------------------- APP FLOW -------------------
if st.session_state.logged_in:
    main_app()
else:
    login()