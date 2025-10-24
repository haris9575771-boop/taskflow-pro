from datetime import datetime, timedelta
import json

def get_color_by_priority(priority):
    """Return color based on priority"""
    colors = {
        'High': '#ff6b6b',
        'Medium': '#ffd93d', 
        'Low': '#6bcf7f'
    }
    return colors.get(priority, '#cccccc')

def get_status_emoji(status):
    """Return emoji based on status"""
    emojis = {
        'Pending': 'Pending',
        'In Progress': 'In Progress',
        'Completed': 'Completed',
        'On Hold': 'On Hold',
        'Cancelled': 'Cancelled'
    }
    return emojis.get(status, 'Task')

def format_date(date_string, format_type='short'):
    """Format date string to readable format"""
    if not date_string:
        return "Not set"
    
    try:
        if isinstance(date_string, str):
            # Handle different date formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                try:
                    date_obj = datetime.strptime(date_string, fmt)
                    break
                except ValueError:
                    continue
            else:
                return str(date_string)
        else:
            date_obj = date_string
            
        if format_type == 'long':
            return date_obj.strftime('%A, %B %d, %Y')
        elif format_type == 'time':
            return date_obj.strftime('%I:%M %p')
        else:
            return date_obj.strftime('%b %d, %Y')
    except:
        return str(date_string)

def calculate_time_remaining(due_date):
    """Calculate days remaining until due date"""
    if not due_date:
        return "No due date"
    
    try:
        if isinstance(due_date, str):
            due = datetime.strptime(due_date, '%Y-%m-%d').date()
        else:
            due = due_date.date()
            
        today = datetime.now().date()
        delta = (due - today).days
        
        if delta < 0:
            return f"Overdue by {abs(delta)} days"
        elif delta == 0:
            return "Due today"
        elif delta == 1:
            return "Due tomorrow"
        elif delta <= 7:
            return f"Due in {delta} days"
        else:
            return f"Due in {delta} days"
    except:
        return "Invalid date"

def calculate_progress_color(progress):
    """Return color based on progress percentage"""
    if progress >= 90:
        return '#28a745'
    elif progress >= 70:
        return '#17a2b8'
    elif progress >= 50:
        return '#ffc107'
    elif progress >= 25:
        return '#fd7e14'
    else:
        return '#dc3545'

def format_duration(minutes):
    """Format duration in minutes to readable format"""
    if minutes < 60:
        return f"{int(minutes)}m"
    elif minutes < 1440:
        hours = minutes // 60
        mins = minutes % 60
        return f"{int(hours)}h {int(mins)}m"
    else:
        days = minutes // 1440
        hours = (minutes % 1440) // 60
        return f"{int(days)}d {int(hours)}h"

def generate_task_id():
    """Generate a unique task ID"""
    return f"TASK-{datetime.now().strftime('%Y%m%d')}-{hash(str(datetime.now()))[-6:].upper()}"

def validate_email(email):
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def get_week_range(date=None):
    """Get start and end of week for a given date"""
    if date is None:
        date = datetime.now()
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)
    return start, end
