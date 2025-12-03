import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import json
import uuid
import time
import os
import hashlib
import base64
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import streamlit.components.v1 as components
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import GoogleAuthError
import traceback

# --- 1. ENTERPRISE BRANDING & CONFIGURATION ---
C21_GOLD = "#BEAF87"
C21_BLACK = "#212121"
C21_DARK_GREY = "#333333"
C21_LIGHT_GREY = "#F2F2F2"
C21_WHITE = "#FFFFFF"
C21_RED_ALERT = "#B00020"
C21_BLUE_INFO = "#2196F3"
C21_GREEN_SUCCESS = "#4CAF50"

@dataclass
class AppConfig:
    """Enterprise application configuration"""
    APP_NAME = "Task Manager - The Burtch Team"
    VERSION = "2.0.0"
    SHEET_ID = "1iIBoWSZSvV-SF9u2Cxi-_fbYgg06-XI32UgF1ZJIxh4"
    DRIVE_FOLDER_ID = ""  # Set your Drive folder ID here
    SESSION_TIMEOUT_MINUTES = 30
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 2

class SecurityConfig:
    """Security configuration with password hashing"""
    # In production, use environment variables or a secure vault
    USER_CREDENTIALS = {
        "Burtch": {
            "password_hash": hashlib.sha256("jayson0922".encode()).hexdigest(),
            "role": "Burtch",
            "full_name": "Burtch Manager"
        },
        "Luke": {
            "password_hash": hashlib.sha256("luke29430".encode()).hexdigest(),
            "role": "Luke",
            "full_name": "Luke Associate"
        },
        "Admin": {
            "password_hash": hashlib.sha256("admin_secure_password".encode()).hexdigest(),
            "role": "Admin",
            "full_name": "System Administrator"
        }
    }
    
    @staticmethod
    def verify_password(username: str, password: str) -> bool:
        """Verify hashed password"""
        if username not in SecurityConfig.USER_CREDENTIALS:
            return False
        
        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        stored_hash = SecurityConfig.USER_CREDENTIALS[username]["password_hash"]
        return hashed_input == stored_hash

