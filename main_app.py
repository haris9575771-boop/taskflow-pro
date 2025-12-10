import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import time
# import hashlib # Removed as requested
from dataclasses import dataclass
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import traceback

# --- 1. ENTERPRISE CONFIGURATION ---
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
    APP_NAME = "Task Manager - The Burtch Team"
    VERSION = "3.0.1 (Simple Auth)"
    SHEET_ID = "1iIBoWSZSvV-SF9u2Cxi-_fbYgg06-XI32UgF1ZJIxh4"  # Replace if needed
    DRIVE_FOLDER_ID = ""  # Optional: Add your Drive Folder ID here
    SESSION_TIMEOUT_MINUTES = 60

class SecurityConfig:
    # --- SIMPLIFIED HARDCODED PASSWORDS ---
    # WARNING: This is INSECURE for a real application.
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
        """Verifies password using direct string comparison."""
        if username not in SecurityConfig.USER_CREDENTIALS:
            return False
        # Direct comparison - simple, but insecure
        return password == SecurityConfig.USER_CREDENTIALS[username]["password"]

# --- 2. DATA MODELS ---
# Expanded Columns for better tracking
COLUMNS = [
    'ID', 'Title', 'Assigned To', 'Start Date', 'Due Date', 'Completed Date',
    'Status', 'Priority', 'Time Spent (Hrs)', 'Description', 'Comments', 
    'Google Drive Link', 'Created By', 'Last Modified', 'Created At'
]

STATUS_LEVELS = ['Assigned', 'In Progress', 'On Hold', 'Completed', 'Archived']
PRIORITY_LEVELS = [1, 2, 3]  # 1=High, 2=Medium, 3=Low

# --- 3. ENTERPRISE STYLING ---
def inject_custom_css():
    st.markdown(f"""
        <style>
            .stApp {{ background-color: #f8f9fa; }}
            
            /* Sidebar */
            [data-testid="stSidebar"] {{
                background-color: {C21_BLACK};
                border-right: 2px solid {C21_GOLD};
            }}
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
                color: {C21_GOLD} !important;
            }}
            
            /* Cards */
            .task-card {{
                background: {C21_WHITE};
                padding: 1.5rem;
                border-radius: 10px;
                border-left: 5px solid {C21_GOLD};
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 1rem;
                transition: transform 0.2s;
            }}
            .task-card:hover {{ transform: translateY(-2px); }}
            
            /* Badges */
            .badge {{
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
            }}
            .badge-high {{ background-color: #ffebee; color: {C21_RED_ALERT}; border: 1px solid {C21_RED_ALERT}; }}
            .badge-med {{ background-color: #fff3e0; color: #ff9800; border: 1px solid #ff9800; }}
            .badge-low {{ background-color: #e8f5e9; color: {C21_GREEN_SUCCESS}; border: 1px solid {C21_GREEN_SUCCESS}; }}
            
            .status-badge {{
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 0.8em;
            }}
            
            /* Buttons */
            div.stButton > button {{
                border-radius: 6px;
                font-weight: 600;
            }}
            
            /* Metric Cards */
            .metric-box {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                border: 1px solid #eee;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }}
            .metric-val {{ font-size: 2rem; font-weight: 700; color: {C21_BLACK}; }}
            .metric-lbl {{ color: #666; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }}
        </style>
    """, unsafe_allow_html=True)

# --- 4. GOOGLE SERVICES & DATA MANAGER ---
def initialize_google_services():
    """Robust Service Initialization"""
    if 'sheets_credentials_json' not in st.secrets:
        st.error("❌ Credentials missing in secrets.toml")
        return False
        
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
        st.error(f"❌ Connection Error: {e}")
        return False

