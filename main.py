import os
import dotenv
import spotipy
from spotipy import SpotifyOAuth
from dotenv import load_dotenv
import flask
from flask import Flask, redirect, url_for, render_template, request
#Loads Environment variables
load_dotenv()

#Resets token to ensure authentication repeats for every run
# May need to be deleted for web deployment
# if os.path.exists(os.getenv('CACHE_PATH')):
#     os.remove(os.getenv('CACHE_PATH'))
#Creates a Spotify Client and defines API permissions.
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id = os.getenv('CLIENT_ID'), 
                                               client_secret= os.getenv('CLIENT_SECRET'),
                                                redirect_uri= os.getenv('REDIRECT_URI'),
                                                scope = os.getenv('SCOPE'),
                                                show_dialog=True))



#Setting up the server
app = Flask(__name__)


@app.route("/", methods = ["GET","POST"])
def landing():
    if request.method == "POST":
        if "action1" in request.form:
            print("HELLO WORLD")
            
    return(render_template("index.html"))



@app.route("/spotify", methods = ["GET", "POST"])
def getSpotify():

    playlistExists = False
    playlist_Name = "Yearly Rewind"
    playlist_Description = "This is a recap of the past year of listening. Brought to you by Akhil Akkineni :)"
    playlist_Created = False
    playlists = sp.current_user_playlists()

    if request.method == "POST":
        print("Posted...")
        if "createPlaylist" in request.form:
            print("Sequence Active.")
            for playlist in playlists["items"]:
                if playlist["name"] == playlist_Name:
                    playlist_uri = playlist["uri"]
                    track_list = sp.playlist_items(playlist_id=playlist_uri)
                    playlist_Created = True
                    for tag in track_list["items"]:
                        track_uri = tag["item"]["uri"]
                        sp.playlist_remove_all_occurrences_of_items(playlist_id=playlist_uri,items=[track_uri])
                        playlistExists = True
            if playlist_Created == False:
                new_playlist = sp.current_user_playlist_create(name= playlist_Name,public=False, description= playlist_Description)
                for playlist in playlists["items"]:
                    if playlist["name"] == playlist_Name:
                        playlist_uri = playlist["uri"]
            if playlistExists == False:
                data = sp.current_user_top_tracks(limit= 20, time_range= "long_term")
                for item in data["items"]:
                    top_list = []
                    song_uri = item["uri"]
                    top_list.append(song_uri)
                    sp.playlist_add_items(playlist_id=playlist_uri,items=top_list)
                print("Passed Through...")
        else:
            print("Not fetching...")            
        return(render_template("index.html"))
    
app.run()
