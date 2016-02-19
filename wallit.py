import sqlite3
import httplib2
import datetime
import json
import pygal
from pygal.style import CleanStyle
import xml.etree.ElementTree as ET
from flask import (
    Flask, request, session, g, redirect, url_for, render_template, flash)
from contextlib import closing
from functools import wraps
from oauth2client.client import OAuth2WebServerFlow


DATABASE = '/tmp/wallit.db'
DEBUG = True
SECRET_KEY = 'development key'
OAUTH_CLIENT_ID = '197145980271-j21e4i5v6dt3mia217npvkik6t0irj05.apps.googleusercontent.com'
OAUTH_SECRET_KEY = 'U9T-UgjX2ngH6ipB9zh9MWHW'
OAUTH_REDIRECT = 'http://localhost:5000/oauth2callback'
OAUTH_SCOPE = 'https://www.googleapis.com/auth/contacts.readonly'


app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('WALLIT_SETTINGS', silent=True)


FLOW = OAuth2WebServerFlow(
    client_id=app.config['OAUTH_CLIENT_ID'],
    client_secret=app.config['OAUTH_SECRET_KEY'],
    redirect_uri=app.config['OAUTH_REDIRECT'],
    scope=app.config['OAUTH_SCOPE'],
    user_agent='wallit/1.0')


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
        if session.get('person'):
            print('OUI SESSION[PERSON]')
            print('ME --> ', session['person'])
            return function(*args, **kwargs)
        else:
            print("SESSION[PERSON] IL N'Y A PAS")
            authorize_url = FLOW.step1_get_authorize_url()
        return redirect(authorize_url)
    return wrapper


@app.route('/oauth2callback')
def oauth2callback():
    code = request.args.get('code')
    if code:
        # credentials = FLOW.step2_exchange(code)
        # http = credentials.authorize(httplib2.Http())
        # _, content = http.request(
        #     "https://www.googleapis.com/plus/v1/people/me")
        # data = json.loads(content.decode('utf-8'))
        # print('MY DATA --> ', data)
        # if 'name' in data:
        #     print('NAME IN DATA OK')
        #     session['person'] = '%s %s' % (
        #         data['name']['givenName'], data['name']['familyName'])
        session['person'] = ['Thibaut Moiroud']
        session['users'] = ['Thibaut Moiroud', 'Clément Plasse', 'Guillaume Ayoub']
        return redirect(url_for('display_wall'))
    else:
        print('ERREUR --> ', request.form.get('error'))
        return redirect(url_for('index'))

@app.route('/', methods=('GET', 'POST'))
def index():
    return redirect(url_for('display_wall'))


@app.route('/home')
@auth
def display_wall():
    """Display all post-its on a wall."""
    s = """ select post_id, p.owner, text, date, code_color, x, y
                from postit p, color c
                where p.owner = c.owner
                order by post_id desc """
    cur = g.db.execute(s)
    postits = []
    for row in cur.fetchall():
        date = datetime.datetime.strptime(row[3], '%Y-%m-%d').strftime('%d/%m/%Y')
        postits.append({
            "post_id": row[0],
            "owner": row[1],
            "text": row[2],
            "date": date,
            "color": row[4],
            "x": row[5],
            "y": row[6]
        })
    return render_template('home.html', postits=postits, title='Accueil')


@app.route('/save_position', methods=['POST'])
@auth
def save_position():
    """Get the post request from the page / when we drop a post-it."""
    g.db.execute(
        "update postit set x=?, y=? where post_id=?",
        [request.form.get(key) for key in ('x', 'y', 'post_id')])
    g.db.commit()
    return redirect(url_for('display_wall'))


@app.route('/profile', methods=['GET', 'POST'])
@auth
def display_config():
    """Allow the user to manage his profile."""
    color = ""
    my_postits = []
    if request.method == 'POST':
        g.db.execute(
            "update color set code_color=? where owner=?",
            [request.form['color'], session['person'][0]])
    cur_color = g.db.execute(
        "select code_color from color where owner=?",
        [session['person'][0]])
    for row in cur_color.fetchall():
        color += row[0]
    cur_post = g.db.execute(
        "select post_id, date, text from postit where owner=? order by date asc",
        [session['person'][0]])
    for row in cur_post.fetchall():
        my_postits.append({
            'id':row[0],
            'date':row[1],
            'text':row[2]
        })
    g.db.commit()
    return render_template('profile.html', title="Profile", color=color,
        postits=my_postits)


@app.route('/new', methods=['GET', 'POST'])
@auth
def add_post_it():
    """Allow the user to add a new post-it on the wall."""
    if request.method == 'POST':
        g.db.execute('insert into postit (owner, text, date) values (?, ?, ?)',
            [request.form['owner'], request.form['text'],
            request.form['date']])
        g.db.commit()
        flash('A new post-it was successefully added')
        return redirect(url_for('display_wall'))
    return render_template('new_post_it.html', title="Ajout de post-it")


@app.route('/statistics')
@auth
def display_stats():
    """Display some statistics from the application"""
    cur_post_count = g.db.execute('select count(post_id) from postit')
    for row in cur_post_count.fetchall():
        stat_post_count = row[0]
    return render_template('statistics.html', stat_post_it=stat_post_count
                ,title="Statistiques")


@app.route('/charts/post_it_by_user_pie.svg')
@auth
def post_it_by_user_pie():
    """Display a graph for the statistics page."""
    post_it_by_user_pie = pygal.Pie(style=CleanStyle)
    post_it_by_user_pie.title = 'Nombre de post-it par personne'
    cur_post_owner = g.db.execute("""select owner, count(post_id)
    from postit group by owner""")
    for row in cur_post_owner.fetchall():
        post_it_by_user_pie.add(row[0], row[1])
    return post_it_by_user_pie.render_response()

@app.route('/modify_post_it', methods=['GET', 'POST'])
@auth
def modify():
    cur = g.db.execute(
        'select post_id, text, date from postit order by post_id desc')
    postits = []
    for row in cur.fetchall():
        postits.append({
            'post_id': row[0],
            'text': row[1],
            'date': row[2]
        })
    if request.method == 'POST':
        g.db.execute(
            "update postit set date=?, text=?, owner=? where post_id=?",
            [request.form.get(key) for key in ('date', 'text', 'owner',
            'post_id')])
        g.db.commit()
        return redirect(url_for('display_wall'))
    return render_template('modify_post_it.html', title="Modifier un post-it",
        postits=postits)


if __name__ == '__main__':
    app.run()