class DataManager:
    @staticmethod
    def _get_service():
        if 'SHEETS_SERVICE' not in st.session_state:
            raise Exception("Google Services not initialized")
        return st.session_state.SHEETS_SERVICE

    @staticmethod
    def ensure_sheet_headers(sheet_id):
        """Ensures the sheet has the correct columns, adding missing ones if necessary."""
        service = DataManager._get_service()
        try:
            # Read header row
            result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range='Task Log!A1:Z1').execute()
            existing_headers = result.get('values', [[]])[0]
            
            # If empty or mismatched
            if not existing_headers or existing_headers != COLUMNS:
                # Update headers
                body = {'values': [COLUMNS]}
                service.spreadsheets().values().update(
                    spreadsheetId=sheet_id, range='Task Log!A1',
                    valueInputOption='USER_ENTERED', body=body
                ).execute()
        except Exception as e:
            st.warning(f"Header check failed: {e}")

    @staticmethod
    def fetch_data() -> pd.DataFrame:
        """Fetch data and normalize to schema"""
        service = DataManager._get_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=AppConfig.SHEET_ID, range="Task Log!A:O"
        ).execute()
        values = result.get('values', [])
        
        if len(values) < 2:
            return pd.DataFrame(columns=COLUMNS)
            
        df = pd.DataFrame(values[1:], columns=COLUMNS)
        
        # Type Conversion
        df['ID'] = pd.to_numeric(df['ID'], errors='coerce')
        df['Priority'] = pd.to_numeric(df['Priority'], errors='coerce').fillna(3).astype(int)
        df['Time Spent (Hrs)'] = pd.to_numeric(df['Time Spent (Hrs)'], errors='coerce').fillna(0.0)
        
        # Date Conversion
        date_cols = ['Due Date', 'Start Date', 'Completed Date', 'Created At', 'Last Modified']
        for col in date_cols:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            
        return df

    @staticmethod
    def add_task(task_data: dict):
        """Append new task"""
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

    @staticmethod
    def update_task(task_id: int, updates: dict):
        """
        Updates a task by first finding its current row index.
        This prevents overwriting the wrong row if the sheet was sorted.
        """
        service = DataManager._get_service()
        
        # 1. Fetch current ID column to find row index
        result = service.spreadsheets().values().get(
            spreadsheetId=AppConfig.SHEET_ID, range="Task Log!A:A"
        ).execute()
        ids = [row[0] if row else '' for row in result.get('values', [])]
        
        try:
            # +1 because sheet is 1-indexed
            row_idx = ids.index(str(task_id)) + 1
        except ValueError:
            raise Exception(f"Task ID {task_id} not found in sheet.")

        # 2. Get current row data to preserve non-updated fields
        current_row_res = service.spreadsheets().values().get(
            spreadsheetId=AppConfig.SHEET_ID, range=f"Task Log!A{row_idx}:O{row_idx}"
        ).execute()
        current_row = current_row_res.get('values', [[]])[0]
        
        # Pad current row if short
        while len(current_row) < len(COLUMNS):
            current_row.append("")

        # 3. Apply updates
        new_row = list(current_row)
        for col, val in updates.items():
            if col in COLUMNS:
                idx = COLUMNS.index(col)
                # Format dates
                if isinstance(val, (datetime.date, datetime.datetime)):
                    val = val.strftime('%Y-%m-%d %H:%M:%S')
                new_row[idx] = val
        
        new_row[COLUMNS.index('Last Modified')] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 4. Write back
        service.spreadsheets().values().update(
            spreadsheetId=AppConfig.SHEET_ID, 
            range=f"Task Log!A{row_idx}:O{row_idx}",
            valueInputOption="USER_ENTERED", 
            body={"values": [new_row]}
        ).execute()

    @staticmethod
    def create_drive_folder(folder_name):
        """Create a folder in Drive"""
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
            return ""

