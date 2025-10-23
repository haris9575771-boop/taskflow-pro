import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.database import get_tasks, get_time_entries, add_time_entry
from utils.helpers import format_duration, format_date

def app():
    st.title("⏰ Time Tracking")
    st.markdown("---")
    
    # Current week time summary
    st.subheader("📅 This Week's Summary")
    
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    time_entries = get_time_entries({
        'date_from': start_of_week.strftime('%Y-%m-%d'),
        'date_to': end_of_week.strftime('%Y-%m-%d'),
        'user_id': st.session_state.user_id
    })
    
    # Calculate totals
    total_minutes = sum(entry['duration_minutes'] for entry in time_entries) if time_entries else 0
    billable_minutes = sum(entry['duration_minutes'] for entry in time_entries if entry['billable']) if time_entries else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Time", format_duration(total_minutes))
    
    with col2:
        st.metric("Billable Time", format_duration(billable_minutes))
    
    with col3:
        st.metric("Non-Billable", format_duration(total_minutes - billable_minutes))
    
    with col4:
        avg_per_day = total_minutes / (today.weekday() + 1) if today.weekday() > 0 else total_minutes
        st.metric("Daily Average", format_duration(avg_per_day))
    
    st.markdown("---")
    
    # Quick time entry
    st.subheader("⏱️ Quick Time Entry")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        tasks = get_tasks({'assigned_to': st.session_state.user_id})
        task_options = {f"{task['title']} (#{task['id']})": task['id'] for task in tasks if task['status'] != 'Completed'}
        selected_task = st.selectbox("Select Task", list(task_options.keys())) if task_options else "No tasks available"
    
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=15, max_value=480, step=15, value=60)
    
    with col3:
        billable = st.checkbox("Billable", value=True)
        description = st.text_input("Description (optional)")
    
    if st.button("⏱️ Log Time", use_container_width=True):
        if selected_task and selected_task != "No tasks available":
            add_time_entry({
                'task_id': task_options[selected_task],
                'user_id': st.session_state.user_id,
                'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': (datetime.now() + timedelta(minutes=duration)).strftime('%Y-%m-%d %H:%M:%S'),
                'duration_minutes': duration,
                'description': description,
                'billable': billable
            })
            st.success("Time entry logged successfully!")
            st.rerun()
    
    st.markdown("---")
    
    # Time entries history
    st.subheader("📋 Recent Time Entries")
    
    # Date filter
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("From Date", today - timedelta(days=30))
    with col2:
        date_to = st.date_input("To Date", today)
    
    # Get filtered time entries
    filtered_entries = get_time_entries({
        'date_from': date_from.strftime('%Y-%m-%d'),
        'date_to': date_to.strftime('%Y-%m-%d'),
        'user_id': st.session_state.user_id
    })
    
    if filtered_entries:
        entries_df = pd.DataFrame(filtered_entries)
        
        # Display summary by task
        st.write("**Summary by Task:**")
        summary = entries_df.groupby('task_title').agg({
            'duration_minutes': 'sum',
            'billable': 'first'
        }).reset_index()
        
        summary['formatted_duration'] = summary['duration_minutes'].apply(format_duration)
        
        for _, row in summary.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{row['task_title']}**")
            with col2:
                st.write(f"**{row['formatted_duration']}** {'💰' if row['billable'] else '📝'}")
        
        st.markdown("---")
        
        # Detailed entries
        st.write("**Detailed Entries:**")
        for entry in filtered_entries[:10]:  # Show last 10 entries
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{entry['task_title']}**")
                    if entry['description']:
                        st.write(f"*{entry['description']}*")
                    st.caption(f"Logged on {format_date(entry['start_time'])}")
                with col2:
                    st.write(f"**{format_duration(entry['duration_minutes'])}**")
                with col3:
                    st.write("💰" if entry['billable'] else "📝")
                
                st.markdown("---")
    else:
        st.info("No time entries found for the selected period.")