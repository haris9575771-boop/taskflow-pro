import streamlit as st
import pandas as pd
from datetime import datetime
from utils.database import get_team_members, get_tasks, add_comment, get_task_comments
from utils.helpers import format_date

def app():
    st.title("Team Collaboration")
    st.markdown("---")
    
    # Team overview
    st.subheader("Team Overview")
    
    team_members = get_team_members()
    tasks = get_tasks()
    df_tasks = pd.DataFrame(tasks) if tasks else pd.DataFrame()
    
    # Team stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Team Members", len(team_members))
    
    with col2:
        active_tasks = len(df_tasks[df_tasks['status'].isin(['Pending', 'In Progress'])]) if not df_tasks.empty else 0
        st.metric("Active Tasks", active_tasks)
    
    with col3:
        completed_this_week = len(df_tasks[
            (df_tasks['status'] == 'Completed') & 
            (pd.to_datetime(df_tasks['completed_date']).dt.isocalendar().week == datetime.now().isocalendar().week)
        ]) if not df_tasks.empty else 0
        st.metric("Completed This Week", completed_this_week)
    
    with col4:
        avg_completion = df_tasks[df_tasks['status'] == 'Completed']['actual_hours'].mean() if not df_tasks.empty else 0
        st.metric("Avg. Completion (hrs)", f"{avg_completion:.1f}")
    
    st.markdown("---")
    
    # Team members grid
    st.subheader("Team Members")
    
    cols = st.columns(3)
    for idx, member in enumerate(team_members):
        with cols[idx % 3]:
            with st.container():
                st.markdown(f"""
                <div style='background: white; padding: 1.5rem; border-radius: 10px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.08);'>
                    <div style='font-size: 2rem; margin-bottom: 0.5rem;'>👤</div>
                    <h3 style='margin: 0;'>{member['name']}</h3>
                    <p style='color: #666; margin: 0.5rem 0;'>{member['email']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Member stats
                member_tasks = df_tasks[df_tasks['assigned_to'] == member['id']] if not df_tasks.empty else pd.DataFrame()
                if not member_tasks.empty:
                    st.write(f"**Tasks:** {len(member_tasks)}")
                    completed = len(member_tasks[member_tasks['status'] == 'Completed'])
                    st.write(f"**Completed:** {completed}")
    
    st.markdown("---")
    
    # Team comments and discussions
    st.subheader("Recent Discussions")
    
    # Show tasks with recent comments
    tasks_with_comments = []
    for task in tasks[:10]:  # Show recent 10 tasks
        comments = get_task_comments(task['id'])
        if comments:
            tasks_with_comments.append({
                'task': task,
                'latest_comment': max(comments, key=lambda x: x['created_date']),
                'comment_count': len(comments)
            })
    
    if tasks_with_comments:
        for item in sorted(tasks_with_comments, key=lambda x: x['latest_comment']['created_date'], reverse=True)[:5]:
            task = item['task']
            latest_comment = item['latest_comment']
            
            with st.expander(f"{task['title']} ({item['comment_count']} comments)"):
                st.write(f"**{latest_comment['user_name']}** - {format_date(latest_comment['created_date'])}")
                st.write(latest_comment['content'])
                
                # Add new comment
                with st.form(key=f"comment_form_{task['id']}"):
                    new_comment = st.text_area("Add your comment", key=f"new_comment_{task['id']}")
                    if st.form_submit_button("Post Comment"):
                        if new_comment:
                            add_comment({
                                'task_id': task['id'],
                                'user_id': st.session_state.user_id,
                                'content': new_comment
                            })
                            st.success("Comment added!")
                            st.rerun()
    else:
        st.info("No recent discussions. Start a conversation by commenting on tasks!")
    
    # Team workload overview
    st.markdown("---")
    st.subheader("Workload Distribution")
    
    if not df_tasks.empty:
        workload_data = []
        for member in team_members:
            member_tasks = df_tasks[df_tasks['assigned_to'] == member['id']]
            workload_data.append({
                'Member': member['name'],
                'Total Tasks': len(member_tasks),
                'Pending': len(member_tasks[member_tasks['status'] == 'Pending']),
                'In Progress': len(member_tasks[member_tasks['status'] == 'In Progress']),
                'Completed': len(member_tasks[member_tasks['status'] == 'Completed'])
            })
        
        workload_df = pd.DataFrame(workload_data)
        st.dataframe(workload_df, use_container_width=True)
