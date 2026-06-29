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
