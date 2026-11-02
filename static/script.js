$(document).ready(function(){
    $('#67').on('submit',function(e){
        e.preventDefault();
        err = 0;
        if ($('#fullname').val().trim() === '' || $('#password').val().trim() != $('#confirm_password').val().trim()){
            err = 1;
        }else{
            err = 0;
        }
        if (err == 0){
            $.ajax({
                url: '/api/user_register',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    name: $('#fullname').val(),
                    password: $('#password').val(),
                    email: $('#email').val()
                })
            })
        }
    })

    $('#login-form').on('submit', function(e){
        e.preventDefault();
        $.ajax({
            url: '/api/login',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                email: $('#username').val(),
                password: $('#password').val()
            })
        }).done(function(){
            window.location.href = '/profile';
        }).fail(function(){
            alert('Неверный email или пароль');
        });
    });

    $('#chat-form').on('submit', function (e) {
        e.preventDefault();
        var text = $('#chat-input').val().trim();
        if (!text) return;

        var $msgs = $('#chat-messages');
        $msgs.append($('<div class="msg user"></div>').text(text));
        $('#chat-input').val('');
        $msgs.scrollTop($msgs[0].scrollHeight);

        $.ajax({
            url: '/api/chat',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ message: text })
        }).done(function (res) {
            $msgs.append($('<div class="msg bot"></div>').text(res.reply));
            $msgs.scrollTop($msgs[0].scrollHeight);
        }).fail(function () {
            $msgs.append($('<div class="msg bot"></div>').text('Ошибка: сервер не ответил'));
            $msgs.scrollTop($msgs[0].scrollHeight);
        });
    });
    
})