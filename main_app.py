import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import time
import hashlib # Re-included for enterprise-grade standard, though simplified logic is used below
from dataclasses import dataclass
from typing import Dict, List, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
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
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2

@dataclass
class AppConfig:
    """Enterprise application configuration"""
    APP_NAME = "Task Manager - The Burtch Team"
    VERSION = "3.1.0 (Notification Integrated)"
    # NOTE: Replace this with your actual Google Sheet ID
    SHEET_ID = "1iIBoWSZSvV-SF9u2Cxi-_fbYgg06-XI32UgF1ZJIxh4"
    DRIVE_FOLDER_ID = ""  # Set your Drive folder ID here
    SESSION_TIMEOUT_MINUTES = 60

class SecurityConfig:
    # WARNING: Direct string passwords are INSECURE.
    # Replace these with real credentials and implement SHA-256 hashing.
    USER_CREDENTIALS = {
        "Burtch": {
            "password": "jayson0922", 
            "role": "Burtch",
            "display_name": "The Burtch Team"
        },
        "Luke": {
            "password": "luke29430",
            "role": "Luke",
            "display_name": "Luke Wise"
        }
    }
    
    @staticmethod
    def verify_password(username: str, password: str) -> bool:
        """Verifies password using direct string comparison (Simple Auth)."""
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
    'Timestamp', 'Task ID', 'Title', 'User', 'Action', 'Details'
]

STATUS_LEVELS = ['Assigned', 'In Progress', 'On Hold', 'Completed', 'Archived']
PRIORITY_LEVELS = [1, 2, 3]  # 1=High, 2=Medium, 3=Low

# --- 3. ENTERPRISE STYLING ---
def inject_custom_css():
    st.markdown(f"""
        <style>
            .stApp {{ background-color: {C21_LIGHT_GREY}; }}
            
            /* Sidebar */
            [data-testid="stSidebar"] {{
                background-color: {C21_BLACK};
                border-right: 2px solid {C21_GOLD};
            }}
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
                color: {C21_GOLD} !important;
            }}
            
            /* Cards & Containers */
            .task-card, .metric-box {{
                background: {C21_WHITE};
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                transition: transform 0.2s;
            }}
            .task-card:hover {{ transform: translateY(-3px); }}
            
            /* Metrics */
            .metric-box {{
                padding: 20px;
                text-align: center;
                border: 1px solid #eee;
            }}
            .metric-val {{ font-size: 2.2rem; font-weight: 700; color: {C21_BLACK}; }}
            .metric-lbl {{ color: #666; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }}

            /* Buttons */
            div.stButton > button {{
                border-radius: 8px;
                font-weight: 600;
                border: 1px solid #ccc;
            }}
            div.stButton > button[kind="primary"] {{
                background-color: {C21_GOLD};
                color: {C21_BLACK};
                border: 1px solid {C21_GOLD};
            }}
            
            /* Status Indicators */
            .status-badge {{
                font-weight: bold; padding: 4px 10px; border-radius: 4px; font-size: 0.8em;
                display: inline-block;
            }}
            .status-Completed {{ background: {C21_GREEN_SUCCESS}1A; color: {C21_GREEN_SUCCESS}; border: 1px solid {C21_GREEN_SUCCESS}; }}
            .status-In-Progress {{ background: {C21_BLUE_INFO}1A; color: {C21_BLUE_INFO}; border: 1px solid {C21_BLUE_INFO}; }}
            .status-On-Hold {{ background: orange1A; color: orange; border: 1px solid orange; }}
            .status-Assigned {{ background: {C21_DARK_GREY}1A; color: {C21_DARK_GREY}; border: 1px solid {C21_DARK_GREY}; }}
            
        </style>
    """, unsafe_allow_html=True)

# --- 4. GOOGLE SERVICES INITIALIZATION ---
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
                scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
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