# --- 2. ENTERPRISE STYLING ---
def inject_custom_css():
    """Inject enterprise-grade CSS styling"""
    st.markdown(f"""
        <style>
            /* Base App Styling */
            .stApp {{
                background: linear-gradient(135deg, {C21_LIGHT_GREY} 0%, #e6e6e6 100%);
                font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
                color: {C21_BLACK};
                min-height: 100vh;
            }}
            
            /* Sidebar Styling */
            [data-testid="stSidebar"] {{
                background: linear-gradient(180deg, {C21_BLACK} 0%, #1a1a1a 100%);
                border-right: 4px solid {C21_GOLD};
                box-shadow: 3px 0 15px rgba(0, 0, 0, 0.2);
            }}
            [data-testid="stSidebar"] .stButton > button {{
                background: linear-gradient(135deg, {C21_GOLD} 0%, #d4b56c 100%);
                color: {C21_BLACK};
                border: none;
                border-radius: 6px;
                font-weight: 600;
                padding: 10px 20px;
                transition: all 0.3s ease;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            }}
            [data-testid="stSidebar"] .stButton > button:hover {{
                background: linear-gradient(135deg, {C21_WHITE} 0%, #f0f0f0 100%);
                transform: translateY(-2px);
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
            }}
            
            /* Main Content Cards */
            .enterprise-card {{
                background: {C21_WHITE};
                border-radius: 12px;
                border-left: 6px solid {C21_GOLD};
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
                transition: all 0.3s ease;
                border: 1px solid #e0e0e0;
            }}
            .enterprise-card:hover {{
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
            }}
            
            .task-card {{
                background: {C21_WHITE};
                border-radius: 10px;
                border-left: 5px solid {C21_GOLD};
                padding: 18px;
                margin-bottom: 15px;
                box-shadow: 0 3px 10px rgba(0, 0, 0, 0.06);
                border: 1px solid #e8e8e8;
            }}
            
            .priority-badge {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.8em;
                font-weight: 600;
                margin-right: 8px;
            }}
            .priority-high {{
                background-color: #FFEBEE;
                color: {C21_RED_ALERT};
                border: 1px solid #FFCDD2;
            }}
            .priority-medium {{
                background-color: #FFF3E0;
                color: #FF9800;
                border: 1px solid #FFE0B2;
            }}
            .priority-low {{
                background-color: #E8F5E9;
                color: #4CAF50;
                border: 1px solid #C8E6C9;
            }}
            
            /* Dashboard Metrics */
            .metric-card {{
                background: linear-gradient(135deg, {C21_WHITE} 0%, #fafafa 100%);
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                border: 1px solid #e0e0e0;
                box-shadow: 0 3px 10px rgba(0, 0, 0, 0.05);
            }}
            .metric-value {{
                font-size: 2.2em;
                font-weight: 700;
                color: {C21_BLACK};
                margin: 10px 0;
            }}
            .metric-label {{
                font-size: 0.9em;
                color: {C21_DARK_GREY};
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            /* Custom Button Styles */
            .btn-primary {{
                background: linear-gradient(135deg, {C21_GOLD} 0%, #d4b56c 100%);
                color: {C21_BLACK};
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            .btn-primary:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(190, 175, 135, 0.3);
            }}
            
            .btn-secondary {{
                background: {C21_WHITE};
                color: {C21_BLACK};
                border: 2px solid {C21_GOLD};
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            .btn-secondary:hover {{
                background: {C21_GOLD};
            }}
            
            /* Form Styling */
            .stTextInput > div > div > input, 
            .stSelectbox > div > div > select,
            .stTextArea > div > div > textarea {{
                border-radius: 6px;
                border: 2px solid #e0e0e0;
                transition: all 0.3s ease;
            }}
            .stTextInput > div > div > input:focus, 
            .stSelectbox > div > div > select:focus,
            .stTextArea > div > div > textarea:focus {{
                border-color: {C21_GOLD};
                box-shadow: 0 0 0 2px rgba(190, 175, 135, 0.2);
            }}
            
            /* Status Indicators */
            .status-assigned {{ color: #2196F3; font-weight: 600; }}
            .status-in-progress {{ color: #FF9800; font-weight: 600; }}
            .status-pending {{ color: #9C27B0; font-weight: 600; }}
            .status-completed {{ color: #4CAF50; font-weight: 600; }}
            .status-archived {{ color: #9E9E9E; font-weight: 600; }}
            
            /* Utility Classes */
            .text-center {{ text-align: center; }}
            .text-right {{ text-align: right; }}
            .text-gold {{ color: {C21_GOLD}; }}
            .text-muted {{ color: #757575; }}
            .mb-3 {{ margin-bottom: 1rem; }}
            .mt-3 {{ margin-top: 1rem; }}
            .p-3 {{ padding: 1rem; }}
            
            /* Loading Spinner */
            .stSpinner > div > div {{
                border-color: {C21_GOLD} transparent transparent transparent;
            }}
            
            /* Toast/Success Messages */
            .stAlert {{
                border-radius: 8px;
                border-left: 4px solid;
            }}
            
            /* Dataframe Styling */
            .dataframe {{
                border-radius: 8px;
                overflow: hidden;
                border: 1px solid #e0e0e0;
            }}
            .dataframe th {{
                background-color: {C21_DARK_GREY};
                color: {C21_WHITE};
                font-weight: 600;
                text-transform: uppercase;
                font-size: 0.85em;
                letter-spacing: 0.5px;
            }}
            .dataframe tr:nth-child(even) {{
                background-color: {C21_LIGHT_GREY};
            }}
            .dataframe tr:hover {{
                background-color: rgba(190, 175, 135, 0.1);
            }}
            
        </style>
    """, unsafe_allow_html=True)

# --- 3. DATA MODELS & CONSTANTS ---
STATUS_LEVELS = ['Assigned', 'In Progress', 'Pending', 'Completed', 'Archived']
PRIORITY_LEVELS = [1, 2, 3]  # 1=High, 2=Medium, 3=Low
ROLES = ["Burtch", "Luke", "Admin"]
COLUMNS = ['ID', 'Title', 'Assigned To', 'Due Date', 'Status', 'Priority', 'Description', 
           'Google Drive Link', 'Created By', 'Last Modified', 'Created At']

# --- 4. ENTERPRISE ERROR HANDLING ---
class TaskManagerError(Exception):
    """Base exception for Task Manager"""
    pass

class GoogleServiceError(TaskManagerError):
    """Google API service errors"""
    pass

class AuthenticationError(TaskManagerError):
    """Authentication errors"""
    pass

class DataValidationError(TaskManagerError):
    """Data validation errors"""
    pass

