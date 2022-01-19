window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        playPreview: function(hoverData) {
            if (hoverData != undefined)
            {
                var url = hoverData.points[0].customdata[2];
                console.log(url);
                document.getElementById('preview-source').setAttribute('src', url)
                document.getElementById('preview-player').load();
                document.getElementById('preview-player').play();
            }
            else
            {
                document.getElementById('preview-player').pause();
            }
        }
    }
});
