// ── Tab switching ─────────────────────────────────────────────────────────
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const group = btn.closest('.tab-group');
      group.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      group.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(btn.dataset.tab).classList.add('active');
    });
  });
}

// ── Star rating picker ────────────────────────────────────────────────────
function initStarPicker() {
  document.querySelectorAll('.star-picker').forEach(picker => {
    const stars = picker.querySelectorAll('.star');
    const input = picker.querySelector('input[type=hidden]');
    stars.forEach((star, i) => {
      star.addEventListener('mouseover', () => highlightStars(stars, i));
      star.addEventListener('mouseout',  () => highlightStars(stars, parseInt(input.value || 0) - 1));
      star.addEventListener('click',     () => {
        input.value = i + 1;
        highlightStars(stars, i);
      });
    });
  });
}
function highlightStars(stars, upTo) {
  stars.forEach((s, i) => s.style.color = i <= upTo ? '#f59e0b' : '#d1d5db');
}

// ── Confirm delete ────────────────────────────────────────────────────────
function confirmDelete(form) {
  if (confirm('Are you sure you want to delete this book? This cannot be undone.')) {
    form.submit();
  }
}

// ── Auto-scroll chat to bottom ─────────────────────────────────────────────
function scrollChatToBottom() {
  const chat = document.querySelector('.chat-body');
  if (chat) chat.scrollTop = chat.scrollHeight;
}

// ── Flash dismiss ─────────────────────────────────────────────────────────
function initFlashDismiss() {
  document.querySelectorAll('.flash-item').forEach(el => {
    const btn = document.createElement('button');
    btn.innerHTML = '&times;';
    btn.style.cssText = 'background:none;border:none;font-size:18px;cursor:pointer;margin-left:auto;opacity:.6;';
    btn.onclick = () => el.remove();
    el.appendChild(btn);
    setTimeout(() => el.remove(), 6000);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initStarPicker();
  scrollChatToBottom();
  initFlashDismiss();
});
