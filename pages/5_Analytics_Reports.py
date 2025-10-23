import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.database import get_tasks, get_time_entries
from utils.helpers import format_date, format_duration
import base64
from io import BytesIO

def app():
    st.title("📈 Analytics & Reports")
    st.markdown("---")
    
    # Date range selection
    col1, col2 = st.columns(2)
    
    with col1:
        date_from = st.date_input("From Date", datetime.now().date() - timedelta(days=30))
    
    with col2:
        date_to = st.date_input("To Date", datetime.now().date())
    
    # Get data
    tasks = get_tasks({
        'date_from': date_from.strftime('%Y-%m-%d'),
        'date_to': date_to.strftime('%Y-%m-%d')
    })
    
    time_entries = get_time_entries({
        'date_from': date_from.strftime('%Y-%m-%d'),
        'date_to': date_to.strftime('%Y-%m-%d')
    })
    
    if not tasks:
        st.info("No data available for the selected period.")
        return
    
    df_tasks = pd.DataFrame(tasks)
    df_time = pd.DataFrame(time_entries) if time_entries else pd.DataFrame()
    
    # Report type selection
    report_type = st.selectbox(
        "Select Report Type",
        [
            "Executive Summary", 
            "Task Performance", 
            "Team Productivity",
            "Time Analysis", 
            "Project Health"
        ]
    )
    
    if report_type == "Executive Summary":
        show_executive_summary(df_tasks, df_time, date_from, date_to)
    elif report_type == "Task Performance":
        show_task_performance(df_tasks, df_time)
    elif report_type == "Team Productivity":
        show_team_productivity(df_tasks, df_time)
    elif report_type == "Time Analysis":
        show_time_analysis(df_tasks, df_time)
    elif report_type == "Project Health":
        show_project_health(df_tasks)
    
    # Export section
    st.markdown("---")
    st.subheader("📤 Export Reports")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Export to Excel", use_container_width=True):
            export_to_excel(df_tasks, df_time, date_from, date_to)
    
    with col2:
        if st.button("Export to CSV", use_container_width=True):
            export_to_csv(df_tasks, df_time)

def show_executive_summary(df_tasks, df_time, date_from, date_to):
    """Display executive summary report"""
    st.subheader("📊 Executive Summary")
    
    # KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_tasks = len(df_tasks)
        st.metric("Total Tasks", total_tasks)
    
    with col2:
        completed_tasks = len(df_tasks[df_tasks['status'] == 'Completed'])
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        st.metric("Completion Rate", f"{completion_rate:.1f}%")
    
    with col3:
        avg_completion_time = df_tasks[df_tasks['status'] == 'Completed']['actual_hours'].mean() if not df_tasks.empty else 0
        st.metric("Avg. Completion Time", f"{avg_completion_time:.1f} hrs")
    
    with col4:
        if not df_time.empty:
            total_billable = df_time[df_time['billable'] == True]['duration_minutes'].sum() / 60
            st.metric("Billable Hours", f"{total_billable:.1f}")
        else:
            st.metric("Billable Hours", "0")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Tasks by status
        status_counts = df_tasks['status'].value_counts()
        fig_status = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="Task Distribution by Status"
        )
        st.plotly_chart(fig_status, use_container_width=True)
    
    with col2:
        # Tasks by priority
        priority_counts = df_tasks['priority'].value_counts()
        fig_priority = px.bar(
            x=priority_counts.values,
            y=priority_counts.index,
            orientation='h',
            title="Tasks by Priority"
        )
        st.plotly_chart(fig_priority, use_container_width=True)

def show_task_performance(df_tasks, df_time):
    """Display task performance analytics"""
    st.subheader("🚀 Task Performance Analysis")
    
    # Completion rate by category
    if 'category' in df_tasks.columns:
        category_performance = df_tasks.groupby('category').agg({
            'id': 'count',
            'status': lambda x: (x == 'Completed').sum()
        }).reset_index()
        category_performance['completion_rate'] = (category_performance['status'] / category_performance['id'] * 100).round(1)
        
        fig_category = px.bar(
            category_performance, 
            x='category', 
            y='completion_rate',
            title='Completion Rate by Category'
        )
        st.plotly_chart(fig_category, use_container_width=True)

