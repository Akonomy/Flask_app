/* Theme toggle */
(function () {
  const html = document.documentElement;

  function setIcon(theme) {
    const icon = document.getElementById('themeIcon');
    if (icon) icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
  }

  setIcon(html.getAttribute('data-bs-theme') || 'light');

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('themeToggle');
    if (btn) {
      btn.addEventListener('click', () => {
        const next = html.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-bs-theme', next);
        localStorage.setItem('theme', next);
        setIcon(next);
      });
    }
  });
})();

/* Auto-dismiss alerts */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert-dismissible').forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  /* Cart quantity auto-submit on change */
  document.querySelectorAll('input[name="quantity"][data-auto-submit]').forEach(input => {
    input.addEventListener('change', () => input.closest('form').submit());
  });
});
