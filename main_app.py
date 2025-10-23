import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from utils.database import init_db, get_tasks
from utils.helpers import get_color_by_priority, get_status_emoji, format_date
from utils.auth import create_default_users
from utils.notifications import get_unread_notifications, mark_notification_as_read
import base64
import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Page configuration
st.set_page_config(
    page_title="TaskFlow Pro - Burtch Team",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    try:
        # Try to load from assets folder
        css_path = os.path.join(os.path.dirname(__file__), 'assets', 'style.css')
        if os.path.exists(css_path):
            with open(css_path) as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        else:
            # Fallback to inline CSS
            st.markdown("""
            <style>
            .login-container {
                background: white;
                padding: 3rem;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                margin-top: 2rem;
                text-align: center;
            }
            .login-title {
                color: #1f77b4;
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 0.5rem;
            }
            .login-subtitle {
                color: #666;
                font-size: 1.1rem;
                margin-bottom: 2rem;
            }
            .user-header {
                display: flex;
                align-items: center;
                padding: 1rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 10px;
                color: white;
                margin-bottom: 1rem;
            }
            .user-avatar {
                width: 50px;
                height: 50px;
                border-radius: 50%;
                background: rgba(255,255,255,0.2);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5rem;
                font-weight: bold;
                margin-right: 1rem;
            }
            .user-name {
                font-weight: bold;
                font-size: 1.1rem;
            }
            .user-role {
                font-size: 0.9rem;
                opacity: 0.9;
            }
            .task-card {
                background: white;
                border-radius: 10px;
                padding: 1.5rem;
                margin: 0.5rem 0;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                border-left: 4px solid #1f77b4;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            .task-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 20px rgba(0,0,0,0.12);
            }
            .task-card-high {
                border-left-color: #ff6b6b;
            }
            .task-card-medium {
                border-left-color: #ffd93d;
            }
            .task-card-low {
                border-left-color: #6bcf7f;
            }
            .priority-badge {
                padding: 0.25rem 0.75rem;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 600;
                text-transform: uppercase;
            }
            .priority-high {
                background-color: #ff6b6b;
                color: white;
            }
            .priority-medium {
                background-color: #ffd93d;
                color: #333;
            }
            .priority-low {
                background-color: #6bcf7f;
                color: white;
            }
            .status-indicator {
                display: inline-flex;
                align-items: center;
                padding: 0.3rem 0.8rem;
                border-radius: 15px;
                font-size: 0.8rem;
                font-weight: 600;
            }
            .status-pending {
                background-color: #fff3cd;
                color: #856404;
            }
            .status-in-progress {
                background-color: #cce7ff;
                color: #004085;
            }
            .status-completed {
                background-color: #d4edda;
                color: #155724;
            }
            .status-on-hold {
                background-color: #e2e3e5;
                color: #383d41;
            }
            .metric-card {
                background: white;
                border-radius: 10px;
                padding: 1.5rem;
                text-align: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                border-top: 4px solid #1f77b4;
            }
            </style>
            """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"CSS loading error: {e}")

def main():
    # Initialize database
    try:
        init_db()
        create_default_users()
    except Exception as e:
        st.error(f"Database initialization error: {e}")
    
    load_css()
    
    # User authentication
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.user_type = None
        st.session_state.user_id = None
        st.session_state.user_email = None
    
    if not st.session_state.authenticated:
        show_login_screen()
        return
    
    # Main app after authentication
    show_main_application()

def show_login_screen():
    """Display login screen with branding"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        st.markdown("<h1 class='login-title'>TaskFlow Pro</h1>", unsafe_allow_html=True)
        st.markdown("<p class='login-subtitle'>Burtch Team Task Management System</p>", unsafe_allow_html=True)
        
        # Quick login buttons
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("🚀 Continue as Luke Wise", use_container_width=True, key="luke_quick"):
                st.session_state.login_user = "luke@theburtchteam.com"
                st.session_state.login_pass = "LukeWise2024!"
                st.rerun()
        
        with col_b:
            if st.button("🏢 Continue as Burtch Team", use_container_width=True, key="burtch_quick"):
                st.session_state.login_user = "client@theburtchteam.com"
                st.session_state.login_pass = "BurtchTeam2024!"
                st.rerun()
        
        # Manual login form
        with st.form("login_form"):
            st.subheader("Manual Login")
            username = st.text_input("Email", value=st.session_state.get('login_user', ''))
            password = st.text_input("Password", type="password", value=st.session_state.get('login_pass', ''))
            remember_me = st.checkbox("Remember me")
            
            if st.form_submit_button("🔐 Login", use_container_width=True):
                from utils.auth import authenticate_user
                user_data = authenticate_user(username, password)
                if user_data:
                    st.session_state.authenticated = True
                    st.session_state.user = user_data['name']
                    st.session_state.user_id = user_data['id']
                    st.session_state.user_type = user_data['type']
                    st.session_state.user_email = user_data['email']
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials. Please try again.")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Demo credentials
        with st.expander("Demo Credentials"):
            st.write("**Luke Wise (Team - Full Access)**")
            st.code("Email: luke@theburtchteam.com\nPassword: LukeWise2024!")
            st.write("**Burtch Team (Client - Limited Access)**")
            st.code("Email: client@theburtchteam.com\nPassword: BurtchTeam2024!")

def show_main_application():
    """Display the main application after login"""
    
    # Sidebar header with user info
    st.sidebar.markdown(f"""
    <div class="user-header">
        <div class="user-avatar">{st.session_state.user[0] if st.session_state.user else 'U'}</div>
        <div class="user-info">
            <div class="user-name">{st.session_state.user}</div>
            <div class="user-role">{st.session_state.user_type.title() if st.session_state.user_type else 'User'}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    
    # Navigation based on user type
    if st.session_state.user_type == "team":
        pages = {
            "📊 Dashboard": "1_Dashboard",
            "📝 Task Management": "2_Task_Management", 
            "📅 Calendar & Timeline": "3_Calendar_View",
            "👥 Team Collaboration": "4_Team_Collaboration",
            "⏰ Time Tracking": "6_Time_Tracking",
            "📈 Analytics & Reports": "5_Analytics_Reports",
            "⚙️ Settings": "7_Settings"
        }
    else:  # client
        pages = {
            "📊 Dashboard": "1_Dashboard",
            "📅 Calendar View": "3_Calendar_View", 
            "📈 Project Reports": "5_Analytics_Reports"
        }
    
    # Navigation
    selection = st.sidebar.radio("Navigate to:", list(pages.keys()))
    
    # Quick stats in sidebar
    display_sidebar_stats()
    
    # Notifications bell
    display_notifications()
    
    # Display selected page
    try:
        # Import and run the selected page
        if selection == "📊 Dashboard":
            from pages.dashboard import app
            app()
        elif selection == "📝 Task Management":
            from pages.task_management import app
            app()
        elif selection == "📅 Calendar & Timeline":
            from pages.calendar_view import app
            app()
        elif selection == "👥 Team Collaboration":
            from pages.team_collaboration import app
            app()
        elif selection == "⏰ Time Tracking":
            from pages.time_tracking import app
            app()
        elif selection == "📈 Analytics & Reports":
            from pages.analytics_reports import app
            app()
        elif selection == "⚙️ Settings":
            from pages.settings import app
            app()
    except Exception as e:
        st.error(f"Error loading page {selection}: {e}")
        st.info("Please try refreshing the page or contact support.")

def display_sidebar_stats():
    """Display quick stats in sidebar"""
    st.sidebar.markdown("---")
    today = datetime.now().date()
    st.sidebar.markdown(f"**📅 Today:** {today.strftime('%A, %B %d, %Y')}")
    
    # Quick stats
    try:
        tasks = get_tasks()
        if tasks:
            df = pd.DataFrame(tasks)
            
            col1, col2 = st.sidebar.columns(2)
            with col1:
                pending = len(df[df['status'] == 'Pending'])
                st.metric("⏳ Pending", pending)
            with col2:
                in_progress = len(df[df['status'] == 'In Progress'])
                st.metric("🔄 In Progress", in_progress)
            
            col3, col4 = st.sidebar.columns(2)
            with col3:
                overdue = len(df[(df['due_date'] < datetime.now().strftime('%Y-%m-%d')) & (df['status'] != 'Completed')])
                st.metric("🚨 Overdue", overdue, delta=None)
            with col4:
                completed_today = len(df[(df['status'] == 'Completed') & (pd.to_datetime(df['completed_date']).dt.date == today)])
                st.metric("✅ Today", completed_today)
    except Exception as e:
        st.sidebar.error("Error loading stats")

def display_notifications():
    """Display notifications in sidebar"""
    try:
        notifications = get_unread_notifications(st.session_state.user_id)
        if notifications:
            st.sidebar.markdown("---")
            with st.sidebar.expander(f"🔔 Notifications ({len(notifications)})", expanded=False):
                for notification in notifications[:5]:  # Show last 5
                    st.write(f"**{notification['title']}**")
                    st.caption(f"{format_date(notification['created_date'])}")
                    if st.button("Mark as read", key=f"read_{notification['id']}"):
                        mark_notification_as_read(notification['id'])
                        st.rerun()
    except Exception as e:
        st.sidebar.error("Error loading notifications")

    # Logout button
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

if __name__ == "__main__":
    main()
