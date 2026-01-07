from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os
from datetime import datetime, timedelta
from matching_engine import MatchingEngine  # Import the matching engine

def check_password(hashed_password, password):
    from werkzeug.security import check_password_hash
    return check_password_hash(hashed_password, password)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'your_secret_key_here'  # Change this to a random secret key

# Database setup
DATABASE = 'study_groups.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db_exists():
    """Ensure the database file and tables exist"""
    try:
        init_db()
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def init_db():
    """Initialize the database with required tables"""
    with app.app_context():
        db = get_db_connection()
        
        # Create users table
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create study_groups table
        db.execute('''
            CREATE TABLE IF NOT EXISTS study_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT,
                goal TEXT,
                date TEXT,
                time TEXT,
                location TEXT,
                max_members INTEGER DEFAULT 4,
                current_members INTEGER DEFAULT 0,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # Check if time and location columns exist, if not add them
        try:
            db.execute('SELECT time, location FROM study_groups LIMIT 1')
        except sqlite3.OperationalError:
            # Add time column if it doesn't exist
            try:
                db.execute('ALTER TABLE study_groups ADD COLUMN time TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Add location column if it doesn't exist
            try:
                db.execute('ALTER TABLE study_groups ADD COLUMN location TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
        
        # Create group_members table
        db.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                group_id INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (group_id) REFERENCES study_groups (id),
                UNIQUE(user_id, group_id)
            )
        ''')
        
        # Create user_preferences table
        db.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                subjects TEXT,  -- Comma-separated subjects of interest
                availability TEXT,  -- JSON string of availability
                learning_style TEXT,
                experience_level TEXT,
                preferred_goals TEXT,  -- Comma-separated goals
                preferred_dates TEXT,  -- Comma-separated dates
                preferred_group_size TEXT,  -- small or large
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        db.commit()
        db.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
