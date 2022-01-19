# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, ClientsideFunction
import webbrowser
import plotly.express as px

from sklearn.manifold import TSNE

# ---

app = dash.Dash(__name__)

# ---

import numpy as np
import pandas as pd
import spotipy

from spotipy.oauth2 import SpotifyOAuth
scope = "user-library-read"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))


tracks = {}
def add_track(t, a=None):
	if a == None:
		a = t
	if t['preview_url'] != None:
		tracks[t['uri']] = {
			'name': t['name'],
			'album': a['album']['name'],
			'artist': a['album']['artists'][0]['name'],
			# 'genre': genre,
			'uri': t['uri'],
			'preview_url': t['preview_url'],
			'href': t['external_urls']['spotify'],
			'release_year': int(a['album']['release_date'][0:4])
		}

albums = sp.current_user_saved_albums()
while albums:
	for i, a in enumerate(albums['items']):
		print("%4d %s %s" % (i + 1 + albums['offset'], a['album']['uri'], a['album']['name']))
		# genre = next(iter(a['album']['artists'][0]['genres']), '') if 'genres' in a['album']['artists'][0] else ''
		# print(genre)
		for t in a['album']['tracks']['items']:
			add_track(t, a)
	if albums['next']:
		# albums = None
		albums = sp.next(albums)
	else:
		albums = None

playlists = sp.current_user_playlists()
while playlists:
	for i, p in enumerate(playlists['items']):
		print("%4d %s" % (i + 1 + playlists['offset'], p['name']))
		if 'items' in p['tracks']:
			for t in p['tracks']['items']:
				add_track(t)
	if playlists['next']:
		# playlists = None
		print('.', end='')
		playlists = sp.next(playlists)
	else:
		playlists = None

likes = sp.current_user_saved_tracks()
while likes:
	for i, item in enumerate(likes['items']):
		add_track(item['track'])
	if likes['next']:
		# likes = None
		print('.', end='')
		likes = sp.next(likes)
	else:
		likes = None

chunk_size = 20
uris = list(tracks.keys())
print(len(uris))

chunked_uris = [uris[i:i + chunk_size] for i in range(0, len(uris), chunk_size)]

chunked_features = [sp.audio_features(uris) for uris in chunked_uris]
for features in chunked_features:
	for f in features:
		tracks[f['uri']].update({
			'instrumentalness': f['instrumentalness'],
			'danceability': f['danceability'],
			'energy': f['energy'],
			'valence': f['valence'],
			'speechiness': f['speechiness'],
			'acousticness': f['acousticness'],
			'tempo': f['tempo'],
			'normalized_tempo': (f['tempo'] - 30) / 170
		  })

tracks_data = list(tracks.values())
data = pd.DataFrame(tracks_data)

#- t-SNE ----------------------------

tsne = TSNE(n_components=2, verbose=1, perplexity=40, n_iter_without_progress=50, n_jobs=-1, square_distances=True) #, n_iter=500)
tsneable_data = data[['instrumentalness','danceability','energy', 'valence', 'normalized_tempo']] #, 'speechiness', 'acousticness']]
tsne_results = tsne.fit_transform(tsneable_data)
data['x'] = tsne_results[:,0]
data['y'] = tsne_results[:,1]

#------------------------------------

fig = px.scatter(data, x="x", y="y", color="danceability", custom_data=("href", "name", "preview_url", "uri", "album", "artist", "release_year"))
fig.update_traces(hovertemplate="""%{customdata[5]}<br>%{customdata[1]}, %{customdata[4]}<br>(%{customdata[6]})""")
fig.update_layout(clickmode='event+select')

#------------------------------------

app.layout = html.Div(children=[
	dcc.Graph(
		id='my-graph',
		figure=fig,
		style={"Width": "100vh", "Height": 750}
	),

	html.Video(id='preview-player', controls=True, autoPlay=False, children=[
		html.Source(id='preview-source', src='https://p.scdn.co/mp3-preview/5c5623fee2333d3400d3face46fb72811b66b241?cid=c701bf448e4b4d609e92a50f462c3d8c', type="audio/mpeg"),
	]),

	html.P(id='no-output-1'),
	html.P(id='no-output-2'),
])

@app.callback(
	Output('no-output-1', 'children'),
	[Input('my-graph', 'clickData')]
)
def open_url(clickData):
	if clickData != None:
		print(clickData)
		url = clickData['points'][0]['customdata'][0]
		webbrowser.open_new(url)

app.clientside_callback(
	ClientsideFunction(
		namespace='clientside',
		function_name='playPreview'
	),
	Output('no-output-2', 'children'),
	Input('my-graph', 'hoverData'),
)

if __name__ == '__main__':
	app.run_server(debug=True, use_reloader=False)
