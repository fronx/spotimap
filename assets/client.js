window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        playPreview: function(hoverData) {
            if (hoverData != undefined && hoverData.points[0].customdata != undefined)
            {
                // matches search?
                if (hoverData.points[0].customdata[11] > 0)
                {
                    var url = hoverData.points[0].customdata[2];
                    document.getElementById('preview-source').setAttribute('src', url)
                    var player = document.getElementById('preview-player');
                    player.load();
                    player.volume = 0.25;
                    player.play();
                    console.log(JSON.stringify(hoverData.points[0].customdata));
                }
            }
            else
            {
                // console.log('other');
                document.getElementById('preview-player').pause();
            }
        },
        pausePreview: function(clientData) {
            document.getElementById('preview-player').pause();
        }
    }
});
