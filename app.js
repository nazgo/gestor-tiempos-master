(function () {
    'use strict';

    const COLLAPSE_KEY = 'nm-sidebar-collapsed';

    document.addEventListener('DOMContentLoaded', function () {
        const shell = document.getElementById('appShell');
        if (!shell) return;

        const collapseButton = document.getElementById('sidebarCollapse');
        const mobileMenuButton = document.getElementById('mobileMenuButton');
        const backdrop = document.getElementById('sidebarBackdrop');
        const sidebarLinks = document.querySelectorAll('.sidebar-link');

        if (window.innerWidth >= 992 && localStorage.getItem(COLLAPSE_KEY) === 'true') {
            shell.classList.add('sidebar-collapsed');
        }

        if (collapseButton) {
            collapseButton.addEventListener('click', function () {
                shell.classList.toggle('sidebar-collapsed');
                localStorage.setItem(COLLAPSE_KEY, shell.classList.contains('sidebar-collapsed'));
            });
        }

        function closeMobileSidebar() {
            shell.classList.remove('mobile-sidebar-open');
            document.body.style.overflow = '';
        }

        if (mobileMenuButton) {
            mobileMenuButton.addEventListener('click', function () {
                const opened = shell.classList.toggle('mobile-sidebar-open');
                document.body.style.overflow = opened ? 'hidden' : '';
            });
        }

        if (backdrop) backdrop.addEventListener('click', closeMobileSidebar);
        sidebarLinks.forEach(function (link) {
            link.addEventListener('click', function () {
                if (window.innerWidth < 992) closeMobileSidebar();
            });
        });

        window.addEventListener('resize', function () {
            if (window.innerWidth >= 992) closeMobileSidebar();
        });
    });
})();
