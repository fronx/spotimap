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
from song.song import SONG

# ---

app = dash.Dash(__name__)

# ---

import numpy as np
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import hashlib

# ---

try:
	data = pd.read_pickle('data-spotify.pkl')
except FileNotFoundError:
	scope = "user-library-read,playlist-read-private,user-read-private"
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

data['artist-0-1'] = [int(hashlib.sha1(a.encode('utf-8')).hexdigest()[:6], 16)/16777216 for a in data['artist']]
data['album-0-1'] = [int(hashlib.sha1(a.encode('utf-8')).hexdigest()[:6], 16)/16777216 for a in data['album']]
# print(data[['artist', 'artist-0-1']])

columns = ['instrumentalness','danceability','energy', 'valence', 'speechiness', 'acousticness', 'normalized_tempo', 'artist-0-1', 'album-0-1']


#- t-SNE ----------------------------

# tsne = TSNE(n_components=2, verbose=1, perplexity=50, n_iter_without_progress=50, n_jobs=-1, square_distances=True)
# tsneable_data = data[columns]
# tsne_results = tsne.fit_transform(tsneable_data)
# data['x'] = tsne_results[:,0]
# data['y'] = tsne_results[:,1]
# # data['z'] = tsne_results[:,2]

# data.to_pickle('data-tsne.pkl')

#------------------------------------

try:
	data = pd.read_pickle('data-song.pkl')
except FileNotFoundError:
	d = data[columns].to_numpy()
	model = SONG(min_dist=0.5, spread=0.9)
	model.fit(d)
	Y = model.transform(d)
	data['x'] = Y[:,0]
	data['y'] = Y[:,1]
	data.to_pickle('data-song.pkl')

data['summary'] = data[['name', 'album', 'artist']].agg(', '.join, axis=1)

top = data[['artist', 'x', 'y']] \
	.groupby(['artist'], as_index=False)[['x','y']] \
	.agg(['count','median','std']) \
	.sort_values([('x','count'),('x','std'),('y','std')], ascending=[False,True,True])[:120]

top['text_size'] = 4 * np.log(top[("x", "count")])

#------------------------------------

clicked_tracks = []

app.layout = html.Div(children=[
	html.Div(id='div-search', children=[
        "Search: ",
        dcc.Input(id='search', value='', type='text', autoFocus=True)
    ]),
	dcc.Graph(
		id='my-graph',
		clear_on_unhover=True,
	),

	html.Video(id='preview-player', controls=True, autoPlay=False, height=30, width=400, children=[
		html.Source(id='preview-source', src='', type="audio/mpeg"),
	]),

	html.Ul(id='click-list', children=[]),

	html.P(id='no-output-1'),
	html.P(id='no-output-2'),
])

@app.callback(
	Output('my-graph', 'figure'),
	Input('search', 'value'))
def filter_graph(query):
	def matching(row):
		if len(query) == 0:
			return True
		else:
			return max(
				query.lower() in row['artist'].lower(),
				query.lower() in row['album'].lower(),
				query.lower() in row['name'].lower())

	data['matching'] = data.apply(matching, axis=1)
	data['opacity'] = [1.0 if m else 0.3 for m in data['matching']]
	data['size'] = [9 if m else 4 for m in data['matching']]
	matches = data.loc[data['matching'] == True]
	nonmatches = data.loc[data['matching'] == False]

	fig = make_subplots()

	fig.add_trace(go.Scatter(
		x=data["x"], y=data["y"],
		mode='markers',
		marker=dict(
			size=data["size"],
			color=data["danceability"],
			opacity=data['opacity'],
			line_width=0.0,
			),
		hoverinfo='skip',
		showlegend=False,
	))

	# fig.add_trace(go.Scatter(
	# 	x=nonmatches["x"], y=nonmatches["y"],
	# 	mode='markers',
	# 	marker=dict(
	# 		size=nonmatches["size"],
	# 		color=nonmatches["danceability"],
	# 		opacity=nonmatches['opacity'],
	# 		line_width=0.0,
	# 		),
	# 	hoverinfo='skip',
	# 	showlegend=False,
	# ))

	# fig.add_trace(go.Scatter(
	# 	x=matches["x"], y=matches["y"],
	# 	mode='markers',
	# 	marker=dict(
	# 		size=matches["size"],
	# 		color=matches["danceability"],
	# 		opacity=matches['opacity'],
	# 		),
	# 	showlegend=False,
	# ))

	fig.add_trace(go.Scatter(
		x=matches["x"], y=matches["y"],
		mode='markers',
		marker=dict(
			size=matches["size"],
			line_width=0.5,
			line_color='rgba(255, 255, 255, 1.0)',
			color='rgba(255, 255, 255, 0.0)',
			),
		customdata=matches[["href", "name", "preview_url", "uri", "album", "artist", "release_year",
			"instrumentalness", "energy", "valence", "tempo", "matching"]],
		hovertemplate='<b>%{customdata[5]}</b><br>%{customdata[1]}, %{customdata[4]}<br>(%{customdata[6]})<br><br>instrumentalness: %{customdata[7]}<br>energy: %{customdata[8]}<br>valence: %{customdata[9]}<br>tempo: %{customdata[10]}<extra></extra>',
		showlegend=False,
	))

	if len(query) == 0:
		fig.add_trace(go.Scatter(
			x=top[("x", "median")],
			y=top[("y", "median")],
			text=top.index,
			textfont_size=top["text_size"],
			mode='text',
			showlegend=False,
		))
	else:
		fig.add_trace(go.Scatter(
			x=matches["x"],
			y=matches["y"],
			text=matches['summary'],
			textfont_size=8,
			mode='text',
			textposition='bottom right',
			showlegend=False,
		))

	fig.update_layout(height=1200, uniformtext_minsize=12, uniformtext_mode='hide', clickmode='event')
	return fig

@app.callback(
	Output('click-list', 'children'),
	[Input('my-graph', 'clickData')],
	[State('click-list','children')]
)
def open_url(clickData, state):
	if clickData == None:
		print("NONE")
		raise PreventUpdate
	print(clickData)
	t = clickData['points'][0]['customdata']
	clicked_tracks.append(t)
	webbrowser.open_new_tab(t[0])
	return [html.Li(children=[
			html.A(href=t[0], children=t[1]), # track link
			html.Span(children=t[4]), # album
			html.Span(children=t[5]), # artist
			html.Span(children=t[6]), # year
			]) for t in reversed(clicked_tracks)]

@app.callback(
	Output('search', 'value'),
	[Input('my-graph', 'clickData')])
def clear_search(clickData):
	print("CLICK")
	if clickData == None:
		return ""
	else:
		raise PreventUpdate

app.clientside_callback(
	ClientsideFunction(
		namespace='clientside',
		function_name='playPreview'
	),
	Output('no-output-1', 'children'),
	Input('my-graph', 'hoverData'),
)

app.clientside_callback(
	ClientsideFunction(
		namespace='clientside',
		function_name='pausePreview'
	),
	Output('no-output-2', 'children'),
	Input('my-graph', 'clickData'),
)

if __name__ == '__main__':
	app.run_server(debug=True, use_reloader=False)
