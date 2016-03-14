$(document).ready(function() {
    $('.popup-link').on('click', function(e) {
        $link = $(this);
        e.preventDefault();
        $('header, main, footer').css({'pointer-events': 'none', 'opacity': '0.4'});
        $('html').css('background-color', '#DCDCDC');
        $.get($link.attr('href'), function(popup) {
            if ($('.popup').size() === 0) {
                $('main').after(popup);
                $('.popup').prepend("<a>X</a>");
                $('.popup a').on('click', function(){
                    $('.popup').remove();
                    $('header, main, footer').css({'pointer-events': 'auto', 'opacity': '1'});
                    $('html').css('background-color', 'transparent');
                });
            }
        });

    });
});
