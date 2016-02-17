# all the import
import sqlite3
import httplib2
import xml.etree.ElementTree as ET
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from contextlib import closing
from functools import wraps
from oauth2client.client import OAuth2WebServerFlow

# configuration
DATABASE = '/tmp/wallit.db'
DEBUG = True
SECRET_KEY = 'development key'
OAUTH_CLIENT_ID = '197145980271-j21e4i5v6dt3mia217npvkik6t0irj05.apps.googleusercontent.com'
OAUTH_SECRET_KEY = 'U9T-UgjX2ngH6ipB9zh9MWHW'
OAUTH_REDIRECT = 'http://localhost:5000/oauth2callback'

# TODO: change this when we get Google's data
#USERS = {'thibaut': 'pass', 'toto':'toto'}

#application
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('WALLIT_SETTINGS', silent=True)

FLOW = OAuth2WebServerFlow(client_id=app.config['OAUTH_CLIENT_ID'],
                           client_secret=app.config['OAUTH_SECRET_KEY'],
                           scope='https://www.google.com/m8/feeds',
                           redirect_uri=app.config['OAUTH_REDIRECT'])

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

def auth(function):
    """Wrapper checking if the user is logged in."""
    @wraps(function)
    def wrapper(*args, **kwargs):
        if session.get('users'):
            return function(*args, **kwargs)
        else:
            authorize_url = FLOW.step1_get_authorize_url()
        return redirect(authorize_url)
    return wrapper

@app.route('/oauth2callback')
def oauth2callback():
    code = request.args.get('code')
    if code:
        credentials = FLOW.step2_exchange(code)
        http = credentials.authorize(httplib2.Http())
        _, content = http.request('https://www.google.com/m8/feeds/contacts/default/full?v=3.0')
        data = ET.fromstring(content)
        session['users'] = [title.text for title in data.findall('./feed/entry')]
        #régler le problème session['users']
        session['users'] = ['Guillaume Ayoub']
        print(session['users'], data, content)
        return redirect(url_for('display_wall'))
    else:
        return request.form.get('error')
"""
@app.route('/', methods=['GET', 'POST'])
def display_connection():
    'Allow the user to connect himself on the application'
    title = "Login"
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
    return render_template('login.html', error=error, title=title)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You were logged out')
    return redirect(url_for('display_connection'))"""

@app.route('/')
@auth
def display_wall():
    """Display all post-its on a wall"""
    print(session['users'])
    title = "Home"
    s = """ select post_id, p.owner, text, date, code_color, x, y
                from postit p, color c
                where p.owner = c.owner
                order by post_id desc """
    cur = g.db.execute(s)
    postits = []
    for row in cur.fetchall():
        postits.append({
            "post_id": row[0],
            "owner": row[1],
            "text": row[2],
            "date": row[3],
            "color": row[4],
            "x": row[5],
            "y": row[6]
        })
    for postit in postits:
        print("DISPLAY_WALL --> ID = ",postit['post_id']," X = ",postit['x'], " Y = ", postit['y'])
    return render_template('home.html', postits=postits, title=title)

@app.route('/save_position', methods=['POST'])
@auth
def save_position():
    """route that get the post request from the page / when we drop
    a post-it"""
    pos_x = request.form.get('x')
    pos_y = request.form.get('y')
    postit_id = request.form.get('post_id')
    #print("SAVE_POSITION --> ID = ",postit_id," X = ", pos_x, " Y = ", pos_y)
    s = """update postit
    set x="""+pos_x+""", y="""+pos_y+"""
    where post_id="""+postit_id
    g.db.execute(s)
    g.db.commit()
    return redirect(url_for('display_wall'))

@app.route('/profile', methods=['GET', 'POST'])
@auth
def display_config():
    """Allow the user to manage his profile"""
    pass

@app.route('/new', methods=['GET','POST'])
@auth
def add_post_it():
    """Allow the user to add a new post-it on the wall."""
    title = "Add post-it"
    error = None
    cur = g.db.execute('select owner from color')
    owners = ([row[0] for row in cur.fetchall()])
    form_error = {}
    default_values = {}
    if request.method == 'POST':
        valid_owner = True
        valid_text = True
        valid_date = True
        if request.form['owner'] in owners:
            valid_owner = True
        else:
            form_error['owner'] = 'This Bullshit must have been said by someone'
            default_values['text'] = request.form['text']
            valid_owner = False
        if not request.form['text']:
            valid_text = False
            form_error['text'] = 'There must be a bullshit message'
        else:
            valid_text = True
        if not request.form['date']:
            valid_date = False
            default_values['text'] = request.form['text']
            form_error['date'] = 'This stupid thing must have been said one day'
        else:
            valid_date = True
        if valid_owner and valid_text and valid_date:
            g.db.execute('insert into postit (owner, text, date) values (?, ?, ?)',
                [request.form['owner'], request.form['text'],
                request.form['date']])
            g.db.commit()
            flash('A new post-it was successefully added')
            return redirect(url_for('display_wall'))
            print('SUCCESS')
        else:
            error = ' invalid data'
    return render_template('new_post_it.html', owners=owners, error=error,
                form_error=form_error, title=title)

@app.route('/statistics')
@auth
def display_stats():
    """Display some statistics from the application"""
    title = "Statistics"
    cur_post_count = g.db.execute('select count(post_id) from postit')
    cur_post_owner = g.db.execute("""select owner, count(post_id)
    from postit group by owner""")
    stat_post_owner = []
    for row in cur_post_count.fetchall():
        stat_post_count = row[0]
    for row in cur_post_owner.fetchall():
        stupidity = ""
        if row[1] <= 3:
            stupidity += "That was a slip of the tongue"
        elif row[1] <= 5:
            stupidity += "This guy must have a problem!"
        elif row[1] <= 8:
            stupidity += "This guy is so stupid!"
        else:
            stupidity += "OMG! he said so much bullshit! I'm done!"
        stat_post_owner.append({
            'owner': row[0],
            'count': row[1],
            'stupidity': stupidity
        })
    return render_template('statistics.html', stat_post_it=stat_post_count,
                stat_post_owner=stat_post_owner, title=title)

if __name__ == '__main__':
    app.run()