def show_team_productivity(df_tasks, df_time):
    """Display team productivity analytics"""
    st.subheader("👥 Team Productivity")
    
    # Tasks by assignee
    if 'assigned_to_name' in df_tasks.columns:
        assignee_stats = df_tasks.groupby('assigned_to_name').agg({
            'id': 'count',
            'status': lambda x: (x == 'Completed').sum()
        }).reset_index()
        assignee_stats['completion_rate'] = (assignee_stats['status'] / assignee_stats['id'] * 100).round(1)
        
        fig_assignee = px.bar(
            assignee_stats,
            x='assigned_to_name',
            y='completion_rate',
            title='Completion Rate by Team Member'
        )
        st.plotly_chart(fig_assignee, use_container_width=True)

def show_time_analysis(df_tasks, df_time):
    """Display time tracking analysis"""
    st.subheader("⏰ Time Analysis")
    
    if not df_time.empty:
        # Time distribution by task
        time_by_task = df_time.groupby('task_title')['duration_minutes'].sum().reset_index()
        time_by_task['hours'] = (time_by_task['duration_minutes'] / 60).round(1)
        
        fig_time_dist = px.bar(
            time_by_task.nlargest(10, 'hours'),
            x='hours',
            y='task_title',
            orientation='h',
            title='Top 10 Tasks by Time Spent (Hours)'
        )
        st.plotly_chart(fig_time_dist, use_container_width=True)

def show_project_health(df_tasks):
    """Display project health indicators"""
    st.subheader("🏥 Project Health Dashboard")
    
    # Calculate health metrics
    total_tasks = len(df_tasks)
    completed_tasks = len(df_tasks[df_tasks['status'] == 'Completed'])
    overdue_tasks = len(df_tasks[
        (df_tasks['due_date'] < datetime.now().strftime('%Y-%m-%d')) & 
        (df_tasks['status'] != 'Completed')
    ])
    
    health_score = 100
    if total_tasks > 0:
        health_score -= (overdue_tasks / total_tasks * 50)  # Overdue penalty
        health_score -= ((total_tasks - completed_tasks) / total_tasks * 30)  # Incomplete penalty
    
    # Health gauge
    fig_health = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = max(0, health_score),
        title = {'text': "Project Health Score"},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 80], 'color': "yellow"},
                {'range': [80, 100], 'color': "lightgreen"},
            ]
        }
    ))
    st.plotly_chart(fig_health, use_container_width=True)

def export_to_excel(df_tasks, df_time, date_from, date_to):
    """Export data to Excel format"""
    output = BytesIO()
    
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Tasks sheet
            df_tasks.to_excel(writer, sheet_name='Tasks', index=False)
            
            # Time entries sheet
            if not df_time.empty:
                df_time.to_excel(writer, sheet_name='Time Entries', index=False)
            
            # Summary sheet
            summary_data = {
                'Metric': ['Total Tasks', 'Completed Tasks', 'Completion Rate', 'Report Period'],
                'Value': [
                    len(df_tasks),
                    len(df_tasks[df_tasks['status'] == 'Completed']),
                    f"{(len(df_tasks[df_tasks['status'] == 'Completed']) / len(df_tasks) * 100) if len(df_tasks) > 0 else 0:.1f}%",
                    f"{date_from} to {date_to}"
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        
        processed_data = output.getvalue()
        
        st.download_button(
            label="📥 Download Excel Report",
            data=processed_data,
            file_name=f"task_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"Error generating Excel file: {e}")

def export_to_csv(df_tasks, df_time):
    """Export data to CSV format"""
    col1, col2 = st.columns(2)
    
    with col1:
        tasks_csv = df_tasks.to_csv(index=False)
        st.download_button(
            label="📥 Download Tasks CSV",
            data=tasks_csv,
            file_name=f"tasks_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col2:
        if not df_time.empty:
            time_csv = df_time.to_csv(index=False)
            st.download_button(
                label="📥 Download Time Data CSV",
                data=time_csv,
                file_name=f"time_entries_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
