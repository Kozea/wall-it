import sqlite3
import httplib2
import json
import pygal
import random as rand

from datetime import datetime
from flask import (
    flash, Flask, g, redirect, render_template, request, send_file,
    session, url_for)
from functools import wraps
from oauth2client.client import OAuth2WebServerFlow
from os import listdir, remove
from pygal.style import CleanStyle
from weasyprint import HTML, CSS


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
    with connect_db() as db:
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


@app.route('/not_allowed')
def not_allowed():
    return render_template('403.html')


def auth(function):
    """Wrapper checking if the user is logged in."""
    @wraps(function)
    def wrapper(*args, **kwargs):
        testing = app.config['TESTING']
        if session.get('users') and session.get('person') or testing:
            return function(*args, **kwargs)
        return redirect(FLOW.step1_get_authorize_url())
    return wrapper


@app.route('/oauth2callback')
def oauth2callback():
    code = request.args.get('code')
    credentials = FLOW.step2_exchange(code)
    http = credentials.authorize(httplib2.Http())
    _, content = http.request(
        "https://people.googleapis.com/v1/people/me")
    data = json.loads(content.decode('utf-8'))
    if data.get('emailAddresses')[0].get('value').endswith('@kozea.fr'):
        if 'names' in data:
            session['person'] = data['names'][0]['displayName']
        _, users_content = http.request(
            "https://people.googleapis.com/v1/people/me/connections"
            "?requestMask.includeField=person.names%2Cperson.emailAddresses"
            "&pageSize=500")
        users_data = json.loads(users_content.decode('utf-8'))
        session['users'] = []
        for connection in users_data.get('connections', []):
            if 'names' in connection and 'emailAddresses' in connection:
                for address in connection['emailAddresses']:
                    if address['value'].endswith('@kozea.fr'):
                        session['users'].append('%s %s' % (
                            connection['names'][0].get('givenName', ''),
                            connection['names'][0].get('familyName', '')))
                        break
    else:
        return redirect(url_for('not_allowed'))
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
    if request.form.get('post_id'):
        g.db.execute(
            "update postit set x=?, y=? where post_id=?",
            [request.form.get(key) for key in ('x', 'y', 'post_id')])
        g.db.commit()
        return redirect(url_for('display_wall'))
    else:
        x = request.form.get('x')
        y = request.form.get('y')
        label_id = request.form.get('label_id')
        for panel in session.get('job_panel'):
            for k, v in panel.items():
                if label_id == k:
                    v['x'] = x
                    v['y'] = y
                    break
        return redirect(url_for('job_panel'))


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
            'id': row[0],
            'text': row[1]
        })
    g.db.commit()
    return render_template('profile.html', color=color, postits=my_postits)


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


@app.route('/statistics', methods=['GET', 'POST'])
@auth
def display_stats():
    """Display some statistics from the application"""
    cur_all_post_it = g.db.execute(
        "select post_id, p.owner, text , code_color "
        "from postit p, color c "
        "where p.owner=c.owner "
        "order by post_id desc")
    all_post_its = [{
        'id': row[0],
        'owner': row[1],
        'text': row[2],
        'color': row[3]} for row in cur_all_post_it.fetchall()]
    cur_post_count = g.db.execute('select count(post_id) from postit')
    for row in cur_post_count.fetchall():
        stat_post_count = row[0]
    if request.method == 'POST':
        all_new_post_its = []
        owner = request.form.get('owner', None)
        text = request.form.get('text', None)
        if text and owner:
            for postit in all_post_its:
                if postit not in all_new_post_its:
                    if (owner.lower() in postit['owner'].lower() and
                       text.lower() in postit['text'].lower()):
                        all_new_post_its.append(postit)
        else:
            if owner:
                for postit in all_post_its:
                    if (owner.lower() in postit['owner'].lower() and
                       postit not in all_new_post_its):
                        all_new_post_its.append(postit)
            if text:
                for postit in all_post_its:
                    if (text.lower() in postit['text'].lower() and
                       postit not in all_new_post_its):
                        all_new_post_its.append(postit)
        return render_template('statistics.html',
                               all_post_its=all_new_post_its,
                               stat_post_count=stat_post_count)
    return render_template(
        'statistics.html', stat_post_count=stat_post_count,
        all_post_its=all_post_its)


