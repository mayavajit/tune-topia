from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, session, jsonify
)
from werkzeug.exceptions import abort
from flaskr.auth import login_required, get_token
from flaskr.db import get_db
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from flaskr.db import get_db
from dotenv import load_dotenv, dotenv_values
import matplotlib.pyplot as plt
import numpy as np

bp = Blueprint('spotifyplayer', __name__, url_prefix='/spotifyplayer')

@bp.route('/')
def player():
    print("Got here")
    token_info = get_token()
    print(token_info)
    access_token = token_info['access_token']
    
    return render_template('player.html', access_token=access_token)
