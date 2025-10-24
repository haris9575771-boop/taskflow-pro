import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import json
import os

def get_db_connection():
    """Get database connection that works on both local and cloud"""
    db_path = 'task_management.db'
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the SQLite database with all tables"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT CHECK(type IN ('team', 'client')) NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            preferences TEXT DEFAULT '{}'
        )
    ''')
    
    # Enhanced tasks table
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            assigned_to INTEGER,
            assigned_by INTEGER,
            priority TEXT CHECK(priority IN ('High', 'Medium', 'Low')) DEFAULT 'Medium',
            status TEXT CHECK(status IN ('Pending', 'In Progress', 'Completed', 'On Hold', 'Cancelled')) DEFAULT 'Pending',
            due_date DATE,
            start_date DATE,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_date TIMESTAMP,
            category TEXT DEFAULT 'General',
            estimated_hours REAL DEFAULT 0,
            actual_hours REAL DEFAULT 0,
            progress INTEGER DEFAULT 0 CHECK(progress >= 0 AND progress <= 100),
            tags TEXT DEFAULT '[]',
            dependencies TEXT DEFAULT '[]',
            recurrence_rule TEXT,
            parent_task_id INTEGER,
            FOREIGN KEY (assigned_to) REFERENCES users (id),
            FOREIGN KEY (assigned_by) REFERENCES users (id),
            FOREIGN KEY (parent_task_id) REFERENCES tasks (id)
        )
    ''')
    
    # Subtasks table
    c.execute('''
        CREATE TABLE IF NOT EXISTS subtasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT CHECK(status IN ('Pending', 'In Progress', 'Completed')) DEFAULT 'Pending',
            assigned_to INTEGER,
            due_date DATE,
            completed_date TIMESTAMP,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks (id),
            FOREIGN KEY (assigned_to) REFERENCES users (id)
        )
    ''')
    
    # Comments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            user_id INTEGER,
            content TEXT NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_edited BOOLEAN DEFAULT 0,
            FOREIGN KEY (task_id) REFERENCES tasks (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Time entries table
    c.execute('''
        CREATE TABLE IF NOT EXISTS time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            user_id INTEGER,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_minutes INTEGER,
            description TEXT,
            billable BOOLEAN DEFAULT 1,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Notifications table
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            message TEXT,
            type TEXT CHECK(type IN ('info', 'warning', 'success', 'error')),
            is_read BOOLEAN DEFAULT 0,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            related_entity_type TEXT,
            related_entity_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_tasks(filters=None):
    """Get tasks with advanced filtering"""
    conn = get_db_connection()
    
    query = """
        SELECT t.*, u.name as assigned_to_name, u2.name as assigned_by_name
        FROM tasks t
        LEFT JOIN users u ON t.assigned_to = u.id
        LEFT JOIN users u2 ON t.assigned_by = u2.id
        WHERE 1=1
    """
    params = []
    
    if filters:
        if filters.get('status'):
            if isinstance(filters['status'], list):
                placeholders = ','.join(['?' for _ in filters['status']])
                query += f" AND t.status IN ({placeholders})"
                params.extend(filters['status'])
            else:
                query += " AND t.status = ?"
                params.append(filters['status'])
                
        if filters.get('priority'):
            query += " AND t.priority = ?"
            params.append(filters['priority'])
            
        if filters.get('assigned_to'):
            query += " AND t.assigned_to = ?"
            params.append(filters['assigned_to'])
            
        if filters.get('category'):
            query += " AND t.category = ?"
            params.append(filters['category'])
            
        if filters.get('date_from'):
            query += " AND t.due_date >= ?"
            params.append(filters['date_from'])
            
        if filters.get('date_to'):
            query += " AND t.due_date <= ?"
            params.append(filters['date_to'])
            
        if filters.get('search'):
            query += " AND (t.title LIKE ? OR t.description LIKE ?)"
            params.extend([f"%{filters['search']}%", f"%{filters['search']}%"])
    
    query += " ORDER BY t.priority DESC, t.due_date, t.created_date DESC"
    
    try:
        df = pd.read_sql_query(query, conn, params=params)
        
        # Parse JSON fields
        for col in ['tags', 'dependencies']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: json.loads(x) if x and x != '[]' else [])
        
        return df.to_dict('records')
    except Exception as e:
        print(f"Error in get_tasks: {e}")
        return []
    finally:
        conn.close()

def add_task(task_data):
    """Add a new task with enhanced fields"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Handle JSON fields
        tags = json.dumps(task_data.get('tags', []))
        dependencies = json.dumps(task_data.get('dependencies', []))
        
        c.execute('''
            INSERT INTO tasks (
                title, description, assigned_to, assigned_by, priority, status, 
                due_date, start_date, category, estimated_hours, progress,
                tags, dependencies
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_data['title'],
            task_data.get('description', ''),
            task_data['assigned_to'],
            task_data['assigned_by'],
            task_data.get('priority', 'Medium'),
            task_data.get('status', 'Pending'),
            task_data.get('due_date'),
            task_data.get('start_date'),
            task_data.get('category', 'General'),
            task_data.get('estimated_hours', 0),
            task_data.get('progress', 0),
            tags,
            dependencies
        ))
        
        task_id = c.lastrowid
        
        # Create notification for assigned user
        if task_data['assigned_to']:
            c.execute('''
                INSERT INTO notifications (user_id, title, message, type, related_entity_type, related_entity_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                task_data['assigned_to'],
                'New Task Assigned',
                f"You have been assigned a new task: {task_data['title']}",
                'info',
                'task',
                task_id
            ))
        
        conn.commit()
        return task_id
    except Exception as e:
        conn.rollback()
        print(f"Error in add_task: {e}")
        return None
    finally:
        conn.close()

def update_task(task_id, updates):
    """Update a task with enhanced fields"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Handle JSON fields
        if 'tags' in updates:
            updates['tags'] = json.dumps(updates['tags'])
        if 'dependencies' in updates:
            updates['dependencies'] = json.dumps(updates['dependencies'])
        
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        values.append(task_id)
        
        c.execute(f'UPDATE tasks SET {set_clause} WHERE id = ?', values)
        
        # Create notification for status changes
        if 'status' in updates and updates['status'] == 'Completed':
            c.execute('SELECT assigned_to FROM tasks WHERE id = ?', (task_id,))
            result = c.fetchone()
            if result and result[0]:
                c.execute('''
                    INSERT INTO notifications (user_id, title, message, type, related_entity_type, related_entity_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    result[0],
                    'Task Completed',
                    f'Task #{task_id} has been marked as completed',
                    'success',
                    'task',
                    task_id
                ))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error in update_task: {e}")
    finally:
        conn.close()

def delete_task(task_id):
    """Delete a task"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error in delete_task: {e}")
    finally:
        conn.close()

def add_time_entry(entry_data):
    """Add a time entry for task tracking"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO time_entries (task_id, user_id, start_time, end_time, duration_minutes, description, billable)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry_data['task_id'],
            entry_data['user_id'],
            entry_data['start_time'],
            entry_data['end_time'],
            entry_data['duration_minutes'],
            entry_data.get('description', ''),
            entry_data.get('billable', True)
        ))
        
        entry_id = c.lastrowid
        conn.commit()
        return entry_id
    except Exception as e:
        conn.rollback()
        print(f"Error in add_time_entry: {e}")
        return None
    finally:
        conn.close()

