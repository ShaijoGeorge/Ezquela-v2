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