import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import time
import hashlib
import json
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import traceback
import base64
from streamlit_option_menu import option_menu
from datetime import timedelta

# --- 1. ENTERPRISE BRANDING & CONFIGURATION ---
C21_GOLD = "#BEAF87"
C21_GOLD_LIGHT = "#D4C9A9"
C21_GOLD_DARK = "#A8956A"
C21_BLACK = "#212121"
C21_DARK_GREY = "#333333"
C21_MEDIUM_GREY = "#666666"
C21_LIGHT_GREY = "#F5F5F5"
C21_WHITE = "#FFFFFF"
C21_RED_ALERT = "#E53935"
C21_ORANGE_WARNING = "#FF9800"
C21_BLUE_INFO = "#2196F3"
C21_GREEN_SUCCESS = "#4CAF50"
C21_TEAL = "#26A69A"
C21_PURPLE = "#9C27B0"

MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2

@dataclass
class AppConfig:
    """Enterprise application configuration"""
    APP_NAME = "TaskFlow Pro"
    APP_SUBTITLE = "The Burtch Team"
    VERSION = "4.0.0 (Enhanced)"
    SHEET_ID = "1iIBoWSZSvV-SF9u2Cxi-_fbYgg06-XI32UgF1ZJIxh4"
    DRIVE_FOLDER_ID = ""
    SESSION_TIMEOUT_MINUTES = 60
    NOTIFICATION_TIMEOUT = 5000  # milliseconds
    ENABLE_BROWSER_NOTIFICATIONS = True

class SecurityConfig:
    USER_CREDENTIALS = {
        "Burtch": {
            "password": "jayson0922", 
            "role": "Burtch",
            "display_name": "The Burtch Team",
            "avatar": "👑"
        },
        "Luke": {
            "password": "luke29430",
            "role": "Luke",
            "display_name": "Luke Wise",
            "avatar": "🚀"
        }
    }
    
    @staticmethod
    def verify_password(username: str, password: str) -> bool:
        if username not in SecurityConfig.USER_CREDENTIALS:
            return False
        return password == SecurityConfig.USER_CREDENTIALS[username]["password"]

# --- 2. DATA MODELS ---
COLUMNS = [
    'ID', 'Title', 'Assigned To', 'Start Date', 'Due Date', 'Completed Date',
    'Status', 'Priority', 'Time Spent (Hrs)', 'Description', 'Comments', 
    'Google Drive Link', 'Created By', 'Last Modified', 'Created At'
]

NOTIFICATION_COLUMNS = [
    'Timestamp', 'Task ID', 'Title', 'User', 'Action', 'Details', 'Read'
]

STATUS_LEVELS = ['Assigned', 'In Progress', 'On Hold', 'Completed', 'Archived']
PRIORITY_LEVELS = [1, 2, 3]
PRIORITY_MAP = {1: 'High', 2: 'Medium', 3: 'Low'}

# --- 3. MODERN ENTERPRISE STYLING ---
def inject_custom_css():
    st.markdown(f"""
        <style>
            /* Base Styles */
            .stApp {{
                background: linear-gradient(135deg, {C21_LIGHT_GREY} 0%, #f8f9fa 100%);
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }}
            
            /* Custom Scrollbar */
            ::-webkit-scrollbar {{
                width: 8px;
                height: 8px;
            }}
            ::-webkit-scrollbar-track {{
                background: {C21_LIGHT_GREY};
            }}
            ::-webkit-scrollbar-thumb {{
                background: {C21_GOLD};
                border-radius: 4px;
            }}
            ::-webkit-scrollbar-thumb:hover {{
                background: {C21_GOLD_DARK};
            }}
            
            /* Sidebar Modernization */
            [data-testid="stSidebar"] {{
                background: linear-gradient(180deg, {C21_BLACK} 0%, #1a1a1a 100%);
                border-right: none;
                box-shadow: 4px 0 20px rgba(0,0,0,0.1);
            }}
            [data-testid="stSidebar"] .sidebar-content {{
                padding: 2rem 1rem;
            }}
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
                color: {C21_GOLD} !important;
                font-weight: 600;
                letter-spacing: -0.5px;
            }}
            
            /* Modern Cards */
            .modern-card {{
                background: {C21_WHITE};
                border-radius: 16px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.08);
                border: 1px solid rgba(190, 175, 135, 0.1);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                overflow: hidden;
                position: relative;
            }}
            .modern-card:hover {{
                transform: translateY(-4px);
                box-shadow: 0 12px 32px rgba(0,0,0,0.12);
                border-color: {C21_GOLD_LIGHT};
            }}
            .modern-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, {C21_GOLD} 0%, {C21_GOLD_DARK} 100%);
                border-radius: 16px 16px 0 0;
            }}
            
            /* Metrics Dashboard */
            .metric-card {{
                background: linear-gradient(135deg, {C21_WHITE} 0%, #fafafa 100%);
                border-radius: 16px;
                padding: 24px;
                border: 1px solid rgba(190, 175, 135, 0.2);
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                text-align: center;
                transition: all 0.3s ease;
            }}
            .metric-card:hover {{
                border-color: {C21_GOLD};
                box-shadow: 0 8px 24px rgba(190, 175, 135, 0.15);
            }}
            .metric-val {{
                font-size: 2.5rem;
                font-weight: 700;
                background: linear-gradient(135deg, {C21_GOLD} 0%, {C21_GOLD_DARK} 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin: 8px 0;
            }}
            .metric-lbl {{
                color: {C21_MEDIUM_GREY};
                font-size: 0.9rem;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                font-weight: 600;
            }}
            
            /* Modern Buttons */
            .stButton > button {{
                border-radius: 12px;
                font-weight: 600;
                padding: 12px 24px;
                border: 2px solid transparent;
                transition: all 0.3s ease;
                font-size: 0.95rem;
                letter-spacing: 0.5px;
            }}
            .stButton > button[kind="primary"] {{
                background: linear-gradient(135deg, {C21_GOLD} 0%, {C21_GOLD_DARK} 100%);
                color: {C21_BLACK};
                border: none;
                box-shadow: 0 4px 12px rgba(190, 175, 135, 0.3);
            }}
            .stButton > button[kind="primary"]:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(190, 175, 135, 0.4);
            }}
            .stButton > button[kind="secondary"] {{
                background: transparent;
                border-color: {C21_GOLD};
                color: {C21_GOLD};
            }}
            
            /* Status Badges */
            .status-badge {{
                font-weight: 600;
                padding: 6px 16px;
                border-radius: 20px;
                font-size: 0.8rem;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                letter-spacing: 0.5px;
            }}
            .status-Assigned {{
                background: rgba(33, 33, 33, 0.1);
                color: {C21_BLACK};
                border: 1px solid {C21_DARK_GREY};
            }}
            .status-In-Progress {{
                background: rgba(33, 150, 243, 0.1);
                color: {C21_BLUE_INFO};
                border: 1px solid {C21_BLUE_INFO};
            }}
            .status-On-Hold {{
                background: rgba(255, 152, 0, 0.1);
                color: {C21_ORANGE_WARNING};
                border: 1px solid {C21_ORANGE_WARNING};
            }}
            .status-Completed {{
                background: rgba(76, 175, 80, 0.1);
                color: {C21_GREEN_SUCCESS};
                border: 1px solid {C21_GREEN_SUCCESS};
            }}
            .status-Archived {{
                background: rgba(158, 158, 158, 0.1);
                color: #9E9E9E;
                border: 1px solid #9E9E9E;
            }}
            
            /* Priority Indicators */
            .priority-badge {{
                width: 12px;
                height: 12px;
                border-radius: 50%;
                display: inline-block;
                margin-right: 6px;
            }}
            .priority-1 {{ background-color: {C21_RED_ALERT}; }}
            .priority-2 {{ background-color: {C21_ORANGE_WARNING}; }}
            .priority-3 {{ background-color: {C21_GREEN_SUCCESS}; }}
            
            /* Notification Bell */
            .notification-bell {{
                position: relative;
                cursor: pointer;
                font-size: 1.5rem;
            }}
            .notification-count {{
                position: absolute;
                top: -8px;
                right: -8px;
                background: {C21_RED_ALERT};
                color: white;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                font-size: 0.7rem;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
            }}
            
            /* Custom Tabs */
            .stTabs [data-baseweb="tab-list"] {{
                gap: 8px;
            }}
            .stTabs [data-baseweb="tab"] {{
                border-radius: 12px 12px 0 0;
                padding: 12px 24px;
                border: 1px solid #e0e0e0;
                background: {C21_WHITE};
                font-weight: 500;
            }}
            .stTabs [aria-selected="true"] {{
                background: linear-gradient(135deg, {C21_GOLD} 0%, {C21_GOLD_DARK} 100%);
                color: {C21_WHITE} !important;
                border-color: {C21_GOLD};
            }}
            
            /* Input Fields */
            .stTextInput > div > div > input {{
                border-radius: 12px;
                border: 2px solid #e0e0e0;
                padding: 12px 16px;
                transition: all 0.3s ease;
            }}
            .stTextInput > div > div > input:focus {{
                border-color: {C21_GOLD};
                box-shadow: 0 0 0 3px rgba(190, 175, 135, 0.1);
            }}
            
            /* Date Input */
            .stDateInput > div > div > input {{
                border-radius: 12px;
                padding: 12px 16px;
            }}
            
            /* Progress Bar */
            .stProgress > div > div > div > div {{
                background: linear-gradient(90deg, {C21_GOLD} 0%, {C21_GOLD_DARK} 100%);
                border-radius: 10px;
            }}
            
            /* Divider */
            hr {{
                border: none;
                height: 1px;
                background: linear-gradient(90deg, transparent, {C21_GOLD_LIGHT}, transparent);
                margin: 2rem 0;
            }}
            
            /* Loading Spinner */
            .stSpinner > div {{
                border-color: {C21_GOLD} transparent transparent transparent !important;
            }}
            
            /* Tooltip */
            .tooltip {{
                position: relative;
                display: inline-block;
            }}
            .tooltip .tooltiptext {{
                visibility: hidden;
                background-color: {C21_BLACK};
                color: {C21_WHITE};
                text-align: center;
                border-radius: 6px;
                padding: 8px 12px;
                position: absolute;
                z-index: 1;
                bottom: 125%;
                left: 50%;
                transform: translateX(-50%);
                opacity: 0;
                transition: opacity 0.3s;
                font-size: 0.85rem;
                white-space: nowrap;
            }}
            .tooltip:hover .tooltiptext {{
                visibility: visible;
                opacity: 1;
            }}
        </style>
    """, unsafe_allow_html=True)