# --- 5. GOOGLE SERVICE MANAGER (Enterprise Grade) ---
def initialize_google_services():
    """Initialize Google services with robust error handling"""
    try:
        # Check if credentials exist in secrets
        if "sheets_credentials_json" not in st.secrets:
            st.error("❌ Google Sheets credentials not found in secrets.toml")
            st.info("""
            Please ensure your secrets.toml contains:
            ```
            [sheets_credentials_json]
            type = "service_account"
            project_id = "taks-manager-480110"
            private_key_id = "59ea17ae4c87a5ac97b9648bd6c93ff2acf6d0af"
            private_key = \"\"\"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\"\"\"
            client_email = "taskmanager@taks-manager-480110.iam.gserviceaccount.com"
            client_id = "110405422782484657058"
            auth_uri = "https://accounts.google.com/o/oauth2/auth"
            token_uri = "https://oauth2.googleapis.com/token"
            auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
            client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/taskmanager%40taks-manager-480110.iam.gserviceaccount.com"
            universe_domain = "googleapis.com"
            ```
            """)
            return False
        
        # Get credentials from secrets
        creds_dict = dict(st.secrets["sheets_credentials_json"])
        
        # Fix private key formatting
        if 'private_key' in creds_dict:
            creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
        
        # Create credentials
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive.file'
            ]
        )
        
        # Initialize services with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                sheets_service = build('sheets', 'v4', credentials=credentials)
                drive_service = build('drive', 'v3', credentials=credentials)
                
                # Test the connection
                sheets_service.spreadsheets().get(spreadsheetId=AppConfig.SHEET_ID).execute()
                
                # Store services in session state
                st.session_state.SHEETS_SERVICE = sheets_service
                st.session_state.DRIVE_SERVICE = drive_service
                st.session_state.google_initialized = True
                
                return True
                
            except HttpError as e:
                if attempt == max_retries - 1:
                    st.error(f"❌ Google API Error: {str(e)}")
                    if "not have permission" in str(e):
                        st.info("""
                        Please ensure:
                        1. The Google Sheet is shared with the service account email: taskmanager@taks-manager-480110.iam.gserviceaccount.com
                        2. The service account has Editor access to the Google Sheet
                        3. The Google Drive folder (if used) is also shared with the same service account
                        """)
                    return False
                time.sleep(2)  # Wait before retry
                
            except Exception as e:
                if attempt == max_retries - 1:
                    st.error(f"❌ Failed to initialize Google services: {str(e)}")
                    return False
                time.sleep(2)  # Wait before retry
        
        return False
        
    except Exception as e:
        st.error(f"❌ Unexpected error initializing Google services: {str(e)}")
        return False

# --- 6. DATA MANAGER WITH CACHING ---
class DataManager:
    """Enterprise data manager with intelligent caching"""
    
    @staticmethod
    @st.cache_data(ttl=300, show_spinner=False)  # 5 minute cache
    def fetch_sheet_data(sheet_id: str, range_name: str) -> pd.DataFrame:
        """Fetch data from Google Sheets with robust error handling"""
        try:
            if 'SHEETS_SERVICE' not in st.session_state:
                raise GoogleServiceError("Google Sheets service not initialized")
            
            service = st.session_state.SHEETS_SERVICE
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id, 
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                return pd.DataFrame(columns=COLUMNS)
            
            # Ensure we have headers
            headers = values[0] if len(values) > 0 else COLUMNS
            data = values[1:] if len(values) > 1 else []
            
            df = pd.DataFrame(data, columns=headers)
            
            # Ensure all required columns exist
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ''
            
            # Data type conversions
            df['Due Date'] = pd.to_datetime(df['Due Date'], errors='coerce')
            df['Priority'] = pd.to_numeric(df['Priority'], errors='coerce').fillna(3).astype(int)
            df['ID'] = pd.to_numeric(df['ID'], errors='coerce')
            
            # Fill missing timestamps
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if 'Created At' not in df.columns or df['Created At'].isna().all():
                df['Created At'] = current_time
            if 'Last Modified' not in df.columns or df['Last Modified'].isna().all():
                df['Last Modified'] = current_time
            
            return df[COLUMNS]
            
        except HttpError as e:
            st.error(f"❌ Google Sheets API Error: {e}")
            raise
        except Exception as e:
            st.error(f"❌ Error fetching sheet data: {e}")
            raise
    
    @staticmethod
    def update_sheet_row(sheet_id: str, row_index: int, updated_data: list) -> dict:
        """Update a single row in Google Sheet"""
        if 'SHEETS_SERVICE' not in st.session_state:
            raise GoogleServiceError("Google Sheets service not initialized")
        
        service = st.session_state.SHEETS_SERVICE
        # Convert to 1-based indexing for Sheets API
        update_range = f"A{row_index + 2}:K{row_index + 2}"
        
        body = {'values': [updated_data]}
        
        result = service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=update_range,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        return result
    
    @staticmethod
    def append_sheet_row(sheet_id: str, range_name: str, new_data: list) -> dict:
        """Append a new row to Google Sheet"""
        if 'SHEETS_SERVICE' not in st.session_state:
            raise GoogleServiceError("Google Sheets service not initialized")
        
        service = st.session_state.SHEETS_SERVICE
        body = {'values': [new_data]}
        
        result = service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        return result
    
    @staticmethod
    def create_drive_folder(folder_name: str, parent_folder_id: str = None) -> str:
        """Create a folder in Google Drive"""
        if 'DRIVE_SERVICE' not in st.session_state:
            raise GoogleServiceError("Google Drive service not initialized")
        
        service = st.session_state.DRIVE_SERVICE
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
        }
        
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]
        
        try:
            file = service.files().create(
                body=file_metadata, 
                fields='id, webViewLink'
            ).execute()
            
            return file.get('webViewLink', f"https://drive.google.com/drive/folders/{file.get('id')}")
        except Exception as e:
            st.error(f"❌ Failed to create Drive folder: {str(e)}")
            return ""

