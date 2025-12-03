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
        [data-testid="stSidebar"] .stButton > button {{
            background-color: {C21_GOLD};
            color: {C21_BLACK};
            border: none;
        }}
        [data-testid="stSidebar"] .stButton > button:hover {{
            background-color: {C21_WHITE};
        }}
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] .stMarkdown > div, [data-testid="stSidebar"] label {{
            color: {C21_WHITE};
        }}
        [data-testid="stSidebar"] .stImage {{
            padding-bottom: 20px;
        }}

        /* Main Content Cards */
        .task-card {{
            border: 1px solid {C21_DARK_GREY};
            border-left: 5px solid {C21_GOLD};
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            background-color: {C21_WHITE};
            box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.1);
        }}
        .task-title {{
            font-weight: bold;
            font-size: 1.2em;
            color: {C21_BLACK};
        }}
        .task-detail {{
            font-size: 0.9em;
            color: {C21_DARK_GREY};
        }}
        .priority-low {{
            color: green;
            font-weight: bold;
        }}
        .priority-medium {{
            color: orange;
            font-weight: bold;
        }}
        .priority-high {{
            color: {C21_RED_ALERT};
            font-weight: bold;
        }}
        
        /* Streamlit Widgets */
        .stSelectbox, .stTextInput, .stDateInput {{
            margin-bottom: 10px;
        }}
        .stTextInput > label, .stDateInput > label, .stSelectbox > label {{
            font-weight: bold;
            color: {C21_BLACK};
        }}
        
        /* Utility */
        .centered {{
            text-align: center;
        }}
        
    </style>
