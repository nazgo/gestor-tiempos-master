(() => {
  const page = document.querySelector('.pc-page');
  if (!page || typeof Chart === 'undefined') return;
  let data;
  try { data = JSON.parse(page.dataset.performance); } catch (_) { return; }
  const canvas = document.getElementById('pcMonthlyChart');
  if (!canvas) return;
  const css = getComputedStyle(document.documentElement);
  const teal = css.getPropertyValue('--pc-accent').trim() || '#08a7a5';
  const muted = css.getPropertyValue('--pc-muted').trim() || '#718096';
  const grid = css.getPropertyValue('--pc-border').trim() || 'rgba(148,163,184,.2)';
  const ctx = canvas.getContext('2d');
  const gradient = ctx.createLinearGradient(0, 0, 0, 280);
  gradient.addColorStop(0, 'rgba(8,167,165,.35)');
  gradient.addColorStop(1, 'rgba(8,167,165,.02)');
  new Chart(canvas, {
    type: 'line',
    data: { labels: data.monthly.labels, datasets: [{ data: data.monthly.values, borderColor: teal, backgroundColor: gradient, fill: true, tension: .38, borderWidth: 3, pointRadius: 3, pointHoverRadius: 6 }] },
    options: { responsive: true, maintainAspectRatio: false, interaction: { intersect: false, mode: 'index' }, plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => `${c.raw} registros` } } }, scales: { x: { grid: { display: false }, ticks: { color: muted } }, y: { beginAtZero: true, grid: { color: grid }, ticks: { color: muted, precision: 0 } } } }
  });
})();
