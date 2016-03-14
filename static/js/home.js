$(document).ready(function() {
    var mainWidth = $('main').width();
    var mainHeight = $('main').height();
    $('article').draggable({
        cursor: 'move',
        containment: 'main',
        scroll: true,
        scrollSensitivity: 20,
        scrollSpeed: 20,
        drag: function(event, ui){
            var matrix = $('main').css('transform');
            var values = matrix.match(/-?[\d\.]+/g);
            if(values == null){
                zoom = 1;
            }
            else{
                var zoom = values[0];
            }

            ui.position.top = Math.min(Math.max(ui.position.top / zoom, 0), mainHeight - $(this).outerHeight());
            ui.position.left = Math.min(Math.max(ui.position.left / zoom, 0), mainWidth - $(this).outerWidth());
        }
    });

    $('main').droppable({
        drop: function(event, ui){
            var x = parseInt(ui.position.left);
            var y = parseInt(ui.position.top);
            var id = ui.helper.data( 'postitId' );
            $.post( '/save_position', { x: x, y: y, post_id: id });
        }
    });

    var scale = 1;
    var xLast = 0;
    var yLast = 0;
    var xMain = 0;
    var yMain = 0;
    $('main').bind('mousewheel', function(e) {
        e.preventDefault();
        var xScreen = e.pageX - $('main').offset().left;
        var yScreen = e.pageY - $('main').offset().top;

        xMain = xMain + ((xScreen - xLast) / scale);
        yMain = yMain + ((yScreen - yLast) / scale);

        if (e.originalEvent.wheelDelta >= 0)
        {
            if (scale < 1) {
                scale += 0.03;
            }
        }
        else
        {
            if (scale > 0.3) {
                scale -= 0.03;
            }
        }

        var xNew = (xScreen - xMain) / scale;
        var yNew = (yScreen - yMain) / scale;

        xLast = xScreen;
        yLast = yScreen;

        // $('main').css({
        //     'transform-origin': xMain + 'px ' + yMain + 'px',
        //     'transform': 'scale(' + scale + ')' + 'translate(' + xNew + 'px, ' + yNew + 'px' + ')'
        // });
        $('main').css('transform', 'scale('+scale+')');
    });
});
