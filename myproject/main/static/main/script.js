document.addEventListener('DOMContentLoaded', function() {
    const userLang = navigator.language || navigator.userLanguage;
    const currentLang = document.cookie.split('; ').find(row => row.startsWith('django_language'))?.split('=')[1];

    if (!currentLang) {
        if (userLang.startsWith('ru')) {
            document.cookie = "django_language=ru";
        } else {
            document.cookie = "django_language=en";
        }
        window.location.reload();
    }

    window.addEventListener('pageshow', function() {
        document.querySelectorAll('video').forEach(video => {
            video.play();
        });
    });
});
