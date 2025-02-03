import os
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from flask import session



def build_comment_tree(comments):
    comment_dict = {}
    for comment in comments:
        comment = dict(comment)  # Convert sqlite3.Row to dictionary
        comment['replies'] = []
        comment_dict[comment['id']] = comment

    for comment in comment_dict.values():
        parent_id = comment['parent_id']
        if parent_id:
            parent_comment = comment_dict[parent_id]
            parent_comment['replies'].append(comment)

    return [comment for comment in comment_dict.values() if comment['parent_id'] is None]
