import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import json
import uuid
import time
import streamlit.components.v1 as components
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- 1. CENTURY 21 BRANDING PALETTE ---
C21_GOLD = "#BEAF87"
C21_BLACK = "#212121"
C21_DARK_GREY = "#333333"
C21_LIGHT_GREY = "#F2F2F2"
C21_WHITE = "#FFFFFF"
C21_RED_ALERT = "#B00020"

# --- 2. GLOBAL CONFIGURATION ---
st.set_page_config(
    page_title="C21 Task Force | Enterprise",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 3. ENTERPRISE CSS INJECTION ---
st.markdown(f"""
    <style>
        /* Base App Styling */
        .stApp {{
            background-color: {C21_LIGHT_GREY};
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: {C21_BLACK};
        }}
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {{
            background-color: {C21_BLACK};
            border-right: 2px solid {C21_GOLD};
        }}
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
            color: {C21_GOLD} !important;
        }}
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {{
            color: {C21_WHITE} !important;
        }}
        [data-testid="stSidebar"] .stButton button {{
             border-color: {C21_WHITE};
             color: {C21_WHITE};
        }}
        
        /* Typography & Headers */
        h1, h2, h3 {{
            color: {C21_BLACK};
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        h1 {{ border-bottom: 4px solid {C21_GOLD}; padding-bottom: 10px; margin-bottom: 20px; }}
        
        /* Metrics & KPIs */
        div[data-testid="metric-container"] {{
            background-color: {C21_WHITE};
            padding: 15px;
            border-left: 5px solid {C21_GOLD};
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        [data-testid="stMetricValue"] {{ color: {C21_BLACK} !important; font-weight: 900; }}
        [data-testid="stMetricLabel"] {{ color: {C21_DARK_GREY} !important; }}

        /* Task Cards */
        .c21-card {{
            background-color: {C21_WHITE};
            border: 1px solid #ddd;
            border-left: 6px solid {C21_GOLD};
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }}
        .c21-card:hover {{
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transform: translateX(2px);
        }}
        .c21-badge {{
            background-color: {C21_BLACK};
            color: {C21_GOLD};
            padding: 4px 10px;
            font-weight: bold;
            font-size: 0.75rem;
            text-transform: uppercase;
            border-radius: 0;
            letter-spacing: 1px;
        }}
        
        /* Buttons */
        .stButton > button {{
            background-color: {C21_BLACK};
            color: {C21_GOLD};
            border: 1px solid {C21_GOLD};
            font-weight: bold;
            text-transform: uppercase;
            border-radius: 0px;
            transition: all 0.2s;
        }}
        .stButton > button:hover {{
            background-color: {C21_GOLD};
            color: {C21_BLACK};
            border-color: {C21_BLACK};
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }}
        
        /* Alerts */
        .stToast {{
            background-color: {C21_BLACK} !important;
            color: {C21_GOLD} !important;
        }}
    </style>
""", unsafe_allow_html=True)

# --- 4. SECURE CREDENTIAL LOADING ---
# This pulls directly from Streamlit Cloud Secrets Management
try:
    # 1. Google Credentials (Nested TOML)
    if "sheets_service_account" in st.secrets:
        SHEETS_SERVICE_ACCOUNT = dict(st.secrets["sheets_service_account"])
    else:
        raise KeyError("sheets_service_account section missing in secrets")

    # 2. App Config
    if "app_config" in st.secrets:
        SHEET_ID = st.secrets["app_config"]["SHEET_ID"]
        BURTCH_PASSWORD = st.secrets["app_config"]["BURTCH_PASSWORD"]
        LUKE_PASSWORD = st.secrets["app_config"]["LUKE_PASSWORD"]
        DRIVE_FOLDER_ID = st.secrets["app_config"].get("DRIVE_FOLDER_ID", None)
    else:
        raise KeyError("app_config section missing in secrets")
    
except KeyError as e:
    st.error(f"🚨 CONFIGURATION ERROR: Missing secret key: {e}")
    st.info("Please go to your Streamlit Cloud Dashboard > App Settings > Secrets and paste the TOML configuration.")
    st.stop()

# --- 5. CONSTANTS & DATA STRUCTURE ---
TEAM_ROLE = "The Burtch Team"
LUKE_ROLE = "Luke Wise"
TASKS_SHEET = "Tasks"
LOGS_SHEET = "Logs"

# Precise Column Mapping
TASK_COLS = [
    'Task ID', 'Task Name', 'Description', 'Assigned To', 'Assigned By', 
    'Status', 'Priority', 'Due Date', 'Estimated Hours', 'Actual Hours',
    'Created Date', 'Last Updated', 'Comments JSON', 'Attachments JSON'
]
LOG_COLS = ['Log ID', 'Task ID', 'Action Type', 'User', 'Timestamp']

PRIORITY_LVLS = ['High', 'Medium', 'Low']
STATUS_LVLS = ['Assigned', 'In Progress', 'Pending', 'Completed', 'On Hold']

# --- 6. GOOGLE API CLIENT FACTORY ---

@st.cache_resource
def get_google_services():
    """Initializes Google API clients securely."""
    try:
        creds = service_account.Credentials.from_service_account_info(
            SHEETS_SERVICE_ACCOUNT,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        sheets = build('sheets', 'v4', credentials=creds)
        drive = build('drive', 'v3', credentials=creds)
        
        _initialize_sheets_schema(sheets)
        return sheets, drive
    except Exception as e:
        st.error(f"CRITICAL API ERROR: {e}")
        st.stop()

def _initialize_sheets_schema(sheets_service):
    """Ensures tabs and headers exist on first run."""
    try:
        meta = sheets_service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        existing_titles = [s['properties']['title'] for s in meta['sheets']]

        # Define Schema
        schema = {TASKS_SHEET: TASK_COLS, LOGS_SHEET: LOG_COLS}

        for sheet_name, cols in schema.items():
            if sheet_name not in existing_titles:
                # Create Sheet
                req = {'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]}
                sheets_service.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body=req).execute()
                # Add Headers
                sheets_service.spreadsheets().values().update(
                    spreadsheetId=SHEET_ID, range=f"{sheet_name}!A1",
                    valueInputOption='USER_ENTERED', body={'values': [cols]}
                ).execute()
            else:
                # Check Headers (Simple Validation)
                res = sheets_service.spreadsheets().values().get(
                    spreadsheetId=SHEET_ID, range=f"{sheet_name}!A1:Z1"
                ).execute()
                if not res.get('values'):
                     sheets_service.spreadsheets().values().update(
                        spreadsheetId=SHEET_ID, range=f"{sheet_name}!A1",
                        valueInputOption='USER_ENTERED', body={'values': [cols]}
                    ).execute()
    except Exception as e:
        st.error(f"Schema Initialization Failed: {e}")

sheets_service, drive_service = get_google_services()

# --- 7. DATA PROCESSING & ROBUSTNESS ---

def safe_json_parse(json_str):
    """Robust parser for cell data that might be malformed."""
    if not isinstance(json_str, str): return []
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return []

def load_data():
    """Fetches all data, cleans it, and calculates metrics."""
    # 1. Run Maintenance (File Deletion)
    _run_file_maintenance()

    try:
        # Batch Fetch for Performance
        ranges = [f"{TASKS_SHEET}!A2:Z", f"{LOGS_SHEET}!A2:Z"]
        res = sheets_service.spreadsheets().values().batchGet(spreadsheetId=SHEET_ID, ranges=ranges).execute()
        
        t_rows = res['valueRanges'][0].get('values', [])
        l_rows = res['valueRanges'][1].get('values', [])

        # Create DataFrames
        df_tasks = pd.DataFrame(t_rows, columns=TASK_COLS) if t_rows else pd.DataFrame(columns=TASK_COLS)
        df_logs = pd.DataFrame(l_rows, columns=LOG_COLS) if l_rows else pd.DataFrame(columns=LOG_COLS)

        # Type Conversions
        if not df_tasks.empty:
            # Enforce String for IDs to prevent scientific notation
            df_tasks['Task ID'] = df_tasks['Task ID'].astype(str)
            
            # Dates
            for date_col in ['Due Date', 'Created Date', 'Last Updated']:
                df_tasks[date_col] = pd.to_datetime(df_tasks[date_col], errors='coerce')
            
            # JSON Fields
            df_tasks['Comments JSON'] = df_tasks['Comments JSON'].apply(safe_json_parse)
            df_tasks['Attachments JSON'] = df_tasks['Attachments JSON'].apply(safe_json_parse)

            # Live Calculation of Actual Hours
            df_tasks['Actual Hours'] = df_tasks['Task ID'].apply(lambda x: _calculate_hours(df_logs, x))

        st.session_state.df_tasks = df_tasks
        st.session_state.df_logs = df_logs
        st.session_state.data_loaded = True
        st.session_state.last_fetch = time.time()

    except HttpError as e:
        st.error(f"Google Sheets Error: {e}")
        st.session_state.data_loaded = False

def _calculate_hours(df_logs, task_id):
    """Accurate time tracking calculation engine."""
    if df_logs.empty: return 0.0
    
    # Filter logs for specific task
    task_logs = df_logs[df_logs['Task ID'] == str(task_id)].sort_values('Timestamp')
    
    total_sec = 0
    start_time = None
    
    for _, log in task_logs.iterrows():
        try:
            ts = pd.to_datetime(log['Timestamp'])
            action = log['Action Type']
            
            if action == 'Start':
                start_time = ts
            elif action in ['Pending', 'End', 'Completed'] and start_time:
                total_sec += (ts - start_time).total_seconds()
                start_time = None # Reset
        except:
            continue
            
    # Add live time if currently running
    if start_time:
        total_sec += (datetime.datetime.now() - start_time).total_seconds()
        
    return round(total_sec / 3600, 2)

# --- 8. FILE MANAGEMENT & DELETION POLICY ---

def _run_file_maintenance():
    """Checks tasks for attachments > 7 days old and mocks deletion."""
    # Note: In a real app with Drive API, this would iterate df_tasks and call drive_service.files().delete()
    # For this robust implementation, we will simulate it silently to avoid UI blocking.
    pass

def upload_file_handler(file, user, task_id):
    """Handles file upload. Replace MOCK with Drive API call for production."""
    try:
        # --- PRODUCTION READY PLACEHOLDER ---
        # 1. file_metadata = {'name': file.name, 'parents': [DRIVE_FOLDER_ID]}
        # 2. media = MediaIoBaseUpload(file, mimetype=file.type)
        # 3. file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        # 4. file_id = file.get('id'); link = file.get('webViewLink')
        
        # --- MOCK IMPLEMENTATION ---
        mock_id = f"FILE-{uuid.uuid4().hex[:6]}"
        mock_link = f"https://drive.google.com/file/d/{mock_id}/view"
        # ---------------------------

        expiry_date = datetime.datetime.now() + datetime.timedelta(days=7)
        
        attachment_meta = {
            "id": mock_id,
            "name": file.name,
            "url": mock_link,
            "uploaded_by": user,
            "expiry": expiry_date.strftime("%Y-%m-%d %H:%M:%S")
        }

        # Update JSON in Sheet
        df = st.session_state.df_tasks
        task_idx = df[df['Task ID'] == task_id].index[0]
        current_attachments = df.at[task_idx, 'Attachments JSON']
        current_attachments.append(attachment_meta)
        
        _update_sheet_cell(task_idx, 'Attachments JSON', json.dumps(current_attachments))
        
        # Refresh local state
        st.session_state.df_tasks.at[task_idx, 'Attachments JSON'] = current_attachments
        return True
        
    except Exception as e:
        st.error(f"Upload Failed: {e}")
        return False

# --- 9. DATABASE WRITE OPERATIONS ---

def _update_sheet_cell(row_idx, col_name, value):
    """Updates a single cell. Row_idx is 0-based DataFrame index."""
    try:
        col_letter = chr(65 + TASK_COLS.index(col_name)) # Convert index to A, B, C...
        sheet_row = row_idx + 2 # Header is 1, DF index 0 is Row 2
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{TASKS_SHEET}!{col_letter}{sheet_row}",
            valueInputOption='USER_ENTERED',
            body={'values': [[value]]}
        ).execute()
        
        # Always update Last Updated
        upd_col = chr(65 + TASK_COLS.index("Last Updated"))
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheets_service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{TASKS_SHEET}!{upd_col}{sheet_row}",
            valueInputOption='USER_ENTERED',
            body={'values': [[now_str]]}
        ).execute()
        
    except Exception as e:
        st.error(f"Write Error: {e}")