# --- 4. BROWSER NOTIFICATION SYSTEM ---
def inject_notification_js():
    """Inject JavaScript for browser notifications"""
    js_code = """
    <script>
    // Request notification permission
    function requestNotificationPermission() {
        if ("Notification" in window) {
            Notification.requestPermission().then(function(permission) {
                console.log("Notification permission:", permission);
            });
        }
    }
    
    // Show browser notification
    function showBrowserNotification(title, message, icon) {
        if ("Notification" in window && Notification.permission === "granted") {
            const notification = new Notification(title, {
                body: message,
                icon: icon || "https://cdn-icons-png.flaticon.com/512/891/891419.png",
                tag: "task-manager"
            });
            
            notification.onclick = function() {
                window.focus();
                notification.close();
            };
            
            setTimeout(notification.close.bind(notification), 5000);
        }
    }
    
    // Play notification sound
    function playNotificationSound() {
        const audio = new Audio('https://assets.mixkit.co/sfx/preview/mixkit-correct-answer-tone-2870.mp3');
        audio.volume = 0.3;
        audio.play().catch(e => console.log("Audio play failed:", e));
    }
    
    // Initialize notifications
    window.addEventListener('load', function() {
        requestNotificationPermission();
    });
    </script>
    """
    st.components.v1.html(js_code, height=0)

def send_browser_notification(title: str, message: str, task_id: Optional[int] = None):
    """Send browser notification using JavaScript"""
    if AppConfig.ENABLE_BROWSER_NOTIFICATIONS:
        icon_map = {
            "Task Created": "🚀",
            "Task Updated": "✏️",
            "Task Completed": "✅",
            "Due Today": "⏰",
            "Overdue": "⚠️",
            "Assigned": "📋"
        }
        
        icon = icon_map.get(title.split(":")[0], "📋")
        
        js = f"""
        <script>
        if (typeof showBrowserNotification === 'function') {{
            showBrowserNotification("{title}", "{message}", "{icon}");
            playNotificationSound();
        }}
        </script>
        """
        st.components.v1.html(js, height=0)

# --- 5. GOOGLE SERVICES INITIALIZATION ---
def initialize_google_services():
    """Robust Service Initialization with retry logic."""
    if 'sheets_credentials_json' not in st.secrets:
        st.error("❌ Credentials missing in secrets.toml")
        return False
        
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            creds_dict = dict(st.secrets["sheets_credentials_json"])
            if 'private_key' in creds_dict:
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
                
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets', 
                       'https://www.googleapis.com/auth/drive']
            )
            
            st.session_state.SHEETS_SERVICE = build('sheets', 'v4', credentials=credentials)
            st.session_state.DRIVE_SERVICE = build('drive', 'v3', credentials=credentials)
            st.session_state.google_initialized = True
            return True
            
        except Exception as e:
            st.warning(f"Connection attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS} failed. Retrying...")
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                st.error(f"❌ Critical Connection Error after {MAX_RETRY_ATTEMPTS} attempts: {e}")
                return False

