// Header scroll effect - 滚动时改变 header 样式
(function() {
  const header = document.querySelector('.site-header');
  if (!header) return;

  let ticking = false;

  function updateHeader() {
    header.classList.toggle('scrolled', window.scrollY > 20);
    ticking = false;
  }

  window.addEventListener('scroll', function() {
    if (!ticking) {
      requestAnimationFrame(updateHeader);
      ticking = true;
    }
  }, { passive: true });

  updateHeader();
})();

// 移动端汉堡菜单
(function() {
  const hamburger = document.getElementById('hamburger');
  const menu = document.getElementById('mobile-menu');
  const overlay = document.getElementById('mobile-menu-overlay');
  if (!hamburger || !menu || !overlay) return;

  function openMenu() {
    hamburger.classList.add('is-open');
    hamburger.setAttribute('aria-expanded', 'true');
    menu.classList.add('is-open');
    menu.setAttribute('aria-hidden', 'false');
    overlay.classList.add('is-open');
    document.body.style.overflow = 'hidden';
  }

  function closeMenu() {
    hamburger.classList.remove('is-open');
    hamburger.setAttribute('aria-expanded', 'false');
    menu.classList.remove('is-open');
    menu.setAttribute('aria-hidden', 'true');
    overlay.classList.remove('is-open');
    document.body.style.overflow = '';
  }

  hamburger.addEventListener('click', function() {
    menu.classList.contains('is-open') ? closeMenu() : openMenu();
  });

  overlay.addEventListener('click', closeMenu);

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeMenu();
  });

  // 移动端搜索框与桌面搜索框同步
  const mobileInput = document.getElementById('mobile-search-input');
  const desktopInput = document.getElementById('search-input');
  if (mobileInput && desktopInput) {
    mobileInput.addEventListener('input', function() {
      desktopInput.value = mobileInput.value;
      desktopInput.dispatchEvent(new Event('input'));
    });
  }
})();
