from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, jsonify
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required, get_token
from flaskr.db import get_db
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

bp = Blueprint('blog', __name__)


@bp.route('/', methods=["GET", "POST"])
@login_required
def index(access_token):
    db = get_db()
    posts = db.execute(
        'SELECT p.id, title, body, created, author_id, username, likes'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    if request.method == "POST":
        track_title = request.form.get('song-name')
        print(track_title)
    return render_template('blog/index.html', posts=posts, access_token=access_token)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    token_info = get_token()
    access_token=token_info['access_token']
    sp = Spotify(auth=access_token)
    tracks = []
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        #track_title = request.form['song-name']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            cursor = db.execute(
                'INSERT INTO post (title, body, author_id)'
                ' VALUES (?, ?, ?)',
                (title, body, g.user['id'])
            )
            db.commit()
            post_id = cursor.lastrowid
    
            return render_template('blog/create.html', post_id=post_id)

    return render_template('blog/create.html', post_id=None)

@bp.route('/search-songs')
@login_required
def search_songs():
    query = request.args.get('query', '')

    if not query:
        return jsonify({'songs': []})
    token_info = get_token()
    access_token=token_info['access_token']
    sp = Spotify(auth=access_token)
    tracks = []
    track_info = sp.search(query, limit=10)
    for track in track_info['tracks']['items']:
        track_name = track['name']
        track_artist = ', '.join([artist['name'] for artist in track['artists']])
        link = track['external_urls']['spotify']
        uri = track['uri']
        image_url = (', '.join([image['url'] for image in track['album']['images']])).split()[0]
        image_url = image_url.replace(",","")
        if (track_name not in tracks and track_artist not in tracks):
            tracks.append({
                'track_name':track_name,
                'track_artist': track_artist,
                'link':link,
                'uri':uri,
                'image_url':image_url
            })
    for track in tracks:
        print(track)
    #print(tracks)
    return jsonify({'tracks': tracks})

    


def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username, likes'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post


@bp.route('/save-track-info', methods=('GET', 'POST'))
def save_track_info():
    print("Got here")
    data = request.get_json()
    print(f"DATA:", data)
    post_id = data.get('post_id')
    uri = data.get('song_uri')
    track_name = data.get('track_name')
    track_artist = data.get('track_artist')
    link = data.get('link')
    image_url = data.get('image_url')
    if not uri or not post_id:
        return jsonify({'error': 'Missing data'}), 400

    print(f"Song uri:", uri)
    db = get_db()
    db.execute('UPDATE post SET song_uri = ?, track_name = ?, track_artist = ?, link = ?, image_url = ?'
                ' WHERE id = ?',
                (uri, track_name, track_artist, link, image_url, post_id))
    db.commit()
    return jsonify({'message': 'Track Info saved successfully!'}), 200



@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)
    token_info = get_token()
    access_token=token_info['access_token']

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('blog.index', access_token=access_token))

    return render_template('blog/update.html', post=post)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    token_info = get_token()
    access_token=token_info['access_token']
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index',access_token=access_token))

@bp.route('/like/<int:id>', methods=['POST'])
@login_required
def like_post(id):
    token_info = get_token()
    access_token=token_info['access_token']
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE post SET likes = likes + 1 WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for('blog.index', access_token=access_token))

@bp.route('/<int:id>', methods=('GET', 'POST'))
def show_post(id):
    post = get_post(id, check_author=False)
    db = get_db()
    comments = db.execute(
        'SELECT c.id, c.body, c.created, c.author_id, u.username, c.likes, c.parent_id, c.post_id'
        ' FROM comment c JOIN user u ON c.author_id = u.id'
        ' WHERE c.post_id = ?'
        ' ORDER BY c.created ASC',
        (id,)
    ).fetchall()
    return render_template('blog/post.html', post=post, comments=comments)

@bp.route('/<int:id>/comment', methods=('POST',))
@login_required
def add_comment(id):
    post = get_post(id, check_author=False)
    body = request.form['body']
    parent_id = request.form.get('parent_id')
    error = None

    if not body:
        error = 'Comment body is required.'

    if error is not None:
        flash(error)
    else:
        db = get_db()
        db.execute(
            'INSERT INTO comment (post_id, author_id, body, parent_id)'
            ' VALUES (?, ?, ?, ?)',
            (id, g.user['id'], body, parent_id)
        )
        db.commit()
        return redirect(url_for('blog.show_post', id=id))

    comments = db.execute(
        'SELECT c.id, c.body, c.created, c.author_id, u.username, c.likes, c.parent_id, c.post_id'
        ' FROM comment c JOIN user u ON c.author_id = u.id'
        ' WHERE c.post_id = ?'
        ' ORDER BY c.created ASC',
        (id,)
    ).fetchall()
    return render_template('blog/post.html', post=post, comments=comments)

@bp.route('/like_comment/<int:comment_id>', methods=['POST'])
@login_required
def like_comment(comment_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE comment SET likes = likes + 1 WHERE id = ?", (comment_id,))
    db.commit()
    post_id = db.execute('SELECT post_id FROM comment WHERE id = ?', (comment_id,)).fetchone()['post_id']
    return redirect(url_for('blog.show_post', id=post_id))