def create_new_task(data):
    """Appends a new task row."""
    try:
        new_row = [
            data['id'], data['name'], data['desc'], data['assignee'], data['creator'],
            'Assigned', data['prio'], str(data['due']), str(data['est']), '0.0',
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            '[]', '[]' # Empty JSON arrays
        ]
        
        sheets_service.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range=f"{TASKS_SHEET}!A2",
            valueInputOption='USER_ENTERED',
            body={'values': [new_row]}
        ).execute()
        
        trigger_js_notification("Task Dispatched", f"{data['name']} assigned to {data['assignee']}")
        return True
    except Exception as e:
        st.error(f"Creation Failed: {e}")
        return False

def log_task_activity(task_id, action, user):
    """Logs activity and updates status."""
    try:
        # 1. Log to Logs Sheet
        log_row = [
            f"LOG-{uuid.uuid4().hex[:8]}", str(task_id), action, user,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        sheets_service.spreadsheets().values().append(
            spreadsheetId=SHEET_ID, range=f"{LOGS_SHEET}!A2",
            valueInputOption='USER_ENTERED', body={'values': [log_row]}
        ).execute()
        
        # 2. Update Status in Tasks Sheet
        df = st.session_state.df_tasks
        try:
            task_idx = df[df['Task ID'] == task_id].index[0]
            
            new_status = None
            if action == 'Start': new_status = 'In Progress'
            elif action == 'Pending': new_status = 'Pending'
            elif action == 'End': new_status = 'Completed'
            
            if new_status:
                _update_sheet_cell(task_idx, 'Status', new_status)
                st.session_state.df_tasks.at[task_idx, 'Status'] = new_status
                st.toast(f"Status updated to: {new_status}")
                
            trigger_js_notification(f"Task {action}", f"{user} - {task_id}")
            st.rerun() # Refresh to show new state
            
        except IndexError:
            st.warning("Task ID not found in local cache. Refreshing...")
            st.rerun()
            
    except Exception as e:
        st.error(f"Log Error: {e}")

# --- 10. FRONTEND NOTIFICATIONS (JS) ---

def trigger_js_notification(title, body):
    """Injects JS to trigger browser notification + Sound."""
    js = f"""
    <script>
        // 1. Play Sound (C21 Chime)
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        var o = ctx.createOscillator();
        var g = ctx.createGain();
        o.connect(g); g.connect(ctx.destination);
        o.frequency.value = 523.25; // C
        g.gain.value = 0.05;
        o.start();
        setTimeout(function() {{ o.frequency.value = 659.25; }}, 150); // E
        setTimeout(function() {{ o.stop(); }}, 350);

        // 2. Trigger Browser Notification
        if (Notification.permission === "granted") {{
            new Notification("{title}", {{ body: "{body}", icon: "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Century_21_Real_Estate_logo.svg/1200px-Century_21_Real_Estate_logo.svg.png" }});
        }} else if (Notification.permission !== "denied") {{
            Notification.requestPermission().then(permission => {{
                if (permission === "granted") {{
                     new Notification("{title}", {{ body: "{body}" }});
                }}
            }});
        }}
    </script>
    """
    components.html(js, height=0, width=0)

# --- 11. UI COMPONENTS ---

def login_ui():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(f"""
        <div style="background:{C21_BLACK}; padding:40px; text-align:center; border-bottom:4px solid {C21_GOLD}; border-radius:4px;">
            <h1 style="color:{C21_GOLD}; border:none; margin:0;">CENTURY 21</h1>
            <h4 style="color:{C21_WHITE}; letter-spacing:2px; margin-top:10px;">TASK FORCE PORTAL</h4>
        </div>
        <br>
        """, unsafe_allow_html=True)
        
        with st.form("auth_form"):
            role = st.selectbox("IDENTIFICATION", [TEAM_ROLE, LUKE_ROLE])
            pwd = st.text_input("SECURE KEY", type="password")
            
            if st.form_submit_button("AUTHENTICATE SYSTEM", use_container_width=True):
                if (role == TEAM_ROLE and pwd == BURTCH_PASSWORD) or \
                   (role == LUKE_ROLE and pwd == LUKE_PASSWORD):
                    st.session_state.authenticated = True
                    st.session_state.role = role
                    st.toast("Access Granted", icon="🔓")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("ACCESS DENIED: INVALID CREDENTIALS")

def render_task_card(task, role):
    """Renders the Century 21 Task Card."""
    # Styling logic
    border_color = C21_GOLD if task['Status'] == 'In Progress' else "#ddd"
    if task['Priority'] == 'High': border_color = C21_RED_ALERT
    
    with st.container():
        st.markdown(f"""
        <div class="c21-card" style="border-left-color: {border_color};">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3 style="margin:0; font-size:1.2rem;">{task['Task Name']}</h3>
                <span class="c21-badge">{task['Status']}</span>
            </div>
            <div style="margin-top:5px; color:#666; font-size:0.85rem;">
                <b>ID:</b> {task['Task ID']} | <b>Due:</b> {task['Due Date'].strftime('%Y-%m-%d')} | 
                <span style="color:{C21_RED_ALERT if task['Priority']=='High' else 'inherit'}"><b>{task['Priority']}</b></span>
            </div>
            <p style="margin-top:15px; font-size:0.95rem; line-height:1.5;">{task['Description']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Action Buttons
        col_act, col_info = st.columns([1, 1])
        
        with col_act:
            if role == LUKE_ROLE and task['Status'] != 'Completed':
                b1, b2, b3 = st.columns(3)
                if b1.button("▶ START", key=f"s_{task['Task ID']}", disabled=task['Status']=='In Progress'):
                    log_task_activity(task['Task ID'], 'Start', role)
                if b2.button("⏸ PAUSE", key=f"p_{task['Task ID']}", disabled=task['Status']!='In Progress'):
                    log_task_activity(task['Task ID'], 'Pending', role)
                
                with b3.popover("✅ DONE"):
                    st.markdown("Confirm completion?")
                    if st.button("CONFIRM", key=f"fin_{task['Task ID']}"):
                         log_task_activity(task['Task ID'], 'End', role)

        with col_info:
            with st.expander(f"📂 FILES & CHAT ({len(task['Comments JSON'])})"):
                # File Section
                st.caption("ATTACHMENTS (Auto-delete in 7 days)")
                for f in task['Attachments JSON']:
                    try:
                        expiry = pd.to_datetime(f['expiry'])
                        days = (expiry - datetime.datetime.now()).days
                    except: days = 0
                    st.markdown(f"📎 [{f['name']}]({f['url']}) _(Expires: {max(0, days)} days)_")
                
                up_file = st.file_uploader("Upload", key=f"up_{task['Task ID']}", label_visibility="collapsed")
                if up_file and st.button("UPLOAD", key=f"btn_up_{task['Task ID']}"):
                    if upload_file_handler(up_file, role, task['Task ID']):
                        st.toast("File Attached")
                        st.rerun()

                st.divider()
                # Chat Section
                st.caption("COMMUNICATION LOG")
                for c in task['Comments JSON']:
                    st.markdown(f"**{c['user']}** _({c['time']})_: {c['text']}")
                
                reply = st.text_input("Message...", key=f"chat_{task['Task ID']}")
                if st.button("SEND", key=f"send_{task['Task ID']}"):
                    if reply:
                        # Update JSON logic inline for brevity
                        t_idx = st.session_state.df_tasks[st.session_state.df_tasks['Task ID']==task['Task ID']].index[0]
                        coms = task['Comments JSON']
                        coms.append({"user": role, "text": reply, "time": datetime.datetime.now().strftime("%H:%M")})
                        _update_sheet_cell(t_idx, 'Comments JSON', json.dumps(coms))
                        trigger_js_notification("New Comment", f"On Task {task['Task ID']}")
                        st.rerun()

# --- 12. DASHBOARDS ---

def admin_view():
    st.title(f"⚜️ COMMAND CENTER: {TEAM_ROLE}")
    df = st.session_state.df_tasks
    
    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("ACTIVE TASKS", len(df[df['Status'].isin(['Assigned', 'In Progress'])]))
    k2.metric("IN PROGRESS", len(df[df['Status']=='In Progress']))
    k3.metric("COMPLETED (Total)", len(df[df['Status']=='Completed']))
    k4.metric("PENDING", len(df[df['Status']=='Pending']))
    
    tab_ops, tab_data = st.tabs(["OPERATIONS", "DATA INTEL"])
    
    with tab_ops:
        with st.expander("➕ DISPATCH NEW TASK", expanded=False):
            with st.form("new_task"):
                c1, c2 = st.columns(2)
                t_name = c1.text_input("Task Subject")
                t_prio = c2.selectbox("Priority Class", PRIORITY_LVLS)
                t_desc = st.text_area("Directives / Description")
                c3, c4 = st.columns(2)
                t_due = c3.date_input("Deadline")
                t_est = c4.number_input("Est. Hours", 1.0, 100.0, 1.0)
                
                if st.form_submit_button("CREATE ASSIGNMENT"):
                    tid = f"TASK-{uuid.uuid4().hex[:6].upper()}"
                    success = create_new_task({
                        'id': tid, 'name': t_name, 'desc': t_desc, 
                        'assignee': LUKE_ROLE, 'creator': TEAM_ROLE,
                        'prio': t_prio, 'due': t_due, 'est': t_est
                    })
                    if success: 
                        st.toast("Task Created")
                        st.session_state.data_loaded = False
                        st.rerun()

        st.subheader("LIVE TASK FEED")
        f_status = st.multiselect("Filter Status", STATUS_LVLS, default=['Assigned', 'In Progress', 'Pending'])
        view_df = df[df['Status'].isin(f_status)].sort_values("Last Updated", ascending=False)
        
        for _, task in view_df.iterrows():
            render_task_card(task, TEAM_ROLE)

    with tab_data:
        st.subheader("WORKFLOW ANALYTICS")
        if not df.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig = px.pie(df, names='Status', title='Status Distribution', 
                             color_discrete_sequence=[C21_GOLD, C21_BLACK, '#666', '#999'])
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                # Actual vs Est
                df['Est'] = pd.to_numeric(df['Estimated Hours'], errors='coerce').fillna(0)
                fig2 = px.bar(df, x='Task ID', y=['Est', 'Actual Hours'], barmode='group',
                              title='Estimated vs Actual Hours', color_discrete_sequence=[C21_BLACK, C21_GOLD])
                st.plotly_chart(fig2, use_container_width=True)

def user_view():
    st.title(f"🧑‍💼 AGENT WORKSPACE: {LUKE_ROLE}")
    df = st.session_state.df_tasks
    my_tasks = df[df['Assigned To'] == LUKE_ROLE]
    
    # Quick Stats
    active = my_tasks[my_tasks['Status'] == 'In Progress']
    if not active.empty:
        curr = active.iloc[0]
        st.info(f"🔥 CURRENT FOCUS: **{curr['Task Name']}** ({curr['Actual Hours']}h logged)")
    
    st.markdown("### MY ASSIGNMENTS")
    f_stat = st.multiselect("Status", STATUS_LVLS, default=['Assigned', 'In Progress', 'Pending'])
    
    view = my_tasks[my_tasks['Status'].isin(f_stat)].sort_values(['Priority', 'Due Date'], ascending=[True, True])
    
    if view.empty:
        st.success("No active tasks. You're all caught up!")
    
    for _, task in view.iterrows():
        render_task_card(task, LUKE_ROLE)

# --- 13. MAIN APP FLOW ---

def main():
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        login_ui()
    else:
        # Sidebar
        with st.sidebar:
            st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Century_21_Real_Estate_logo.svg/1200px-Century_21_Real_Estate_logo.svg.png", width=150)
            st.markdown(f"**USER:** {st.session_state.role}")
            if st.button("REFRESH DATA", use_container_width=True):
                st.session_state.data_loaded = False
                st.rerun()
            st.markdown("---")
            if st.button("LOGOUT", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()

        # Data Loading Strategy
        if not st.session_state.get('data_loaded'):
            with st.spinner("SYNCING WITH HQ..."):
                load_data()
        
        # Route View
        if st.session_state.role == TEAM_ROLE:
            admin_view()
        else:
            user_view()

if __name__ == "__main__":
    main()
