import streamlit as st
import pandas as pd
from datetime import datetime
from utils.database import get_tasks
from utils.helpers import get_color_by_priority

def app():
    st.title("📅 Calendar View")
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
    
    # Get tasks
    tasks = get_tasks()
    if not tasks:
        st.info("No tasks found.")
        return
    
    df = pd.DataFrame(tasks)
    
    if view_type == "Day":
        st.subheader(f"Tasks for {selected_date}")
        
        day_tasks = df[df['due_date'] == selected_date.strftime('%Y-%m-%d')]
        
        if day_tasks.empty:
            st.info("No tasks scheduled for this day.")
        else:
            for _, task in day_tasks.iterrows():
                priority_color = get_color_by_priority(task['priority'])
                
                with st.container():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"**{task['title']}**")
                        st.write(f"Priority: {task['priority']} | Status: {task['status']}")
                    with col_b:
                        st.markdown(
                            f"<div style='background-color: {priority_color}; padding: 10px; border-radius: 5px; text-align: center; color: white;'>"
                            f"{task['priority']} Priority"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    st.markdown("---")
    
    elif view_type == "Week":
        st.subheader(f"Week View")
        
        # Calculate week start and end
        start_of_week = selected_week - pd.Timedelta(days=selected_week.weekday())
        end_of_week = start_of_week + pd.Timedelta(days=6)
        
        week_tasks = df[
            (df['due_date'] >= start_of_week.strftime('%Y-%m-%d')) & 
            (df['due_date'] <= end_of_week.strftime('%Y-%m-%d'))
        ]
        
        # Display by day
        for i in range(7):
            day = start_of_week + pd.Timedelta(days=i)
            day_tasks = week_tasks[week_tasks['due_date'] == day.strftime('%Y-%m-%d')]
            
            with st.expander(f"{day.strftime('%A, %b %d')} - {len(day_tasks)} tasks"):
                for _, task in day_tasks.iterrows():
                    priority_color = get_color_by_priority(task['priority'])
                    st.write(f"**{task['title']}** ({task['priority']} Priority) - {task['status']}")
    
    else:  # Month view
        st.subheader(f"Month View - {selected_month.strftime('%B %Y')}")
        
        month_tasks = df[
            df['due_date'].str.startswith(selected_month.strftime('%Y-%m'))
        ]
        
        # Create a calendar view (simplified)
        tasks_by_day = month_tasks.groupby('due_date').size()
        
        if tasks_by_day.empty:
            st.info("No tasks scheduled for this month.")
        else:
            st.write("Tasks per day:")
            for date, count in tasks_by_day.items():
                st.write(f"{date}: {count} task(s)")
            
            # Task list for the month
            st.subheader("All Monthly Tasks")
            for _, task in month_tasks.iterrows():
                priority_color = get_color_by_priority(task['priority'])
                st.write(f"**{task['due_date']}**: {task['title']} ({task['priority']} Priority)")