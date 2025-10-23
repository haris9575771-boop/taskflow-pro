import sqlite3
import bcrypt
import json
from utils.database import get_db_connection

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed_password):
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except:
        return False

def create_default_users():
    """Create default users for the system"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if users already exist
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        # Create Luke Wise (team)
        c.execute('''
            INSERT INTO users (email, password_hash, name, type, preferences)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            'luke@burrichteam.com',
            hash_password('LukeWise2024!'),
            'Luke Wise',
            'team',
            json.dumps({'theme': 'light', 'notifications': True, 'default_view': 'dashboard'})
        ))
        
        # Create Burtch Team (client)
        c.execute('''
            INSERT INTO users (email, password_hash, name, type, preferences)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            'client@burrichteam.com',
            hash_password('BurtchTeam2024!'),
            'The Burtch Team',
            'client',
            json.dumps({'theme': 'light', 'notifications': True})
        ))
        
        # Create additional team members for demo
        team_members = [
            ('sarah@burrichteam.com', 'SarahChen2024!', 'Sarah Chen', 'team'),
            ('mike@burrichteam.com', 'MikeRodriguez2024!', 'Mike Rodriguez', 'team'),
            ('emma@burrichteam.com', 'EmmaWilson2024!', 'Emma Wilson', 'team')
        ]
        
        for email, password, name, user_type in team_members:
            c.execute('''
                INSERT INTO users (email, password_hash, name, type)
                VALUES (?, ?, ?, ?)
            ''', (email, hash_password(password), name, user_type))
    
    conn.commit()
    conn.close()

def authenticate_user(email, password):
    """Authenticate a user"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT id, email, password_hash, name, type, preferences 
        FROM users 
        WHERE email = ? AND is_active = 1
    ''', (email,))
    
    result = c.fetchone()
    conn.close()
    
    if result and verify_password(password, result[2]):
        return {
            'id': result[0],
            'email': result[1],
            'name': result[3],
            'type': result[4],
            'preferences': json.loads(result[5]) if result[5] else {}
        }
    
    return None

def get_team_members():
    """Get all active team members"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT id, name, email 
        FROM users 
        WHERE type = 'team' AND is_active = 1
        ORDER BY name
    ''')
    
    results = c.fetchall()
    conn.close()
    
    return [{'id': row[0], 'name': row[1], 'email': row[2]} for row in results]