import functools
import os
#import utils
#from utils import get_spotify_client
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)
from werkzeug.security import check_password_hash, generate_password_hash
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from flaskr.db import get_db
from dotenv import load_dotenv, dotenv_values
import time

load_dotenv()

os.environ['SPOTIPY_CLIENT_ID']= os.environ.get("SPOTIPY_CLIENT_ID")
os.environ['SPOTIPY_CLIENT_SECRET']= os.environ.get("SPOTIPY_CLIENT_SECRET")
os.environ['SPOTIPY_REDIRECT_URI'] = os.environ.get("SPOTIPY_REDIRECT_URI")
os.environ['SPOTIPY_CACHE_PATH']= os.environ.get("SPOTIPY_CACHE_PATH")
os.environ['SPOTIPY_SCOPE']= os.environ.get("SPOTIPY_SCOPE")

bp = Blueprint('auth', __name__, url_prefix='/auth')


'''@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'

        if error is None:
            try:
                db.execute(
                    "INSERT INTO user (username, password) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')'''

@bp.route('/login/spotify')
def login_spotify():
    load_dotenv()
    print(os.getenv('SPOTIPY_REDIRECT_URI'))
    print("Spotify login initiated")
    sp_oauth =SpotifyOAuth(
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI'),
        cache_path=os.getenv('SPOTIPY_CACHE_PATH'),
        scope=os.getenv('SPOTIPY_SCOPE')
    )
    auth_url = sp_oauth.get_authorize_url()
    print(auth_url)
    return redirect(auth_url)
    

@bp.route('/callback/spotify')
def callback_spotify():
    print("Spotify callback reached")
    sp_oauth =SpotifyOAuth(
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI'),
        cache_path=os.getenv('SPOTIPY_CACHE_PATH'),
        scope=os.getenv('SPOTIPY_SCOPE')
    )
    session.clear()
    code = request.args.get('code')
    print(f"Authorization code: {code}")
    if code is None:
        return "Authorization code is missing", 400
    
    token_info = sp_oauth.get_access_token(code)
    print(f"Token info: {token_info}")
    session['token_info'] = token_info
    access_token = token_info['access_token']

    sp = Spotify(auth=access_token)
    user_info = sp.current_user()
    '''
    print(f"User info: {user_info}")
    print(f"User's most played artist: {sp.current_user_top_artists(limit=1)}")
    print(f"User's profile picture: {user_info['images'][0]['url']}")
    current_track = sp.current_user_playing_track()
    artists = current_track['item']['artists']
    artists_names = ', '.join([artist['name'] for artist in artists])
    if current_track is not None and current_track['is_playing']:
        print(f"Currently playing:", current_track['item']['name'], f"by", artists_names)'''
    spotify_id = user_info['id']
    profile_pic_url = user_info['images'][0]['url']
    #password = "randompass"

    db = get_db()
    user = db.execute(
        'SELECT * FROM user WHERE spotify_id = ?', (spotify_id,)
    ).fetchone()

    if user is None:
        db.execute(
            "INSERT INTO user (username, spotify_id, profile_pic_url) VALUES (?, ?, ?)",
            (user_info['display_name'], spotify_id, profile_pic_url),
        )
        db.commit()
        user = db.execute(
            'SELECT * FROM user WHERE spotify_id = ?', (spotify_id,)
        ).fetchone()

    session['user_id'] = user['id']
    return redirect(url_for('index', access_token=access_token))



@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    spotify_id = session.get('spotify_id')

    if user_id is None and spotify_id is None:
        g.user = None
    elif spotify_id is None:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE spotify_id = ?', (spotify_id,)
        ).fetchone()

def get_token():
    sp_oauth =SpotifyOAuth(
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI'),
        cache_path=os.getenv('SPOTIPY_CACHE_PATH'),
        scope=os.getenv('SPOTIPY_SCOPE')
    )
    token_info = session.get('token_info', None)
    if not token_info:
        return None
    now = int(time.time())
    is_expired = token_info['expires_at'] - now < 60
    if is_expired:
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    return token_info

@bp.route('/logout')
def logout():
    token_info = get_token()
    access_token=token_info['access_token']
    session.clear()
    return redirect(url_for('index',access_token=access_token))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login_spotify'))

        return view(**kwargs)

    return wrapped_view