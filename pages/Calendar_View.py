import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.database import get_tasks
from utils.helpers import get_color_by_priority, format_date

def app():
    st.title("Calendar View")
    st.markdown("---")
    
    # Date selection
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        view_type = st.selectbox("View", ["Day", "Week", "Month"])
    
    with col2:
        if view_type == "Day":
            selected_date = st.date_input("Select Date", datetime.now().date())
        elif view_type == "Week":
            selected_week = st.date_input("Select Week", datetime.now().date())
        else:  # Month
            selected_month = st.date_input("Select Month", datetime.now().date())
    
    # Get tasks based on user role - FIXED to include all tasks
    if st.session_state.user_type == "team":
        tasks = get_tasks({'assigned_to': st.session_state.user_id}, include_completed=True)
    else:
        tasks = get_tasks(include_completed=True)
        
    if not tasks:
        st.info("No tasks found.")
        return
    
    if view_type == "Day":
        st.subheader(f"Tasks for {selected_date}")
        
        day_tasks = [t for t in tasks if t['due_date'] == selected_date.strftime('%Y-%m-%d')]
        
        if not day_tasks:
            st.info("No tasks scheduled for this day.")
        else:
            for task in day_tasks:
                priority_color = get_color_by_priority(task['priority'])
                
                with st.container():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"**{task['title']}**")
                        st.write(f"Priority: {task['priority']} | Status: {task['status']}")
                        st.write(f"Assigned to: {task.get('assigned_to_name', 'Unassigned')}")
                        if task['description']:
                            st.write(f"Description: {task['description']}")
                    with col_b:
                        st.markdown(
                            f"<div style='background-color: {priority_color}; padding: 10px; border-radius: 5px; text-align: center; color: white;'>"
                            f"{task['priority']} Priority"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        st.write(f"**Status:** {task['status']}")
                    st.markdown("---")
    
    elif view_type == "Week":
        st.subheader(f"Week View")
        
        # Calculate week start and end
        start_of_week = selected_week - timedelta(days=selected_week.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        week_tasks = [
            t for t in tasks 
            if t['due_date'] and 
            start_of_week.strftime('%Y-%m-%d') <= t['due_date'] <= end_of_week.strftime('%Y-%m-%d')
        ]
        
        # Display by day
        for i in range(7):
            day = start_of_week + timedelta(days=i)
            day_tasks = [t for t in week_tasks if t['due_date'] == day.strftime('%Y-%m-%d')]
            
            with st.expander(f"{day.strftime('%A, %b %d')} - {len(day_tasks)} tasks"):
                for task in day_tasks:
                    priority_color = get_color_by_priority(task['priority'])
                    st.write(f"**{task['title']}** ({task['priority']} Priority) - {task['status']}")
                    if task['description']:
                        st.write(f"_{task['description']}_")
    
    else:  # Month view
        st.subheader(f"Month View - {selected_month.strftime('%B %Y')}")
        
        month_tasks = [
            t for t in tasks 
            if t['due_date'] and t['due_date'].startswith(selected_month.strftime('%Y-%m'))
        ]
        
        # Create a calendar view (simplified)
        tasks_by_day = {}
        for task in month_tasks:
            day = task['due_date']
            if day not in tasks_by_day:
                tasks_by_day[day] = []
            tasks_by_day[day].append(task)
        
        if not tasks_by_day:
            st.info("No tasks scheduled for this month.")
        else:
            st.write("Tasks per day:")
            for date, day_tasks in sorted(tasks_by_day.items()):
                with st.expander(f"{date}: {len(day_tasks)} task(s)"):
                    for task in day_tasks:
                        st.write(f"**{task['title']}** ({task['priority']} Priority) - {task['status']}")
