$(document).ready(function() {

  var getWallScale = function() {
    return parseFloat($('.wall').css('transform').match(/-?[\d\.]+/g)[0]);
  };

  var getElemFloatCss = function(element, css) {
    return parseFloat($(element).css(css));
  };

  var defaultMaxScale = 1;
  var defaultMinScale = 0.3;
  var defaultScaling = 0.02;

  $('main').css('height', getElemFloatCss('.wall', 'height') * getWallScale() + 'px');
  $('main').css('width', getElemFloatCss('.wall', 'width') * getWallScale() + 'px');

  $('article').draggable({
    cursor: 'move',
    scroll: true,
    scrollSensitivity: 20,
    scrollSpeed: 20,
    drag: function(event, ui){
      var zoom = getWallScale();
      ui.position.top = Math.min(Math.max(ui.position.top / zoom, 0), getElemFloatCss('.wall', 'height') - $(this).outerHeight());
      ui.position.left = Math.min(Math.max(ui.position.left / zoom, 0), getElemFloatCss('.wall', 'width') - $(this).outerWidth());
    }
  });

  $('.wall')
  .mousedown(function(event) {
    if(event.which == 2) {
      if ($('.wall').hasClass('ui-draggable')) {
        $('.wall').draggable('enable');
      }
      else {
        $('.wall').draggable();
      }
      event.which = 1;
    }
  })
  .trigger({
    type: 'mousedown',
    which: 2
  })
  .mouseup(function(event) {
    if ($('.wall').hasClass('ui-draggable')) {
      $('.wall').draggable('disable');
    }
  })
  .droppable({
    drop: function(event, ui){
      var x = parseInt(ui.position.left);
      var y = parseInt(ui.position.top);
      var post_id = null;
      var label_id = null;
      if($(this).find('article').hasClass('classic')) {
        post_id = ui.helper.data( 'postitId' );
      }
      else {
        label_id = ui.helper.data( 'labelId' );
      }
      $.post( '/save_position', { x: x, y: y, post_id: post_id, label_id: label_id});
    }
  })
  .bind('mousewheel', function(e) {
    e.preventDefault();

    var isZooming = false;
    var scale = getWallScale();
    var mouseLeft = e.clientX - getElemFloatCss('.wall', 'left');
    var mouseTop = e.clientY - getElemFloatCss('.wall', 'left');
    var oldZoom = scale;

    if (e.originalEvent.wheelDelta >= 0)
    {
      if (scale < defaultMaxScale) {
        scale += defaultScaling;
        isZooming = true;
      }
    }
    else
    {
      if (scale > defaultMinScale) {
        scale -= defaultScaling;
        isZooming = true;
      }
    }

    var ratio = oldZoom / scale;
    var deltaWidth = (1 - ratio) * $('.wall').outerWidth() * scale;
    var deltaTop = (1 - ratio) * $('.wall').outerHeight() * scale;
    var mouseXRatio = mouseLeft / (getElemFloatCss('.wall', 'width') * scale);
    var mouseYRatio = mouseTop / (getElemFloatCss('.wall', 'height') * scale);

    if (isZooming) {

      $('main').css('height', getElemFloatCss('.wall', 'height') * scale + 'px');
      $('main').css('width', getElemFloatCss('.wall', 'width') * scale + 'px');

      $('.wall').css({
        'transform': 'scale('+scale+')',
        'left': getElemFloatCss('.wall', 'left')-deltaWidth*mouseXRatio + 'px',
        'top': getElemFloatCss('.wall', 'top')-deltaTop*mouseYRatio + 'px'
      });
    }
  });
});
