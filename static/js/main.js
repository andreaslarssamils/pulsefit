// Toasts (notifications). Dismissible and auto-dismiss after 6 seconds.
document.addEventListener('click', function (event) {
  const close = event.target.closest('.toast__close');
  if (!close) return;
  const toast = close.closest('.toast');
  if (toast) toast.remove();
});

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.toast').forEach(function (toast) {
    setTimeout(function () {
      toast.remove();
    }, 6000);
  });
});

// Show/hide password toggle. Buttons opt in with
// data-toggle-password="<input id>" (see auth templates).
document.addEventListener('click', function (event) {
  const btn = event.target.closest('[data-toggle-password]');
  if (!btn) return;

  const input = document.getElementById(
    btn.getAttribute('data-toggle-password'),
  );
  if (!input) return;

  const showing = input.type === 'password';
  input.type = showing ? 'text' : 'password';
  btn.textContent = showing ? 'Hide' : 'Show';
  btn.setAttribute('aria-label', showing ? 'Hide password' : 'Show password');
});

// Catalog category filter (plans + shop). Tabs filter the already-rendered cards
// client-side so there is no page reload. Progressive enhancement:
// without JS the full list renders and every card stays visible.
(function () {
  const tabs = document.querySelectorAll('.filter-tab');
  const grid = document.querySelector('[data-catalog-grid]');
  if (!tabs.length || !grid) return;

  const cards = grid.querySelectorAll('[data-category]');
  const emptyState = document.querySelector('[data-empty-state]');

  function applyFilter(filter) {
    let visible = 0;
    cards.forEach(function (card) {
      const match =
        filter === 'all' || card.getAttribute('data-category') === filter;
      card.hidden = !match;
      if (match) visible += 1;
    });
    // Reveal the filter-aware empty state when a filter hides every card.
    if (emptyState) emptyState.hidden = visible !== 0;
  }

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) {
        t.classList.remove('is-active');
      });
      tab.classList.add('is-active');
      applyFilter(tab.getAttribute('data-filter'));
    });
  });
})();
