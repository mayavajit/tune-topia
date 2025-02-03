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

bp = Blueprint('profile', __name__, url_prefix='/profile')


@bp.route('/<int:id>')
def profile_base(id):
    if id is None:
        id = request.args.get('id')
    print(id)
    db = get_db()
    
    #follower count
    followers = []
    cursor = db.execute('SELECT COUNT(*) as follower_count FROM follows WHERE following_id = ?', (id,))
    follower_count = cursor.fetchone()['follower_count']
    cursor = db.execute('SELECT u.username, u.profile_pic_url FROM user u JOIN follows f ON u.id = f.follower_id WHERE f.following_id = ?', (id,))
    print(f"Follower Count:",follower_count)
    followers_list = cursor.fetchall()
    for follower in followers_list:
        follower_username = follower['username']
        follower_profile_pic = follower['profile_pic_url']
        followers.append({
            'follower_username': follower_username,
            'follower_profile_pic': follower_profile_pic
        })
    print(followers)
    
    #following count
    following = []
    cursor = db.execute('SELECT COUNT(*) as following_count FROM follows WHERE follower_id = ?', (id,))
    following_count = cursor.fetchone()['following_count']
    cursor = db.execute('SELECT u.username, u.profile_pic_url FROM user u JOIN follows f ON u.id = f.following_id WHERE f.follower_id = ?', (id,))
    following_list = cursor.fetchall()
    for follow in following_list:
        following_username = follow['username']
        following_profile_pic = follow['profile_pic_url']
        following.append({
            'following_username': following_username,
            'following_profile_pic': following_profile_pic
        })
    print(following)

    #current track
    token_info = get_token()
    sp = Spotify(auth=token_info['access_token'])
    current_track_info = sp.current_user_playing_track()
    if current_track_info is not None and current_track_info['is_playing']:
        track_name = current_track_info['item']['name']
        artists = current_track_info['item']['artists']
        artists_names = ', '.join([artist['name'] for artist in artists])
        link = current_track_info['item']['external_urls']['spotify']
    else:
        track_name = ""
        artists = ""
        artists_names = ""
        link = ""
    current_track = {
        'track_name': track_name,
        'track_artist': artists_names,
        'link': link
    }
    if current_track_info is not None and current_track_info['is_playing']:
        print(f"Currently playing:", current_track)

    #top tracks
    top_track_info = sp.current_user_top_tracks(limit=5, time_range = "long_term")
    top_tracks = []
    for track in top_track_info['items']:
        top_track_name = track['name']
        track_artist = ', '.join([artist['name'] for artist in track['artists']])
        link = track['external_urls']['spotify']
        top_tracks.append({
            'track_name': top_track_name,
            'track_artist': track_artist,
            'link': link
        })
    print(top_tracks)

    #top artists
    top_artist_info = sp.current_user_top_artists(limit=5, time_range="long_term")
    top_artists = []
    for artist in top_artist_info['items']:
        top_artist_name = artist['name']
        image_url = (', '.join([image['url'] for image in artist['images']])).split()[0]
        image_url = image_url.replace(",","")
        print(f"Image url:", image_url)
        link = artist['external_urls']['spotify']
        top_artists.append({
            'artist_name': top_artist_name,
            'image_url': image_url,
            'link': link
        })
    print(top_artists)

    

    '''
    recommendations = sp.recommendations(seed_artists=["0NIPkIjTV8mB795yEIiPYL"], limit=5)
    for rec in recommendations['tracks']:
        print(rec['name'])'''


    return render_template('profile/profile_base.html', followers=followers, follower_count=follower_count,
                           following=following, following_count=following_count,
                           current_track=current_track,
                           top_tracks = top_tracks,
                           top_artists = top_artists)

@bp.route('/get_genres')
def get_genres():
    token_info = get_token()
    sp = Spotify(auth=token_info['access_token'])
    #top genres
    top_track_genre_info = sp.current_user_top_tracks(limit=20, time_range = "long_term")
    top_track_genres = []
    genre_dict = {}
    for track in top_track_genre_info['items']:
        for artist in track['artists']:
            artist_id = artist['id']
            print(f"Artist id:", artist_id)
            artist_info = sp.artist(artist_id)
            artist_genres = artist_info['genres']
            print(f"Artist genres: ", artist_genres)
            for genre in artist_genres:
                if genre_dict.__contains__(genre):
                    genre_dict[genre] = genre_dict[genre] + 1
                else:
                    genre_dict[genre] = 1
    print(genre_dict)
    genre_arr = []
    count_arr = np.array([])
    for genre, count in genre_dict.items():
        genre_arr.append(genre)
        print(count)
        count_arr = np.append(count_arr, count)
    plt.pie(count_arr, labels = genre_arr)
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.subplots_adjust(right=1)
    plt.savefig('flaskr\static\images\genre-plot.png')
    #plt.show()

    return jsonify(genre_dict)




'''
@bp.route('/user/<int:id>/followers')
def get_followers(id):
    db = get_db()
    cursor = db.execute('SELECT COUNT(*) as follower_count FROM follows WHERE following_id = ?', (id,))
    follower_count = cursor.fetchone()['follower_count']
    print(follower_count)

    return render_template('profile/profile_base.html', follower_count=follower_count)
'''