""" % locals(), unsafe_allow_html=True)


# --- 4. ROLES & AUTH CONFIGURATION ---
BURTCH_ROLE = "Burtch"
LUKE_ROLE = "Luke"
ADMIN_ROLE = "Admin"
ROLES = [BURTCH_ROLE, LUKE_ROLE, ADMIN_ROLE]

# Hardcoded application configuration variables
SHEET_ID = "1iIBoWSZSvV-SF9u2Cxi-_fbYgg06-XI32UgF1ZJIxh4"
DRIVE_FOLDER_ID = "" 
BURTCH_PASSWORD = "jayson0922"
LUKE_PASSWORD = "luke29430"
ADMIN_PASSWORD = "admin_secure_password" # Set a strong password here!


# --- 5. STATUS AND PRIORITY DEFINITIONS ---
STATUS_LVLS = ['Assigned', 'In Progress', 'Pending', 'Completed', 'Archived']
PRIORITY_LVLS = [1, 2, 3] # 1 is High, 3 is Low

# --- 6. DATA FRAME COLUMNS ---
COLUMNS = ['ID', 'Title', 'Assigned To', 'Due Date', 'Status', 'Priority', 'Description', 'Google Drive Link', 'Created By', 'Last Modified']


# --- 7. UTILITY FUNCTIONS ---
@st.cache_data(ttl=600) # Cache data for 10 minutes
def get_sheets_data(sheet_id, range_name):
    """Retrieves data from a specified Google Sheet range."""
    # Build the service object (SERVICE is defined globally after auth)
    # Using st.session_state ensures the service object is available in the cached function
    try:
        service = st.session_state.SERVICE 
    except AttributeError:
        # Re-initialize the service if it's missing (shouldn't happen if main() runs first)
        st.error("Google Sheets Service not initialized.")
        st.stop()
        
    result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range_name).execute()
    values = result.get('values', [])
    if not values:
        return pd.DataFrame(columns=COLUMNS)
    
    # Use the first row as headers, handle case where data is missing but headers exist
    df = pd.DataFrame(values[1:], columns=values[0])
    
    # Ensure all required columns exist, even if sheet is empty
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ''
    
    # Data type conversion and cleanup
    df['Due Date'] = pd.to_datetime(df['Due Date'], errors='coerce')
    df['Priority'] = pd.to_numeric(df['Priority'], errors='coerce').fillna(3).astype(int)
    
    return df[COLUMNS]


def update_sheet_row(sheet_id, range_name, row_index, updated_data):
    """Updates a single row in the Google Sheet."""
    
    # The API update range needs to start at the actual row index + 1 (for 1-based indexing)
    # and another +1 because the first row is headers. So row_index + 2
    update_range = f"A{row_index + 2}:J{row_index + 2}"
    
    # Convert DataFrame row to list of lists for API
    update_values = [updated_data.tolist()]

    body = {
        'values': update_values
    }
    
    result = st.session_state.SERVICE.spreadsheets().values().update(
        spreadsheetId=sheet_id, 
        range=update_range,
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    return result

def append_sheet_row(sheet_id, range_name, new_data):
    """Appends a new row to the Google Sheet."""
    
    body = {
        'values': [new_data]
    }
    
    result = st.session_state.SERVICE.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()
    return result

def create_google_drive_folder(folder_name, parent_folder_id):
    """Creates a folder in Google Drive."""
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    file = st.session_state.DRIVE_SERVICE.files().create(body=file_metadata, fields='id').execute()
    return file.get('id')


# --- 8. AUTHENTICATION UI ---
def login_ui():
    """Renders the login form."""
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        st.markdown(f"<div class='centered'><h1>C21 Task Force</h1><p>Internal Login Required</p></div>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.selectbox("Username", ROLES)
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                # Use hardcoded passwords from the Python file
                if username == BURTCH_ROLE and password == BURTCH_PASSWORD:
                    st.session_state.authenticated = True
                    st.session_state.role = BURTCH_ROLE
                    st.rerun()
                elif username == LUKE_ROLE and password == LUKE_PASSWORD:
                    st.session_state.authenticated = True
                    st.session_state.role = LUKE_ROLE
                    st.rerun()
                elif username == ADMIN_ROLE and password == ADMIN_PASSWORD:
                    st.session_state.authenticated = True
                    st.session_state.role = ADMIN_ROLE
                    st.rerun()
                else:
                    st.error("Invalid username or password")


# --- 9. UI COMPONENTS ---

def render_task_card(task, current_user_role):
    """Renders an individual task card with an update form."""
    
    # Determine priority class for styling
    if task['Priority'] == 1:
        priority_class = "priority-high"
        priority_display = "High (1)"
    elif task['Priority'] == 2:
        priority_class = "priority-medium"
        priority_display = "Medium (2)"
    else:
        priority_class = "priority-low"
        priority_display = "Low (3)"
        
    
    # Use HTML to structure the card
    st.markdown(f"""
        <div class='task-card'>
            <div class='task-title'>Task #{task['ID']}: {task['Title']}</div>
            <div class='task-detail'>
                Assigned To: **{task['Assigned To']}** | 
                Priority: <span class='{priority_class}'>{priority_display}</span> |
                Due: **{task['Due Date'].strftime('%Y-%m-%d') if pd.notna(task['Due Date']) else 'N/A'}**
            </div>
            <div class='task-detail'>Description: {task['Description']}</div>
            {f"<div class='task-detail'>**Drive Link:** <a href='{task['Google Drive Link']}' target='_blank'>Open Folder</a></div>" if task['Google Drive Link'] else ''}
            <div class='task-detail'>Status: <strong>{task['Status']}</strong></div>
        </div>
    """, unsafe_allow_html=True)

    # Only show update form if the user is assigned or is Admin
    if current_user_role == task['Assigned To'] or current_user_role == ADMIN_ROLE:
        with st.expander(f"Update Status for Task #{task['ID']}"):
            
            with st.form(f"update_form_{task['ID']}", clear_on_submit=False):
                
                new_status = st.selectbox(
                    "Change Status",
                    STATUS_LVLS,
                    index=STATUS_LVLS.index(task['Status']),
                    key=f"status_{task['ID']}"
                )
                
                submitted = st.form_submit_button("APPLY UPDATE", use_container_width=True)
                
                if submitted:
                    df = st.session_state.df
                    
                    # Find the original index of the row to update
                    # Sheets API is 1-based, 1st row is headers, so df index 0 is API row 2
                    row_index = df[df['ID'] == task['ID']].index[0] 
                    
                    # Update the DataFrame in session state
                    df.loc[row_index, 'Status'] = new_status
                    df.loc[row_index, 'Last Modified'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    # Prepare data for API update (ensure correct column order)
                    updated_data = df.loc[row_index, COLUMNS]
                    
                    try:
                        update_sheet_row(SHEET_ID, "Task Log!A:J", row_index, updated_data)
                        st.success(f"Task #{task['ID']} updated to: {new_status}")
                        st.session_state.data_loaded = False
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating sheet: {e}")
                        st.stop()


# --- 10. GOOGLE SHEETS AUTHENTICATION ---
# Global service objects will be stored in st.session_state after successful auth
def initialize_google_services():
    """Initializes Google Sheets and Drive services using secrets."""
    try:
        if "sheets_credentials_json" in st.secrets:
            # Load the JSON string from the secrets and parse it into a dictionary
            # This robustly handles the credential structure
            service_account_info = json.loads(st.secrets["sheets_credentials_json"]["json"])
            
            creds = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']
            )
            
            st.session_state.SERVICE = build('sheets', 'v4', credentials=creds)
            st.session_state.DRIVE_SERVICE = build('drive', 'v3', credentials=creds)
            return True
        else:
            st.error("Missing Google Sheets Service Account credentials in secrets.toml. Please ensure the [sheets_credentials_json] section is present.")
            return False

    except HttpError as e:
        st.error(f"Google API Error: {e.content.decode()}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred during setup: {e}")
        return False


# --- 11. TASK MANAGEMENT VIEWS ---

def admin_view(df):
    """Admin view: Show all open tasks and allow task creation."""
    st.title("Admin Dashboard")
    
    st.header("Create New Task")
    with st.expander("Expand to Create Task"):
        with st.form("new_task_form"):
            task_title = st.text_input("Title", max_chars=100)
            task_assigned = st.selectbox("Assigned To", ROLES)
            task_due_date = st.date_input("Due Date", min_value=datetime.date.today(), value=datetime.date.today())
            task_priority = st.selectbox("Priority (1=High, 3=Low)", PRIORITY_LVLS, index=2)
            task_desc = st.text_area("Description")
            
            # Form submission
            submitted = st.form_submit_button("CREATE TASK", type="primary", use_container_width=True)
            
            if submitted and task_title:
                # Generate unique ID
                new_id = int(time.time() * 1000) % 1000000 
                
                # Format data for sheet
                new_row = [
                    new_id,
                    task_title,
                    task_assigned,
                    task_due_date.strftime('%Y-%m-%d'),
                    'Assigned', # Initial Status
                    task_priority,
                    task_desc,
                    '', # Google Drive Link (optional)
                    st.session_state.role, # Created By
                    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') # Last Modified
                ]
                
                try:
                    
                    # 2. Optionally create Drive folder and update link in the new_row data
                    if DRIVE_FOLDER_ID:
                        folder_name = f"{task_assigned} - Task {new_id} - {task_title}"
                        new_folder_id = create_google_drive_folder(folder_name, DRIVE_FOLDER_ID)
                        folder_link = f"https://drive.google.com/drive/folders/{new_folder_id}"
                        new_row[7] = folder_link # Index 7 is 'Google Drive Link'
                    
                    # 1. Append to Google Sheet (using the row potentially updated with Drive Link)
                    append_sheet_row(SHEET_ID, "Task Log!A:J", new_row)
                    
                    st.success(f"Task '{task_title}' created and assigned to {task_assigned}!")
                    st.session_state.data_loaded = False
                    st.cache_data.clear() # Clear cache to force reload of fresh data
                    time.sleep(1)
                    st.rerun() # Rerun to refresh data and show new task
                    
                except Exception as e:
                    st.error(f"Error creating task: {e}")
                    st.stop()
            elif submitted:
                st.warning("Please enter a Title for the task.")

    
    st.header("All Open Tasks")
    
    # Filter out Completed and Archived tasks for the default view
    active_df = df[~df['Status'].isin(['Completed', 'Archived'])].copy()
    
    # Sort by Priority and Due Date
    active_df.sort_values(['Priority', 'Due Date'], ascending=[True, True], inplace=True)
    
    # Display statistics
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Active Tasks", len(active_df))
    col_b.metric("High Priority (1)", len(active_df[active_df['Priority'] == 1]))
    
    # Calculate overdue tasks safely
    today = datetime.date.today()
    overdue_count = len(active_df[pd.to_datetime(active_df['Due Date'], errors='coerce').dt.date < today])
    col_c.metric("Overdue Tasks", overdue_count)
    
    # Show the table of all active tasks
    st.dataframe(active_df, use_container_width=True, hide_index=True)
    
    st.header("Task Cards for All Users")
    for role in ROLES:
        st.subheader(f"Tasks for {role}")
        role_tasks = active_df[active_df['Assigned To'] == role].sort_values(['Priority', 'Due Date'], ascending=[True, True])
        
        if role_tasks.empty:
            st.info(f"No active tasks for {role}.")
        
        for _, task in role_tasks.iterrows():
            render_task_card(task, st.session_state.role)


def user_view(df, role):
    """User view: Show tasks assigned only to the current user."""
    st.title(f"{role}'s Task List")
    
    my_tasks = df[df['Assigned To'] == role].copy()
    
    # Display statistics
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Tasks", len(my_tasks))
    col_b.metric("In Progress", len(my_tasks[my_tasks['Status'] == 'In Progress']))
    
    # Calculate tasks completed today safely
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    completed_today_count = len(my_tasks[(my_tasks['Status'] == 'Completed') & (my_tasks['Last Modified'].str.startswith(today_str, na=False))])
    col_c.metric("Completed Today", completed_today_count)

    st.subheader("Filter and View Tasks")
    f_stat = st.multiselect("Filter by Status", STATUS_LVLS, default=['Assigned', 'In Progress', 'Pending'])
    
    view = my_tasks[my_tasks['Status'].isin(f_stat)].sort_values(['Priority', 'Due Date'], ascending=[True, True])
    
    if view.empty:
        st.success("No active tasks. You're all caught up!")
    
    for _, task in view.iterrows():
        # FIX: Ensure we pass the actual user role for update permission logic
        render_task_card(task, role)

# --- 13. MAIN APP FLOW ---
def main():
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    
    # 0. Initialize Google Services only once
    if 'SERVICE' not in st.session_state:
        if not initialize_google_services():
            return # Stop execution if service initialization failed

    if not st.session_state.authenticated:
        login_ui()
    else:
        # Sidebar
        with st.sidebar:
            st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Century_21_Real_Estate_logo.svg/1200px-Century_21_Real_Estate_logo.svg.png", width=150)
            st.markdown(f"**USER:** {st.session_state.role}")
            if st.button("REFRESH DATA", use_container_width=True):
                st.session_state.data_loaded = False
                st.cache_data.clear() # Clear cache
                st.rerun()
            st.markdown("---")
            if st.button("LOGOUT", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()

        # Data Loading Strategy
        if not st.session_state.get('data_loaded'):
            with st.spinner("SYNCING TASKS FROM GOOGLE SHEETS..."):
                try:
                    # Function is decorated with @st.cache_data now
                    df = get_sheets_data(SHEET_ID, "Task Log!A:J") 
                    st.session_state.df = df
                    st.session_state.data_loaded = True
                except Exception as e:
                    st.error(f"Failed to load data from Google Sheets. Error: {e}")
                    st.session_state.data_loaded = False
                    
        # Main View
        if st.session_state.get('data_loaded'):
            if st.session_state.role == ADMIN_ROLE:
                admin_view(st.session_state.df)
            else:
                user_view(st.session_state.df, st.session_state.role)

if __name__ == "__main__":
    main()
