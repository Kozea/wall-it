import sqlite3
import httplib2
import json
import pygal
from pygal.style import CleanStyle
from flask import (
    abort, Flask, request, session, g, redirect, url_for, render_template, flash)
from contextlib import closing
from functools import wraps
from oauth2client.client import OAuth2WebServerFlow


app = Flask(__name__)
app.config.from_envvar('WALLIT_SETTINGS')


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
            if session.get('person') in session.get('users'):
                return function(*args, **kwargs)
            else:
                return redirect(FLOW.step1_get_authorize_url())
        abort(403)
    return wrapper


@app.route('/oauth2callback')
def oauth2callback():
    code = request.args.get('code')
    credentials = FLOW.step2_exchange(code)
    http = credentials.authorize(httplib2.Http())
    _, content = http.request(
        "https://people.googleapis.com/v1/people/me")
    data = json.loads(content.decode('utf-8'))
    if 'names' in data:
        session['person'] = data['names'][0]['displayName']
    _, users_content = http.request(
        "https://people.googleapis.com/v1/people/me/connections"
        "?requestMask.includeField=person.names%2Cperson.emailAddresses"
        "&pageSize=500")
    users_data = json.loads(users_content.decode('utf-8'))
    session['users'] = []
    for connection in users_data['connections']:
        if 'names' in connection and 'emailAddresses' in connection:
            for address in connection['emailAddresses']:
                if address['value'].endswith('@kozea.fr'):
                    session['users'].append('%s %s' % (
                        connection['names'][0].get('givenName', ''),
                        connection['names'][0].get('familyName', '')))
                    break
    return redirect(url_for('display_wall'))


@app.route('/')
@app.route('/home')
@auth
def display_wall():
    """Display all post-its on a wall."""
    s = """ select post_id, p.owner, text, code_color, x, y
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
            "color": row[3],
            "x": row[4],
            "y": row[5]
        })
    return render_template('home.html', postits=postits)


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
    cur_owners_with_color = g.db.execute("select owner from color")
    owners_with_color = []
    for owner in cur_owners_with_color.fetchall():
        owners_with_color.append(owner[0])
    if request.method == 'POST':
        if session['person'] in owners_with_color:
            g.db.execute(
                "update color set code_color=? where owner=?",
                [request.form['color'], session['person']])
            g.db.commit()
        else:
            g.db.execute(
                "insert into color (code_color, owner) values (?, ?)",
                [request.form['color'], session['person']])
            g.db.commit()
    cur_color = g.db.execute(
        "select code_color from color where owner=?",
        [session['person']])
    for row in cur_color.fetchall():
        color += row[0]
    cur_post = g.db.execute(
        "select post_id, text from postit where owner=? order by post_id desc",
        [session['person']])
    for row in cur_post.fetchall():
        my_postits.append({
            'id':row[0],
            'text':row[1]
        })
    g.db.commit()
    return render_template('profile.html', color=color,
        postits=my_postits)


@app.route('/new', methods=['GET', 'POST'])
@auth
def add_post_it():
    """Allow the user to add a new post-it on the wall."""
    if request.method == 'POST':
        cur_owners_with_color = g.db.execute("select owner from color")
        owners_with_color = []
        for owner in cur_owners_with_color.fetchall():
            owners_with_color.append(owner[0])
        if request.form['owner'] in session['users']:
            g.db.execute(
                'insert into postit (owner, text) values (?, ?)',
                [request.form['owner'], request.form['text']])
            g.db.commit()
            if request.form['owner'] not in owners_with_color:
                g.db.execute(
                    'insert into color (code_color, owner) values (?, ?)',
                    ['#FFFFFF', request.form['owner']])
                g.db.commit()
            flash('A new post-it was successefully added')
        return redirect(url_for('display_wall'))
    return render_template('new_post_it.html')


@app.route('/statistics')
@auth
def display_stats():
    """Display some statistics from the application"""
    cur_post_count = g.db.execute('select count(post_id) from postit')
    for row in cur_post_count.fetchall():
        stat_post_count = row[0]
    return render_template('statistics.html', stat_post_it=stat_post_count)


@app.route('/charts/post_it_by_user_pie.svg')
@auth
def post_it_by_user_pie():
    """Display a graph for the statistics page."""
    post_it_by_user_pie = pygal.Pie(style=CleanStyle)
    post_it_by_user_pie.title = 'Nombre de post-it par personne'
    cur_post_owner = g.db.execute(
        "select owner, count(post_id) from postit group by owner")
    for row in cur_post_owner.fetchall():
        post_it_by_user_pie.add(row[0], row[1])
    return post_it_by_user_pie.render_response()


@app.route('/modify_post_it/<int:post_id>', methods=['GET', 'POST'])
@auth
def modify(post_id):
    cur_postit = g.db.execute(
        "select text, owner from postit where post_id=?", [post_id])
    for row in cur_postit.fetchall():
        text = row[0]
        owner = row[1]
    if request.method == 'POST':
        cur_owners_with_color = g.db.execute("select owner from color")
        owners_with_color = []
        for owner in cur_owners_with_color.fetchall():
            owners_with_color.append(owner[0])
        g.db.execute(
        "update postit set text=?, owner=? where post_id=?",
            [request.form.get('text'), request.form.get('owner'), post_id])
        g.db.commit()
        if request.form.get('owner') not in owners_with_color:
            g.db.execute(
                'insert into color (code_color, owner) values (?, ?)',
                ['#FFFFFF', request.form['owner']])
            g.db.commit()
        return redirect(url_for('display_wall'))
    return render_template('modify_post_it.html', post_id=post_id, owner=owner,
        text=text)


@app.route('/delete/<int:post_id>', methods=['GET', 'POST'])
@auth
def delete(post_id):
    cur_postit = g.db.execute(
        "select owner from postit where post_id=?", [post_id])
    for row in cur_postit.fetchall():
        owner = row[0]
    vowels = 'aeiouïüéè'
    if owner[0] in vowels or owner[0] in vowels.upper():
        prefix = "d'"
    else:
        prefix = "de "
    if request.method == 'POST':
        g.db.execute('delete from postit where post_id=?', [post_id])
        g.db.commit()
        return redirect(url_for('display_wall'))
    return render_template('delete.html', post_id=post_id, owner=owner,
        prefix=prefix)

if __name__ == '__main__':
    app.run()