# --- 6. ENHANCED DATA MANAGER ---
class DataManager:
    @staticmethod
    def _get_service():
        if 'SHEETS_SERVICE' not in st.session_state:
            raise Exception("Google Sheets Service not initialized.")
        return st.session_state.SHEETS_SERVICE

    @staticmethod
    def ensure_sheet_headers(sheet_id: str, sheet_name: str, columns: List[str]):
        """Ensures a sheet (tab) exists and has the correct columns."""
        service = DataManager._get_service()
        range_name = f"'{sheet_name}'!A1"
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id, range=range_name
            ).execute()
            existing_headers = result.get('values', [[]])[0]
            
            if not existing_headers or existing_headers != columns:
                body = {'values': [columns]}
                service.spreadsheets().values().update(
                    spreadsheetId=sheet_id, range=range_name,
                    valueInputOption='USER_ENTERED', body=body
                ).execute()
                st.toast(f"✅ Headers updated for '{sheet_name}'.")
        except HttpError as e:
            if e.resp.status == 400 and 'Unable to parse range' in str(e):
                requests = [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
                body = {'requests': requests}
                service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()
                
                body = {'values': [columns]}
                service.spreadsheets().values().update(
                    spreadsheetId=sheet_id, range=range_name,
                    valueInputOption='USER_ENTERED', body=body
                ).execute()
            else:
                st.warning(f"Header check failed for '{sheet_name}': {e}")

    @staticmethod
    @st.cache_data(ttl=60)  # Reduced TTL for more real-time updates
    def fetch_data() -> pd.DataFrame:
        """Fetch data with improved error handling and data validation."""
        service = DataManager._get_service()
        
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=AppConfig.SHEET_ID, range="Task Log!A:O"
            ).execute()
            values = result.get('values', [])
            
            if len(values) < 2:
                return pd.DataFrame(columns=COLUMNS)
            
            expected_cols = len(COLUMNS)
            padded_values = []
            for row in values[1:]:
                if len(row) < expected_cols:
                    row.extend([""] * (expected_cols - len(row)))
                padded_values.append(row[:expected_cols])
            
            df = pd.DataFrame(padded_values, columns=COLUMNS)
            
            # Enhanced type conversion with error handling
            df['ID'] = pd.to_numeric(df['ID'], errors='coerce')
            df['Priority'] = pd.to_numeric(df['Priority'], errors='coerce').fillna(3).astype('Int64')
            df['Time Spent (Hrs)'] = pd.to_numeric(df['Time Spent (Hrs)'], errors='coerce').fillna(0.0)
            
            # Date conversion with multiple formats
            date_cols = ['Due Date', 'Start Date', 'Completed Date', 'Created At', 'Last Modified']
            for col in date_cols:
                df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')
            
            # Clean up string columns
            string_cols = ['Title', 'Description', 'Comments', 'Assigned To', 'Status']
            for col in string_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
            
            return df
            
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return pd.DataFrame(columns=COLUMNS)

    @staticmethod
    def add_task(task_data: dict):
        """Append new task with notifications."""
        service = DataManager._get_service()
        
        # Generate ID if not provided
        if 'ID' not in task_data or not task_data['ID']:
            task_data['ID'] = int(time.time() * 1000) % 1000000
        
        row = [task_data.get(c, "") for c in COLUMNS]
        
        # Format dates
        for idx, val in enumerate(row):
            if isinstance(val, (datetime.date, datetime.datetime)):
                row[idx] = val.strftime('%Y-%m-%d %H:%M:%S')
            elif val is None:
                row[idx] = ""
        
        try:
            service.spreadsheets().values().append(
                spreadsheetId=AppConfig.SHEET_ID, range="Task Log!A:A",
                valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
                body={"values": [row]}
            ).execute()
            
            st.cache_data.clear()
            st.toast("🚀 Task Created Successfully!", icon="✅")
            
            # Send notification
            if task_data.get('Assigned To') == "Luke":
                send_browser_notification(
                    "Task Assigned",
                    f"New task: {task_data.get('Title', 'Untitled')}",
                    task_data['ID']
                )
            
            return True
            
        except Exception as e:
            st.error(f"Failed to add task: {e}")
            return False

    @staticmethod
    def update_task(task_id: int, updates: dict, current_user: str):
        """Updates a task with enhanced change tracking."""
        service = DataManager._get_service()
        
        # Fetch current ID column to find row index
        result = service.spreadsheets().values().get(
            spreadsheetId=AppConfig.SHEET_ID, range="Task Log!A:A"
        ).execute()
        ids = [row[0] if row else '' for row in result.get('values', [])]
        
        try:
            row_idx = ids.index(str(task_id)) + 1
        except ValueError:
            st.error(f"Task ID {task_id} not found.")
            return False

        # Get current row data
        current_row_res = service.spreadsheets().values().get(
            spreadsheetId=AppConfig.SHEET_ID, range=f"Task Log!A{row_idx}:O{row_idx}"
        ).execute()
        current_row_values = current_row_res.get('values', [[]])[0]
        while len(current_row_values) < len(COLUMNS):
            current_row_values.append("")
        current_task = dict(zip(COLUMNS, current_row_values))

        # Apply updates and track changes
        new_row = list(current_row_values)
        changes = []
        task_title = current_task.get('Title', f"Task #{task_id}")

        for col, new_val in updates.items():
            if col in COLUMNS:
                idx = COLUMNS.index(col)
                old_val = new_row[idx]
                
                # Format dates
                if isinstance(new_val, (datetime.date, datetime.datetime)):
                    formatted_val = new_val.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    formatted_val = str(new_val)

                if old_val != formatted_val and col != 'Comments':
                    changes.append(f"{col}: '{old_val}' → '{formatted_val}'")
                
                new_row[idx] = formatted_val

        # Update last modified timestamp
        new_row[COLUMNS.index('Last Modified')] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Write back
        try:
            service.spreadsheets().values().update(
                spreadsheetId=AppConfig.SHEET_ID, 
                range=f"Task Log!A{row_idx}:O{row_idx}",
                valueInputOption="USER_ENTERED", 
                body={"values": [new_row]}
            ).execute()
            
            # Log notification
            if changes or updates.get('Comments'):
                NotificationManager.log_update(
                    task_id=task_id,
                    title=task_title,
                    user=current_user,
                    action="Task Updated",
                    details="; ".join(changes) or updates.get('Comments', 'Updated'),
                    read=False
                )
            
            # Send browser notification for status changes
            if 'Status' in updates:
                if updates['Status'] == 'Completed' and current_task.get('Assigned To') == "Luke":
                    send_browser_notification(
                        "Task Completed ✅",
                        f"{task_title} has been completed",
                        task_id
                    )
                elif current_task.get('Assigned To') == "Luke":
                    send_browser_notification(
                        "Task Updated",
                        f"{task_title} status: {updates['Status']}",
                        task_id
                    )
            
            st.cache_data.clear()
            st.toast("✅ Task Updated!", icon="👍")
            return True
            
        except Exception as e:
            st.error(f"Failed to update task: {e}")
            return False

    @staticmethod
    def delete_task(task_id: int, current_user: str):
        """Archive a task (soft delete)."""
        return DataManager.update_task(task_id, {'Status': 'Archived'}, current_user)

    @staticmethod
    def create_drive_folder(folder_name):
        """Create a folder in Drive for a new task."""
        if 'DRIVE_SERVICE' not in st.session_state:
            return ""
        try:
            service = st.session_state.DRIVE_SERVICE
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if AppConfig.DRIVE_FOLDER_ID:
                metadata['parents'] = [AppConfig.DRIVE_FOLDER_ID]
                
            file = service.files().create(body=metadata, fields='webViewLink,id').execute()
            return file.get('webViewLink', "")
        except Exception as e:
            st.warning(f"Could not create Drive folder: {e}")
            return ""

# --- 7. ENHANCED NOTIFICATION MANAGER ---
class NotificationManager:
    @staticmethod
    def log_update(task_id: int, title: str, user: str, action: str, details: str, read: bool = False):
        """Logs task updates to Notifications Log."""
        service = DataManager._get_service()
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_row = [
            timestamp,
            task_id,
            title,
            user,
            action,
            details,
            "Yes" if read else "No"
        ]
        
        try:
            service.spreadsheets().values().append(
                spreadsheetId=AppConfig.SHEET_ID, 
                range="Notifications Log!A:A",
                valueInputOption="USER_ENTERED", 
                insertDataOption="INSERT_ROWS",
                body={"values": [log_row]}
            ).execute()
        except Exception as e:
            st.warning(f"Failed to log notification: {e}")

    @staticmethod
    @st.cache_data(ttl=30)
    def fetch_notifications() -> pd.DataFrame:
        """Fetches notifications with unread count."""
        service = DataManager._get_service()
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=AppConfig.SHEET_ID, range="Notifications Log!A:G"
            ).execute()
            values = result.get('values', [])
            
            if len(values) < 2:
                return pd.DataFrame(columns=NOTIFICATION_COLUMNS)
            
            df = pd.DataFrame(values[1:], columns=NOTIFICATION_COLUMNS)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
            df['Task ID'] = pd.to_numeric(df['Task ID'], errors='coerce').astype('Int64')
            
            return df.sort_values('Timestamp', ascending=False).dropna(subset=['Timestamp'])
        except Exception as e:
            st.warning(f"Failed to fetch notifications: {e}")
            return pd.DataFrame(columns=NOTIFICATION_COLUMNS)

    @staticmethod
    def get_unread_count():
        """Count unread notifications."""
        df = NotificationManager.fetch_notifications()
        if df.empty:
            return 0
        return len(df[df['Read'] == 'No'])

    @staticmethod
    def mark_all_as_read():
        """Mark all notifications as read."""
        df = NotificationManager.fetch_notifications()
        if not df.empty:
            # Implementation would update the sheet
            pass

