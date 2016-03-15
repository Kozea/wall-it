$(document).ready(function() {
    $('main').css('transform', 'scale(1)');
    var mainWidth = $('main').width();
    var mainHeight = $('main').height();
    $('article').draggable({
        cursor: 'move',
        scroll: true,
        scrollSensitivity: 20,
        scrollSpeed: 20,
        drag: function(event, ui){
            var matrix = $('main').css('transform');
            var values = matrix.match(/-?[\d\.]+/g);
            // if(values == null){
            //     zoom = 1;
            // }
            // else{
            zoom = values[0];
            // }
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
    $('main').bind('mousewheel', function(e) {

        e.preventDefault();

        if (e.originalEvent.wheelDelta >= 0)
        {
            if (scale < 1) {
                scale += 0.02;
            }
        }
        else
        {
            if (scale > 0.3) {
                scale -= 0.02;
            }
        }

        $('main').css('transform', 'scale('+scale+')');
        $('body').css('height', parseFloat($('main').css('height'))*scale + 'px');
    });
});