@app.route('/charts/post_it_by_user.svg')
@auth
def post_it_by_user():
    """Display a graph for the statistics page."""
    post_it_by_user = pygal.HorizontalBar(style=CleanStyle, show_legend=False)
    post_it_by_user.title = 'Nombre de post-it par personne'
    cur_post_owner = g.db.execute(
        "select p.owner, code_color, count(post_id) "
        "from postit p, color c "
        "where p.owner=c.owner "
        "group by p.owner, code_color")
    for row in cur_post_owner.fetchall():
        post_it_by_user.add(
            row[0], [{'value': row[2], 'style': 'fill: {}'.format(row[1])}])
    return post_it_by_user.render_response()


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
    return render_template(
        'delete_post_it.html', post_id=post_id, owner=owner, prefix=prefix)


@app.route('/job_panel')
@auth
def job_panel():
    if not session.get('job_panel'):
        session['job_panel'] = []
    return render_template('meeting/job_panel.html')


@app.route('/new_label', methods=['GET', 'POST'])
@auth
def new_label():
    if request.method == 'POST':
        already_used_rand = []
        random_id = rand.randint(0, 10000)
        while random_id in already_used_rand:
            random_id = rand.randint(0, 10000)
        text = request.form.get('text')
        color = request.form.get('color')
        session['job_panel'].append({str(random_id): {
            'text': text, 'color': color, 'x': 0, 'y': 0}})
        return redirect(url_for('job_panel'))
    return render_template('meeting/new_label.html')


@app.route('/modify_label/<int:label_id>', methods=['GET', 'POST'])
@auth
def modify_label(label_id):
    for label in session.get('job_panel'):
        color = None
        text = ''
        if label.get(str(label_id)):
            color = label.get(str(label_id)).get('color', None)
            text = label.get(str(label_id)).get('text', None)
            break
    if request.method == 'POST':
        color = request.form.get('color')
        text = request.form.get('text')
        for label in session.get('job_panel'):
            if label.get(str(label_id)):
                label[str(label_id)]['text'] = text
                label[str(label_id)]['color'] = color
                break
        return redirect(url_for('job_panel'))
    return render_template(
        'meeting/modify_label.html', label_id=label_id, color=color, text=text)


@app.route('/delete_label/<int:label_id>', methods=['GET', 'POST'])
@auth
def delete_label(label_id):
    if request.method == 'POST':
        for i in range(len(session.get('job_panel'))):
            if session['job_panel'][i].get(str(label_id)):
                session['job_panel'].pop(i)
                break
        return redirect(url_for('job_panel'))
    return render_template('meeting/delete_label.html', label_id=label_id)


@app.route('/print_panel', methods=['GET', 'POST'])
@auth
def print_panel():
    if request.method == 'POST':
        if request.form.get('title'):
            today = datetime.today().strftime('%d-%m-%Y_%H:%M:%S')
            content_string = request.form.get('html_to_print')
            file_ = "uploads/{}_{}.pdf".format(
                request.form.get('title'), today)
            data_style = ""
            my_style = open('static/style.css', 'r')
            lines = my_style.readlines()
            for line in lines:
                data_style += line.strip()
            my_style.close()
            data_style += """
                @page {
                    margin: 0;
                    width: 1900px;
                    height: 1000px;
                    size: A3 landscape;
                }"""
            HTML(string=content_string).write_pdf(
                target=file_, stylesheets=[CSS(string=data_style)])
            del(session['job_panel'])
            tmp_file = send_file(file_, as_attachment=True)
            filelist = [f for f in listdir("uploads/") if f.endswith('.pdf')]
            for f in filelist:
                remove('uploads/{}'.format(f))
            return tmp_file
    return render_template('meeting/print.html')


if __name__ == '__main__':
    app.run()
