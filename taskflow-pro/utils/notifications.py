import sqlite3
import pandas as pd
from datetime import datetime
from utils.database import get_db_connection

def create_notification(user_id, title, message, notification_type='info', related_entity_type=None, related_entity_id=None):
    """Create a new notification"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO notifications (user_id, title, message, type, related_entity_type, related_entity_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, title, message, notification_type, related_entity_type, related_entity_id))
        
        conn.commit()
    except Exception as e:
        print(f"Error in create_notification: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_unread_notifications(user_id, limit=10):
    """Get unread notifications for a user"""
    conn = get_db_connection()
    
    query = """
        SELECT id, title, message, type, created_date, related_entity_type, related_entity_id
        FROM notifications 
        WHERE user_id = ? AND is_read = 0
        ORDER BY created_date DESC
        LIMIT ?
    """
    
    try:
        df = pd.read_sql_query(query, conn, params=(user_id, limit))
        return df.to_dict('records')
    except Exception as e:
        print(f"Error in get_unread_notifications: {e}")
        return []
    finally:
        conn.close()

def mark_notification_as_read(notification_id):
    """Mark a notification as read"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('UPDATE notifications SET is_read = 1 WHERE id = ?', (notification_id,))
        conn.commit()
    except Exception as e:
        print(f"Error in mark_notification_as_read: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_notification_count(user_id):
    """Get count of unread notifications"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0', (user_id,))
        count = c.fetchone()[0]
        return count
    except Exception as e:
        print(f"Error in get_notification_count: {e}")
        return 0
    finally:
        conn.close()