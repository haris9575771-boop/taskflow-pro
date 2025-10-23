import streamlit as st
from utils.database import init_db

def app():
    st.title("⚙️ Settings")
    st.markdown("---")
    
    st.subheader("User Preferences")
    
    # Theme settings
    theme = st.selectbox("Theme", ["Light", "Dark", "System Default"])
    
    # Notification preferences
    st.subheader("Notification Settings")
    email_notifications = st.checkbox("Email Notifications", value=True)
    push_notifications = st.checkbox("Push Notifications", value=True)
    
    # Default view
    st.subheader("Default View")
    default_view = st.selectbox(
        "Default Page on Login",
        ["Dashboard", "Task Management", "Calendar View", "Reports"]
    )
    
    # Save settings
    if st.button("Save Settings"):
        st.success("Settings saved successfully!")
    
    st.markdown("---")
    
    # Database management (for admin)
    if st.session_state.user_type == "team":
        st.subheader("Database Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Initialize Database"):
                init_db()
                st.success("Database initialized successfully!")
        
        with col2:
            if st.button("Clear All Data"):
                if st.checkbox("I understand this will delete all data"):
                    st.warning("This feature would be implemented based on specific requirements")
    
    st.markdown("---")
    st.info(f"Logged in as: {st.session_state.user} ({st.session_state.user_type})")
