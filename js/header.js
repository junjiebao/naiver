/**
 * NAVIER YACHTS Header Component
 * Dynamically inserts the header/navigation into all pages
 */
document.addEventListener('DOMContentLoaded', function() {
    const headerEl = document.querySelector('header');
    if (!headerEl) return;

    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const navItems = [
        { href: 'index.html', label: 'Home' },
        { href: 'about.html', label: 'DEALER' },
        { href: 'products.html', label: 'Products & Services' },
        { href: 'projects.html', label: 'Projects' },
        { href: 'news.html', label: 'News & Events' },
        { href: 'contact.html', label: 'Contact Us' }
    ];

    const navHTML = navItems.map(item => {
        const activeClass = (currentPage === item.href ||
            (currentPage === '' && item.href === 'index.html')) ? ' class="active"' : '';
        return `<li><a href="${item.href}"${activeClass}>${item.label}</a></li>`;
    }).join('');

    headerEl.innerHTML = `
        <div class="container">
            <div class="logo">
                <a href="index.html">
                    <img src="images/logo narrow.png" alt="NAVIER YACHTS Logo">
                </a>
            </div>
            <nav>
                <div class="menu-toggle">
                    <i class="fas fa-bars"></i>
                </div>
                <ul class="nav-menu">
                    ${navHTML}
                    <li class="language-selector">
                        <a href="#" id="current-lang">EN</a>
                        <ul class="language-dropdown">
                            <li><a href="#" data-lang="en">English</a></li>
                            <li><a href="#" data-lang="zh">中文</a></li>
                        </ul>
                    </li>
                </ul>
            </nav>
        </div>`;
});