# --- 8. ENHANCED REPORT GENERATOR ---
class ReportGenerator:
    @staticmethod
    def generate_html_report(df: pd.DataFrame, start_date, end_date, user: str = "Luke"):
        """Generates modern HTML report with analytics."""
        
        # Filter data
        user_df = df[df['Assigned To'] == user]
        mask = (user_df['Created At'].dt.date >= start_date) & (user_df['Created At'].dt.date <= end_date)
        period_df = user_df[mask]
        
        if period_df.empty:
            return "<h3>No data for selected period</h3>"
        
        completed = period_df[period_df['Status'] == 'Completed']
        
        # Calculate metrics
        total_tasks = len(period_df)
        completed_count = len(completed)
        completion_rate = int((completed_count / total_tasks * 100) if total_tasks > 0 else 0)
        total_hours = completed['Time Spent (Hrs)'].sum()
        avg_hours = completed['Time Spent (Hrs)'].mean() if completed_count > 0 else 0
        
        # Create charts
        fig_status = px.pie(period_df, names='Status', title="Task Status Distribution",
                           color_discrete_sequence=[C21_GOLD, C21_BLUE_INFO, C21_ORANGE_WARNING, C21_GREEN_SUCCESS, C21_DARK_GREY])
        chart_html = fig_status.to_html(full_html=False, include_plotlyjs='cdn')
        
        # Priority distribution
        priority_counts = period_df['Priority'].value_counts().sort_index()
        
        # HTML Template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Report - {user}</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
                
                body {{
                    font-family: 'Inter', sans-serif;
                    color: {C21_BLACK};
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 40px;
                    background: {C21_LIGHT_GREY};
                }}
                
                .report-container {{
                    background: {C21_WHITE};
                    border-radius: 24px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.08);
                    padding: 50px;
                    position: relative;
                    overflow: hidden;
                }}
                
                .report-container::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 6px;
                    background: linear-gradient(90deg, {C21_GOLD}, {C21_GOLD_DARK});
                }}
                
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 40px;
                    border-bottom: 2px solid {C21_LIGHT_GREY};
                    padding-bottom: 30px;
                }}
                
                .logo-section {{
                    flex: 1;
                }}
                
                .logo {{
                    font-size: 32px;
                    font-weight: 700;
                    background: linear-gradient(135deg, {C21_GOLD}, {C21_GOLD_DARK});
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-bottom: 10px;
                }}
                
                .subtitle {{
                    color: {C21_MEDIUM_GREY};
                    font-size: 16px;
                    font-weight: 500;
                }}
                
                .report-info {{
                    text-align: right;
                }}
                
                .employee-name {{
                    font-size: 24px;
                    font-weight: 600;
                    color: {C21_BLACK};
                    margin-bottom: 5px;
                }}
                
                .period {{
                    color: {C21_MEDIUM_GREY};
                    font-size: 14px;
                    background: {C21_LIGHT_GREY};
                    padding: 8px 16px;
                    border-radius: 12px;
                    display: inline-block;
                }}
                
                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 40px 0;
                }}
                
                .metric-card {{
                    background: linear-gradient(135deg, #f8f9fa, #ffffff);
                    border-radius: 16px;
                    padding: 24px;
                    border: 1px solid rgba(190, 175, 135, 0.2);
                    text-align: center;
                    transition: all 0.3s ease;
                }}
                
                .metric-card:hover {{
                    transform: translateY(-5px);
                    box-shadow: 0 15px 30px rgba(190, 175, 135, 0.15);
                    border-color: {C21_GOLD};
                }}
                
                .metric-value {{
                    font-size: 42px;
                    font-weight: 700;
                    background: linear-gradient(135deg, {C21_GOLD}, {C21_GOLD_DARK});
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin: 10px 0;
                }}
                
                .metric-label {{
                    color: {C21_MEDIUM_GREY};
                    font-size: 14px;
                    text-transform: uppercase;
                    letter-spacing: 1.5px;
                    font-weight: 600;
                }}
                
                .charts-container {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                    gap: 30px;
                    margin: 40px 0;
                }}
                
                .chart-box {{
                    background: {C21_WHITE};
                    border-radius: 16px;
                    padding: 25px;
                    border: 1px solid #eee;
                }}
                
                table {{
                    width: 100%;
                    border-collapse: separate;
                    border-spacing: 0;
                    margin: 30px 0;
                    background: {C21_WHITE};
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.05);
                }}
                
                th {{
                    background: linear-gradient(135deg, {C21_GOLD}, {C21_GOLD_DARK});
                    color: {C21_WHITE};
                    padding: 18px 15px;
                    text-align: left;
                    font-weight: 600;
                    font-size: 14px;
                }}
                
                td {{
                    padding: 15px;
                    border-bottom: 1px solid {C21_LIGHT_GREY};
                    font-size: 14px;
                }}
                
                tr:hover td {{
                    background: rgba(190, 175, 135, 0.05);
                }}
                
                .priority-badge {{
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 600;
                }}
                
                .priority-high {{ background: rgba(229, 57, 53, 0.1); color: {C21_RED_ALERT}; }}
                .priority-medium {{ background: rgba(255, 152, 0, 0.1); color: {C21_ORANGE_WARNING}; }}
                .priority-low {{ background: rgba(76, 175, 80, 0.1); color: {C21_GREEN_SUCCESS}; }}
                
                .footer {{
                    margin-top: 50px;
                    padding-top: 20px;
                    border-top: 1px solid {C21_LIGHT_GREY};
                    text-align: center;
                    color: {C21_MEDIUM_GREY};
                    font-size: 12px;
                }}
                
                @media print {{
                    body {{ -webkit-print-color-adjust: exact; }}
                    .report-container {{ box-shadow: none; }}
                }}
            </style>
        </head>
        <body>
            <div class="report-container">
                <div class="header">
                    <div class="logo-section">
                        <div class="logo">The Burtch Team</div>
                        <div class="subtitle">Performance Analytics Report</div>
                    </div>
                    <div class="report-info">
                        <div class="employee-name">{user}</div>
                        <div class="period">{start_date} → {end_date}</div>
                    </div>
                </div>
                
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{total_tasks}</div>
                        <div class="metric-label">Total Tasks</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{completed_count}</div>
                        <div class="metric-label">Completed</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{completion_rate}%</div>
                        <div class="metric-label">Completion Rate</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{total_hours:.1f}</div>
                        <div class="metric-label">Total Hours</div>
                    </div>
                </div>
                
                <div class="charts-container">
                    <div class="chart-box">
                        <h3>📊 Task Status Distribution</h3>
                        {chart_html}
                    </div>
                </div>
                
                <h3>📋 Task Details</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Task ID</th>
                            <th>Title</th>
                            <th>Status</th>
                            <th>Priority</th>
                            <th>Hours</th>
                            <th>Completed Date</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for _, row in completed.iterrows():
            priority_class = f"priority-{PRIORITY_MAP[row['Priority']].lower()}"
            priority_text = PRIORITY_MAP.get(row['Priority'], 'Low')
            c_date = row['Completed Date'].strftime('%Y-%m-%d') if pd.notna(row['Completed Date']) else '-'
            
            html += f"""
                <tr>
                    <td><strong>#{row['ID']}</strong></td>
                    <td>{row['Title']}</td>
                    <td><span class="status-badge status-Completed">Completed</span></td>
                    <td><span class="priority-badge {priority_class}">{priority_text}</span></td>
                    <td>{row['Time Spent (Hrs)']:.1f}</td>
                    <td>{c_date}</td>
                </tr>
            """
            
        html += f"""
                    </tbody>
                </table>
                
                <div class="footer">
                    Generated by TaskFlow Pro v{AppConfig.VERSION} | The Burtch Team<br>
                    Report generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
                </div>
            </div>
        </body>
        </html>
        """
        return html

# --- 9. MODERN UI COMPONENTS ---

def render_login():
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        # Animated gradient header
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem 0;">
            <h1 style="
                font-size: 3.5rem;
                font-weight: 800;
                background: linear-gradient(135deg, {C21_GOLD}, {C21_GOLD_DARK});
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 0.5rem;
            ">TaskFlow Pro</h1>
            <p style="
                color: {C21_MEDIUM_GREY};
                font-size: 1.1rem;
                letter-spacing: 2px;
                text-transform: uppercase;
                margin-bottom: 2rem;
            ">The Burtch Team • Enterprise Edition</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Login Card
        with st.container():
            st.markdown("""
            <div class="modern-card" style="padding: 2rem;">
            """, unsafe_allow_html=True)
            
            with st.form("login_form"):
                col_a, col_b = st.columns(2)
                with col_a:
                    role_display = st.selectbox(
                        "Select User",
                        ["The Burtch Team", "Luke Wise"],
                        index=0,
                        help="Choose your account"
                    )
                
                username = "Burtch" if role_display == "The Burtch Team" else "Luke"
                user_avatar = SecurityConfig.USER_CREDENTIALS[username]["avatar"]
                
                with col_b:
                    password = st.text_input(
                        "Password",
                        type="password",
                        help="Enter your password"
                    )
                
                st.markdown("---")
                
                col_c, col_d, col_e = st.columns([1, 2, 1])
                with col_d:
                    if st.form_submit_button(
                        f"{user_avatar} Log In",
                        use_container_width=True,
                        type="primary"
                    ):
                        if SecurityConfig.verify_password(username, password):
                            st.session_state.authenticated = True
                            st.session_state.role = username
                            st.session_state.user_display_name = SecurityConfig.USER_CREDENTIALS[username]["display_name"]
                            st.session_state.user_avatar = user_avatar
                            st.rerun()
                        else:
                            st.error("Invalid Credentials")
            
            st.markdown("""
            </div>
            """, unsafe_allow_html=True)
            
            # Footer
            st.markdown(f"""
            <div style="text-align: center; margin-top: 2rem; color: {C21_MEDIUM_GREY}; font-size: 0.9rem;">
                Version {AppConfig.VERSION} • Secure Enterprise Portal
            </div>
            """, unsafe_allow_html=True)

