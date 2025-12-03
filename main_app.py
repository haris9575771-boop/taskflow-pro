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
    VERSION = "2.0.2"
    SHEET_ID = "1iIBoWSZSvV-SF9u2Cxi-_fbYgg06-XI32UgF1ZJIxh4"
    DRIVE_FOLDER_ID = ""  # Set your Drive folder ID here
    SESSION_TIMEOUT_MINUTES = 30
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 2

class SecurityConfig:
    """Security configuration with password hashing"""
    # Display names for login screen
    USER_DISPLAY_NAMES = {
        "Burtch": "The Burtch Team",
        "Luke": "Luke Wise"
    }
    
    USER_CREDENTIALS = {
        "Burtch": {
            "password_hash": hashlib.sha256("jayson0922".encode()).hexdigest(),
            "role": "Burtch",
            "full_name": "The Burtch Team",
            "display_name": "The Burtch Team"
        },
        "Luke": {
            "password_hash": hashlib.sha256("luke29430".encode()).hexdigest(),
            "role": "Luke",
            "full_name": "Luke Wise",
            "display_name": "Luke Wise"
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
ROLES = ["Burtch", "Luke"]
DISPLAY_ROLES = ["The Burtch Team", "Luke Wise"]
ROLE_MAPPING = {
    "The Burtch Team": "Burtch",
    "Luke Wise": "Luke"
}
COLUMNS = ['ID', 'Title', 'Assigned To', 'Due Date', 'Status', 'Priority', 'Description', 
           'Comments', 'Google Drive Link', 'Created By', 'Last Modified', 'Created At']

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
    def initialize_sheet_structure(sheet_id: str):
        """Initialize Google Sheet with proper headers if empty"""
        try:
            if 'SHEETS_SERVICE' not in st.session_state:
                raise GoogleServiceError("Google Sheets service not initialized")
            
            service = st.session_state.SHEETS_SERVICE
            
            # Check if sheet exists and get all sheets
            spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            
            # Check if Task Log sheet exists
            task_log_exists = any(sheet['properties']['title'] == 'Task Log' for sheet in sheets)
            
            if not task_log_exists:
                # Create Task Log sheet
                requests = [{
                    'addSheet': {
                        'properties': {
                            'title': 'Task Log',
                            'gridProperties': {
                                'rowCount': 1000,
                                'columnCount': len(COLUMNS)
                            }
                        }
                    }
                }]
                
                body = {'requests': requests}
                service.spreadsheets().batchUpdate(
                    spreadsheetId=sheet_id,
                    body=body
                ).execute()
                
                st.info("📝 Created 'Task Log' sheet")
            
            # Get data from Task Log sheet
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id, 
                range='Task Log!A1:L1'
            ).execute()
            
            values = result.get('values', [])
            
            # If sheet is empty or headers don't match, create headers
            if not values or len(values[0]) != len(COLUMNS) or values[0] != COLUMNS:
                # Write headers
                body = {
                    'values': [COLUMNS]
                }
                
                service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range='Task Log!A1',
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
                
                # Format headers
                requests = [{
                    'repeatCell': {
                        'range': {
                            'sheetId': next((s['properties']['sheetId'] for s in sheets if s['properties']['title'] == 'Task Log'), 0),
                            'startRowIndex': 0,
                            'endRowIndex': 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': len(COLUMNS)
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {
                                    'red': 0.13,
                                    'green': 0.13,
                                    'blue': 0.13
                                },
                                'textFormat': {
                                    'foregroundColor': {
                                        'red': 1,
                                        'green': 1,
                                        'blue': 1
                                    },
                                    'bold': True,
                                    'fontSize': 11
                                },
                                'horizontalAlignment': 'CENTER'
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                    }
                }]
                
                body = {'requests': requests}
                service.spreadsheets().batchUpdate(
                    spreadsheetId=sheet_id,
                    body=body
                ).execute()
                
                # Freeze header row
                freeze_request = [{
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': next((s['properties']['sheetId'] for s in sheets if s['properties']['title'] == 'Task Log'), 0),
                            'gridProperties': {
                                'frozenRowCount': 1
                            }
                        },
                        'fields': 'gridProperties.frozenRowCount'
                    }
                }]
                
                body = {'requests': freeze_request}
                service.spreadsheets().batchUpdate(
                    spreadsheetId=sheet_id,
                    body=body
                ).execute()
                
                st.success("✅ Sheet structure initialized with headers")
                
            return True
            
        except HttpError as e:
            st.error(f"❌ Google Sheets API Error during initialization: {e}")
            raise
        except Exception as e:
            st.error(f"❌ Error initializing sheet structure: {e}")
            raise
    
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
            
            # Handle legacy data without Comments column
            if len(headers) == 11:  # Old format without Comments
                headers = headers[:7] + ['Comments'] + headers[7:]
                for row in data:
                    if len(row) == 11:
                        row.insert(7, '')  # Add empty Comments column
            
            # Ensure we have the right number of columns
            while len(headers) < len(COLUMNS):
                headers.append('')
            for row in data:
                while len(row) < len(COLUMNS):
                    row.append('')
            
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
            
            # Remove duplicate rows to prevent form key conflicts
            if 'ID' in df.columns:
                df = df.drop_duplicates(subset='ID', keep='last')
            
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
        update_range = f"A{row_index + 2}:L{row_index + 2}"
        
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
            # Use display names for the selectbox
            selected_display = st.selectbox(
                "Select User Role",
                DISPLAY_ROLES,
                help="Choose your role to access the system"
            )
            
            # Map display name to internal role
            username = ROLE_MAPPING.get(selected_display, selected_display)
            
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
                    st.success(f"Welcome, {st.session_state.user_info['display_name']}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")

