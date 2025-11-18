import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.database import get_tasks, add_task, update_task, archive_task, get_team_members, add_comment, get_task_comments
from utils.helpers import get_color_by_priority, get_status_emoji, format_date

def app():
    st.title("Task Management")
    st.markdown("---")
    
    # Role-specific functionality
    if st.session_state.user_type == "client":
        # Burtch Team - Can create and manage all tasks
        show_client_task_management()
    else:
        # Luke Wise - Can only view and update assigned tasks
        show_team_task_management()

def show_client_task_management():
    """Task management for The Burtch Team (Client)"""
    
    # Task creation form
    with st.expander("Create New Task", expanded=False):
        with st.form("task_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("Task Title*")
                description = st.text_area("Description")
                
                # Get team members for assignment - ONLY LUKE WISE
                team_members = get_team_members()
                if team_members:
                    assigned_options = {member['name']: member['id'] for member in team_members}
                    assigned_to = st.selectbox("Assign To", list(assigned_options.keys()))
                else:
                    st.error("No team members available")
                    assigned_to = None
                
                category = st.selectbox("Category", ["Development", "Design", "Meeting", "Documentation", "Review", "Other"])
            
            with col2:
                priority = st.selectbox("Priority", ["High", "Medium", "Low"])
                due_date = st.date_input("Due Date", min_value=datetime.now().date())
                start_date = st.date_input("Start Date", min_value=datetime.now().date())
                estimated_hours = st.number_input("Estimated Hours", min_value=0.0, step=0.5)
            
            if st.form_submit_button("Create Task"):
                if title and assigned_to:
                    task_data = {
                        'title': title,
                        'description': description,
                        'assigned_to': assigned_options[assigned_to],
                        'assigned_by': st.session_state.user_id,
                        'priority': priority,
                        'status': "Pending",
                        'due_date': due_date.strftime('%Y-%m-%d'),
                        'start_date': start_date.strftime('%Y-%m-%d'),
                        'category': category,
                        'estimated_hours': estimated_hours
                    }
                    
                    task_id = add_task(task_data)
                    if task_id:
                        st.success(f"Task '{title}' created successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to create task. Please try again.")
                else:
                    st.error("Please fill in the task title and assignee!")

    # Task management section
    st.subheader("Manage Tasks")
    
    # Task filters - FIXED to properly handle completed tasks
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filter_status = st.selectbox("Filter by Status", ["All", "Pending", "In Progress", "Completed", "On Hold"])
    
    with col2:
        filter_priority = st.selectbox("Filter by Priority", ["All", "High", "Medium", "Low"])
    
    with col3:
        team_members = get_team_members()
        assignee_options = ["All"] + [member['name'] for member in team_members]
        filter_assigned = st.selectbox("Filter by Assignee", assignee_options)
    
    with col4:
        show_completed = st.checkbox("Show Completed Tasks", value=True)
    
    # Build filters - FIXED to properly handle status filtering
    filters = {}
    if filter_status != "All":
        filters['status'] = filter_status
    
    if filter_priority != "All":
        filters['priority'] = filter_priority
    
    if filter_assigned != "All":
        # Find user ID for the selected assignee
        assignee_id = next((member['id'] for member in team_members if member['name'] == filter_assigned), None)
        if assignee_id:
            filters['assigned_to'] = assignee_id
    
    # Get filtered tasks - FIXED to include completed tasks based on checkbox
    tasks = get_tasks(filters, include_completed=show_completed)
    display_task_list(tasks, True)

def show_team_task_management():
    """Task management for Luke Wise (Team)"""
    st.subheader("My Tasks")
    
    # Task filters for team member
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_status = st.selectbox("Filter by Status", ["All", "Pending", "In Progress", "Completed", "On Hold"])
    
    with col2:
        filter_priority = st.selectbox("Filter by Priority", ["All", "High", "Medium", "Low"])
    
    with col3:
        show_completed = st.checkbox("Show Completed Tasks", value=False)
    
    # Build filters
    filters = {'assigned_to': st.session_state.user_id}
    if filter_status != "All":
        filters['status'] = filter_status
    
    if filter_priority != "All":
        filters['priority'] = filter_priority
    
    # Get filtered tasks - FIXED to properly handle completed tasks
    tasks = get_tasks(filters, include_completed=show_completed)
    display_task_list(tasks, False)

def display_task_list(tasks, is_client=False):
    """Display task list with appropriate controls based on user role"""
    if not tasks:
        st.info("No tasks found matching your filters.")
        return
    
    # Display tasks
    for task in tasks:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                status_text = get_status_emoji(task['status'])
                priority_color = get_color_by_priority(task['priority'])
                
                with st.expander(f"{status_text} {task['title']} - {task['priority']} Priority", expanded=False):
                    st.write(f"**Description:** {task['description']}")
                    st.write(f"**Assigned To:** {task['assigned_to_name']}")
                    st.write(f"**Due Date:** {task['due_date']}")
                    st.write(f"**Category:** {task['category']}")
                    st.write(f"**Estimated Hours:** {task.get('estimated_hours', 'Not set')}")
                    
                    # Comments section
                    st.write("---")
                    st.write("**Comments:**")
                    comments = get_task_comments(task['id'])
                    if comments:
                        for comment in comments:
                            st.write(f"**{comment['user_name']}** ({format_date(comment['created_date'])}):")
                            st.write(f"{comment['content']}")
                            st.write("---")
                    else:
                        st.write("No comments yet.")
                    
                    # Add comment
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
                    
                    # Task actions based on user role
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        if not is_client or st.session_state.user_type == "team":
                            # Team members and clients can update status
                            new_status = st.selectbox(
                                "Update Status",
                                ["Pending", "In Progress", "Completed", "On Hold"],
                                index=["Pending", "In Progress", "Completed", "On Hold"].index(task['status']),
                                key=f"status_{task['id']}"
                            )
                            if new_status != task['status']:
                                if st.button("Update Status", key=f"update_{task['id']}"):
                                    update_data = {'status': new_status}
                                    if new_status == 'Completed':
                                        update_data['completed_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    update_task(task['id'], update_data)
                                    st.success("Status updated!")
                                    st.rerun()
                    
                    with col_b:
                        if st.session_state.user_type == "team":
                            # Only team members can log actual hours
                            actual_hours = st.number_input(
                                "Actual Hours",
                                min_value=0.0,
                                step=0.5,
                                value=float(task.get('actual_hours', 0)),
                                key=f"hours_{task['id']}"
                            )
                            if actual_hours != task.get('actual_hours', 0):
                                if st.button("Save Hours", key=f"save_hours_{task['id']}"):
                                    update_task(task['id'], {'actual_hours': actual_hours})
                                    st.success("Hours updated!")
                                    st.rerun()
                    
                    with col_c:
                        if is_client and st.session_state.user_type == "client":
                            # Only clients can archive tasks
                            if st.button("Archive Task", key=f"archive_{task['id']}"):
                                archive_task(task['id'])
                                st.success("Task archived!")
                                st.rerun()
            
            with col2:
                st.write(f"**Due:** {task['due_date']}")
                try:
                    due_date = datetime.strptime(task['due_date'], '%Y-%m-%d').date()
                    today = datetime.now().date()
                    days_until = (due_date - today).days
                    
                    if days_until < 0 and task['status'] != 'Completed':
                        st.error("Overdue!")
                    elif days_until <= 2 and task['status'] != 'Completed':
                        st.warning("Due soon!")
                    elif task['status'] == 'Completed':
                        st.success("Completed!")
                    else:
                        st.info(f"{days_until} days")
                except:
                    st.info("No due date")
            
            with col3:
                st.write(f"**Priority:**")
                st.markdown(
                    f"<div class='priority-badge priority-{task['priority'].lower()}'>"
                    f"{task['priority']}"
                    f"</div>",
                    unsafe_allow_html=True
                )
        
        st.markdown("---")
