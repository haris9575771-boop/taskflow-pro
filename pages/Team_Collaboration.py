import streamlit as st
import pandas as pd
from datetime import datetime
from utils.database import get_team_members, get_tasks, add_comment, get_task_comments
from utils.helpers import format_date

def app():
    st.title("Team Collaboration")
    st.markdown("---")
    
    # Team overview - ONLY LUKE WISE
    st.subheader("Team Overview")
    
    team_members = get_team_members()
    tasks = get_tasks()
    
    # Team stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Team Members", len(team_members))
    
    with col2:
        active_tasks = len([t for t in tasks if t['status'] in ['Pending', 'In Progress']])
        st.metric("Active Tasks", active_tasks)
    
    with col3:
        current_week = datetime.now().isocalendar().week
        completed_this_week = len([
            t for t in tasks 
            if t['status'] == 'Completed' and 
            t.get('completed_date') and 
            datetime.strptime(t['completed_date'], '%Y-%m-%d %H:%M:%S').isocalendar().week == current_week
        ])
        st.metric("Completed This Week", completed_this_week)
    
    with col4:
        completed_tasks = [t for t in tasks if t['status'] == 'Completed' and t.get('actual_hours')]
        avg_completion = sum(t['actual_hours'] for t in completed_tasks) / len(completed_tasks) if completed_tasks else 0
        st.metric("Avg. Completion (hrs)", f"{avg_completion:.1f}")
    
    st.markdown("---")
    
    # Team members grid - ONLY LUKE WISE
    st.subheader("Team Member")
    
    if team_members:
        for member in team_members:
            with st.container():
                st.markdown(f"""
                <div style='background: white; padding: 1.5rem; border-radius: 10px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.08);'>
                    <div style='font-size: 2rem; margin-bottom: 0.5rem;'>👤</div>
                    <h3 style='margin: 0;'>{member['name']}</h3>
                    <p style='color: #666; margin: 0.5rem 0;'>{member['email']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Member stats
                member_tasks = [t for t in tasks if t['assigned_to'] == member['id']]
                if member_tasks:
                    st.write(f"**Total Tasks:** {len(member_tasks)}")
                    completed = len([t for t in member_tasks if t['status'] == 'Completed'])
                    st.write(f"**Completed:** {completed}")
                    st.write(f"**Completion Rate:** {(completed/len(member_tasks)*100):.1f}%")
    else:
        st.info("No team members available")
    
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