@app.route('/auth/register', methods=['POST'])
def register():
    # Check if request is JSON (from frontend JavaScript)
    if request.is_json or request.content_type == 'application/json':
        data = request.get_json()
        name = data.get('name', '').strip()
        student_id = data.get('student_id', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Validate required fields
        if not name or not student_id or not password:
            return jsonify({'success': False, 'message': 'Name, Student ID, and Password are required'}), 400
        
        # Hash the password before storing
        from werkzeug.security import generate_password_hash
        hashed_password = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            conn.execute(
                'INSERT INTO users (student_id, name, email, password_hash) VALUES (?, ?, ?, ?)',
                (student_id, name, email, hashed_password)
            )
            
            # Get the newly created user ID
            cursor = conn.execute('SELECT id FROM users WHERE student_id = ?', (student_id,))
            user_row = cursor.fetchone()
            if user_row is None:
                conn.close()
                return jsonify({'success': False, 'message': 'Registration failed, user not found'}), 500
            user_id = user_row['id']
            
            # Insert default user preferences
            conn.execute(
                'INSERT INTO user_preferences (user_id, subjects, availability, learning_style, experience_level, preferred_goals, preferred_dates, preferred_group_size) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (user_id, '', '', '', '', '', '', '')
            )
            
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Registration successful'})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'message': 'Student ID or email already exists'}), 400
    else:
        # Handle traditional form submission
        if request.method == 'POST':
            name = request.form['name']
            username = request.form['student_id']  # Using student_id field from form
            email = request.form['email']
            password = request.form['password']
                    
            # Hash the password before storing
            from werkzeug.security import generate_password_hash
            hashed_password = generate_password_hash(password)
                    
            try:
                conn = get_db_connection()
                conn.execute(
                    'INSERT INTO users (student_id, name, email, password_hash) VALUES (?, ?, ?, ?)',
                    (username, name, email, hashed_password)
                )
                        
                # Get the newly created user ID
                cursor = conn.execute('SELECT id FROM users WHERE student_id = ?', (username,))
                user_row = cursor.fetchone()
                if user_row is None:
                    conn.close()
                    return render_template('register.html', error='Registration failed, user not found')
                user_id = user_row['id']
                
                # Insert default user preferences
                conn.execute(
                    'INSERT INTO user_preferences (user_id, subjects, availability, learning_style, experience_level, preferred_goals, preferred_dates, preferred_group_size) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (user_id, '', '', '', '', '', '', '')
                )
                
                conn.commit()
                conn.close()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                return render_template('register.html', error='Username or email already exists')
        
        return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
@app.route('/auth/login', methods=['POST'])
def login():
    # Check if request is JSON (from frontend JavaScript)
    if request.is_json or request.content_type == 'application/json':
        data = request.get_json()
        student_id = data.get('student_id', '').strip()
        password = data.get('password', '')
        
        # Validate required fields
        if not student_id or not password:
            return jsonify({'success': False, 'message': 'Student ID and Password are required'}), 400
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE student_id = ?', (student_id,)
        ).fetchone()
        conn.close()
        
        if user and check_password(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['student_id']
            session['role'] = 'admin' if user['is_admin'] else 'student'
            
            # Return success response for JSON request
            return jsonify({'success': True, 'message': 'Login successful', 'redirect_url': '/'})
        else:
            return jsonify({'success': False, 'message': 'Invalid Student ID or password'}), 401
    else:
        # Handle traditional form submission
        if request.method == 'POST':
            username = request.form['student_id']
            password = request.form['password']
            
            conn = get_db_connection()
            user = conn.execute(
                'SELECT * FROM users WHERE student_id = ?', (username,)
            ).fetchone()
            conn.close()
            
            if user and check_password(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['student_id']
                session['role'] = 'admin' if user['is_admin'] else 'student'
                
                if user['is_admin']:
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('find_group'))
            else:
                return render_template('login.html', error='Invalid Student ID or password')
        
        return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    
    # If request is AJAX/JSON, return JSON response
    if request.is_json or (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')):
        return jsonify({'message': 'Logged out successfully'})
    
    return redirect(url_for('index'))


@app.route('/admin-logout')
def admin_logout():
    session.clear()
    
    # If request is AJAX/JSON, return JSON response
    if request.is_json or (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')):
        return jsonify({'message': 'Admin logged out successfully'})
    
    return redirect(url_for('index'))

@app.route('/create-group', methods=['GET', 'POST'])
def create_group():
    if 'user_id' not in session:
        if request.is_json or (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')):
            return jsonify({'error': 'Not logged in'}), 401
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Handle both JSON and form requests
        if request.is_json or (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')):
            # JSON request from JavaScript
            data = request.get_json()
            subject = data.get('subject', '').strip()
            goal = data.get('goal', '').strip()
            date = data.get('date', '').strip()
            time = data.get('time', '').strip()
            location = data.get('location', '').strip()
            max_members = int(data.get('maxMembers', 10))
            
            # Generate a name and description based on the inputs
            name = f"{subject} Study Group"
            description = f"Study session for {subject} on {date} at {time} located at {location}. Goal: {goal}"
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO study_groups (name, subject, description, goal, date, time, location, max_members, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (name, subject, description, goal, date, time, location, max_members, session['user_id'])
            )
            group_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Add the creator as a member of their own group
            conn = get_db_connection()
            conn.execute(
                'INSERT OR IGNORE INTO group_members (user_id, group_id) VALUES (?, ?)',
                (session['user_id'], group_id)
            )
            conn.execute(
                'UPDATE study_groups SET current_members = current_members + 1 WHERE id = ?',
                (group_id,)
            )
            conn.commit()
            conn.close()
            
            return jsonify({'message': 'Group created successfully', 'group_id': group_id})
        else:
            # Form request
            name = request.form['name']
            subject = request.form['subject']
            description = request.form['description']
            goal = request.form.get('goal', '')
            date = request.form.get('date', '')
            time = request.form.get('time', '')  # Get time from form if available
            location = request.form.get('location', '')  # Get location from form if available
            max_members = int(request.form['max_members'])
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO study_groups (name, subject, description, goal, date, time, location, max_members, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (name, subject, description, goal, date, time, location, max_members, session['user_id'])
            )
            group_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Add the creator as a member of their own group
            conn = get_db_connection()
            conn.execute(
                'INSERT OR IGNORE INTO group_members (user_id, group_id) VALUES (?, ?)',
                (session['user_id'], group_id)
            )
            conn.execute(
                'UPDATE study_groups SET current_members = current_members + 1 WHERE id = ?',
                (group_id,)
            )
            conn.commit()
            conn.close()
            
            return redirect(url_for('my_groups'))
    
    return render_template('create-group.html')

@app.route('/find-group')
def find_group():
    if 'user_id' not in session:
        if (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')) or \
           request.args.get('format') == 'json' or \
           (request.path.startswith('/find-group') and request.is_json):
            return jsonify({'error': 'Not logged in'}), 401
        return redirect(url_for('login'))
    
    # Get filter parameters
    subject_filter = request.args.get('subject')
    goal_filter = request.args.get('goal')
    date_filter = request.args.get('date')
    
    conn = get_db_connection()
    
    # Build the query with optional filters
    query = '''
        SELECT g.id, g.name, g.subject, g.description, g.goal, g.date, g.time, g.location, g.max_members, g.current_members, g.created_by, g.created_at, u.student_id as creator 
        FROM study_groups g 
        JOIN users u ON g.created_by = u.id 
        WHERE 1=1
    '''
    params = []
        
    if subject_filter and subject_filter != 'all':
        query += ' AND g.subject = ?'
        params.append(subject_filter)
        
    if goal_filter and goal_filter != 'all':
        query += ' AND g.goal = ?'
        params.append(goal_filter)
        
    # Add date filtering logic
    if date_filter and date_filter != 'all':
        # datetime and timedelta are already imported at the top of the file
        today = datetime.now().date()
            
        if date_filter == 'today':
            query += ' AND date(g.date) = date(?)'
            params.append(today.strftime('%Y-%m-%d'))
        elif date_filter == 'thisWeek':
            # Calculate start of week (Monday) and end of week (Sunday)
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            query += ' AND date(g.date) BETWEEN date(?) AND date(?)'
            params.append(start_of_week.strftime('%Y-%m-%d'))
            params.append(end_of_week.strftime('%Y-%m-%d'))
        elif date_filter == 'nextWeek':
            # Calculate start of next week and end of next week
            start_of_next_week = today - timedelta(days=today.weekday()) + timedelta(weeks=1)
            end_of_next_week = start_of_next_week + timedelta(days=6)
            query += ' AND date(g.date) BETWEEN date(?) AND date(?)'
            params.append(start_of_next_week.strftime('%Y-%m-%d'))
            params.append(end_of_next_week.strftime('%Y-%m-%d'))
        
    groups = conn.execute(query, params).fetchall()
    conn.close()
    
    # Return JSON if requested by JavaScript
    if (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')) or \
       request.args.get('format') == 'json' or \
       (request.path.startswith('/find-group') and request.is_json):
        groups_list = []
        for group in groups:
            groups_list.append({
                'id': group['id'],
                'name': group['name'],
                'subject': group['subject'],
                'goal': group['goal'],
                'date': group['date'],
                'time': group['time'] if group['time'] else '',  # time might not exist in schema
                'location': group['location'] if group['location'] else '',  # location might not exist in schema
                'current_members': group['current_members'],
                'max_members': group['max_members'],
                'creator': group['creator']
            })
        return jsonify(groups_list)
    
    return render_template('find-group.html', groups=groups)

@app.route('/my-groups')
def my_groups():
    if 'user_id' not in session:
        if (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')) or \
           request.args.get('format') == 'json' or \
           (request.path.startswith('/my-groups') and request.is_json):
            return jsonify({'error': 'Not logged in'}), 401
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get groups the user has joined
    my_groups = conn.execute('''
        SELECT sg.id, sg.name, sg.subject, sg.description, sg.goal, sg.date, sg.time, sg.location, sg.max_members, sg.current_members, sg.created_by, sg.created_at, u.student_id as creator 
        FROM study_groups sg
        JOIN group_members gm ON sg.id = gm.group_id
        JOIN users u ON sg.created_by = u.id
        WHERE gm.user_id = ?
        ORDER BY sg.created_at DESC
    ''', (session['user_id'],)).fetchall()
    
    # Get groups the user has created
    created_groups = conn.execute(
        'SELECT id, name, subject, description, goal, date, time, location, max_members, current_members, created_by, created_at, (SELECT student_id FROM users WHERE id = created_by) as creator FROM study_groups WHERE created_by = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
    
    conn.close()
    
    # Return JSON if requested by JavaScript
    if (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')) or \
       request.args.get('format') == 'json' or \
       (request.path.startswith('/my-groups') and request.is_json):
        groups_list = []
        
        # Combine and sort all groups by creation date in descending order
        all_groups = []
        
        # Create a set of created group IDs to identify them properly
        created_group_ids = set(group['id'] for group in created_groups)
        
        # Add joined groups and determine type
        for group in my_groups:
            group_type = 'created' if group['id'] in created_group_ids else 'joined'
            all_groups.append({
                'id': group['id'],
                'name': group['name'],
                'subject': group['subject'],
                'goal': group['goal'],
                'date': group['date'],
                'time': group['time'] if group['time'] else '',  # time might not exist in schema
                'location': group['location'] if group['location'] else '',  # location might not exist in schema
                'current_members': group['current_members'],
                'max_members': group['max_members'],
                'creator': group['creator'],
                'created_at': group['created_at'],
                'type': group_type
            })
        
        # Add groups that user created but is not a member of (edge case)
        for group in created_groups:
            if not any(g['id'] == group['id'] for g in all_groups):
                all_groups.append({
                    'id': group['id'],
                    'name': group['name'],
                    'subject': group['subject'],
                    'goal': group['goal'],
                    'date': group['date'],
                    'time': group['time'] if group['time'] else '',  # time might not exist in schema
                    'location': group['location'] if group['location'] else '',  # location might not exist in schema
                    'current_members': group['current_members'],
                    'max_members': group['max_members'],
                    'creator': group['creator'],
                    'created_at': group['created_at'],
                    'type': 'created'  # indicate this is a created group
                })
        
        # Sort all groups by creation date in descending order
        all_groups.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify(all_groups)
    
    return render_template('my-groups.html', my_groups=my_groups, created_groups=created_groups)

@app.route('/join-group/<int:group_id>', methods=['GET', 'POST'])
def join_group(group_id):
    if 'user_id' not in session:
        if request.method == 'POST':
            return jsonify({'error': 'Not logged in'}), 401
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Check if user is already in the group
    existing_member = conn.execute(
        'SELECT * FROM group_members WHERE user_id = ? AND group_id = ?',
        (session['user_id'], group_id)
    ).fetchone()
    
    if existing_member:
        conn.close()
        if request.method == 'POST':
            return jsonify({'error': 'Already joined this group'})
        return redirect(url_for('find_group'))
    
    # Add user to the group
    try:
        conn.execute(
            'INSERT INTO group_members (user_id, group_id) VALUES (?, ?)',
            (session['user_id'], group_id)
        )
        # Update current members count
        conn.execute(
            'UPDATE study_groups SET current_members = current_members + 1 WHERE id = ?',
            (group_id,)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # User already joined
    finally:
        conn.close()
    
    if request.method == 'POST':
        return jsonify({'message': 'Successfully joined group', 'group_id': group_id})
    
    return redirect(url_for('my_groups'))

@app.route('/group/<int:group_id>')
def view_group(group_id):
    if 'user_id' not in session:
        if (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')) or \
           request.args.get('format') == 'json' or \
           (request.path.startswith('/group/') and request.is_json):
            return jsonify({'error': 'Not logged in'}), 401
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Check if user is a member of the group
    user_is_member = conn.execute(
        'SELECT 1 FROM group_members WHERE user_id = ? AND group_id = ?',
        (session['user_id'], group_id)
    ).fetchone()
    
    # Also check if user is the creator of the group
    user_is_creator = conn.execute(
        'SELECT 1 FROM study_groups WHERE id = ? AND created_by = ?',
        (group_id, session['user_id'])
    ).fetchone()
    
    if not user_is_member and not user_is_creator:
        conn.close()
        if (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')) or \
           request.args.get('format') == 'json' or \
           (request.path.startswith('/group/') and request.is_json):
            return jsonify({'error': 'Access denied - not a member of this group'}), 403
        return render_template('find-group.html', groups=[], error='You are not a member of this group')
    
    # Get group details
    group = conn.execute(
        'SELECT sg.*, u.student_id as creator FROM study_groups sg JOIN users u ON sg.created_by = u.id WHERE sg.id = ?',
        (group_id,)
    ).fetchone()
    
    if not group:
        conn.close()
        if (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')) or \
           request.args.get('format') == 'json' or \
           (request.path.startswith('/group/') and request.is_json):
            return jsonify({'error': 'Group not found'}), 404
        return render_template('find-group.html', groups=[], error='Group not found')
    
    # Get group members
    members = conn.execute(
        'SELECT u.student_id, u.name FROM users u JOIN group_members gm ON u.id = gm.user_id WHERE gm.group_id = ? ORDER BY u.name',
        (group_id,)
    ).fetchall()
    
    conn.close()
    
    # Return JSON if requested by JavaScript
    if (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')) or \
       request.args.get('format') == 'json' or \
       (request.path.startswith('/group/') and request.is_json):
        return jsonify({
            'group': {
                'id': group['id'],
                'name': group['name'],
                'subject': group['subject'],
                'description': group['description'],
                'goal': group['goal'],
                'date': group['date'],
                'time': group['time'] if group['time'] else '',
                'location': group['location'] if group['location'] else '',
                'max_members': group['max_members'],
                'current_members': group['current_members'],
                'creator': group['creator']
            },
            'members': [{
                'student_id': member['student_id'],
                'name': member['name']
            } for member in members]
        })
    
    return render_template('view-group.html', group=group, members=members)


@app.route('/leave-group/<int:group_id>')
def leave_group(group_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Remove user from the group
    conn.execute(
        'DELETE FROM group_members WHERE user_id = ? AND group_id = ?',
        (session['user_id'], group_id)
    )
    # Update current members count
    conn.execute(
        'UPDATE study_groups SET current_members = current_members - 1 WHERE id = ?',
        (group_id,)
    )
    conn.commit()
    conn.close()
    
    return redirect(url_for('my_groups'))

@app.route('/user-delete-group/<int:group_id>', methods=['DELETE'])
def user_delete_group(group_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    conn = get_db_connection()
    
    try:
        # Check if the user is the creator of the group
        group = conn.execute(
            'SELECT created_by FROM study_groups WHERE id = ?', (group_id,)
        ).fetchone()
        
        if not group:
            conn.close()
            return jsonify({'success': False, 'message': 'Group not found'}), 404
        
        if group['created_by'] != session['user_id']:
            conn.close()
            return jsonify({'success': False, 'message': 'Not authorized to delete this group'}), 403
        
        # Begin transaction
        conn.execute('BEGIN IMMEDIATE')
        
        # Delete group members
        conn.execute('DELETE FROM group_members WHERE group_id = ?', (group_id,))
        
        # Delete the study group
        conn.execute('DELETE FROM study_groups WHERE id = ?', (group_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Group deleted successfully'})
    
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': 'Failed to delete group'}), 500

@app.route('/api/user')
def api_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT id, student_id, name, is_admin FROM users WHERE id = ?', (session['user_id'],)
    ).fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'id': user['id'],
            'name': user['name'],
            'is_admin': bool(user['is_admin'])
        })
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/api/subjects')
def api_subjects():
    conn = get_db_connection()
    subjects = conn.execute('''
        SELECT DISTINCT subject FROM study_groups WHERE subject IS NOT NULL AND subject != ''
    ''').fetchall()
    conn.close()
    
    return jsonify([{'subject': s['subject']} for s in subjects])

@app.route('/api/goals')
def api_goals():
    conn = get_db_connection()
    goals = conn.execute('''
        SELECT DISTINCT goal FROM study_groups WHERE goal IS NOT NULL AND goal != ''
    ''').fetchall()
    conn.close()
    
    return jsonify([{'goal': g['goal']} for g in goals])

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    # Check if request is JSON (from frontend JavaScript)
    if request.is_json or request.content_type == 'application/json':
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validate required fields
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and Password are required'}), 400
        
        # In a real app, you'd have proper admin authentication
        # For now, we'll use a simple check
        if username == 'admin' and password == 'admin123':  # Change this in production
            session['user_id'] = 0  # Admin ID
            session['role'] = 'admin'
            
            # Return success response for JSON request
            return jsonify({'success': True, 'message': 'Admin login successful', 'redirect_url': '/admin', 'is_admin': True})
        else:
            return jsonify({'success': False, 'message': 'Invalid admin credentials'}), 401
    else:
        # Handle traditional form submission
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            # In a real app, you'd have proper admin authentication
            # For now, we'll use a simple check
            if username == 'admin' and password == 'admin123':  # Change this in production
                session['user_id'] = 0  # Admin ID
                session['role'] = 'admin'
                return redirect(url_for('admin_dashboard'))
            else:
                return render_template('admin-login.html', error='Invalid admin credentials')
        
        return render_template('admin-login.html')

# Admin routes
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        if request.is_json or (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')):
            return jsonify({'error': 'Admin access required'}), 401
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    groups = conn.execute('SELECT * FROM study_groups ORDER BY created_at DESC').fetchall()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return render_template('admin-dashboard.html', groups=groups, users=users, view='dashboard')


@app.route('/admin/users')
def admin_users():
    if session.get('role') != 'admin':
        if request.is_json or (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')):
            return jsonify({'error': 'Admin access required'}), 401
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return render_template('admin-dashboard.html', users=users, view='users')


@app.route('/admin/groups')
def admin_groups():
    if session.get('role') != 'admin':
        if request.is_json or (request.headers.get('Content-Type') and 'application/json' in request.headers.get('Content-Type')):
            return jsonify({'error': 'Admin access required'}), 401
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    groups = conn.execute('SELECT * FROM study_groups ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return render_template('admin-dashboard.html', groups=groups, view='groups')


@app.route('/admin/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 401
    
    conn = get_db_connection()
    
    try:
        # Begin transaction
        conn.execute('BEGIN IMMEDIATE')
        
        # Delete user's group memberships
        conn.execute('DELETE FROM group_members WHERE user_id = ?', (user_id,))
        
        # Delete user's preferences
        conn.execute('DELETE FROM user_preferences WHERE user_id = ?', (user_id,))
        
        # Delete study groups created by this user
        conn.execute('DELETE FROM study_groups WHERE created_by = (SELECT student_id FROM users WHERE id = ?)', (user_id,))
        
        # Finally, delete the user
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': 'Failed to delete user'}), 500

@app.route('/admin/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 401
    
    conn = get_db_connection()
    
    try:
        # Begin transaction
        conn.execute('BEGIN IMMEDIATE')
        
        # Delete group members
        conn.execute('DELETE FROM group_members WHERE group_id = ?', (group_id,))
        
        # Delete the study group
        conn.execute('DELETE FROM study_groups WHERE id = ?', (group_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Group deleted successfully'})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': 'Failed to delete group'}), 500

@app.route('/auto-match', methods=['POST'])
def auto_match():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get user preferences
    conn = get_db_connection()
    user_prefs = conn.execute(
        'SELECT * FROM user_preferences WHERE user_id = ?',
        (session['user_id'],)
    ).fetchone()
    conn.close()
    
    if not user_prefs:
        return jsonify({'error': 'User preferences not set'})
    
    # Use the matching engine to find compatible groups
    engine = MatchingEngine()
    recommendations = engine.get_recommendations(user_id=session['user_id'])
    
    # Format the recommendations for the frontend
    formatted_recommendations = []
    for rec in recommendations:
        group = rec['group']
        formatted_recommendations.append({
            'id': group['id'],
            'name': group['name'],
            'subject': group['subject'],
            'description': group.get('description', ''),
            'goal': group.get('goal', ''),
            'date': group.get('date', ''),
            'time': group['time'] if group['time'] else '',
            'location': group['location'] if group['location'] else '',
            'current_members': group.get('current_members', 0),
            'max_members': group.get('max_members', 10),
            'creator': group.get('creator', ''),
            'final_score': rec['final_score'],
            'rules_score': rec['rules_score'],
            'cf_score': rec['cf_score']
        })
    
    return jsonify({'matched_groups': formatted_recommendations})

if __name__ == '__main__':
    ensure_db_exists()  # Ensure database and tables exist
    app.run(debug=True)
    