# --- 7. UI COMPONENTS ---
def render_login_ui() -> None:
    """Render enterprise login interface"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div class='enterprise-card text-center'>
                <h1 style='color: #BEAF87;'>🏠 Task Manager</h1>
                <h3 style='color: #212121;'>The Burtch Team</h3>
                <p class='text-muted'>Enterprise Task Management System</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=True):
            username = st.selectbox(
                "Select User Role",
                ROLES,
                help="Choose your role to access the system"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                help="Enter your secure password"
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                submitted = st.form_submit_button(
                    "🔐 Login",
                    use_container_width=True,
                    type="primary"
                )
            with col_b:
                if st.form_submit_button("🔄 Reset", use_container_width=True):
                    st.rerun()
            
            if submitted:
                if SecurityConfig.verify_password(username, password):
                    st.session_state.authenticated = True
                    st.session_state.role = username
                    st.session_state.user_info = SecurityConfig.USER_CREDENTIALS[username]
                    st.session_state.login_time = datetime.datetime.now()
                    st.success(f"Welcome, {st.session_state.user_info['full_name']}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")

def render_task_card(task: pd.Series, current_user_role: str) -> None:
    """Render an enterprise task card"""
    
    # Priority styling
    priority_map = {
        1: ("priority-high", "🔴 High"),
        2: ("priority-medium", "🟡 Medium"),
        3: ("priority-low", "🟢 Low")
    }
    priority_class, priority_text = priority_map.get(task['Priority'], ("priority-low", "Low"))
    
    # Status styling
    status_class = f"status-{task['Status'].lower().replace(' ', '-')}"
    
    # Due date styling
    due_date = task['Due Date']
    if pd.notna(due_date):
        due_date_str = due_date.strftime('%b %d, %Y')
        days_remaining = (due_date.date() - datetime.date.today()).days
        
        if days_remaining < 0:
            due_style = "color: #D32F2F; font-weight: bold;"
            due_text = f"⏰ Overdue by {-days_remaining} days"
        elif days_remaining == 0:
            due_style = "color: #FF9800; font-weight: bold;"
            due_text = "⏰ Due today"
        elif days_remaining <= 3:
            due_style = "color: #FF9800; font-weight: bold;"
            due_text = f"⏰ Due in {days_remaining} days"
        else:
            due_style = "color: #4CAF50;"
            due_text = f"📅 Due {due_date_str}"
    else:
        due_style = "color: #9E9E9E;"
        due_text = "No due date"
    
    st.markdown(f"""
        <div class='task-card'>
            <div style='display: flex; justify-content: space-between; align-items: start;'>
                <div>
                    <h4 style='margin: 0; color: {C21_BLACK};'>#{task['ID']} - {task['Title']}</h4>
                    <p style='margin: 5px 0; color: {C21_DARK_GREY}; font-size: 0.9em;'>
                        👤 Assigned to: <strong>{task['Assigned To']}</strong>
                    </p>
                </div>
                <div>
                    <span class='priority-badge {priority_class}'>{priority_text}</span>
                </div>
            </div>
            
            <div style='margin: 10px 0;'>
                <p style='margin: 0; color: {C21_DARK_GREY}; font-size: 0.95em;'>
                    {task['Description'][:150]}{'...' if len(task['Description']) > 150 else ''}
                </p>
            </div>
            
            <div style='display: flex; justify-content: space-between; align-items: center; margin-top: 15px;'>
                <div>
                    <span style='{due_style}; font-size: 0.9em;'>{due_text}</span>
                </div>
                <div>
                    <span class='{status_class}' style='font-size: 0.9em;'>
                        📊 {task['Status']}
                    </span>
                </div>
            </div>
            
            {f"<div style='margin-top: 10px;'><a href='{task['Google Drive Link']}' target='_blank' style='color: {C21_BLUE_INFO}; text-decoration: none;'>📁 Open Drive Folder</a></div>" if task.get('Google Drive Link') else ''}
            
            <div style='margin-top: 10px; font-size: 0.8em; color: #9E9E9E;'>
                Created by {task['Created By']} | Last modified: {task['Last Modified']}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Update form (only for assigned user or admin)
    if current_user_role == task['Assigned To'] or current_user_role == "Admin":
        with st.expander(f"🔄 Update Task #{task['ID']}", expanded=False):
            with st.form(f"update_form_{task['ID']}"):
                new_status = st.selectbox(
                    "Update Status",
                    STATUS_LEVELS,
                    index=STATUS_LEVELS.index(task['Status']) if task['Status'] in STATUS_LEVELS else 0,
                    key=f"status_{task['ID']}"
                )
                
                new_priority = st.selectbox(
                    "Update Priority",
                    PRIORITY_LEVELS,
                    index=task['Priority'] - 1,
                    key=f"priority_{task['ID']}"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button(
                        "💾 Save Changes",
                        type="primary",
                        use_container_width=True
                    )
                with col2:
                    if st.form_submit_button("❌ Cancel", use_container_width=True):
                        st.rerun()
                
                if submitted:
                    try:
                        df = st.session_state.df
                        row_index = df[df['ID'] == task['ID']].index[0]
                        
                        # Update dataframe
                        df.loc[row_index, 'Status'] = new_status
                        df.loc[row_index, 'Priority'] = new_priority
                        df.loc[row_index, 'Last Modified'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Update Google Sheet
                        updated_data = df.loc[row_index, COLUMNS].tolist()
                        DataManager.update_sheet_row(
                            AppConfig.SHEET_ID,
                            row_index,
                            updated_data
                        )
                        
                        st.success(f"✅ Task #{task['ID']} updated successfully!")
                        st.session_state.data_loaded = False
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error updating task: {str(e)}")

def render_metrics(metrics: dict) -> None:
    """Render dashboard metrics"""
    cols = st.columns(len(metrics))
    
    for idx, (key, value) in enumerate(metrics.items()):
        with cols[idx]:
            st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-value'>{value}</div>
                    <div class='metric-label'>{key}</div>
                </div>
            """, unsafe_allow_html=True)

# --- 8. VIEW CONTROLLERS ---
def admin_dashboard(df: pd.DataFrame) -> None:
    """Admin dashboard view"""
    st.title("👑 Admin Dashboard")
    
    # Task creation section
    with st.expander("➕ Create New Task", expanded=False):
        with st.form("create_task_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                task_title = st.text_input("Task Title", max_chars=200)
                task_assigned = st.selectbox("Assign To", ROLES)
                task_due_date = st.date_input(
                    "Due Date",
                    min_value=datetime.date.today(),
                    value=datetime.date.today() + datetime.timedelta(days=7)
                )
            
            with col2:
                task_priority = st.selectbox(
                    "Priority Level",
                    options=PRIORITY_LEVELS,
                    format_func=lambda x: f"{x} - {'High' if x == 1 else 'Medium' if x == 2 else 'Low'}"
                )
                task_desc = st.text_area("Description", height=100)
                
                # Drive folder option
                create_drive_folder = st.checkbox("Create Google Drive Folder", value=True)
            
            col_a, col_b = st.columns(2)
            with col_a:
                submitted = st.form_submit_button(
                    "🚀 Create Task",
                    type="primary",
                    use_container_width=True
                )
            with col_b:
                if st.form_submit_button("🗑️ Clear Form", use_container_width=True):
                    st.rerun()
            
            if submitted and task_title:
                try:
                    # Generate unique ID
                    new_id = int(time.time() * 1000) % 1000000
                    
                    # Prepare new row
                    new_row = [
                        new_id,
                        task_title,
                        task_assigned,
                        task_due_date.strftime('%Y-%m-%d'),
                        'Assigned',
                        task_priority,
                        task_desc,
                        '',  # Drive link placeholder
                        st.session_state.role,
                        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ]
                    
                    # Create Drive folder if requested
                    if create_drive_folder and AppConfig.DRIVE_FOLDER_ID:
                        folder_name = f"Task_{new_id}_{task_title[:30]}"
                        drive_link = DataManager.create_drive_folder(
                            folder_name,
                            AppConfig.DRIVE_FOLDER_ID
                        )
                        new_row[7] = drive_link
                    
                    # Append to Google Sheet
                    DataManager.append_sheet_row(
                        AppConfig.SHEET_ID,
                        "Task Log!A:K",
                        new_row
                    )
                    
                    st.success(f"✅ Task '{task_title}' created successfully!")
                    st.session_state.data_loaded = False
                    st.cache_data.clear()
                    time.sleep(1.5)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error creating task: {str(e)}")
            elif submitted:
                st.warning("⚠️ Please enter a task title.")
    
    st.markdown("---")
    
    # Dashboard metrics
    active_df = df[~df['Status'].isin(['Completed', 'Archived'])].copy()
    
    metrics = {
        "Total Tasks": len(df),
        "Active Tasks": len(active_df),
        "High Priority": len(active_df[active_df['Priority'] == 1]),
        "Overdue": len(active_df[pd.to_datetime(active_df['Due Date'], errors='coerce').dt.date < datetime.date.today()])
    }
    
    render_metrics(metrics)
    
    # Data visualization
    col1, col2 = st.columns(2)
    
    with col1:
        # Status distribution
        status_counts = df['Status'].value_counts()
        if not status_counts.empty:
            fig1 = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Task Status Distribution",
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            fig1.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Priority distribution
        priority_counts = df['Priority'].value_counts().sort_index()
        if not priority_counts.empty:
            fig2 = px.bar(
                x=['High', 'Medium', 'Low'],
                y=priority_counts.values,
                title="Task Priority Distribution",
                color=['#D32F2F', '#FF9800', '#4CAF50'],
                labels={'x': 'Priority', 'y': 'Count'}
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    st.markdown("---")
    
    # Task management tabs
    tab1, tab2, tab3 = st.tabs(["📋 All Tasks", "👥 User Tasks", "📊 Analytics"])
    
    with tab1:
        st.subheader("All Tasks Overview")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.multiselect(
                "Filter by Status",
                STATUS_LEVELS,
                default=['Assigned', 'In Progress', 'Pending']
            )
        with col2:
            priority_filter = st.multiselect(
                "Filter by Priority",
                PRIORITY_LEVELS,
                default=[1, 2, 3]
            )
        with col3:
            assigned_filter = st.multiselect(
                "Filter by Assignee",
                ROLES,
                default=ROLES
            )
        
        # Apply filters
        filtered_df = df[
            df['Status'].isin(status_filter) &
            df['Priority'].isin(priority_filter) &
            df['Assigned To'].isin(assigned_filter)
        ].sort_values(['Priority', 'Due Date'], ascending=[True, True])
        
        # Display table
        st.dataframe(
            filtered_df.style.apply(
                lambda x: ['background: #FFEBEE' if x['Priority'] == 1 else 
                          'background: #FFF3E0' if x['Priority'] == 2 else 
                          'background: #E8F5E9' for _ in x],
                axis=1
            ),
            use_container_width=True,
            height=400
        )
    
    with tab2:
        st.subheader("Tasks by User")
        for role in ROLES:
            with st.expander(f"👤 {role}'s Tasks"):
                user_tasks = df[df['Assigned To'] == role]
                if not user_tasks.empty:
                    for _, task in user_tasks.iterrows():
                        render_task_card(task, "Admin")
                else:
                    st.info(f"No tasks assigned to {role}")
    
    with tab3:
        st.subheader("Advanced Analytics")
        
        # Completion rate over time
        df['Created Date'] = pd.to_datetime(df['Created At']).dt.date
        df['Completed'] = df['Status'] == 'Completed'
        
        completion_by_date = df.groupby('Created Date')['Completed'].mean().reset_index()
        
        if not completion_by_date.empty:
            fig3 = px.line(
                completion_by_date,
                x='Created Date',
                y='Completed',
                title="Completion Rate Over Time",
                markers=True
            )
            fig3.update_yaxes(tickformat=".0%", title="Completion Rate")
            st.plotly_chart(fig3, use_container_width=True)

def user_dashboard(df: pd.DataFrame, role: str) -> None:
    """User dashboard view"""
    st.title(f"👋 Welcome, {role}")
    
    # Get user's tasks
    user_tasks = df[df['Assigned To'] == role].copy()
    active_tasks = user_tasks[~user_tasks['Status'].isin(['Completed', 'Archived'])]
    
    # User metrics
    metrics = {
        "Total Tasks": len(user_tasks),
        "Active": len(active_tasks),
        "High Priority": len(active_tasks[active_tasks['Priority'] == 1]),
        "Due This Week": len(active_tasks[
            (pd.to_datetime(active_tasks['Due Date']).dt.date >= datetime.date.today()) &
            (pd.to_datetime(active_tasks['Due Date']).dt.date <= datetime.date.today() + datetime.timedelta(days=7))
        ])
    }
    
    render_metrics(metrics)
    
    st.markdown("---")
    
    # Task filtering
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.multiselect(
            "Filter by Status",
            STATUS_LEVELS,
            default=['Assigned', 'In Progress', 'Pending'],
            key="user_status_filter"
        )
    with col2:
        priority_filter = st.multiselect(
            "Filter by Priority",
            PRIORITY_LEVELS,
            default=[1, 2, 3],
            key="user_priority_filter"
        )
    
    # Apply filters
    filtered_tasks = user_tasks[
        user_tasks['Status'].isin(status_filter) &
        user_tasks['Priority'].isin(priority_filter)
    ].sort_values(['Priority', 'Due Date'], ascending=[True, True])
    
    if filtered_tasks.empty:
        st.success("🎉 All caught up! No tasks match your filters.")
        
        # Show completed tasks if no active tasks
        completed_tasks = user_tasks[user_tasks['Status'] == 'Completed']
        if not completed_tasks.empty:
            with st.expander("📚 View Completed Tasks"):
                for _, task in completed_tasks.iterrows():
                    render_task_card(task, role)
    else:
        # Display tasks
        for _, task in filtered_tasks.iterrows():
            render_task_card(task, role)
        
        # Quick stats
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            high_priority = len(filtered_tasks[filtered_tasks['Priority'] == 1])
            st.metric("High Priority Tasks", high_priority)
        
        with col2:
            overdue = len(filtered_tasks[
                pd.to_datetime(filtered_tasks['Due Date']).dt.date < datetime.date.today()
            ])
            st.metric("Overdue Tasks", overdue, delta_color="inverse")
        
        with col3:
            completion_rate = len(user_tasks[user_tasks['Status'] == 'Completed']) / len(user_tasks) * 100
            st.metric("Completion Rate", f"{completion_rate:.1f}%")

# --- 9. MAIN APPLICATION ---
def main():
    """Main application entry point"""
    
    # Page configuration
    st.set_page_config(
        page_title=AppConfig.APP_NAME,
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://www.century21.com',
            'Report a bug': None,
            'About': f"""
            ## {AppConfig.APP_NAME}
            
            **Version:** {AppConfig.VERSION}
            
            Enterprise Task Management System for The Burtch Team
            
            Built with Streamlit & Google Workspace
            """
        }
    )
    
    # Inject custom CSS
    inject_custom_css()
    
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None
    
    # Check session timeout
    if (st.session_state.authenticated and 
        st.session_state.login_time and 
        (datetime.datetime.now() - st.session_state.login_time).seconds > AppConfig.SESSION_TIMEOUT_MINUTES * 60):
        st.warning("Session expired. Please log in again.")
        st.session_state.authenticated = False
        st.session_state.role = None
        st.session_state.user_info = None
        st.rerun()
    
    # Authentication flow
    if not st.session_state.authenticated:
        render_login_ui()
        return
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
            <div class='text-center'>
                <img src='https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Century_21_Real_Estate_logo.svg/800px-Century_21_Real_Estate_logo.svg.png' 
                     width='120' style='margin-bottom: 20px;'>
                <h3 style='color: {C21_GOLD};'>{AppConfig.APP_NAME}</h3>
                <p style='color: {C21_WHITE}; font-size: 0.9em;'>Version {AppConfig.VERSION}</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # User info
        st.markdown(f"""
            <div style='padding: 10px; background: rgba(255,255,255,0.1); border-radius: 8px; margin-bottom: 20px;'>
                <p style='margin: 0; color: {C21_WHITE}; font-size: 0.9em;'>👤 Logged in as:</p>
                <p style='margin: 0; color: {C21_GOLD}; font-weight: bold;'>{st.session_state.user_info['full_name']}</p>
                <p style='margin: 0; color: {C21_WHITE}; font-size: 0.8em;'>{st.session_state.role} Role</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Navigation
        st.markdown("### 📊 Navigation")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.session_state.data_loaded = False
                st.cache_data.clear()
                st.rerun()
        
        with col2:
            if st.button("📈 Dashboard", use_container_width=True):
                st.rerun()
        
        # System status
        st.markdown("---")
        st.markdown("### 🔧 System Status")
        
        # Check Google services
        if 'google_initialized' in st.session_state and st.session_state.google_initialized:
            st.success("✅ Google Services Connected")
        else:
            st.error("❌ Google Services Not Initialized")
            if st.button("🔄 Reinitialize Google Services", use_container_width=True):
                if initialize_google_services():
                    st.success("✅ Google services reinitialized!")
                    st.rerun()
                else:
                    st.error("❌ Failed to initialize Google services")
        
        # Data status
        if st.session_state.get('data_loaded'):
            st.success("✅ Data Synced")
        else:
            st.warning("🔄 Syncing Data...")
        
        st.markdown("---")
        
        # Logout
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.role = None
            st.session_state.user_info = None
            st.session_state.data_loaded = False
            if 'google_initialized' in st.session_state:
                del st.session_state.google_initialized
            if 'SHEETS_SERVICE' in st.session_state:
                del st.session_state.SHEETS_SERVICE
            if 'DRIVE_SERVICE' in st.session_state:
                del st.session_state.DRIVE_SERVICE
            st.rerun()
    
    # Main content
    try:
        # Initialize Google services if not already done
        if 'google_initialized' not in st.session_state or not st.session_state.google_initialized:
            with st.spinner("🔄 Initializing Google services..."):
                if not initialize_google_services():
                    st.error("""
                    ❌ Failed to initialize Google services. Please check:
                    
                    1. Your secrets.toml file contains correct credentials
                    2. The service account has access to the Google Sheet
                    3. The Google Sheet ID is correct
                    
                    **Google Sheet ID:** `1iIBoWSZSvV-SF9u2Cxi-_fbYgg06-XI32UgF1ZJIxh4`
                    **Service Account:** `taskmanager@taks-manager-480110.iam.gserviceaccount.com`
                    """)
                    return
        
        # Load data if needed
        if not st.session_state.get('data_loaded'):
            with st.spinner("📥 Loading tasks from Google Sheets..."):
                try:
                    df = DataManager.fetch_sheet_data(
                        AppConfig.SHEET_ID,
                        "Task Log!A:K"
                    )
                    st.session_state.df = df
                    st.session_state.data_loaded = True
                    st.success(f"✅ Loaded {len(df)} tasks from Google Sheets")
                except Exception as e:
                    st.error(f"❌ Failed to load data: {str(e)}")
                    
                    # Show troubleshooting help
                    with st.expander("🛠️ Troubleshooting Help"):
                        st.markdown("""
                        ### Common Issues & Solutions:
                        
                        1. **Google Sheet Permissions**
                           - Ensure the Google Sheet is shared with: `taskmanager@taks-manager-480110.iam.gserviceaccount.com`
                           - Grant **Editor** access to the service account
                        
                        2. **Secrets Configuration**
                           - Verify `secrets.toml` has correct credentials
                           - Check that the private key is properly formatted
                        
                        3. **Google Sheet ID**
                           - Current Sheet ID: `1iIBoWSZSvV-SF9u2Cxi-_fbYgg06-XI32UgF1ZJIxh4`
                           - Ensure this matches your actual Google Sheet
                        
                        4. **Service Account Status**
                           - Verify the service account is active in Google Cloud Console
                        
                        **Error Details:**
                        """)
                        st.code(str(e))
                    
                    return
        
        # Render appropriate dashboard
        if st.session_state.role == "Admin":
            admin_dashboard(st.session_state.df)
        else:
            user_dashboard(st.session_state.df, st.session_state.role)
            
    except Exception as e:
        st.error(f"❌ Application error: {str(e)}")
        with st.expander("📋 Error Details"):
            st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