# --- 5. DATA MANAGER ---
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
            # Try to read the first row
            result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range_name).execute()
            existing_headers = result.get('values', [[]])[0]
            
            if not existing_headers or existing_headers != columns:
                # Update headers if they are missing or mismatched
                body = {'values': [columns]}
                service.spreadsheets().values().update(
                    spreadsheetId=sheet_id, range=range_name,
                    valueInputOption='USER_ENTERED', body=body
                ).execute()
                st.toast(f"✅ Headers updated for '{sheet_name}'.")
        except HttpError as e:
            # If the sheet (tab) doesn't exist, this will typically throw a 400 error.
            if e.resp.status == 400 and 'Unable to parse range' in str(e):
                # Create the sheet tab
                requests = [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
                body = {'requests': requests}
                service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()
                st.toast(f"✅ Created new tab: '{sheet_name}'.")
                
                # Write the headers to the new tab
                body = {'values': [columns]}
                service.spreadsheets().values().update(
                    spreadsheetId=sheet_id, range=range_name,
                    valueInputOption='USER_ENTERED', body=body
                ).execute()
            else:
                st.warning(f"Header check failed for '{sheet_name}': {e}")


    @staticmethod
    @st.cache_data(ttl=300) # Enterprise-grade caching for 5 minutes
    def fetch_data() -> pd.DataFrame:
        """Fetch data, fix the column mismatch bug, and normalize types."""
        service = DataManager._get_service()
        
        # Request data for all 15 columns (A:O)
        result = service.spreadsheets().values().get(
            spreadsheetId=AppConfig.SHEET_ID, range="Task Log!A:O"
        ).execute()
        values = result.get('values', [])
        
        if len(values) < 2:
            return pd.DataFrame(columns=COLUMNS)
            
        # --- BUG FIX: PAD ROWS TO PREVENT COLUMN MISMATCH ---
        expected_cols = len(COLUMNS)
        padded_values = []
        for row in values[1:]:
            # Ensure every row has exactly 15 elements, even if they are empty
            if len(row) < expected_cols:
                row.extend([""] * (expected_cols - len(row)))
            padded_values.append(row[:expected_cols]) # Truncate if somehow too many columns
            
        df = pd.DataFrame(padded_values, columns=COLUMNS)
        
        # Type Conversion
        df['ID'] = pd.to_numeric(df['ID'], errors='coerce')
        df['Priority'] = pd.to_numeric(df['Priority'], errors='coerce').fillna(3).astype('Int64')
        df['Time Spent (Hrs)'] = pd.to_numeric(df['Time Spent (Hrs)'], errors='coerce').fillna(0.0)
        
        # Date Conversion
        date_cols = ['Due Date', 'Start Date', 'Completed Date', 'Created At', 'Last Modified']
        for col in date_cols:
            # Use format specified by Google Sheets API if available, otherwise 'coerce'
            df[col] = pd.to_datetime(df[col], errors='coerce')
            
        return df

    @staticmethod
    def add_task(task_data: dict):
        """Append new task to the Task Log."""
        service = DataManager._get_service()
        row = [task_data.get(c, "") for c in COLUMNS]
        # Format dates for string serialization
        for idx, val in enumerate(row):
            if isinstance(val, (datetime.date, datetime.datetime)):
                row[idx] = val.strftime('%Y-%m-%d %H:%M:%S')
                
        service.spreadsheets().values().append(
            spreadsheetId=AppConfig.SHEET_ID, range="Task Log!A:A",
            valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
            body={"values": [row]}
        ).execute()
        st.cache_data.clear()
        st.toast("🚀 Task Created Successfully!", icon="✅")

    @staticmethod
    def update_task(task_id: int, updates: dict, current_user: str):
        """Updates a task and logs notification."""
        service = DataManager._get_service()
        
        # 1. Fetch current ID column to find row index
        result = service.spreadsheets().values().get(
            spreadsheetId=AppConfig.SHEET_ID, range="Task Log!A:A"
        ).execute()
        ids = [row[0] if row else '' for row in result.get('values', [])]
        
        try:
            row_idx = ids.index(str(task_id)) + 1
        except ValueError:
            raise Exception(f"Task ID {task_id} not found in sheet.")

        # 2. Get current row data for comparison
        current_row_res = service.spreadsheets().values().get(
            spreadsheetId=AppConfig.SHEET_ID, range=f"Task Log!A{row_idx}:O{row_idx}"
        ).execute()
        current_row_values = current_row_res.get('values', [[]])[0]
        while len(current_row_values) < len(COLUMNS):
            current_row_values.append("")
        current_task = dict(zip(COLUMNS, current_row_values))

        # 3. Apply updates and track changes for notification
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
                    changes.append(f"{col} changed from '{old_val}' to '{formatted_val}'")
                
                new_row[idx] = formatted_val

        new_row[COLUMNS.index('Last Modified')] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 4. Write back
        service.spreadsheets().values().update(
            spreadsheetId=AppConfig.SHEET_ID, 
            range=f"Task Log!A{row_idx}:O{row_idx}",
            valueInputOption="USER_ENTERED", 
            body={"values": [new_row]}
        ).execute()

        # 5. Log Notification
        if changes or updates.get('Comments'):
            NotificationManager.log_update(
                task_id=task_id,
                title=task_title,
                user=current_user,
                action="Task Updated",
                details="; ".join(changes) or updates.get('Comments', 'No explicit details.')
            )

        st.cache_data.clear()
        st.toast("✅ Task Updated!", icon="👍")

    @staticmethod
    def create_drive_folder(folder_name):
        """Create a folder in Drive for a new task."""
        if 'DRIVE_SERVICE' not in st.session_state: return ""
        try:
            service = st.session_state.DRIVE_SERVICE
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if AppConfig.DRIVE_FOLDER_ID:
                metadata['parents'] = [AppConfig.DRIVE_FOLDER_ID]
                
            file = service.files().create(body=metadata, fields='webViewLink').execute()
            return file.get('webViewLink')
        except Exception:
            st.warning("Could not create Drive folder. Check API scopes/permissions.")
            return ""

# --- 6. NOTIFICATION MANAGER ---
class NotificationManager:
    @staticmethod
    def log_update(task_id: int, title: str, user: str, action: str, details: str):
        """Logs a critical task update to the dedicated Notifications Log sheet."""
        service = DataManager._get_service()
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_row = [
            timestamp,
            task_id,
            title,
            user,
            action,
            details
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
    @st.cache_data(ttl=60) # Cache notifications for 1 minute
    def fetch_notifications() -> pd.DataFrame:
        """Fetches the full notification history."""
        service = DataManager._get_service()
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=AppConfig.SHEET_ID, range="Notifications Log!A:F"
            ).execute()
            values = result.get('values', [])
            
            if len(values) < 2:
                return pd.DataFrame(columns=NOTIFICATION_COLUMNS)
                
            df = pd.DataFrame(values[1:], columns=NOTIFICATION_COLUMNS)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
            df['Task ID'] = pd.to_numeric(df['Task ID'], errors='coerce').astype('Int64')
            
            return df.sort_values('Timestamp', ascending=False).dropna(subset=['Timestamp'])
        except Exception:
            return pd.DataFrame(columns=NOTIFICATION_COLUMNS)


# --- 7. REPORT GENERATOR (HTML/INFOGRAPHIC) ---
class ReportGenerator:
    @staticmethod
    def generate_html_report(df: pd.DataFrame, start_date, end_date):
        """Generates a styled HTML report string for printing/downloading"""
        
        # Filter Data
        mask = (df['Created At'].dt.date >= start_date) & (df['Created At'].dt.date <= end_date)
        period_df = df[mask]
        completed = period_df[period_df['Status'] == 'Completed']
        
        # Metrics
        total_tasks = len(period_df)
        completed_count = len(completed)
        completion_rate = int((completed_count / total_tasks * 100) if total_tasks > 0 else 0)
        total_hours = completed['Time Spent (Hrs)'].sum()
        avg_priority = completed['Priority'].mean() if completed_count > 0 else 0
        
        # Plotly chart (Rendered as image or Base64 embed for full self-contained report)
        fig_status = px.pie(period_df, names='Status', title="Task Status Distribution")
        chart_html = fig_status.to_html(full_html=False, include_plotlyjs='cdn')

        # HTML Template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Report - Luke Wise</title>
            <style>
                body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #333; max-width: 900px; margin: 0 auto; padding: 20px; }}
                .header {{ border-bottom: 4px solid {C21_GOLD}; padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; }}
                .logo {{ color: {C21_GOLD}; font-size: 28px; font-weight: bold; }}
                .title {{ font-size: 32px; color: {C21_BLACK}; margin: 0; }}
                
                .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }}
                .metric-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border: 1px solid #ddd; }}
                .metric-val {{ font-size: 36px; font-weight: bold; color: {C21_GOLD}; margin-bottom: 5px; }}
                .metric-lbl {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #555; }}
                
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 14px; }}
                th {{ background-color: {C21_BLACK}; color: white; padding: 12px; text-align: left; }}
                td {{ border-bottom: 1px solid #eee; padding: 12px; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                
                .chart-container {{ margin-top: 40px; border: 1px solid #ddd; padding: 20px; border-radius: 8px; background: white; }}

                .footer {{ margin-top: 50px; font-size: 12px; color: #999; text-align: center; border-top: 1px solid #eee; padding-top: 20px; }}
                
                @media print {{
                    body {{ -webkit-print-color-adjust: exact; }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div>
                    <div class="logo">The Burtch Team</div>
                    <div class="subtitle">Task Performance Report</div>
                </div>
                <div style="text-align: right;">
                    <div><strong>Employee:</strong> Luke Wise</div>
                    <div>{start_date} to {end_date}</div>
                </div>
            </div>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-val">{total_tasks}</div>
                    <div class="metric-lbl">Total Tasks Assigned</div>
                </div>
                <div class="metric-card">
                    <div class="metric-val">{completed_count}</div>
                    <div class="metric-lbl">Tasks Completed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-val">{completion_rate}%</div>
                    <div class="metric-lbl">Completion Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-val">{total_hours:.1f}</div>
                    <div class="metric-lbl">Total Hours Logged</div>
                </div>
            </div>

            <div class="chart-container">
                <h3>📊 Task Status Distribution</h3>
                {chart_html}
            </div>
            
            <h3>📋 Completed Tasks Summary ({completed_count} items)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Task Title</th>
                        <th>Completed Date</th>
                        <th>Hours Logged</th>
                        <th>Priority</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for _, row in completed.iterrows():
            p_map = {1: 'High', 2: 'Medium', 3: 'Low'}
            c_date = row['Completed Date'].strftime('%Y-%m-%d') if pd.notna(row['Completed Date']) else '-'
            html += f"""
                <tr>
                    <td><strong>#{row['ID']}</strong> {row['Title']}</td>
                    <td>{c_date}</td>
                    <td>{row['Time Spent (Hrs)']}</td>
                    <td>{p_map.get(row['Priority'], 'Low')}</td>
                </tr>
            """
            
        html += """
                </tbody>
            </table>
            
            <div class="footer">
                Generated by Task Manager v3.1 | The Burtch Team
            </div>
        </body>
        </html>
        """
        return html

# --- 8. UI COMPONENTS ---

def render_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"<h1 style='text-align: center; color: {C21_GOLD};'>🏠 Task Manager</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Enterprise Edition v3.1</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            role_display = st.selectbox("Select User", ["The Burtch Team", "Luke Wise"])
            username = "Burtch" if role_display == "The Burtch Team" else "Luke"
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Log In", use_container_width=True, type="primary"):
                if SecurityConfig.verify_password(username, password):
                    st.session_state.authenticated = True
                    st.session_state.role = username
                    st.rerun()
                else:
                    st.error("Invalid Credentials")

def render_task_card(task, current_user, index):
    """Card View with Action Buttons"""
    
    # Styling variables
    p_color = {1: C21_RED_ALERT, 2: "#FF9800", 3: C21_GREEN_SUCCESS}
    p_text = {1: "HIGH", 2: "MED", 3: "LOW"}
    
    border_color = p_color.get(task['Priority'], "#ccc")
    
    with st.container():
        st.markdown(f"""
        <div class="task-card" style="border-left: 5px solid {border_color};">
            <div style="display: flex; justify-content: space-between;">
                <h4 style="margin: 0; color: {C21_DARK_GREY}">#{task['ID']} {task['Title']}</h4>
                <span style="background: {border_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em;">{p_text.get(task['Priority'])}</span>
            </div>
            <div style="color: #666; font-size: 0.9em; margin: 5px 0;">
                📅 Due: {task['Due Date'].strftime('%b %d, %Y') if pd.notna(task['Due Date']) else 'No Date'} | 
                👤 To: {task['Assigned To']} | 
                ⏳ Hours: {task.get('Time Spent (Hrs)', 0)}
            </div>
            <div style="margin: 10px 0;">{task['Description']}</div>
            <div style="font-size: 0.85em; margin-bottom: 10px;">
                Current Status: <span class="status-badge status-{task['Status'].replace(' ', '-')}">
                    {task['Status']}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Actions Expander
        with st.expander(f"⚙️ Manage Task #{task['ID']}"):
            
            # --- Quick Actions for Luke ---
            if current_user == "Luke" and task['Assigned To'] == "Luke":
                col_a, col_b, col_c = st.columns(3)
                
                # Start Button
                if task['Status'] not in ['In Progress', 'Completed']:
                    with col_a:
                        if st.button("▶ Start Task", key=f"start_{task['ID']}"):
                            DataManager.update_task(task['ID'], {
                                'Status': 'In Progress',
                                'Start Date': datetime.datetime.now().strftime('%Y-%m-%d')
                            }, current_user)
                            st.rerun()

                # Hold Button
                if task['Status'] == 'In Progress':
                    with col_b:
                        if st.button("⏸ Hold Task", key=f"hold_{task['ID']}"):
                            DataManager.update_task(task['ID'], {'Status': 'On Hold'}, current_user)
                            st.rerun()
                            
                # Complete Button
                with col_c:
                    if st.button("✅ Complete Task", key=f"comp_{task['ID']}"):
                        st.session_state[f'completing_{task["ID"]}'] = True

                # Completion Dialog
                if st.session_state.get(f'completing_{task["ID"]}'):
                    with st.form(f"finish_{task['ID']}"):
                        st.write("Confirm Final Details")
                        final_hours = st.number_input("Total Hours Spent", min_value=0.0, step=0.5, value=float(task.get('Time Spent (Hrs)', 0)))
                        final_comment = st.text_area("Final Notes")
                        if st.form_submit_button("Submit Completion", type="primary"):
                            DataManager.update_task(task['ID'], {
                                'Status': 'Completed',
                                'Completed Date': datetime.datetime.now(),
                                'Time Spent (Hrs)': final_hours,
                                'Comments': f"{task['Comments']}\n[Completed]: {final_comment}".strip()
                            }, current_user)
                            del st.session_state[f'completing_{task["ID"]}']
                            st.rerun()

            # --- General Update Form (Manager & User) ---
            with st.form(f"update_{task['ID']}"):
                st.write("📝 **Advanced Edit**")
                c1, c2 = st.columns(2)
                new_status = c1.selectbox("Status", STATUS_LEVELS, index=STATUS_LEVELS.index(task['Status']) if task['Status'] in STATUS_LEVELS else 0)
                new_hours = c2.number_input("Hours Spent", value=float(task.get('Time Spent (Hrs)', 0.0)))
                new_comment = st.text_area("Add Comment", height=80)
                
                if st.form_submit_button("Save Changes"):
                    updates = {
                        'Status': new_status,
                        'Time Spent (Hrs)': new_hours
                    }
                    if new_comment:
                        timestamp = datetime.datetime.now().strftime('%m/%d %H:%M')
                        # Append the new comment to the existing comments
                        updates['Comments'] = f"{task['Comments']}\n[{timestamp} {current_user}]: {new_comment}".strip()
                    
                    DataManager.update_task(task['ID'], updates, current_user)
                    st.rerun()

# --- 9. DASHBOARD VIEWS ---

def manager_view(df):
    current_user = "Burtch"
    st.title(f"👑 Manager Dashboard")
    
    # Context-aware metrics
    active_mask = ~df['Status'].isin(['Completed', 'Archived'])
    active_df = df[active_mask]
    completed_df = df[df['Status'] == 'Completed']
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-box"><div class="metric-val">{len(active_df)}</div><div class="metric-lbl">Active Tasks</div></div>""", unsafe_allow_html=True)
    with col2:
        high_p = len(active_df[active_df['Priority'] == 1])
        st.markdown(f"""<div class="metric-box"><div class="metric-val" style="color:{C21_RED_ALERT}">{high_p}</div><div class="metric-lbl">High Priority</div></div>""", unsafe_allow_html=True)
    with col3:
        today = pd.Timestamp.now().normalize()
        overdue = len(active_df[active_df['Due Date'] < today])
        st.markdown(f"""<div class="metric-box"><div class="metric-val">{overdue}</div><div class="metric-lbl">Overdue</div></div>""", unsafe_allow_html=True)
    with col4:
        hrs = completed_df['Time Spent (Hrs)'].sum()
        st.markdown(f"""<div class="metric-box"><div class="metric-val">{hrs:.1f}</div><div class="metric-lbl">Total Hrs Logged</div></div>""", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Create Task", "📋 Task Board", "📊 Reports", "🔔 Notifications"])
    
    # --- Tab 1: Creation ---
    with tab1:
        st.subheader("Assign New Task")
        with st.form("create_task"):
            c1, c2 = st.columns(2)
            title = c1.text_input("Title")
            assignee = c2.selectbox("Assign To", ["Luke", "Burtch"])
            
            c3, c4, c5 = st.columns(3)
            start_dt = c3.date_input("Start Date", value=datetime.date.today())
            due_dt = c4.date_input("Due Date", value=datetime.date.today() + datetime.timedelta(days=3))
            prio = c5.selectbox("Priority", [1, 2, 3], format_func=lambda x: f"{x} - {'High' if x==1 else 'Med' if x==2 else 'Low'}")
            
            desc = st.text_area("Description")
            drive = st.checkbox("Create Drive Folder (for attachments/context)", value=True)
            
            if st.form_submit_button("🚀 Assign Task", type="primary"):
                if not title:
                    st.error("Title required")
                else:
                    new_id = int(time.time() * 1000) % 1000000
                    drive_link = DataManager.create_drive_folder(f"{new_id}_{title}") if drive else ""
                    
                    new_task = {
                        'ID': new_id,
                        'Title': title,
                        'Assigned To': assignee,
                        'Start Date': start_dt,
                        'Due Date': due_dt,
                        'Priority': prio,
                        'Status': 'Assigned',
                        'Description': desc,
                        'Google Drive Link': drive_link,
                        'Created By': current_user,
                        'Created At': datetime.datetime.now(),
                        'Last Modified': datetime.datetime.now(),
                        'Time Spent (Hrs)': 0
                    }
                    DataManager.add_task(new_task)
                    st.rerun()

    # --- Tab 2: Task Board ---
    with tab2:
        st.subheader("Task Log & Management")
        col_l, col_r = st.columns([2, 1])
        with col_l:
            filter_status = st.multiselect("Filter Status", STATUS_LEVELS, default=['Assigned', 'In Progress', 'On Hold'])
        with col_r:
            filter_user = st.selectbox("Filter User", ["All", "Luke", "Burtch"])
            
        view_df = df[df['Status'].isin(filter_status)]
        if filter_user != "All":
            view_df = view_df[view_df['Assigned To'] == filter_user]
            
        view_df = view_df.sort_values(['Priority', 'Due Date'])
        
        for i, (_, row) in enumerate(view_df.iterrows()):
            render_task_card(row, current_user, i)

    # --- Tab 3: Reports ---
    with tab3:
        st.subheader("Performance Reporting for Luke Wise")
        
        rc1, rc2 = st.columns(2)
        r_start = rc1.date_input("Report Start Date", value=datetime.date.today() - datetime.timedelta(days=30))
        r_end = rc2.date_input("Report End Date", value=datetime.date.today())
        
        luke_df = df[df['Assigned To'] == "Luke"]
        
        if st.button("Generate Luke's Report", type="primary"):
            html_report = ReportGenerator.generate_html_report(luke_df, r_start, r_end)
            
            # Preview & Download
            st.components.v1.html(html_report, height=500, scrolling=True)
            st.download_button(
                "📥 Download Report (HTML)",
                data=html_report,
                file_name=f"Performance_Report_Luke_{r_start}_{r_end}.html",
                mime="text/html",
                help="Open this file in your browser and use Print > Save as PDF for the final document."
            )
            
            # Analytics Charts (In-App)
            filtered = luke_df[(luke_df['Created At'].dt.date >= r_start) & (luke_df['Created At'].dt.date <= r_end)]
            if not filtered.empty:
                st.markdown("### Visual Analytics")
                c1, c2 = st.columns(2)
                with c1:
                    fig_status = px.pie(filtered, names='Status', title="Task Status Mix")
                    st.plotly_chart(fig_status, use_container_width=True)
                with c2:
                    daily_effort = filtered.groupby(filtered['Completed Date'].dt.date)['Time Spent (Hrs)'].sum().reset_index(name='Hours')
                    fig_eff = px.bar(daily_effort.dropna(), x='Completed Date', y='Hours', title="Daily Hours Logged (Completed Tasks)")
                    st.plotly_chart(fig_eff, use_container_width=True)

    # --- Tab 4: Notifications ---
    with tab4:
        st.subheader("Persistent Notification Log")
        
        notifications_df = NotificationManager.fetch_notifications()
        
        if notifications_df.empty:
            st.info("No updates have been logged yet.")
        else:
            st.dataframe(
                notifications_df,
                use_container_width=True,
                column_config={
                    "Timestamp": st.column_config.DatetimeColumn("Time", format="YYYY-MM-DD HH:mm"),
                    "Task ID": "Task ID",
                    "Title": "Task",
                    "User": "Updated By",
                    "Action": "Event",
                    "Details": "Changes/Comments"
                }
            )


def user_view(df):
    current_user = "Luke"
    st.title(f"👋 Welcome Back, Luke Wise")
    
    # Context-aware metrics (Luke's tasks only)
    luke_tasks = df[df['Assigned To'] == current_user]
    active_mask = ~luke_tasks['Status'].isin(['Completed', 'Archived'])
    active_df = luke_tasks[active_mask]
    completed_df = luke_tasks[luke_tasks['Status'] == 'Completed']
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-box"><div class="metric-val">{len(active_df)}</div><div class="metric-lbl">My Active Tasks</div></div>""", unsafe_allow_html=True)
    with col2:
        high_p = len(active_df[active_df['Priority'] == 1])
        st.markdown(f"""<div class="metric-box"><div class="metric-val" style="color:{C21_RED_ALERT}">{high_p}</div><div class="metric-lbl">Urgent Priority</div></div>""", unsafe_allow_html=True)
    with col3:
        today = pd.Timestamp.now().normalize()
        overdue = len(active_df[active_df['Due Date'] < today])
        st.markdown(f"""<div class="metric-box"><div class="metric-val">{overdue}</div><div class="metric-lbl">Overdue</div></div>""", unsafe_allow_html=True)
    with col4:
        hrs = completed_df['Time Spent (Hrs)'].sum()
        st.markdown(f"""<div class="metric-box"><div class="metric-val">{hrs:.1f}</div><div class="metric-lbl">Lifetime Hrs Logged</div></div>""", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🚀 My Workspace", "📚 Task History"])
    
    my_tasks = luke_tasks.sort_values(['Priority', 'Due Date'])
    
    with tab1:
        st.subheader("Focus: Current and Upcoming Tasks")
        active = my_tasks[~my_tasks['Status'].isin(['Completed', 'Archived'])]
        
        if active.empty:
            st.info("You have no active tasks. Ready for a new assignment!")
        else:
            overdue = active[active['Due Date'] < pd.Timestamp.now().normalize()]
            today = active[active['Due Date'] == pd.Timestamp.now().normalize()]
            upcoming = active[active['Due Date'] > pd.Timestamp.now().normalize()]
            
            if not overdue.empty:
                st.error(f"⚠️ **{len(overdue)} Overdue Tasks** - Highest Priority")
                for i, row in overdue.iterrows(): render_task_card(row, current_user, i)
            
            if not today.empty:
                st.warning(f"🔥 **{len(today)} Due Today** - Must Complete")
                for i, row in today.iterrows(): render_task_card(row, current_user, i)
                
            st.markdown(f"**Upcoming ({len(upcoming)})**")
            for i, row in upcoming.iterrows(): render_task_card(row, current_user, i)

    with tab2:
        st.subheader("Completed Task History")
        completed = completed_df.sort_values('Completed Date', ascending=False)
        st.dataframe(
            completed[['Title', 'Completed Date', 'Time Spent (Hrs)', 'Priority', 'Comments']], 
            use_container_width=True
        )

# --- 10. MAIN ENTRY ---
def main():
    st.set_page_config(page_title=AppConfig.APP_NAME, layout="wide", page_icon="🏠")
    inject_custom_css()
    
    # Init Session
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    
    # Auth Flow
    if not st.session_state.authenticated:
        render_login()
        return
        
    # Sidebar
    with st.sidebar:
        st.header(AppConfig.APP_NAME)
        st.markdown(f"Logged in as: **{SecurityConfig.USER_CREDENTIALS[st.session_state.role]['display_name']}**")
        st.markdown(f"<small>App Version: {AppConfig.VERSION}</small>", unsafe_allow_html=True)
        
        st.subheader("Actions")
        if st.button("🔄 Refresh Data Cache", use_container_width=True):
            st.cache_data.clear()
            st.toast("Data refreshed from Google Sheet.")
            st.rerun()
            
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
            
    # Main App Logic
    try:
        # Initialize Google Services
        if 'google_initialized' not in st.session_state:
            if initialize_google_services():
                # Ensure both sheets/tabs are set up
                DataManager.ensure_sheet_headers(AppConfig.SHEET_ID, "Task Log", COLUMNS)
                DataManager.ensure_sheet_headers(AppConfig.SHEET_ID, "Notifications Log", NOTIFICATION_COLUMNS)
            else:
                st.stop()
        
        # Load Data
        df = DataManager.fetch_data()
        
        # Route View
        if st.session_state.role == "Burtch":
            manager_view(df)
        elif st.session_state.role == "Luke":
            user_view(df)
            
    except Exception as e:
        st.error(f"❌ Application Error: {e}")
        with st.expander("📋 Technical Details"):
            st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
