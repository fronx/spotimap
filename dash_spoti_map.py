# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, ClientsideFunction
from dash.exceptions import PreventUpdate
import webbrowser
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from sklearn.manifold import TSNE

# ---

app = dash.Dash(__name__)

# ---

import numpy as np
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth


try:
	data = pd.read_pickle('data-tsne.pkl')
except FileNotFoundError:
	try:
		data = pd.read_pickle('data-spotify.pkl')
	except FileNotFoundError:
		scope = "user-library-read"
		sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

		tracks = {}
		def add_track(t, a=None, track_liked=False):
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
					'release_year': int(a['album']['release_date'][0:4]),
					'track_liked': track_liked
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
				add_track(item['track'], track_liked=True)
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
		data.to_pickle('data-spotify.pkl')

	#- artist name as a number between 0 and 1 ----

	art = data['artist'].sort_values().unique()
	# print(art)
	n_artists = len(art)
	# def calc(row):
	# 	return np.where(art == row['artist'])[0][0]/n_artists
	# data['artist-0-1'] = data['artist']
	data['artist-0-1'] = [np.where(art == a)[0][0]/n_artists for a in data['artist']]
	print(data) #['artist-0-1'][100:])
	# quit()

	#- t-SNE ----------------------------

	tsne = TSNE(n_components=2, verbose=1, perplexity=50, n_iter_without_progress=50, n_jobs=-1, square_distances=True)
	tsneable_data = data[['instrumentalness','danceability','energy', 'valence', 'normalized_tempo', 'artist-0-1']] #, 'speechiness', 'acousticness']]
	tsne_results = tsne.fit_transform(tsneable_data)
	data['x'] = tsne_results[:,0]
	data['y'] = tsne_results[:,1]
	# data['z'] = tsne_results[:,2]

	data.to_pickle('data-tsne.pkl')

#------------------------------------

fig = make_subplots()

fig.add_trace(go.Scatter(
	x=data["x"], y=data["y"],
	mode='markers',
	marker_color=data["danceability"],
	customdata=data[["href", "name", "preview_url", "uri", "album", "artist", "release_year"]],
	hovertemplate='%{customdata[5]}<br>%{customdata[1]}, %{customdata[4]}<br>(%{customdata[6]})',
	showlegend=False,
))

top = data[['artist', 'x', 'y']] \
	.groupby(['artist'], as_index=False)[['x','y']] \
	.agg(['count','median','std']) \
	.sort_values([('x','count'),('x','std'),('y','std')], ascending=[False,True,True])[:120]

top['text_size'] = 4 * np.log(top[("x", "count")])

fig.add_trace(go.Scatter(
	x=top[("x", "median")],
	y=top[("y", "median")],
	text=top.index,
	textfont_size=top["text_size"],
	mode='text',
	showlegend=False,
))

fig.update_layout(height=750, uniformtext_minsize=12, uniformtext_mode='hide', clickmode='event')

fig.show()

#------------------------------------

clicked_tracks = []

app.layout = html.Div(children=[
	dcc.Graph(
		id='my-graph',
		figure=fig
	),

	html.Video(id='preview-player', controls=True, autoPlay=False, height=30, width=400, children=[
		html.Source(id='preview-source', src='https://p.scdn.co/mp3-preview/5c5623fee2333d3400d3face46fb72811b66b241?cid=c701bf448e4b4d609e92a50f462c3d8c', type="audio/mpeg"),
	]),

	html.Ul(id='click-list', children=[]),

	html.P(id='no-output-2'),
])

@app.callback(
	Output('click-list', 'children'),
	[Input('my-graph', 'clickData')],
	[State('click-list','children')]
)
def open_url(clickData, state):
	if clickData == None:
		raise PreventUpdate
	print(clickData)
	clicked_tracks.append(clickData['points'][0]['customdata'])
	return [html.Li(children=[
			html.A(href=t[0], children=t[1]), # track link
			html.Span(children=t[4]), # album
			html.Span(children=t[5]), # artist
			html.Span(children=t[6]), # year
			]) for t in reversed(clicked_tracks)]

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
