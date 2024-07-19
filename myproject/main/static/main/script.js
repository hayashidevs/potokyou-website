document.addEventListener('click', function(event) {
    var mobileButton = document.getElementById('mobileButton');
    var desktopButton = document.getElementById('desktopButton');
    var mobileMenu = document.querySelector('[aria-labelledby="mobileButton"]');
    var desktopMenu = document.querySelector('[aria-labelledby="desktopButton"]');

    if (mobileButton.contains(event.target)) {
        mobileMenu.classList.toggle('show');
    } else if (desktopButton.contains(event.target)) {
        desktopMenu.classList.toggle('show');
    } else {
        if (mobileMenu.classList.contains('show')) {
            mobileMenu.classList.remove('show');
        }
        if (desktopMenu.classList.contains('show')) {
            desktopMenu.classList.remove('show');
        }
    }
});
