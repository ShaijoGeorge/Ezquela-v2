from flask import *
import pymysql
from flask_wtf import CSRFProtect
import secrets
import functools
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dbutils.pooled_db import PooledDB

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
csrf = CSRFProtect(app)

# Database connection pool configuration
pool = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=2,
    maxcached=5,
    maxshared=3,
    blocking=True,
    maxusage=None,
    setsession=[],
    ping=1,
    host='localhost',
    port=3306,
    user='root',
    password='',
    database='school',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=False
)

def get_db():
    if 'db' not in g:
        g.db = pool.connection()
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def login_required(func):
    @functools.wraps(func)
    def secure_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for('user'))
        return func(*args, **kwargs)
    return secure_function

def get_user_role(user_id: int):
    """Return role from users table: admin/teacher/student"""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT role FROM users WHERE id = %s AND is_active = 1", (user_id,))
        row = cursor.fetchone()
    return row['role'] if row else None

def get_current_user():
    """Optional helper if you want user details in many views"""
    uid = session.get('user_id')
    if not uid:
        return None
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT id, username, email, role, is_active FROM users WHERE id = %s", (uid,))
        return cursor.fetchone()
    
@app.route('/')
def index():
    if 'user_id' in session:
        role = get_user_role(session['user_id'])
        if role == "admin":
            return redirect(url_for('admin_home'))
        elif role == "teacher":
            return redirect(url_for('teacher_home'))
        elif role == "student":
            return redirect(url_for('student_home'))
    return redirect(url_for('user'))


@app.route('/login', methods=["GET", "POST"])
def user():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == "POST":
        username = request.form.get('textfield', '').strip()
        password = request.form.get('textfield2', '')

        if not username or not password:
            flash("Username and password required", "danger")
            return redirect(url_for('user'))

        db = get_db()
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, password_hash, role, is_active "
                "FROM users WHERE username = %s",
                (username,)
            )
            user_row = cursor.fetchone()

        if not user_row:
            flash("Invalid username or password", "danger")
            return redirect(url_for('user'))

        if not user_row['is_active']:
            flash("Account is disabled. Contact administrator.", "warning")
            return redirect(url_for('user'))

        if not check_password_hash(user_row['password_hash'], password):
            flash("Invalid username or password", "danger")
            return redirect(url_for('user'))

        # Login OK
        session['user_id'] = user_row['id']
        session['role'] = user_row['role']

        if user_row['role'] == "admin":
            return redirect(url_for('admin_home'))
        elif user_row['role'] == "teacher":
            return redirect(url_for('teacher_home'))
        elif user_row['role'] == "student":
            return redirect(url_for('student_home'))

        return redirect(url_for('index'))

    response = make_response(render_template('login.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Expires'] = 0
    response.headers['Pragma'] = 'no-cache'
    return response


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    return redirect(url_for('user'))

@app.route('/admin_home')
@login_required
def admin_home():
    if session.get('role') != "admin":
        return redirect(url_for('index'))
    return render_template('admin/base.html')

@app.route('/teacher_home')
@login_required
def teacher_home():
    if session.get('role') != "teacher":
        return redirect(url_for('index'))
    return render_template('teacher/base.html')

@app.route('/student_home')
@login_required
def student_home():
    if session.get('role') != "student":
        return redirect(url_for('index'))
    return render_template('student/base.html')

if __name__ == '__main__':
    print("🚀 Starting Flask server...")
    app.run(debug=True, host='127.0.0.1', port=5000)