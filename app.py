from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Helper functions ---
def init_db():
    with sqlite3.connect('users.db') as conn:
        # conn.execute('''CREATE TABLE IF NOT EXISTS users (
        #                 id INTEGER PRIMARY KEY AUTOINCREMENT,
        #                 username TEXT UNIQUE NOT NULL,
        #                 password TEXT NOT NULL)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE NOT NULL,
                            password TEXT NOT NULL)''')
        try:
            conn.execute("ALTER TABLE uploads ADD COLUMN title TEXT")
        except sqlite3.OperationalError:
            pass # Column already exists
        try:
            conn.execute("ALTER TABLE uploads ADD COLUMN description TEXT")
        except sqlite3.OperationalError:
            pass # Column already exists
        # end new code
        conn.execute('''CREATE TABLE IF NOT EXISTS uploads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        filename TEXT,
                        title TEXT,
                        description TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(id))''')

def get_user(username):
    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        return cur.fetchone()

# --- Routes ---
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('upload'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        with sqlite3.connect('users.db') as conn:
            try:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                flash("Registered successfully. Please log in.")
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash("Username already taken.")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_input = request.form['password']
        user = get_user(username)

        if user and check_password_hash(user[2], password_input):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('upload'))
        else:
            flash("Invalid credentials.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files['image']
        title = request.form['title']
        desc = request.form['description']
        
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            with sqlite3.connect('users.db') as conn:
                conn.execute("INSERT INTO uploads (user_id, filename, title, description) VALUES (?, ?, ?, ?)",
                       (session['user_id'], filename, title, desc))
            flash("Image uploaded successfully.")
            return redirect(url_for('gallery'))

    return render_template('upload.html')

@app.route('/gallery')
def gallery():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT filename, title, description, id FROM uploads WHERE user_id = ?", (session['user_id'],))
        images = cur.fetchall()

    return render_template('gallery.html', images=images)


@app.route('/delete/<int:image_id>', methods=['POST'])
def delete(image_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT filename FROM uploads WHERE id = ? AND user_id = ?", (image_id, session['user_id']))
        result = cur.fetchone()
        if result:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], result[0]))
            cur.execute("DELETE FROM uploads WHERE id = ?", (image_id,))
            conn.commit()
    return redirect(url_for('gallery'))



if __name__ == '__main__':
    init_db()
    app.run(debug=True)
