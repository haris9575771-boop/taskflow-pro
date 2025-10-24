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
    initial_sidebar_state="collapsed"  # Start with collapsed sidebar
)

# Load custom CSS
def load_css():
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
    .main-header {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #1f77b4 0%, #2e8bc0 100%);
        color: white;
        margin-bottom: 2rem;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    # Initialize database
    try:
        init_db()
        create_default_users()
    except Exception as e:
        st.error(f"Database initialization error: {e}")
    
    load_css()
    
    # User authentication state
    if 'user_selected' not in st.session_state:
        st.session_state.user_selected = False
        st.session_state.user = None
        st.session_state.user_type = None
        st.session_state.user_id = None
        st.session_state.user_email = None
    
    if not st.session_state.user_selected:
        show_user_selection()
        return
    
    # Main app after user selection
    show_main_application()

def show_user_selection():
    """Display user selection screen"""
    st.markdown("""
    <div class="main-header">
        <h1>TaskFlow Pro</h1>
        <p>Burtch Team Task Management System</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        st.markdown("<h2 class='login-title'>Select Your Role</h2>", unsafe_allow_html=True)
        st.markdown("<p class='login-subtitle'>Choose how you want to access the system</p>", unsafe_allow_html=True)
        
        # User selection buttons
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("Continue as Luke Wise", use_container_width=True, key="luke"):
                set_user_session("Luke Wise", "team", 1)
        
        with col_b:
            if st.button("Continue as The Burtch Team", use_container_width=True, key="burtch"):
                set_user_session("The Burtch Team", "client", 2)
        
        st.markdown("---")
        st.info("""
        **Role Information:**
        - **Luke Wise (Team)**: Task execution, time tracking, comments, task updates
        - **The Burtch Team (Client)**: Task creation, assignment, prioritization, scheduling, reports
        """)
        
        st.markdown("</div>", unsafe_allow_html=True)

def set_user_session(user_name, user_type, user_id):
    """Set user session and redirect to main app"""
    st.session_state.user_selected = True
    st.session_state.user = user_name
    st.session_state.user_type = user_type
    st.session_state.user_id = user_id
    st.session_state.user_email = f"{user_name.lower().replace(' ', '.')}@burrichteam.com"
    st.rerun()

def show_main_application():
    """Display the main application after user selection"""
    
    # Configure sidebar to be expanded now
    st.markdown(
        """
        <style>
            section[data-testid="stSidebar"] {
                width: 300px !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
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
        # Luke Wise - Task executor view
        pages = {
            "Dashboard": dashboard,
            "My Tasks": task_management, 
            "Calendar": calendar_view,
            "Time Tracking": time_tracking,
            "Team Collaboration": team_collaboration
        }
    else:  # client - The Burtch Team
        pages = {
            "Dashboard": dashboard,
            "Task Management": task_management,
            "Calendar": calendar_view,
            "Reports": analytics_reports,
            "Team Overview": team_collaboration
        }
    
    # Navigation
    selection = st.sidebar.radio("Navigate to:", list(pages.keys()))
    
    # Quick stats in sidebar
    display_sidebar_stats()
    
    # Notifications
    display_notifications()
    
    # Display selected page
    try:
        page_module = pages[selection]
        page_module.app()
    except Exception as e:
        st.error(f"Error loading page {selection}: {e}")
        st.info("Please try refreshing the page.")

def display_sidebar_stats():
    """Display quick stats in sidebar"""
    st.sidebar.markdown("---")
    today = datetime.now().date()
    st.sidebar.markdown(f"**Today:** {today.strftime('%A, %B %d, %Y')}")
    
    # Quick stats
    try:
        if st.session_state.user_type == "team":
            # For Luke Wise, show only assigned tasks
            tasks = get_tasks({'assigned_to': st.session_state.user_id})
        else:
            # For Burtch Team, show all tasks
            tasks = get_tasks()
            
        if tasks:
            df = pd.DataFrame(tasks)
            
            col1, col2 = st.sidebar.columns(2)
            with col1:
                pending = len(df[df['status'] == 'Pending'])
                st.metric("Pending", pending)
            with col2:
                in_progress = len(df[df['status'] == 'In Progress'])
                st.metric("In Progress", in_progress)
            
            col3, col4 = st.sidebar.columns(2)
            with col3:
                overdue = len(df[(df['due_date'] < datetime.now().strftime('%Y-%m-%d')) & (df['status'] != 'Completed')])
                st.metric("Overdue", overdue)
            with col4:
                completed_today = len(df[(df['status'] == 'Completed') & (pd.to_datetime(df['completed_date']).dt.date == today)])
                st.metric("Completed Today", completed_today)
    except Exception as e:
        st.sidebar.error("Error loading stats")

def display_notifications():
    """Display notifications in sidebar"""
    try:
        notifications = get_unread_notifications(st.session_state.user_id)
        if notifications:
            st.sidebar.markdown("---")
            with st.sidebar.expander(f"Notifications ({len(notifications)})", expanded=False):
                for notification in notifications[:5]:
                    st.write(f"**{notification['title']}**")
                    st.caption(f"{format_date(notification['created_date'])}")
                    if st.button("Mark as read", key=f"read_{notification['id']}"):
                        mark_notification_as_read(notification['id'])
                        st.rerun()
    except Exception as e:
        st.sidebar.error("Error loading notifications")

    # Logout button
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

if __name__ == "__main__":
    main()
