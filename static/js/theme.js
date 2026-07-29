(function () {
    'use strict';

    const STORAGE_KEY = 'nm-theme';

    function currentTheme() {
        return document.documentElement.dataset.theme || 'light';
    }

    function applyTheme(theme) {
        const safeTheme = theme === 'dark' ? 'dark' : 'light';
        document.documentElement.dataset.theme = safeTheme;
        localStorage.setItem(STORAGE_KEY, safeTheme);

        const metaTheme = document.querySelector('meta[name="theme-color"]');
        if (metaTheme) {
            metaTheme.setAttribute('content', safeTheme === 'dark' ? '#0f1718' : '#009b9d');
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const toggle = document.getElementById('themeToggle');
        if (!toggle) return;

        toggle.addEventListener('click', function () {
            applyTheme(currentTheme() === 'dark' ? 'light' : 'dark');
        });
    });
})();
