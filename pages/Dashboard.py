import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.database import get_tasks
from utils.helpers import get_color_by_priority, get_status_emoji

def app():
    st.title("Dashboard")
    st.markdown("---")
    
    # Get tasks based on user role
    if st.session_state.user_type == "team":
        # Luke Wise sees only assigned tasks
        tasks = get_tasks({'assigned_to': st.session_state.user_id})
    else:
        # Burtch Team sees all tasks
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
    
    # Role-specific dashboard content
    if st.session_state.user_type == "team":
        show_team_dashboard(df)
    else:
        show_client_dashboard(df)

def show_team_dashboard(df):
    """Dashboard for Luke Wise (Team member)"""
    st.subheader("My Task Overview")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Tasks by Status
        st.write("Tasks by Status")
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
        st.write("Recent Tasks")
        recent_tasks = df.sort_values('created_date', ascending=False).head(10)
        for _, task in recent_tasks.iterrows():
            priority_class = f"task-card-{task['priority'].lower()}" if task['priority'] else "task-card"
            with st.container():
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    status_text = get_status_emoji(task['status'])
                    priority_color = get_color_by_priority(task['priority'])
                    st.markdown(
                        f"<div class='task-card {priority_class}'>"
                        f"<strong>{status_text} {task['title']}</strong><br>"
                        f"Priority: <span style='color: {priority_color};'>{task['priority']}</span> | "
                        f"Due: {task['due_date']} | "
                        f"Status: {task['status']}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
    
    with col2:
        # Tasks by Priority
        st.write("Tasks by Priority")
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
        st.write("Upcoming Deadlines")
        upcoming = df[
            (df['due_date'] >= datetime.now().strftime('%Y-%m-%d')) & 
            (df['status'] != 'Completed')
        ].sort_values('due_date').head(5)
        
        for _, task in upcoming.iterrows():
            days_left = (datetime.strptime(task['due_date'], '%Y-%m-%d') - datetime.now()).days
            st.write(f"**{task['title']}** - {days_left} days left")

def show_client_dashboard(df):
    """Dashboard for The Burtch Team (Client)"""
    st.subheader("Project Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Tasks by Status
        st.write("Tasks by Status")
        status_counts = df['status'].value_counts()
        fig_status = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="Task Distribution"
        )
        st.plotly_chart(fig_status, use_container_width=True)
        
        # Team Performance
        st.write("Team Performance")
        if 'assigned_to_name' in df.columns:
            performance = df.groupby('assigned_to_name').agg({
                'id': 'count',
                'status': lambda x: (x == 'Completed').sum()
            }).reset_index()
            performance['completion_rate'] = (performance['status'] / performance['id'] * 100).round(1)
            
            fig_performance = px.bar(
                performance,
                x='assigned_to_name',
                y='completion_rate',
                title='Completion Rate by Team Member'
            )
            st.plotly_chart(fig_performance, use_container_width=True)
    
    with col2:
        # Tasks by Priority
        st.write("Tasks by Priority")
        priority_counts = df['priority'].value_counts()
        fig_priority = px.bar(
            x=priority_counts.values,
            y=priority_counts.index,
            orientation='h',
            title="Tasks by Priority"
        )
        st.plotly_chart(fig_priority, use_container_width=True)
        
        # Recent Activity
        st.write("Recent Activity")
        recent_tasks = df.sort_values('created_date', ascending=False).head(10)
        for _, task in recent_tasks.iterrows():
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.write(f"**{task['title']}**")
                st.write(f"Assigned to: {task.get('assigned_to_name', 'Unassigned')}")
            with col_b:
                st.write(f"Status: {task['status']}")
            st.markdown("---")
