document.addEventListener('DOMContentLoaded', function() {
    const overlay = document.querySelector('.transition-overlay');

    // Show overlay during navigation
    function showOverlay() {
        overlay.classList.add('transition-active');
    }

    // Hide overlay on page load
    function hideOverlay() {
        overlay.classList.remove('transition-active');
    }

    // Handle page navigation
    document.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', function(event) {
            if (this.href && this.href.startsWith(window.location.origin)) {
                event.preventDefault();
                const url = this.href;
                showOverlay();
                setTimeout(() => window.location.href = url, 500);
            }
        });
    });

    // Hide overlay after page loads
    setTimeout(hideOverlay, 500);

    // Ensure videos play on page show
    window.addEventListener('pageshow', function() {
        document.querySelectorAll('video').forEach(video => video.play());
    });

    // Language settings
    const currentLang = getCookie('django_language') || detectUserLanguage() || 'en';
    highlightActiveLanguage(currentLang);
    updateLanguageSwitcherLinks();
    cleanURL();
});

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

function highlightActiveLanguage(activeLang) {
    document.querySelectorAll('.language-switch a').forEach(link => {
        link.classList.toggle('active', link.dataset.lang === activeLang);
    });
}

function updateLanguageSwitcherLinks() {
    document.querySelectorAll('.language-switch a').forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            changeLanguage(this.dataset.lang);
        });
    });
}

function changeLanguage(language) {
    document.cookie = `django_language=${language}; path=/`;
    location.reload();
}

function cleanURL() {
    if (window.location.search.includes('language=')) {
        const url = new URL(window.location.href);
        url.searchParams.delete('language');
        window.history.replaceState({}, document.title, url.pathname + url.hash);
    }
}

function detectUserLanguage() {
    const userLang = navigator.language || navigator.userLanguage;
    return userLang.startsWith('ru') ? 'ru' : 'en';
}

// Handle scroll inertia
document.querySelectorAll('.scrollable-container').forEach(container => {
    let isScrolling;
    let scrollSpeed = 0;
    let inertiaFrame;

    container.addEventListener('wheel', (event) => {
        event.preventDefault();
        const delta = event.deltaY;

        if (!isScrolling) {
            scrollSpeed = -delta * 0.1;
            isScrolling = true;
        }

        scrollSpeed += delta * 0.2;

        if (inertiaFrame) cancelAnimationFrame(inertiaFrame);
        inertiaFrame = requestAnimationFrame(smoothScroll);
    });

    function smoothScroll() {
        scrollSpeed *= 0.92;

        if (Math.abs(scrollSpeed) < 0.5) {
            isScrolling = false;
            return;
        }

        container.scrollTop += scrollSpeed;
        inertiaFrame = requestAnimationFrame(smoothScroll);
    }

    let touchStartY = 0;
    let touchStartScrollTop = 0;
    let touchSpeed = 0;
    let touchFrame;

    container.addEventListener('touchstart', (event) => {
        touchStartY = event.touches[0].clientY;
        touchStartScrollTop = container.scrollTop;
        touchSpeed = 0;
        if (touchFrame) cancelAnimationFrame(touchFrame);
    });

    container.addEventListener('touchmove', (event) => {
        const deltaY = event.touches[0].clientY - touchStartY;
        touchSpeed = deltaY * 0.2;
        container.scrollTop = touchStartScrollTop - deltaY;
    });

    container.addEventListener('touchend', () => {
        if (Math.abs(touchSpeed) > 0.5) {
            touchFrame = requestAnimationFrame(smoothTouchScroll);
        }
    });

    function smoothTouchScroll() {
        touchSpeed *= 0.92;

        if (Math.abs(touchSpeed) < 0.5) {
            return;
        }

        container.scrollTop -= touchSpeed;
        touchFrame = requestAnimationFrame(smoothTouchScroll);
    }
});
