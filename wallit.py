# all the import
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from contextlib import closing

# configuration
DATABASE = '/tmp/wallit.db'
DEBUG = True
SECRET_KEY = 'development key'

# TODO: change this when we get Google's data
USERS = {'thibaut': 'pass', 'toto':'toto'}

#application
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('WALLIT_SETTINGS', silent=True)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        with app.open_resource('content.sql', mode='r') as e:
            db.cursor().executescript(e.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.route('/', methods=['GET', 'POST'])
def display_connection():
    """Allow the user to connect himself on the application"""
    error = None
    is_logged = False
    if request.method == 'POST':
        the_user_name = request.form['username']
        the_user_pass = request.form['password']
        is_logged = (the_user_name, the_user_pass) in app.config['USERS'].items()
        if is_logged:
            session['user_id'] = the_user_name
            flash('You were logged in')
            return redirect(url_for('display_wall'))
        else:
            error = 'Invalid password or login'
    return render_template('login.html', error=error)

@app.route('/home')
def display_wall():
    """Display all post-its on a wall"""
    s = """ select p.owner, text, date, code_color
                from postit p, color c
                where p.owner = c.owner
                order by post_id desc """
    cur = g.db.execute(s)
    postits = []
    for row in cur.fetchall():
        postits.append({
            "owner": row[0],
            "text": row[1],
            "date": row[2],
            "color": row[3]
        })
    return render_template('home.html', postits=postits)

@app.route('/profile')
def display_config():
    """Allow the user to manage his profile"""
    return redirect(url_for('display_wall'))

@app.route('/new', methods=['POST'])
def add_post_it():
    """Allow the user to add a new post-it on the wall."""
    return redirect(url_for('display_wall'))

@app.route('/statistics')
def display_stats():
    """Display some statistics from the application"""
    return redirect(url_for('display_wall'))

if __name__ == '__main__':
    app.run()
