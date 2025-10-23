import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.database import get_tasks
from utils.helpers import get_color_by_priority, get_status_emoji

def app():
    st.title("📊 Dashboard")
    st.markdown("---")
    
    # Get tasks
    tasks = get_tasks()
    if not tasks:
        st.info("No tasks found. Start by adding some tasks!")
        return
    
    df = pd.DataFrame(tasks)
    
    # KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_tasks = len(df)
        st.metric("Total Tasks", total_tasks)
    
    with col2:
        completed_tasks = len(df[df['status'] == 'Completed'])
        st.metric("Completed", completed_tasks)
    
    with col3:
        pending_tasks = len(df[df['status'] == 'Pending'])
        st.metric("Pending", pending_tasks)
    
    with col4:
        overdue_tasks = len(df[(df['due_date'] < datetime.now().strftime('%Y-%m-%d')) & (df['status'] != 'Completed')])
        st.metric("Overdue", overdue_tasks)
    
    st.markdown("---")
    
    # Main dashboard content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Tasks by Status
        st.subheader("Tasks by Status")
        status_counts = df['status'].value_counts()
        fig_status = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            color=status_counts.index,
            color_discrete_map={
                'Completed': '#00cc96',
                'In Progress': '#636efa',
                'Pending': '#ef553b',
                'On Hold': '#ab63fa'
            }
        )
        st.plotly_chart(fig_status, use_container_width=True)
        
        # Recent Tasks
        st.subheader("Recent Tasks")
        recent_tasks = df.sort_values('created_date', ascending=False).head(10)
        for _, task in recent_tasks.iterrows():
            priority_class = f"task-card-{task['priority'].lower()}" if task['priority'] else "task-card"
            with st.container():
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    emoji = get_status_emoji(task['status'])
                    priority_color = get_color_by_priority(task['priority'])
                    st.markdown(
                        f"<div class='task-card {priority_class}'>"
                        f"<strong>{emoji} {task['title']}</strong><br>"
                        f"Priority: <span style='color: {priority_color};'>{task['priority']}</span> | "
                        f"Due: {task['due_date']} | "
                        f"Status: {task['status']}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
    
    with col2:
        # Tasks by Priority
        st.subheader("Tasks by Priority")
        priority_counts = df['priority'].value_counts()
        fig_priority = px.bar(
            x=priority_counts.values,
            y=priority_counts.index,
            orientation='h',
            color=priority_counts.index,
            color_discrete_map={
                'High': '#ff6b6b',
                'Medium': '#ffd93d',
                'Low': '#6bcf7f'
            }
        )
        fig_priority.update_layout(showlegend=False)
        st.plotly_chart(fig_priority, use_container_width=True)
        
        # Upcoming Deadlines
        st.subheader("⏰ Upcoming Deadlines")
        upcoming = df[
            (df['due_date'] >= datetime.now().strftime('%Y-%m-%d')) & 
            (df['status'] != 'Completed')
        ].sort_values('due_date').head(5)
        
        for _, task in upcoming.iterrows():
            days_left = (datetime.strptime(task['due_date'], '%Y-%m-%d') - datetime.now()).days
            st.write(f"**{task['title']}** - {days_left} days left")