def render_task_card(task: pd.Series, current_user_role: str, card_index: int) -> None:
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
    
    # Due date styling - FIXED: Calculate due_date_str and due_text
    due_date = task['Due Date']
    due_date_str = ""
    due_text = ""
    
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
        due_date_str = "No due date"
        due_text = "No due date"
    
    # Determine display name for "Created By"
    created_by_display = task['Created By']
    if task['Created By'] == "Burtch":
        created_by_display = "The Burtch Team"
    elif task['Created By'] == "Luke":
        created_by_display = "Luke Wise"
    
    # Get comments if available
    comments = task.get('Comments', '')
    comments_display = ""
    if comments and pd.notna(comments) and str(comments).strip():
        comments_display = f"""
        <div style='margin: 10px 0; padding: 10px; background-color: #F5F5F5; border-radius: 5px; border-left: 3px solid {C21_GOLD};'>
            <p style='margin: 0; font-size: 0.9em; color: {C21_DARK_GREY};'><strong>💬 Comments:</strong> {comments}</p>
        </div>
        """
    
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
            
            {comments_display}
            
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
            
            {f"<div style='margin-top: 10px;'><a href='{task['Google Drive Link']}' target='_blank' style='color: {C21_BLUE_INFO}; text-decoration: none;'>📁 Open Drive Folder</a></div>" if task.get('Google Drive Link') and pd.notna(task['Google Drive Link']) and str(task['Google Drive Link']).strip() else ''}
            
            <div style='margin-top: 10px; font-size: 0.8em; color: #9E9E9E;'>
                Created by {created_by_display} | Last modified: {task['Last Modified']}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Update form (only for assigned user or Burtch)
    if current_user_role == task['Assigned To'] or current_user_role == "Burtch":
        with st.expander(f"🔄 Update Task #{task['ID']}", expanded=False):
            # FIXED: Display task details for context in update form
            st.markdown(f"""
                <div style='margin: 10px 0; padding: 10px; background-color: #f9f9f9; border-radius: 5px; border-left: 3px solid {C21_GOLD};'>
                    <p style='margin: 0; color: {C21_BLACK}; font-size: 0.95em;'>
                        <strong>Task Description:</strong> {task['Description']}
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
                <div style='display: flex; justify-content: space-between; align-items: center; margin: 10px 0; padding: 10px; background-color: #f0f0f0; border-radius: 5px;'>
                    <div>
                        <span style='{due_style}; font-size: 0.9em;'>{due_text}</span>
                    </div>
                    <div>
                        <span class='{status_class}' style='font-size: 0.9em;'>
                            📊 Current Status: {task['Status']}
                        </span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Create unique form key using task ID AND card index to prevent duplicates
            form_key = f"update_form_{task['ID']}_{card_index}_{int(time.time())}"
            
            with st.form(form_key):
                new_status = st.selectbox(
                    "Update Status",
                    STATUS_LEVELS,
                    index=STATUS_LEVELS.index(task['Status']) if task['Status'] in STATUS_LEVELS else 0,
                    key=f"status_{task['ID']}_{card_index}"
                )
                
                new_priority = st.selectbox(
                    "Update Priority",
                    PRIORITY_LEVELS,
                    index=task['Priority'] - 1 if task['Priority'] in PRIORITY_LEVELS else 2,
                    key=f"priority_{task['ID']}_{card_index}"
                )
                
                # Comments field for updates
                current_comments = task.get('Comments', '')
                new_comments = st.text_area(
                    "Add/Update Comments",
                    value=current_comments if pd.notna(current_comments) else '',
                    height=100,
                    key=f"comments_{task['ID']}_{card_index}",
                    help="Add comments or updates about this task"
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
                        df.loc[row_index, 'Comments'] = new_comments
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
                        st.cache_data.clear()
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
def manager_dashboard(df: pd.DataFrame) -> None:
    """Manager dashboard view for The Burtch Team"""
    st.title("👑 Manager Dashboard - The Burtch Team")
    
    # Task creation section - FIXED: Allow assigning to both Luke and Burtch
    with st.expander("➕ Create & Assign New Task", expanded=False):
        with st.form("create_task_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                task_title = st.text_input("Task Title *", max_chars=200, help="Enter a clear title for the task")
                task_assigned = st.selectbox("Assign To *", ["Luke Wise", "The Burtch Team"], help="Select who this task should be assigned to")
                task_due_date = st.date_input(
                    "Due Date *",
                    min_value=datetime.date.today(),
                    value=datetime.date.today() + datetime.timedelta(days=7),
                    help="Set the deadline for this task"
                )
            
            with col2:
                task_priority = st.selectbox(
                    "Priority Level *",
                    options=PRIORITY_LEVELS,
                    format_func=lambda x: f"{x} - {'High' if x == 1 else 'Medium' if x == 2 else 'Low'}",
                    help="Set task priority"
                )
                task_desc = st.text_area("Description *", height=100, help="Provide detailed description of the task")
                
                # Drive folder option
                create_drive_folder = st.checkbox("Create Google Drive Folder", value=True, 
                                                 help="Create a dedicated folder for this task in Google Drive")
            
            col_a, col_b = st.columns(2)
            with col_a:
                submitted = st.form_submit_button(
                    "🚀 Create & Assign Task",
                    type="primary",
                    use_container_width=True
                )
            with col_b:
                if st.form_submit_button("🗑️ Clear Form", use_container_width=True):
                    st.rerun()
            
            if submitted:
                if task_title and task_desc:
                    try:
                        # Generate unique ID
                        new_id = int(time.time() * 1000) % 1000000
                        
                        # Map display name to internal role
                        if task_assigned == "Luke Wise":
                            assigned_to = "Luke"
                        else:
                            assigned_to = "Burtch"
                        
                        # Prepare new row
                        new_row = [
                            new_id,
                            task_title,
                            assigned_to,  # Use mapped role
                            task_due_date.strftime('%Y-%m-%d'),
                            'Assigned',
                            task_priority,
                            task_desc,
                            '',  # Comments placeholder
                            '',  # Drive link placeholder
                            st.session_state.role,
                            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ]
                        
                        # Create Drive folder if requested
                        if create_drive_folder and AppConfig.DRIVE_FOLDER_ID:
                            folder_name = f"Task_{new_id}_{task_title[:30]}".replace(" ", "_")
                            drive_link = DataManager.create_drive_folder(
                                folder_name,
                                AppConfig.DRIVE_FOLDER_ID
                            )
                            new_row[8] = drive_link
                        
                        # Append to Google Sheet
                        DataManager.append_sheet_row(
                            AppConfig.SHEET_ID,
                            "Task Log!A:L",
                            new_row
                        )
                        
                        st.success(f"✅ Task '{task_title}' created and assigned to {task_assigned}!")
                        st.session_state.data_loaded = False
                        st.cache_data.clear()
                        time.sleep(1.5)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error creating task: {str(e)}")
                else:
                    st.warning("⚠️ Please fill in all required fields (marked with *)")
    
    st.markdown("---")
    
    # Report Generation Section
    with st.expander("📊 Generate Task Reports", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            report_start_date = st.date_input(
                "Start Date",
                value=datetime.date.today() - datetime.timedelta(days=30),
                help="Select start date for report period"
            )
        
        with col2:
            report_end_date = st.date_input(
                "End Date",
                value=datetime.date.today(),
                help="Select end date for report period"
            )
        
        report_type = st.selectbox(
            "Report Type",
            ["Completed Tasks", "All Tasks", "High Priority Tasks", "Overdue Tasks"],
            help="Select the type of report to generate"
        )
        
        if st.button("📥 Generate Report", type="primary", use_container_width=True):
            try:
                # Convert dates for comparison
                start_date = pd.to_datetime(report_start_date)
                end_date = pd.to_datetime(report_end_date)
                
                # Filter tasks based on creation date
                df['Created Date'] = pd.to_datetime(df['Created At']).dt.date
                filtered_df = df[
                    (pd.to_datetime(df['Created Date']) >= start_date) &
                    (pd.to_datetime(df['Created Date']) <= end_date)
                ].copy()
                
                # Apply additional filters based on report type
                if report_type == "Completed Tasks":
                    filtered_df = filtered_df[filtered_df['Status'] == 'Completed']
                elif report_type == "High Priority Tasks":
                    filtered_df = filtered_df[filtered_df['Priority'] == 1]
                elif report_type == "Overdue Tasks":
                    filtered_df = filtered_df[
                        (pd.to_datetime(filtered_df['Due Date']).dt.date < datetime.date.today()) &
                        (~filtered_df['Status'].isin(['Completed', 'Archived']))
                    ]
                
                if not filtered_df.empty:
                    # Prepare data for download
                    report_data = filtered_df.copy()
                    report_data['Due Date'] = report_data['Due Date'].dt.strftime('%Y-%m-%d')
                    
                    # Convert to CSV
                    csv = report_data.to_csv(index=False)
                    
                    # Download button
                    st.download_button(
                        label="💾 Download Report as CSV",
                        data=csv,
                        file_name=f"task_report_{report_start_date}_{report_end_date}_{report_type.replace(' ', '_')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    
                    # Display preview
                    st.subheader("📋 Report Preview")
                    st.dataframe(report_data, use_container_width=True)
                else:
                    st.info(f"No tasks found for the selected period and report type.")
                    
            except Exception as e:
                st.error(f"❌ Error generating report: {str(e)}")
    
    st.markdown("---")
    
    # Dashboard metrics - FIXED: Include both Luke's and Burtch's tasks
    active_df = df[~df['Status'].isin(['Completed', 'Archived'])].copy()
    burtch_tasks = df[df['Assigned To'] == 'Burtch']
    luke_tasks = df[df['Assigned To'] == 'Luke']
    
    metrics = {
        "Total Tasks": len(df),
        "Active Tasks": len(active_df),
        "Luke's Tasks": len(luke_tasks),
        "Burtch's Tasks": len(burtch_tasks),
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
        else:
            st.info("No tasks available for status distribution.")
    
    with col2:
        # Priority distribution - FIXED VERSION
        # Create a DataFrame with all priority levels
        priority_data = {'Priority': ['High', 'Medium', 'Low'], 'Count': [0, 0, 0]}
        
        # Count tasks by priority
        if not df.empty:
            # Ensure we have numeric priorities
            df['Priority'] = pd.to_numeric(df['Priority'], errors='coerce').fillna(3).astype(int)
            
            # Count each priority level
            for priority in [1, 2, 3]:
                count = len(df[df['Priority'] == priority])
                if priority == 1:
                    priority_data['Count'][0] = count
                elif priority == 2:
                    priority_data['Count'][1] = count
                elif priority == 3:
                    priority_data['Count'][2] = count
        
        # Create the bar chart
        priority_df = pd.DataFrame(priority_data)
        
        if not priority_df.empty and priority_df['Count'].sum() > 0:
            fig2 = px.bar(
                priority_df,
                x='Priority',
                y='Count',
                title="Task Priority Distribution",
                color='Priority',
                color_discrete_map={
                    'High': '#D32F2F',
                    'Medium': '#FF9800',
                    'Low': '#4CAF50'
                },
                labels={'Count': 'Number of Tasks'}
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No tasks available for priority distribution.")
    
    st.markdown("---")
    
    # Task management tabs - FIXED: Changed to show assigned tasks for both users
    tab1, tab2, tab3, tab4 = st.tabs(["📋 All Tasks", "👥 Assigned Tasks", "📈 Trends", "🧑‍💼 My Tasks"])
    
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
                ["Luke", "Burtch"],
                default=["Luke", "Burtch"]
            )
        
        # Apply filters
        filtered_df = df[
            df['Status'].isin(status_filter) &
            df['Priority'].isin(priority_filter) &
            df['Assigned To'].isin(assigned_filter)
        ].sort_values(['Priority', 'Due Date'], ascending=[True, True])
        
        if not filtered_df.empty:
            # Display table with better formatting
            display_df = filtered_df.copy()
            display_df['Due Date'] = display_df['Due Date'].dt.strftime('%Y-%m-%d')
            display_df['Priority'] = display_df['Priority'].apply(
                lambda x: f"{x} - {'High' if x == 1 else 'Medium' if x == 2 else 'Low'}"
            )
            
            st.dataframe(
                display_df.style.apply(
                    lambda x: ['background: #FFEBEE' if x['Priority'] == '1 - High' else 
                              'background: #FFF3E0' if x['Priority'] == '2 - Medium' else 
                              'background: #E8F5E9' for _ in x],
                    axis=1
                ),
                use_container_width=True,
                height=400
            )
        else:
            st.info("No tasks match the selected filters.")
    
    with tab2:
        st.subheader("Assigned Tasks Overview")
        
        # Show tasks by assignee
        assignee_tabs = st.tabs(["👤 Luke's Tasks", "👑 Burtch's Tasks"])
        
        with assignee_tabs[0]:
            luke_tasks = df[df['Assigned To'] == "Luke"]
            if not luke_tasks.empty:
                # Sort by priority and due date
                luke_tasks = luke_tasks.sort_values(['Priority', 'Due Date'], ascending=[True, True])
                
                # Display upcoming tasks (not completed/archived)
                upcoming_tasks = luke_tasks[~luke_tasks['Status'].isin(['Completed', 'Archived'])]
                if not upcoming_tasks.empty:
                    st.markdown(f"### 📅 Luke's Upcoming Tasks ({len(upcoming_tasks)})")
                    for idx, (_, task) in enumerate(upcoming_tasks.iterrows()):
                        render_task_card(task, "Burtch", idx)
                else:
                    st.success("🎉 All of Luke's tasks are completed or archived!")
                
                # Display completed tasks
                completed_tasks = luke_tasks[luke_tasks['Status'] == 'Completed']
                if not completed_tasks.empty:
                    with st.expander(f"✅ Luke's Completed Tasks ({len(completed_tasks)})", expanded=False):
                        for idx, (_, task) in enumerate(completed_tasks.iterrows()):
                            render_task_card(task, "Burtch", idx)
            else:
                st.info("No tasks assigned to Luke.")
        
        with assignee_tabs[1]:
            burtch_tasks = df[df['Assigned To'] == "Burtch"]
            if not burtch_tasks.empty:
                # Sort by priority and due date
                burtch_tasks = burtch_tasks.sort_values(['Priority', 'Due Date'], ascending=[True, True])
                
                # Display upcoming tasks (not completed/archived)
                upcoming_tasks = burtch_tasks[~burtch_tasks['Status'].isin(['Completed', 'Archived'])]
                if not upcoming_tasks.empty:
                    st.markdown(f"### 📅 Burtch's Upcoming Tasks ({len(upcoming_tasks)})")
                    for idx, (_, task) in enumerate(upcoming_tasks.iterrows()):
                        render_task_card(task, "Burtch", idx)
                else:
                    st.success("🎉 All of Burtch's tasks are completed or archived!")
                
                # Display completed tasks
                completed_tasks = burtch_tasks[burtch_tasks['Status'] == 'Completed']
                if not completed_tasks.empty:
                    with st.expander(f"✅ Burtch's Completed Tasks ({len(completed_tasks)})", expanded=False):
                        for idx, (_, task) in enumerate(completed_tasks.iterrows()):
                            render_task_card(task, "Burtch", idx)
            else:
                st.info("No tasks assigned to The Burtch Team.")
    
    with tab3:
        st.subheader("Performance Trends")
        
        # Completion rate over time
        if not df.empty:
            df['Created Date'] = pd.to_datetime(df['Created At']).dt.date
            df['Completed'] = df['Status'] == 'Completed'
            
            # Weekly completion rate
            df['Week'] = pd.to_datetime(df['Created At']).dt.to_period('W').apply(lambda r: r.start_time)
            weekly_completion = df.groupby('Week')['Completed'].mean().reset_index()
            
            if not weekly_completion.empty:
                fig3 = px.line(
                    weekly_completion,
                    x='Week',
                    y='Completed',
                    title="Weekly Completion Rate",
                    markers=True,
                    line_shape='spline'
                )
                fig3.update_yaxes(tickformat=".0%", title="Completion Rate")
                fig3.update_xaxes(title="Week")
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No completion data available for trend analysis.")
            
            # Task load over time
            daily_tasks = df.groupby('Created Date').size().reset_index(name='Task Count')
            if not daily_tasks.empty:
                fig4 = px.bar(
                    daily_tasks,
                    x='Created Date',
                    y='Task Count',
                    title="Daily Task Creation",
                    color_discrete_sequence=[C21_GOLD]
                )
                st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No data available for trend analysis.")
    
    with tab4:
        st.subheader("My Tasks (The Burtch Team)")
        my_tasks = df[df['Assigned To'] == "Burtch"]
        if not my_tasks.empty:
            # Sort by priority and due date
            my_tasks = my_tasks.sort_values(['Priority', 'Due Date'], ascending=[True, True])
            
            # Display upcoming tasks (not completed/archived)
            upcoming_tasks = my_tasks[~my_tasks['Status'].isin(['Completed', 'Archived'])]
            if not upcoming_tasks.empty:
                st.markdown(f"### 📅 My Upcoming Tasks ({len(upcoming_tasks)})")
                for idx, (_, task) in enumerate(upcoming_tasks.iterrows()):
                    render_task_card(task, "Burtch", idx)
            else:
                st.success("🎉 All my tasks are completed or archived!")
            
            # Display completed tasks
            completed_tasks = my_tasks[my_tasks['Status'] == 'Completed']
            if not completed_tasks.empty:
                with st.expander(f"✅ My Completed Tasks ({len(completed_tasks)})", expanded=False):
                    for idx, (_, task) in enumerate(completed_tasks.iterrows()):
                        render_task_card(task, "Burtch", idx)
        else:
            st.info("No tasks assigned to you.")

def user_dashboard(df: pd.DataFrame, role: str) -> None:
    """User dashboard view for Luke Wise"""
    display_name = SecurityConfig.USER_DISPLAY_NAMES.get(role, role)
    st.title(f"👋 Welcome, {display_name}")
    
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
    
    # Upcoming tasks section (not completed/archived)
    st.subheader("📅 Upcoming & Active Tasks")
    
    if active_tasks.empty:
        st.success("🎉 All caught up! No active tasks.")
    else:
        # Sort by priority and due date
        active_tasks = active_tasks.sort_values(['Priority', 'Due Date'], ascending=[True, True])
        
        # Display upcoming tasks this week
        this_week_tasks = active_tasks[
            (pd.to_datetime(active_tasks['Due Date']).dt.date >= datetime.date.today()) &
            (pd.to_datetime(active_tasks['Due Date']).dt.date <= datetime.date.today() + datetime.timedelta(days=7))
        ]
        
        if not this_week_tasks.empty:
            st.markdown(f"### This Week ({len(this_week_tasks)} tasks)")
            for idx, (_, task) in enumerate(this_week_tasks.iterrows()):
                render_task_card(task, role, idx)
        
        # Display other upcoming tasks
        other_tasks = active_tasks[
            (pd.to_datetime(active_tasks['Due Date']).dt.date > datetime.date.today() + datetime.timedelta(days=7)) |
            (pd.isna(active_tasks['Due Date']))
        ]
        
        if not other_tasks.empty:
            with st.expander(f"Future Tasks ({len(other_tasks)})", expanded=False):
                for idx, (_, task) in enumerate(other_tasks.iterrows()):
                    render_task_card(task, role, idx)
        
        # Display overdue tasks
        overdue_tasks = active_tasks[
            pd.to_datetime(active_tasks['Due Date']).dt.date < datetime.date.today()
        ]
        
        if not overdue_tasks.empty:
            st.markdown("---")
            st.markdown(f"### ⚠️ Overdue Tasks ({len(overdue_tasks)})")
            for idx, (_, task) in enumerate(overdue_tasks.iterrows()):
                render_task_card(task, role, idx)
    
    st.markdown("---")
    
    # Completed tasks section
    completed_tasks = user_tasks[user_tasks['Status'] == 'Completed']
    if not completed_tasks.empty:
        with st.expander(f"📚 Completed Tasks ({len(completed_tasks)})", expanded=False):
            # Sort by completion date (last modified)
            completed_tasks = completed_tasks.sort_values('Last Modified', ascending=False)
            for idx, (_, task) in enumerate(completed_tasks.iterrows()):
                render_task_card(task, role, idx)
    
    # Quick update section
    st.markdown("---")
    st.subheader("⚡ Quick Task Update")
    
    if not active_tasks.empty:
        # Simple form for quick status updates
        with st.form("quick_update_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                task_to_update = st.selectbox(
                    "Select Task",
                    active_tasks.apply(lambda x: f"#{x['ID']} - {x['Title']}", axis=1).tolist(),
                    help="Select a task to update"
                )
            
            with col2:
                new_status = st.selectbox(
                    "Update Status",
                    ['In Progress', 'Pending', 'Completed'],
                    help="Update task status"
                )
            
            with col3:
                quick_comment = st.text_input(
                    "Quick Comment",
                    help="Add a brief comment about the update"
                )
            
            if st.form_submit_button("🚀 Quick Update", type="primary", use_container_width=True):
                try:
                    # Extract task ID from selection
                    task_id = int(task_to_update.split("#")[1].split(" - ")[0])
                    
                    # Find and update task
                    df = st.session_state.df
                    row_index = df[df['ID'] == task_id].index[0]
                    
                    # Update dataframe
                    df.loc[row_index, 'Status'] = new_status
                    if quick_comment:
                        current_comments = df.loc[row_index, 'Comments']
                        new_comments = f"{current_comments}\n{datetime.datetime.now().strftime('%Y-%m-%d')}: {quick_comment}".strip()
                        df.loc[row_index, 'Comments'] = new_comments
                    df.loc[row_index, 'Last Modified'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Update Google Sheet
                    updated_data = df.loc[row_index, COLUMNS].tolist()
                    DataManager.update_sheet_row(
                        AppConfig.SHEET_ID,
                        row_index,
                        updated_data
                    )
                    
                    st.success(f"✅ Task #{task_id} updated to '{new_status}'!")
                    st.session_state.data_loaded = False
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error updating task: {str(e)}")

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
    if 'sheet_initialized' not in st.session_state:
        st.session_state.sheet_initialized = False
    
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
        user_display_name = st.session_state.user_info.get('display_name', st.session_state.user_info['full_name'])
        st.markdown(f"""
            <div style='padding: 10px; background: rgba(255,255,255,0.1); border-radius: 8px; margin-bottom: 20px;'>
                <p style='margin: 0; color: {C21_WHITE}; font-size: 0.9em;'>👤 Logged in as:</p>
                <p style='margin: 0; color: {C21_GOLD}; font-weight: bold;'>{user_display_name}</p>
                <p style='margin: 0; color: {C21_WHITE}; font-size: 0.8em;'>{'Manager' if st.session_state.role == 'Burtch' else 'Team Member'} Role</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Navigation
        st.markdown("### 📊 Navigation")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Data", use_container_width=True, help="Reload data from Google Sheets"):
                st.session_state.data_loaded = False
                st.cache_data.clear()
                st.rerun()
        
        with col2:
            if st.button("📈 Dashboard", use_container_width=True, help="Return to dashboard"):
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
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
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
        
        # Initialize sheet structure (creates headers if needed)
        if 'sheet_initialized' not in st.session_state or not st.session_state.sheet_initialized:
            with st.spinner("📝 Initializing Google Sheet structure..."):
                try:
                    DataManager.initialize_sheet_structure(AppConfig.SHEET_ID)
                    st.session_state.sheet_initialized = True
                except Exception as e:
                    st.error(f"❌ Failed to initialize sheet structure: {str(e)}")
                    return
        
        # Load data if needed
        if not st.session_state.get('data_loaded'):
            with st.spinner("📥 Loading tasks from Google Sheets..."):
                try:
                    df = DataManager.fetch_sheet_data(
                        AppConfig.SHEET_ID,
                        "Task Log!A:L"
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
        if st.session_state.role == "Burtch":
            manager_dashboard(st.session_state.df)
        else:
            user_dashboard(st.session_state.df, st.session_state.role)
            
    except Exception as e:
        st.error(f"❌ Application error: {str(e)}")
        with st.expander("📋 Error Details"):
            st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
