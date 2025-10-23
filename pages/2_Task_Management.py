import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.database import get_tasks, add_task, update_task, delete_task, get_team_members
from utils.helpers import get_color_by_priority, get_status_emoji

def app():
    st.title("📝 Task Management")
    st.markdown("---")
    
    # Task creation form
    with st.expander("➕ Add New Task", expanded=False):
        with st.form("task_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("Task Title*")
                description = st.text_area("Description")
                
                # Get team members for assignment
                team_members = get_team_members()
                assigned_options = {member['name']: member['id'] for member in team_members}
                assigned_to = st.selectbox("Assign To", list(assigned_options.keys()))
                
                category = st.selectbox("Category", ["Development", "Design", "Meeting", "Documentation", "Review", "Other"])
            
            with col2:
                priority = st.selectbox("Priority", ["High", "Medium", "Low"])
                due_date = st.date_input("Due Date", min_value=datetime.now().date())
                status = st.selectbox("Status", ["Pending", "In Progress", "On Hold"])
                estimated_hours = st.number_input("Estimated Hours", min_value=0.0, step=0.5)
            
            if st.form_submit_button("Create Task"):
                if title:
                    task_data = {
                        'title': title,
                        'description': description,
                        'assigned_to': assigned_options[assigned_to],
                        'assigned_by': st.session_state.user_id,
                        'priority': priority,
                        'status': status,
                        'due_date': due_date.strftime('%Y-%m-%d'),
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
                    st.error("Please fill in the task title!")
    
    # Task filters
    st.subheader("Task List")
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
    
    # Build filters
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
    
    if not show_completed:
        if 'status' in filters:
            if filters['status'] == 'Completed':
                filters['status'] = 'Pending'  # Fallback if Completed was selected but now hidden
        else:
            filters['status'] = ['Pending', 'In Progress', 'On Hold']
    
    # Get filtered tasks
    tasks = get_tasks(filters)
    
    if not tasks:
        st.info("No tasks found matching your filters.")
        return
    
    df = pd.DataFrame(tasks)
    
    # Display tasks
    for _, task in df.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                emoji = get_status_emoji(task['status'])
                priority_color = get_color_by_priority(task['priority'])
                
                with st.expander(f"{emoji} {task['title']} - {task['priority']} Priority", expanded=False):
                    st.write(f"**Description:** {task['description']}")
                    st.write(f"**Assigned To:** {task['assigned_to_name']}")
                    st.write(f"**Due Date:** {task['due_date']}")
                    st.write(f"**Category:** {task['category']}")
                    st.write(f"**Estimated Hours:** {task.get('estimated_hours', 'Not set')}")
                    
                    # Task actions
                    col_a, col_b, col_c, col_d = st.columns(4)
                    
                    with col_a:
                        new_status = st.selectbox(
                            "Update Status",
                            ["Pending", "In Progress", "Completed", "On Hold"],
                            index=["Pending", "In Progress", "Completed", "On Hold"].index(task['status']),
                            key=f"status_{task['id']}"
                        )
                        if new_status != task['status']:
                            if st.button("Update", key=f"update_{task['id']}"):
                                update_data = {'status': new_status}
                                if new_status == 'Completed':
                                    update_data['completed_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                update_task(task['id'], update_data)
                                st.success("Status updated!")
                                st.rerun()
                    
                    with col_b:
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
                        if st.button("📝 Edit", key=f"edit_{task['id']}"):
                            st.session_state.editing_task = task['id']
                    
                    with col_d:
                        if st.button("🗑️ Delete", key=f"delete_{task['id']}"):
                            delete_task(task['id'])
                            st.success("Task deleted!")
                            st.rerun()
            
            with col2:
                st.write(f"**Due:** {task['due_date']}")
                days_until = (datetime.strptime(task['due_date'], '%Y-%m-%d') - datetime.now()).days
                if days_until < 0 and task['status'] != 'Completed':
                    st.error("Overdue!")
                elif days_until <= 2 and task['status'] != 'Completed':
                    st.warning("Due soon!")
                else:
                    st.info(f"{days_until} days")
            
            with col3:
                st.write(f"**Priority:**")
                st.markdown(
                    f"<div class='priority-badge priority-{task['priority'].lower()}'>"
                    f"{task['priority']}"
                    f"</div>",
                    unsafe_allow_html=True
                )
        
        st.markdown("---")
