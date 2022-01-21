window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        playPreview: function(hoverData) {
            if (hoverData != undefined && hoverData.points[0].customdata != undefined)
            {
                var url = hoverData.points[0].customdata[2];
                document.getElementById('preview-source').setAttribute('src', url)
                document.getElementById('preview-player').load();
                document.getElementById('preview-player').play();
                console.log(JSON.stringify(hoverData.points[0].customdata));
            }
            else
            {
                // document.getElementById('preview-player').pause();
            }
        }
    }
});
