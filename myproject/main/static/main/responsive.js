/*document.addEventListener('DOMContentLoaded', function() {
    const baseStyle = document.getElementById('base-style');
    let deviceStyle;

    if (window.innerWidth <= 375) {
        deviceStyle = "{% static 'main/style-mobile.css' %}";
    } else if (window.innerWidth <= 768) {
        deviceStyle = "{% static 'main/style-tablet-md.css' %}";
    } else if (window.innerWidth <= 1024) {
        deviceStyle = "{% static 'main/style-tablet-lg.css' %}";
    }

    if (deviceStyle) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = deviceStyle;
        document.head.appendChild(link);
    }
});*/