def get_time_entries(filters=None):
    """Get time entries with filtering"""
    conn = get_db_connection()
    
    query = """
        SELECT te.*, t.title as task_title, u.name as user_name
        FROM time_entries te
        JOIN tasks t ON te.task_id = t.id
        JOIN users u ON te.user_id = u.id
        WHERE 1=1
    """
    params = []
    
    if filters:
        if filters.get('user_id'):
            query += " AND te.user_id = ?"
            params.append(filters['user_id'])
        if filters.get('task_id'):
            query += " AND te.task_id = ?"
            params.append(filters['task_id'])
        if filters.get('date_from'):
            query += " AND DATE(te.start_time) >= ?"
            params.append(filters['date_from'])
        if filters.get('date_to'):
            query += " AND DATE(te.start_time) <= ?"
            params.append(filters['date_to'])
    
    query += " ORDER BY te.start_time DESC"
    
    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df.to_dict('records')
    except Exception as e:
        print(f"Error in get_time_entries: {e}")
        return []
    finally:
        conn.close()

def add_comment(comment_data):
    """Add a comment to a task"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO comments (task_id, user_id, content)
            VALUES (?, ?, ?)
        ''', (
            comment_data['task_id'],
            comment_data['user_id'],
            comment_data['content']
        ))
        
        comment_id = c.lastrowid
        conn.commit()
        return comment_id
    except Exception as e:
        conn.rollback()
        print(f"Error in add_comment: {e}")
        return None
    finally:
        conn.close()

def get_task_comments(task_id):
    """Get all comments for a task"""
    conn = get_db_connection()
    
    query = """
        SELECT c.*, u.name as user_name
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.task_id = ?
        ORDER BY c.created_date ASC
    """
    
    try:
        df = pd.read_sql_query(query, conn, params=(task_id,))
        return df.to_dict('records')
    except Exception as e:
        print(f"Error in get_task_comments: {e}")
        return []
    finally:
        conn.close()

def get_team_members():
    """Get all active team members"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT id, name, email 
            FROM users 
            WHERE type = 'team' AND is_active = 1
            ORDER BY name
        ''')
        
        results = c.fetchall()
        return [{'id': row[0], 'name': row[1], 'email': row[2]} for row in results]
    except Exception as e:
        print(f"Error in get_team_members: {e}")
        return []
    finally:
        conn.close()