# --- 5. REPORT GENERATOR (HTML/INFOGRAPHIC) ---
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
        total_hours = period_df['Time Spent (Hrs)'].sum()
        
        # HTML Template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Report - Luke Wise</title>
            <style>
                body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #333; max-width: 900px; margin: 0 auto; padding: 20px; }}
                .header {{ border-bottom: 4px solid {C21_GOLD}; padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; }}
                .logo {{ color: {C21_GOLD}; font-size: 24px; font-weight: bold; }}
                .title {{ font-size: 32px; color: {C21_BLACK}; margin: 0; }}
                .subtitle {{ color: #666; font-size: 14px; }}
                
                .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }}
                .metric-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border: 1px solid #ddd; }}
                .metric-val {{ font-size: 36px; font-weight: bold; color: {C21_GOLD}; margin-bottom: 5px; }}
                .metric-lbl {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #555; }}
                
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 14px; }}
                th {{ background-color: {C21_BLACK}; color: white; padding: 12px; text-align: left; }}
                td {{ border-bottom: 1px solid #eee; padding: 12px; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                
                .status-badge {{ padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
                .status-Completed {{ background: #e8f5e9; color: green; }}
                .status-In-Progress {{ background: #fff3e0; color: orange; }}
                
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
                    <div class="metric-lbl">Total Tasks</div>
                </div>
                <div class="metric-card">
                    <div class="metric-val">{completed_count}</div>
                    <div class="metric-lbl">Completed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-val">{completion_rate}%</div>
                    <div class="metric-lbl">Efficiency</div>
                </div>
                <div class="metric-card">
                    <div class="metric-val">{total_hours:.1f}</div>
                    <div class="metric-lbl">Hours Logged</div>
                </div>
            </div>
            
            <h3>📋 Completed Tasks Summary</h3>
            <table>
                <thead>
                    <tr>
                        <th>Task</th>
                        <th>Completed Date</th>
                        <th>Hours</th>
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
                Generated by Task Manager v3.0 | The Burtch Team
            </div>
        </body>
        </html>
        """
        return html

# --- 6. UI COMPONENTS ---

def render_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"<h1 style='text-align: center; color: {C21_GOLD};'>🏠 Task Manager</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Enterprise Edition v3.0 (Simple Auth)</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            role_display = st.selectbox("Select User", ["The Burtch Team", "Luke Wise"])
            username = "Burtch" if role_display == "The Burtch Team" else "Luke"
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Log In", use_container_width=True):
                if SecurityConfig.verify_password(username, password):
                    st.session_state.authenticated = True
                    st.session_state.role = username
                    st.rerun()
                else:
                    st.error("Invalid Credentials")

def render_metrics(df, user_role):
    """Context-aware metrics"""
    
    # Filter for active tasks
    active_mask = ~df['Status'].isin(['Completed', 'Archived'])
    
    if user_role == "Luke":
        df = df[df['Assigned To'] == "Luke"]
        active_mask = active_mask & (df['Assigned To'] == "Luke")
        
    active_df = df[active_mask]
    completed_df = df[df['Status'] == 'Completed']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""<div class="metric-box"><div class="metric-val">{len(active_df)}</div><div class="metric-lbl">Active Tasks</div></div>""", unsafe_allow_html=True)
    with col2:
        high_p = len(active_df[active_df['Priority'] == 1])
        st.markdown(f"""<div class="metric-box"><div class="metric-val" style="color:{C21_RED_ALERT}">{high_p}</div><div class="metric-lbl">High Priority</div></div>""", unsafe_allow_html=True)
    with col3:
        # Overdue
        today = pd.Timestamp.now().normalize()
        overdue = len(active_df[active_df['Due Date'] < today])
        st.markdown(f"""<div class="metric-box"><div class="metric-val">{overdue}</div><div class="metric-lbl">Overdue</div></div>""", unsafe_allow_html=True)
    with col4:
        hrs = completed_df['Time Spent (Hrs)'].sum()
        st.markdown(f"""<div class="metric-box"><div class="metric-val">{hrs:.1f}</div><div class="metric-lbl">Hours Logged</div></div>""", unsafe_allow_html=True)

def render_task_card(task, current_user, index):
    """Card View with Action Buttons"""
    
    # Styling variables
    p_color = {1: C21_RED_ALERT, 2: "#FF9800", 3: C21_GREEN_SUCCESS}
    p_text = {1: "HIGH", 2: "MED", 3: "LOW"}
    
    border_color = p_color.get(task['Priority'], "#ccc")
    
    with st.container():
        st.markdown(f"""
        <div style="border-left: 5px solid {border_color}; background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <div style="display: flex; justify-content: space-between;">
                <h4 style="margin: 0;">#{task['ID']} {task['Title']}</h4>
                <span style="background: {border_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em;">{p_text.get(task['Priority'])}</span>
            </div>
            <div style="color: #666; font-size: 0.9em; margin: 5px 0;">
                📅 Due: {task['Due Date'].strftime('%b %d') if pd.notna(task['Due Date']) else 'No Date'} | 
                👤 To: {task['Assigned To']} | 
                ⏳ Hours: {task.get('Time Spent (Hrs)', 0)}
            </div>
            <div style="margin: 10px 0;">{task['Description']}</div>
            <div style="font-size: 0.85em; color: {C21_BLUE_INFO};">
                Current Status: <strong>{task['Status']}</strong>
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
                        if st.button("▶ Start", key=f"start_{task['ID']}"):
                            DataManager.update_task(task['ID'], {
                                'Status': 'In Progress',
                                'Start Date': datetime.datetime.now().strftime('%Y-%m-%d')
                            })
                            st.success("Task Started!")
                            st.rerun()

                # Hold Button
                if task['Status'] == 'In Progress':
                    with col_b:
                        if st.button("⏸ Hold", key=f"hold_{task['ID']}"):
                            DataManager.update_task(task['ID'], {'Status': 'On Hold'})
                            st.rerun()
                            
                # Complete Button
                with col_c:
                    if st.button("✅ Complete", key=f"comp_{task['ID']}"):
                        st.session_state[f'completing_{task["ID"]}'] = True

                # Completion Dialog
                if st.session_state.get(f'completing_{task["ID"]}'):
                    with st.form(f"finish_{task['ID']}"):
                        st.write("Confirm Completion")
                        final_hours = st.number_input("Total Hours Spent", min_value=0.0, step=0.5, value=float(task.get('Time Spent (Hrs)', 0)))
                        final_comment = st.text_area("Final Notes")
                        if st.form_submit_button("Submit Completion"):
                            DataManager.update_task(task['ID'], {
                                'Status': 'Completed',
                                'Completed Date': datetime.datetime.now(),
                                'Time Spent (Hrs)': final_hours,
                                'Comments': f"{task['Comments']}\n[Completed]: {final_comment}".strip()
                            })
                            del st.session_state[f'completing_{task["ID"]}']
                            st.rerun()

            # --- General Update Form (Manager & User) ---
            with st.form(f"update_{task['ID']}"):
                st.write("📝 **Edit Details**")
                c1, c2 = st.columns(2)
                new_status = c1.selectbox("Status", STATUS_LEVELS, index=STATUS_LEVELS.index(task['Status']) if task['Status'] in STATUS_LEVELS else 0)
                new_hours = c2.number_input("Hours Spent", value=float(task.get('Time Spent (Hrs)', 0.0)))
                new_comment = st.text_area("Add Comment", height=80)
                
                if st.form_submit_button("Update Task"):
                    updates = {
                        'Status': new_status,
                        'Time Spent (Hrs)': new_hours
                    }
                    if new_comment:
                        timestamp = datetime.datetime.now().strftime('%m/%d %H:%M')
                        updates['Comments'] = f"{task['Comments']}\n[{timestamp} {current_user}]: {new_comment}".strip()
                    
                    DataManager.update_task(task['ID'], updates)
                    st.success("Updated!")
                    st.rerun()

# --- 7. MAIN APP VIEWS ---

def manager_view(df):
    st.title(f"👑 Manager Dashboard")
    render_metrics(df, "Burtch")
    
    tab1, tab2, tab3 = st.tabs(["➕ Create Task", "📋 Task Board", "📊 Reports"])
    
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
            drive = st.checkbox("Create Drive Folder", value=True)
            
            if st.form_submit_button("🚀 Assign Task", type="primary"):
                if not title:
                    st.error("Title required")
                else:
                    new_id = int(time.time() * 1000) % 1000000
                    drive_link = ""
                    if drive:
                        drive_link = DataManager.create_drive_folder(f"{new_id}_{title}")
                    
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
                        'Created By': 'Burtch',
                        'Created At': datetime.datetime.now(),
                        'Last Modified': datetime.datetime.now(),
                        'Time Spent (Hrs)': 0
                    }
                    DataManager.add_task(new_task)
                    st.success(f"Task assigned to {assignee}")
                    time.sleep(1)
                    st.rerun()

    # --- Tab 2: Board ---
    with tab2:
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
            render_task_card(row, "Burtch", i)

    # --- Tab 3: Reports ---
    with tab3:
        st.subheader("Performance Reporting")
        
        rc1, rc2 = st.columns(2)
        r_start = rc1.date_input("Report Start", value=datetime.date.today() - datetime.timedelta(days=30))
        r_end = rc2.date_input("Report End", value=datetime.date.today())
        
        if st.button("Generate Luke's Report"):
            html_report = ReportGenerator.generate_html_report(df[df['Assigned To'] == "Luke"], r_start, r_end)
            
            # Preview
            st.components.v1.html(html_report, height=500, scrolling=True)
            
            # Download
            st.download_button(
                "📥 Download Report (HTML)",
                data=html_report,
                file_name=f"Report_Luke_{r_start}_{r_end}.html",
                mime="text/html",
                help="Open this file in your browser and select 'Print > Save as PDF' for a perfect PDF."
            )
            
            # Analytics Charts
            filtered = df[(df['Created At'].dt.date >= r_start) & (df['Created At'].dt.date <= r_end) & (df['Assigned To'] == "Luke")]
            if not filtered.empty:
                st.markdown("### Visual Analytics")
                c1, c2 = st.columns(2)
                with c1:
                    fig_status = px.pie(filtered, names='Status', title="Task Status Mix")
                    st.plotly_chart(fig_status, use_container_width=True)
                with c2:
                    daily_effort = filtered.groupby('Completed Date')['Time Spent (Hrs)'].sum().reset_index()
                    fig_eff = px.bar(daily_effort, x='Completed Date', y='Time Spent (Hrs)', title="Daily Hours")
                    st.plotly_chart(fig_eff, use_container_width=True)

def user_view(df):
    st.title(f"👋 Hi Luke")
    render_metrics(df, "Luke")
    
    tab1, tab2 = st.tabs(["🚀 My Workspace", "📚 History"])
    
    my_tasks = df[df['Assigned To'] == "Luke"].sort_values(['Priority', 'Due Date'])
    
    with tab1:
        st.subheader("Active Tasks")
        active = my_tasks[~my_tasks['Status'].isin(['Completed', 'Archived'])]
        
        if active.empty:
            st.info("No active tasks! Great job.")
        else:
            # Group by urgency
            overdue = active[active['Due Date'] < pd.Timestamp.now().normalize()]
            today = active[active['Due Date'] == pd.Timestamp.now().normalize()]
            upcoming = active[active['Due Date'] > pd.Timestamp.now().normalize()]
            
            if not overdue.empty:
                st.error(f"⚠️ Overdue ({len(overdue)})")
                for i, row in overdue.iterrows(): render_task_card(row, "Luke", i)
            
            if not today.empty:
                st.warning(f"🔥 Due Today ({len(today)})")
                for i, row in today.iterrows(): render_task_card(row, "Luke", i)
                
            st.markdown(f"**Upcoming ({len(upcoming)})**")
            for i, row in upcoming.iterrows(): render_task_card(row, "Luke", i)

    with tab2:
        st.subheader("Completed History")
        completed = my_tasks[my_tasks['Status'] == 'Completed'].sort_values('Completed Date', ascending=False)
        st.dataframe(
            completed[['Title', 'Completed Date', 'Time Spent (Hrs)', 'Priority']], 
            use_container_width=True
        )

# --- 8. MAIN ENTRY ---
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
        st.write(f"Logged in as: **{st.session_state.role}**")
        
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
            
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()
            
    # Main App Logic
    try:
        # Initialize
        if 'google_initialized' not in st.session_state:
            if initialize_google_services():
                DataManager.ensure_sheet_headers(AppConfig.SHEET_ID)
            else:
                st.stop()
        
        # Load Data (Live)
        df = DataManager.fetch_data()
        
        # Route View
        if st.session_state.role == "Burtch":
            manager_view(df)
        elif st.session_state.role == "Luke":
            user_view(df)
            
    except Exception as e:
        st.error(f"Application Error: {e}")
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