def render_task_card(task, current_user, show_actions=True):
    """Modern task card with enhanced visuals."""
    
    # Priority styling
    priority_colors = {
        1: {'bg': f'linear-gradient(135deg, {C21_RED_ALERT}20, {C21_RED_ALERT}10)', 'text': C21_RED_ALERT},
        2: {'bg': f'linear-gradient(135deg, {C21_ORANGE_WARNING}20, {C21_ORANGE_WARNING}10)', 'text': C21_ORANGE_WARNING},
        3: {'bg': f'linear-gradient(135deg, {C21_GREEN_SUCCESS}20, {C21_GREEN_SUCCESS}10)', 'text': C21_GREEN_SUCCESS}
    }
    
    priority_info = priority_colors.get(task['Priority'], priority_colors[3])
    
    # Status icon mapping
    status_icons = {
        'Assigned': '📋',
        'In Progress': '⚡',
        'On Hold': '⏸️',
        'Completed': '✅',
        'Archived': '📁'
    }
    
    # Calculate days until due
    if pd.notna(task['Due Date']):
        due_date = task['Due Date'].to_pydatetime().date()
        today = datetime.date.today()
        days_until = (due_date - today).days
        
        if days_until < 0:
            due_text = f"⏰ {abs(days_until)} days overdue"
            due_color = C21_RED_ALERT
            due_bg = f"{C21_RED_ALERT}15"
        elif days_until == 0:
            due_text = "⚠️ Due today"
            due_color = C21_ORANGE_WARNING
            due_bg = f"{C21_ORANGE_WARNING}15"
        elif days_until <= 3:
            due_text = f"⏳ Due in {days_until} days"
            due_color = C21_ORANGE_WARNING
            due_bg = f"{C21_ORANGE_WARNING}15"
        else:
            due_text = f"📅 Due in {days_until} days"
            due_color = C21_GREEN_SUCCESS
            due_bg = f"{C21_GREEN_SUCCESS}15"
    else:
        due_text = "No due date"
        due_color = C21_MEDIUM_GREY
        due_bg = f"{C21_MEDIUM_GREY}15"
    
    # Render card
    with st.container():
        st.markdown(f"""
        <div class="modern-card" style="
            margin-bottom: 1rem;
            padding: 1.5rem;
            border-left: 4px solid {priority_info['text']};
        ">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                        <h4 style="margin: 0; color: {C21_BLACK}; font-size: 1.1rem;">
                            #{task['ID']} • {task['Title']}
                        </h4>
                        <span style="
                            background: {priority_info['bg']};
                            color: {priority_info['text']};
                            padding: 4px 12px;
                            border-radius: 12px;
                            font-size: 0.75rem;
                            font-weight: 600;
                            border: 1px solid {priority_info['text']}30;
                        ">
                            <span class="priority-badge priority-{task['Priority']}"></span>
                            {PRIORITY_MAP.get(task['Priority'], 'Low')}
                        </span>
                    </div>
                    
                    <div style="color: {C21_MEDIUM_GREY}; font-size: 0.9rem; margin-bottom: 12px;">
                        {status_icons.get(task['Status'], '📋')} 
                        <span class="status-badge status-{task['Status'].replace(' ', '-')}">
                            {task['Status']}
                        </span>
                        • 👤 {task['Assigned To']} • ⏱️ {task.get('Time Spent (Hrs)', 0):.1f} hours
                    </div>
                </div>
                
                <div style="
                    background: {due_bg};
                    color: {due_color};
                    padding: 8px 16px;
                    border-radius: 12px;
                    font-size: 0.85rem;
                    font-weight: 500;
                    border: 1px solid {due_color}30;
                ">
                    {due_text}
                </div>
            </div>
            
            <div style="
                background: rgba(245, 245, 245, 0.5);
                padding: 12px;
                border-radius: 8px;
                margin: 12px 0;
                font-size: 0.95rem;
                color: {C21_DARK_GREY};
                border-left: 3px solid {C21_GOLD_LIGHT};
            ">
                {task['Description'][:200]}{'...' if len(task['Description']) > 200 else ''}
            </div>
            
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.85rem;
                color: {C21_MEDIUM_GREY};
                margin-top: 1rem;
                padding-top: 1rem;
                border-top: 1px solid rgba(0,0,0,0.05);
            ">
                <div>
                    📅 Started: {task['Start Date'].strftime('%b %d, %Y') if pd.notna(task['Start Date']) else 'Not started'}
                </div>
                <div>
                    🔄 Last updated: {task['Last Modified'].strftime('%b %d') if pd.notna(task['Last Modified']) else 'Never'}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if show_actions:
            render_task_actions(task, current_user)

def render_task_actions(task, current_user):
    """Task action buttons with modern design."""
    
    # Quick actions for Luke
    if current_user == "Luke" and task['Assigned To'] == "Luke":
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if task['Status'] not in ['In Progress', 'Completed', 'Archived']:
                if st.button("▶ Start", key=f"start_{task['ID']}", use_container_width=True):
                    DataManager.update_task(task['ID'], {
                        'Status': 'In Progress',
                        'Start Date': datetime.datetime.now().strftime('%Y-%m-%d')
                    }, current_user)
                    st.rerun()
        
        with col2:
            if task['Status'] == 'In Progress':
                if st.button("⏸ Hold", key=f"hold_{task['ID']}", use_container_width=True):
                    DataManager.update_task(task['ID'], {'Status': 'On Hold'}, current_user)
                    st.rerun()
        
        with col3:
            if task['Status'] not in ['Completed', 'Archived']:
                if st.button("✅ Complete", key=f"complete_{task['ID']}", use_container_width=True):
                    st.session_state[f'completing_{task["ID"]}'] = True
                    st.rerun()
        
        with col4:
            if st.button("🗑️ Archive", key=f"archive_{task['ID']}", use_container_width=True):
                DataManager.delete_task(task['ID'], current_user)
                st.rerun()
        
        # Completion dialog
        if st.session_state.get(f'completing_{task["ID"]}'):
            with st.expander(f"🎯 Complete Task #{task['ID']}", expanded=True):
                with st.form(f"finish_{task['ID']}"):
                    st.write("### Finalize Task Completion")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        final_hours = st.number_input(
                            "Total Hours Spent",
                            min_value=0.0,
                            step=0.5,
                            value=float(task.get('Time Spent (Hrs)', 0)),
                            format="%.1f"
                        )
                    with col_b:
                        completed_date = st.date_input(
                            "Completion Date",
                            value=datetime.date.today()
                        )
                    
                    final_comment = st.text_area(
                        "Completion Notes",
                        placeholder="Add any final comments or notes...",
                        height=100
                    )
                    
                    col_c, col_d = st.columns(2)
                    with col_c:
                        if st.form_submit_button("✅ Submit Completion", type="primary", use_container_width=True):
                            DataManager.update_task(task['ID'], {
                                'Status': 'Completed',
                                'Completed Date': completed_date,
                                'Time Spent (Hrs)': final_hours,
                                'Comments': f"{task['Comments']}\\n[Completed {datetime.datetime.now().strftime('%m/%d %H:%M')}]: {final_comment}".strip()
                            }, current_user)
                            del st.session_state[f'completing_{task["ID"]}']
                            st.rerun()
                    with col_d:
                        if st.form_submit_button("✖️ Cancel", use_container_width=True):
                            del st.session_state[f'completing_{task["ID"]}']
                            st.rerun()
    
    # Advanced edit for all users
    with st.expander(f"⚙️ Advanced Edit", icon="⚙️"):
        with st.form(f"advanced_edit_{task['ID']}"):
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                new_status = st.selectbox(
                    "Status",
                    STATUS_LEVELS,
                    index=STATUS_LEVELS.index(task['Status']) if task['Status'] in STATUS_LEVELS else 0
                )
            
            with col_b:
                new_hours = st.number_input(
                    "Hours Spent",
                    value=float(task.get('Time Spent (Hrs)', 0.0)),
                    step=0.5,
                    format="%.1f"
                )
            
            with col_c:
                new_priority = st.selectbox(
                    "Priority",
                    [1, 2, 3],
                    index=[1, 2, 3].index(task['Priority']) if task['Priority'] in [1, 2, 3] else 2,
                    format_func=lambda x: f"{x} - {PRIORITY_MAP[x]}"
                )
            
            new_comment = st.text_area(
                "Add Comment",
                placeholder="Type your comment here...",
                height=80,
                help="This will be appended to existing comments"
            )
            
            if st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                updates = {
                    'Status': new_status,
                    'Time Spent (Hrs)': new_hours,
                    'Priority': new_priority
                }
                
                if new_comment:
                    timestamp = datetime.datetime.now().strftime('%m/%d %H:%M')
                    updates['Comments'] = f"{task['Comments']}\\n[{timestamp} {current_user}]: {new_comment}".strip()
                
                DataManager.update_task(task['ID'], updates, current_user)
                st.rerun()

def render_notification_center():
    """Modern notification center."""
    notifications_df = NotificationManager.fetch_notifications()
    unread_count = NotificationManager.get_unread_count()
    
    if notifications_df.empty:
        st.info("📭 No notifications yet")
        return
    
    # Group by date
    notifications_df['Date'] = notifications_df['Timestamp'].dt.date
    grouped = notifications_df.groupby('Date')
    
    for date, group in grouped:
        st.markdown(f"### 📅 {date}")
        
        for _, notif in group.iterrows():
            # Determine icon based on action
            action_icons = {
                "Task Created": "🚀",
                "Task Updated": "✏️",
                "Task Completed": "✅",
                "Task Archived": "🗑️"
            }
            
            icon = action_icons.get(notif['Action'], "📢")
            read_style = "opacity: 0.7;" if notif['Read'] == 'Yes' else ""
            
            with st.container():
                st.markdown(f"""
                <div style="
                    {read_style}
                    padding: 1rem;
                    margin: 0.5rem 0;
                    background: {'rgba(76, 175, 80, 0.05)' if notif['Action'] == 'Task Completed' else 'white'};
                    border-radius: 12px;
                    border-left: 4px solid {C21_GOLD};
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                ">
                    <div style="display: flex; align-items: flex-start; gap: 12px;">
                        <div style="font-size: 1.2rem;">{icon}</div>
                        <div style="flex: 1;">
                            <div style="
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                                margin-bottom: 4px;
                            ">
                                <strong style="color: {C21_BLACK};">{notif['Action']}</strong>
                                <small style="color: {C21_MEDIUM_GREY}">
                                    {notif['Timestamp'].strftime('%H:%M')}
                                </small>
                            </div>
                            <div style="color: {C21_DARK_GREY}; margin-bottom: 4px;">
                                <strong>Task #{notif['Task ID']}:</strong> {notif['Title']}
                            </div>
                            <div style="color: {C21_MEDIUM_GREY}; font-size: 0.9em;">
                                👤 {notif['User']} • {notif['Details']}
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# --- 10. DASHBOARD VIEWS ---

def manager_view(df):
    """Enhanced manager dashboard."""
    current_user = "Burtch"
    
    # Header with stats
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        st.title(f"👑 Manager Dashboard")
        st.markdown(f"Welcome back, **{st.session_state.user_display_name}**")
    
    with col3:
        notifications_df = NotificationManager.fetch_notifications()
        unread_count = NotificationManager.get_unread_count()
        
        if unread_count > 0:
            st.markdown(f"""
            <div class="notification-bell" onclick="alert('{unread_count} unread notifications')">
                🔔 <span class="notification-count">{unread_count}</span>
            </div>
            """, unsafe_allow_html=True)
    
    # Quick stats
    active_mask = ~df['Status'].isin(['Completed', 'Archived'])
    active_df = df[active_mask]
    completed_df = df[df['Status'] == 'Completed']
    luke_tasks = df[df['Assigned To'] == 'Luke']
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{len(active_df)}</div>
            <div class="metric-lbl">Active Tasks</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        high_p = len(active_df[active_df['Priority'] == 1])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val" style="color:{C21_RED_ALERT}">{high_p}</div>
            <div class="metric-lbl">High Priority</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        today = pd.Timestamp.now().normalize()
        overdue = len(active_df[active_df['Due Date'] < today])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{overdue}</div>
            <div class="metric-lbl">Overdue</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        hrs = completed_df['Time Spent (Hrs)'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{hrs:.1f}</div>
            <div class="metric-lbl">Total Hours</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        luke_completed = len(luke_tasks[luke_tasks['Status'] == 'Completed'])
        luke_total = len(luke_tasks)
        completion_rate = int((luke_completed / luke_total * 100) if luke_total > 0 else 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{completion_rate}%</div>
            <div class="metric-lbl">Luke's Rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Modern tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🚀 Create Task",
        "📋 Task Board",
        "📊 Analytics",
        "🔔 Notifications",
        "⚙️ Settings"
    ])
    
    # Tab 1: Create Task
    with tab1:
        st.subheader("Create New Task")
        
        with st.form("create_task", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                title = st.text_input(
                    "Task Title",
                    placeholder="Enter task title...",
                    help="Be descriptive and clear"
                )
            with col_b:
                assignee = st.selectbox(
                    "Assign To",
                    ["Luke", "Burtch"],
                    format_func=lambda x: f"{'👤 ' if x == 'Luke' else '👑 '}{x}"
                )
            
            col_c, col_d, col_e = st.columns(3)
            with col_c:
                start_date = st.date_input(
                    "Start Date",
                    value=datetime.date.today(),
                    help="When work should begin"
                )
            with col_d:
                due_date = st.date_input(
                    "Due Date",
                    value=datetime.date.today() + datetime.timedelta(days=3),
                    help="When task should be completed"
                )
            with col_e:
                priority = st.selectbox(
                    "Priority",
                    [1, 2, 3],
                    index=1,
                    format_func=lambda x: f"{'🔴' if x == 1 else '🟡' if x == 2 else '🟢'} {PRIORITY_MAP[x]}"
                )
            
            description = st.text_area(
                "Description",
                placeholder="Provide detailed description of the task...",
                height=120,
                help="Include requirements, context, and expected outcomes"
            )
            
            col_f, col_g = st.columns(2)
            with col_f:
                create_drive = st.checkbox(
                    "Create Google Drive Folder",
                    value=True,
                    help="Automatically create a folder for task files"
                )
            with col_g:
                notify_user = st.checkbox(
                    "Send Notification",
                    value=True,
                    help="Send notification to assigned user"
                )
            
            if st.form_submit_button("🚀 Create Task", type="primary", use_container_width=True):
                if not title:
                    st.error("Task title is required!")
                else:
                    new_id = int(time.time() * 1000) % 1000000
                    drive_link = ""
                    
                    if create_drive:
                        drive_link = DataManager.create_drive_folder(f"{new_id}_{title}")
                    
                    new_task = {
                        'ID': new_id,
                        'Title': title,
                        'Assigned To': assignee,
                        'Start Date': start_date,
                        'Due Date': due_date,
                        'Priority': priority,
                        'Status': 'Assigned',
                        'Description': description,
                        'Google Drive Link': drive_link,
                        'Created By': current_user,
                        'Created At': datetime.datetime.now(),
                        'Last Modified': datetime.datetime.now(),
                        'Time Spent (Hrs)': 0
                    }
                    
                    if DataManager.add_task(new_task):
                        if notify_user and assignee == "Luke":
                            send_browser_notification(
                                "Task Assigned",
                                f"New task: {title}",
                                new_id
                            )
                        st.rerun()
    
    # Tab 2: Task Board
    with tab2:
        st.subheader("Task Management Board")
        
        # Filters
        col_filter1, col_filter2, col_filter3, col_filter4 = st.columns([2, 2, 2, 1])
        
        with col_filter1:
            filter_status = st.multiselect(
                "Status",
                STATUS_LEVELS,
                default=['Assigned', 'In Progress'],
                label_visibility="collapsed",
                placeholder="Filter by status..."
            )
        
        with col_filter2:
            filter_user = st.selectbox(
                "Assigned To",
                ["All", "Luke", "Burtch"],
                label_visibility="collapsed"
            )
        
        with col_filter3:
            filter_priority = st.multiselect(
                "Priority",
                ["High", "Medium", "Low"],
                default=[],
                label_visibility="collapsed",
                placeholder="Filter by priority..."
            )
        
        with col_filter4:
            show_archived = st.checkbox("Show Archived", value=False)
        
        # Apply filters
        view_df = df.copy()
        
        if filter_status:
            view_df = view_df[view_df['Status'].isin(filter_status)]
        
        if filter_user != "All":
            view_df = view_df[view_df['Assigned To'] == filter_user]
        
        if filter_priority:
            priority_map_rev = {v: k for k, v in PRIORITY_MAP.items()}
            selected_priorities = [priority_map_rev[p] for p in filter_priority if p in priority_map_rev]
            view_df = view_df[view_df['Priority'].isin(selected_priorities)]
        
        if not show_archived:
            view_df = view_df[view_df['Status'] != 'Archived']
        
        # Sort and display
        sort_by = st.selectbox(
            "Sort by",
            ["Priority", "Due Date", "Created Date", "Title"],
            index=0
        )
        
        sort_columns = {
            "Priority": ['Priority', 'Due Date'],
            "Due Date": ['Due Date', 'Priority'],
            "Created Date": ['Created At', 'Priority'],
            "Title": ['Title', 'Priority']
        }
        
        view_df = view_df.sort_values(sort_columns[sort_by])
        
        if view_df.empty:
            st.info("📭 No tasks match your filters")
        else:
            for i, (_, row) in enumerate(view_df.iterrows()):
                render_task_card(row, current_user)
    
    # Tab 3: Analytics
    with tab3:
        st.subheader("📈 Performance Analytics")
        
        col_anal1, col_anal2 = st.columns(2)
        
        with col_anal1:
            st.markdown("### Luke's Performance")
            
            # Calculate metrics
            luke_active = luke_tasks[~luke_tasks['Status'].isin(['Completed', 'Archived'])]
            luke_completed = luke_tasks[luke_tasks['Status'] == 'Completed']
            
            # Progress chart
            if not luke_completed.empty:
                fig_completion = px.bar(
                    luke_completed.groupby(luke_completed['Completed Date'].dt.to_period('M')).size().reset_index(name='Count'),
                    x='Completed Date',
                    y='Count',
                    title="Monthly Completion Rate",
                    color_discrete_sequence=[C21_GOLD]
                )
                st.plotly_chart(fig_completion, use_container_width=True)
            
            # Hours chart
            if not luke_completed.empty:
                fig_hours = px.pie(
                    luke_completed,
                    values='Time Spent (Hrs)',
                    names='Priority',
                    title="Hours by Priority",
                    color_discrete_sequence=[C21_RED_ALERT, C21_ORANGE_WARNING, C21_GREEN_SUCCESS]
                )
                st.plotly_chart(fig_hours, use_container_width=True)
        
        with col_anal2:
            st.markdown("### Team Overview")
            
            # Status distribution
            fig_status = px.pie(
                df,
                names='Status',
                title="Overall Status Distribution",
                color_discrete_sequence=[C21_GOLD, C21_BLUE_INFO, C21_ORANGE_WARNING, C21_GREEN_SUCCESS, C21_DARK_GREY]
            )
            st.plotly_chart(fig_status, use_container_width=True)
            
            # Report generation
            st.markdown("### 📊 Generate Report")
            
            col_report1, col_report2 = st.columns(2)
            with col_report1:
                report_start = st.date_input(
                    "Start Date",
                    value=datetime.date.today() - datetime.timedelta(days=30),
                    key="report_start"
                )
            with col_report2:
                report_end = st.date_input(
                    "End Date",
                    value=datetime.date.today(),
                    key="report_end"
                )
            
            if st.button("📥 Generate Luke's Report", type="primary", use_container_width=True):
                html_report = ReportGenerator.generate_html_report(df, report_start, report_end, "Luke")
                
                # Preview
                st.components.v1.html(html_report, height=600, scrolling=True)
                
                # Download button
                st.download_button(
                    "💾 Download HTML Report",
                    data=html_report,
                    file_name=f"Luke_Performance_Report_{report_start}_{report_end}.html",
                    mime="text/html",
                    use_container_width=True
                )
    
    # Tab 4: Notifications
    with tab4:
        st.subheader("🔔 Notification Center")
        
        # Notification stats
        notif_col1, notif_col2, notif_col3 = st.columns(3)
        
        with notif_col1:
            total_notifs = len(notifications_df)
            st.metric("Total Notifications", total_notifs)
        
        with notif_col2:
            st.metric("Unread", unread_count)
        
        with notif_col3:
            today_notifs = len(notifications_df[notifications_df['Timestamp'].dt.date == datetime.date.today()])
            st.metric("Today", today_notifs)
        
        # Notification list
        render_notification_center()
    
    # Tab 5: Settings
    with tab5:
        st.subheader("⚙️ Application Settings")
        
        col_set1, col_set2 = st.columns(2)
        
        with col_set1:
            st.markdown("#### Notification Settings")
            
            enable_notifs = st.checkbox(
                "Enable Browser Notifications",
                value=True,
                help="Show desktop notifications for task updates"
            )
            
            notify_on_assign = st.checkbox(
                "Notify on Task Assignment",
                value=True,
                help="Send notification when task is assigned"
            )
            
            notify_on_complete = st.checkbox(
                "Notify on Completion",
                value=True,
                help="Send notification when task is completed"
            )
            
            if st.button("🔔 Test Notification", use_container_width=True):
                send_browser_notification(
                    "Test Notification",
                    "This is a test notification from TaskFlow Pro",
                    999
                )
                st.success("Test notification sent!")
        
        with col_set2:
            st.markdown("#### Data Settings")
            
            cache_ttl = st.slider(
                "Cache Duration (minutes)",
                min_value=1,
                max_value=60,
                value=5,
                help="How long to cache data before refreshing"
            )
            
            auto_refresh = st.checkbox(
                "Auto-refresh Data",
                value=True,
                help="Automatically refresh data periodically"
            )
            
            if st.button("🔄 Clear Cache", use_container_width=True):
                st.cache_data.clear()
                st.success("Cache cleared successfully!")
                time.sleep(1)
                st.rerun()

def user_view(df):
    """Enhanced user dashboard for Luke."""
    current_user = "Luke"
    
    # Header
    col1, col2, col3 = st.columns([3, 2, 1])
    
    with col1:
        st.title(f"🚀 Welcome, Luke Wise!")
        st.markdown("Your personal task workspace")
    
    with col3:
        # Notification bell
        notifications_df = NotificationManager.fetch_notifications()
        unread_count = NotificationManager.get_unread_count()
        
        if unread_count > 0:
            st.markdown(f"""
            <div class="notification-bell" onclick="alert('{unread_count} unread notifications')">
                🔔 <span class="notification-count">{unread_count}</span>
            </div>
            """, unsafe_allow_html=True)
    
    # Luke's tasks only
    luke_tasks = df[df['Assigned To'] == current_user]
    active_mask = ~luke_tasks['Status'].isin(['Completed', 'Archived'])
    active_df = luke_tasks[active_mask]
    completed_df = luke_tasks[luke_tasks['Status'] == 'Completed']
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{len(active_df)}</div>
            <div class="metric-lbl">Active Tasks</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        high_p = len(active_df[active_df['Priority'] == 1])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val" style="color:{C21_RED_ALERT}">{high_p}</div>
            <div class="metric-lbl">Urgent</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        today = pd.Timestamp.now().normalize()
        overdue = len(active_df[active_df['Due Date'] < today])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{overdue}</div>
            <div class="metric-lbl">Overdue</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        hrs = completed_df['Time Spent (Hrs)'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{hrs:.1f}</div>
            <div class="metric-lbl">Total Hours</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "🎯 My Tasks",
        "📊 My Progress",
        "🔔 Notifications"
    ])
    
    # Tab 1: My Tasks
    with tab1:
        # Check for overdue tasks
        overdue_tasks = active_df[active_df['Due Date'] < today]
        due_today = active_df[active_df['Due Date'] == today]
        upcoming = active_df[active_df['Due Date'] > today]
        
        if not overdue_tasks.empty:
            st.error(f"⚠️ **{len(overdue_tasks)} Overdue Tasks**")
            for _, row in overdue_tasks.iterrows():
                render_task_card(row, current_user)
        
        if not due_today.empty:
            st.warning(f"🔥 **{len(due_today)} Due Today**")
            for _, row in due_today.iterrows():
                render_task_card(row, current_user)
        
        st.markdown(f"### 📋 Upcoming Tasks ({len(upcoming)})")
        
        if upcoming.empty:
            st.info("🎉 No upcoming tasks! You're all caught up.")
        else:
            # Sort by priority and due date
            upcoming = upcoming.sort_values(['Priority', 'Due Date'])
            for _, row in upcoming.iterrows():
                render_task_card(row, current_user)
    
    # Tab 2: My Progress
    with tab2:
        col_prog1, col_prog2 = st.columns(2)
        
        with col_prog1:
            # Completion rate
            total_tasks = len(luke_tasks)
            completed_tasks = len(completed_df)
            completion_rate = int((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0)
            
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 3rem; font-weight: 700; color: {C21_GOLD};">
                    {completion_rate}%
                </div>
                <div style="color: {C21_MEDIUM_GREY};">
                    Overall Completion Rate
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Recent activity
            st.markdown("### 📈 Recent Activity")
            
            if not completed_df.empty:
                recent_completed = completed_df.sort_values('Completed Date', ascending=False).head(5)
                
                for _, task in recent_completed.iterrows():
                    st.markdown(f"""
                    <div style="
                        padding: 12px;
                        margin: 8px 0;
                        background: {C21_LIGHT_GREY};
                        border-radius: 10px;
                        border-left: 4px solid {C21_GREEN_SUCCESS};
                    ">
                        <strong>{task['Title']}</strong><br>
                        <small style="color: {C21_MEDIUM_GREY}">
                            ✅ Completed on {task['Completed Date'].strftime('%b %d')} • 
                            ⏱️ {task['Time Spent (Hrs)']:.1f} hours
                        </small>
                    </div>
                    """, unsafe_allow_html=True)
        
        with col_prog2:
            # Hours chart
            if not completed_df.empty:
                # Group by week
                completed_df['Week'] = completed_df['Completed Date'].dt.to_period('W').apply(lambda r: r.start_time)
                weekly_hours = completed_df.groupby('Week')['Time Spent (Hrs)'].sum().reset_index()
                
                if not weekly_hours.empty:
                    fig_hours = px.bar(
                        weekly_hours.tail(8),  # Last 8 weeks
                        x='Week',
                        y='Time Spent (Hrs)',
                        title="Weekly Hours Logged",
                        color_discrete_sequence=[C21_GOLD]
                    )
                    st.plotly_chart(fig_hours, use_container_width=True)
            
            # Performance metrics
            st.markdown("### 📊 Performance Metrics")
            
            avg_hours = completed_df['Time Spent (Hrs)'].mean() if not completed_df.empty else 0
            avg_duration = None
            
            if not completed_df.empty:
                completed_df['Duration'] = (completed_df['Completed Date'] - completed_df['Start Date']).dt.days
                avg_duration = completed_df['Duration'].mean()
            
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric("Avg Hours/Task", f"{avg_hours:.1f}")
            with metric_col2:
                if avg_duration:
                    st.metric("Avg Duration", f"{avg_duration:.0f} days")
    
    # Tab 3: Notifications
    with tab3:
        render_notification_center()

# --- 11. MAIN APPLICATION ---
def main():
    # Configure page
    st.set_page_config(
        page_title=f"{AppConfig.APP_NAME} - {AppConfig.APP_SUBTITLE}",
        layout="wide",
        page_icon="🏠",
        initial_sidebar_state="expanded"
    )
    
    # Inject custom CSS and JavaScript
    inject_custom_css()
    inject_notification_js()
    
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'user_display_name' not in st.session_state:
        st.session_state.user_display_name = ""
    if 'user_avatar' not in st.session_state:
        st.session_state.user_avatar = ""
    
    # Authentication flow
    if not st.session_state.authenticated:
        render_login()
        return
    
    # Modern sidebar
    with st.sidebar:
        # User profile section
        st.markdown(f"""
        <div style="
            text-align: center;
            padding: 2rem 1rem;
            background: linear-gradient(135deg, rgba(190, 175, 135, 0.1), rgba(190, 175, 135, 0.05));
            border-radius: 16px;
            margin-bottom: 2rem;
            border: 1px solid rgba(190, 175, 135, 0.2);
        ">
            <div style="font-size: 3rem; margin-bottom: 1rem;">
                {st.session_state.user_avatar}
            </div>
            <h3 style="margin: 0; color: {C21_BLACK};">
                {st.session_state.user_display_name}
            </h3>
            <div style="
                display: inline-block;
                background: {C21_GOLD}20;
                color: {C21_GOLD_DARK};
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 0.85rem;
                font-weight: 600;
                margin-top: 0.5rem;
                border: 1px solid {C21_GOLD}40;
            ">
                {st.session_state.role}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation
        st.markdown("## 📍 Navigation")
        
        # Quick actions
        col_sb1, col_sb2 = st.columns(2)
        with col_sb1:
            if st.button("🔄 Refresh", use_container_width=True, help="Refresh all data"):
                st.cache_data.clear()
                st.toast("Data refreshed from Google Sheets")
                st.rerun()
        
        with col_sb2:
            if st.button("📊 Reports", use_container_width=True, help="View reports"):
                st.session_state.show_reports = True
        
        # Check for due today notifications
        if st.session_state.role == "Luke":
            df = DataManager.fetch_data()
            luke_tasks = df[df['Assigned To'] == "Luke"]
            today = pd.Timestamp.now().normalize()
            due_today = luke_tasks[
                (luke_tasks['Status'].isin(['Assigned', 'In Progress'])) &
                (luke_tasks['Due Date'] == today)
            ]
            
            if not due_today.empty:
                st.markdown("---")
                st.warning(f"⚠️ **{len(due_today)} tasks due today!**")
                
                for _, task in due_today.iterrows():
                    with st.expander(f"#{task['ID']} {task['Title'][:30]}..."):
                        st.write(task['Description'][:100])
                        if st.button("Start", key=f"sidebar_start_{task['ID']}", use_container_width=True):
                            DataManager.update_task(task['ID'], {
                                'Status': 'In Progress',
                                'Start Date': datetime.datetime.now().strftime('%Y-%m-%d')
                            }, "Luke")
                            st.rerun()
        
        # App info
        st.markdown("---")
        st.markdown(f"""
        <div style="
            padding: 1rem;
            background: {C21_LIGHT_GREY};
            border-radius: 12px;
            font-size: 0.85rem;
            color: {C21_MEDIUM_GREY};
        ">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span>Version:</span>
                <strong>{AppConfig.VERSION}</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span>Last Sync:</span>
                <strong>{datetime.datetime.now().strftime('%H:%M')}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Logout button
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            st.session_state.clear()
            st.rerun()
    
    # Main content area
    try:
        # Initialize Google services
        if 'google_initialized' not in st.session_state:
            with st.spinner("🔗 Connecting to Google Services..."):
                if initialize_google_services():
                    # Ensure sheets exist
                    DataManager.ensure_sheet_headers(AppConfig.SHEET_ID, "Task Log", COLUMNS)
                    DataManager.ensure_sheet_headers(AppConfig.SHEET_ID, "Notifications Log", NOTIFICATION_COLUMNS)
                    st.toast("✅ Connected to Google Sheets")
                else:
                    st.error("Failed to initialize Google services")
                    st.stop()
        
        # Load data with progress indicator
        with st.spinner("📊 Loading task data..."):
            df = DataManager.fetch_data()
        
        # Send due date notifications (only for Luke)
        if st.session_state.role == "Luke":
            today = datetime.date.today()
            luke_tasks = df[df['Assigned To'] == "Luke"]
            active_tasks = luke_tasks[~luke_tasks['Status'].isin(['Completed', 'Archived'])]
            
            for _, task in active_tasks.iterrows():
                if pd.notna(task['Due Date']):
                    due_date = task['Due Date'].to_pydatetime().date()
                    days_until = (due_date - today).days
                    
                    # Send notification for tasks due today
                    if days_until == 0 and not st.session_state.get(f'notified_today_{task["ID"]}'):
                        send_browser_notification(
                            "Due Today ⏰",
                            f"Task '{task['Title']}' is due today!",
                            task['ID']
                        )
                        st.session_state[f'notified_today_{task["ID"]}'] = True
        
        # Route to appropriate view
        if st.session_state.role == "Burtch":
            manager_view(df)
        elif st.session_state.role == "Luke":
            user_view(df)
            
    except Exception as e:
        st.error(f"❌ Application Error")
        
        # Show error details
        with st.expander("🔧 Technical Details", expanded=False):
            st.code(traceback.format_exc())
        
        # Recovery options
        col_err1, col_err2 = st.columns(2)
        with col_err1:
            if st.button("🔄 Retry Connection", use_container_width=True):
                if 'google_initialized' in st.session_state:
                    del st.session_state.google_initialized
                st.rerun()
        
        with col_err2:
            if st.button("📋 Copy Error", use_container_width=True):
                st.code(traceback.format_exc())
                st.toast("Error details copied to clipboard (manually)")

if __name__ == "__main__":
    main()
