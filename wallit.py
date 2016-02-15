# all the import
import sqlite3
import httplib2
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from contextlib import closing
from functools import wraps
from apiclient.discovery import build
from oauth2client.client import OAuth2WebServerFlow

# configuration
DATABASE = '/tmp/wallit.db'
DEBUG = True
SECRET_KEY = 'development key'
OAUTH_CLIENT_ID = '197145980271-j21e4i5v6dt3mia217npvkik6t0irj05.apps.googleusercontent.com'
OAUTH_SECRET_KEY = 'U9T-UgjX2ngH6ipB9zh9MWHW'
OAUTH_REDIRECT = 'http://wall-it.kozea.fr/oauth2callback'

# TODO: change this when we get Google's data
#USERS = {'thibaut': 'pass', 'toto':'toto'}

#application
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('WALLIT_SETTINGS', silent=True)

FLOW = OAuth2WebServerFlow(client_id=app.config['OAUTH_CLIENT_ID'],
                           client_secret=app.config['OAUTH_SECRET_KEY'],
                           scope='profile',
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
        if session.get('user'):
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
        service = build('admin', 'directory_v1', http=http)
        users = service.users().list(domain='kozea.fr').execute()
        for user in users:
            print(user)
    else:
        print(request.form.get('error'))
        #return redirect(url_for('display_connection'))

"""@app.route('/', methods=['GET', 'POST'])
@auth
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
    return render_template('login.html', error=error, title=title)"""

"""@app.route('/logout')
@auth
def logout():
    session.pop('user_id', None)
    flash('You were logged out')
    return redirect(url_for('display_connection'))"""

@app.route('/')
@auth
def display_wall():
    """Display all post-its on a wall"""
    title = "Home"
    s = """ select post_id, p.owner, text, date, code_color
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
            "color": row[3],
            "post_id": row[4]
        })
    return render_template('home.html', postits=postits, title=title)

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
    if request.method == 'POST':
        valid_owner = True
        valid_text = True
        valid_date = True
        if request.form['owner'] in owners:
            valid_owner = True
        else:
            form_error['owner'] = 'This Bullshit must have been said by someone'
            valid_owner = False
        if not request.form['text']:
            valid_text = False
            form_error['text'] = 'There must be a bullshit message'
        else:
            valid_text = True
        if not request.form['date']:
            valid_date = False
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
