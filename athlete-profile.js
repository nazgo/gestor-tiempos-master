(() => {
  'use strict';

  const tabs = [...document.querySelectorAll('.profile-tab[data-target]')];
  const sections = [...document.querySelectorAll('.profile-section')];

  function activateSection(targetId, updateHash = true) {
    const target = document.getElementById(targetId);
    if (!target) return;
    tabs.forEach(tab => tab.classList.toggle('active', tab.dataset.target === targetId));
    sections.forEach(section => section.classList.toggle('profile-section-active', section.id === targetId));
    if (updateHash) history.replaceState(null, '', `#${targetId}`);
    requestAnimationFrame(() => window.dispatchEvent(new Event('resize')));
  }

  tabs.forEach(tab => tab.addEventListener('click', () => activateSection(tab.dataset.target)));
  document.querySelectorAll('.profile-jump[data-target]').forEach(button => {
    button.addEventListener('click', () => {
      activateSection(button.dataset.target);
      document.querySelector('.profile-tabs')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  const initialHash = window.location.hash.replace('#', '');
  if (sections.some(section => section.id === initialHash)) activateSection(initialHash, false);

  const dataNode = document.getElementById('athlete-profile-data');
  if (!dataNode || typeof Chart === 'undefined') return;

  let data = { temporadas: [], mejores_marcas: [] };
  try { data = JSON.parse(dataNode.textContent || '{}'); } catch (error) { console.warn('No fue posible leer los datos del perfil.', error); }

  const css = getComputedStyle(document.documentElement);
  const textColor = css.getPropertyValue('--app-muted').trim() || '#667085';
  const gridColor = css.getPropertyValue('--app-border').trim() || 'rgba(148,163,184,.22)';
  const accent = '#13b8ad';
  const accentDark = '#087d78';
  const purple = '#6d4aff';

  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.color = textColor;

  const seasons = [...(data.temporadas || [])].sort((a, b) => Number(a.anio) - Number(b.anio));
  const seasonLabels = seasons.map(item => String(item.anio));
  const seasonValues = seasons.map(item => Number(item.total) || 0);

  const activityCanvas = document.getElementById('seasonActivityChart');
  if (activityCanvas && seasons.length) {
    new Chart(activityCanvas, {
      type: 'bar',
      data: { labels: seasonLabels, datasets: [{ label: 'Tiempos registrados', data: seasonValues, borderRadius: 9, borderSkipped: false, backgroundColor: accent, hoverBackgroundColor: accentDark, maxBarThickness: 52 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { displayColors: false } }, scales: { x: { grid: { display: false }, border: { display: false } }, y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: gridColor }, border: { display: false } } } }
    });
  }

  const trendCanvas = document.getElementById('seasonTrendChart');
  if (trendCanvas && seasons.length) {
    const context = trendCanvas.getContext('2d');
    const gradient = context.createLinearGradient(0, 0, 0, 310);
    gradient.addColorStop(0, 'rgba(19,184,173,.32)');
    gradient.addColorStop(1, 'rgba(19,184,173,.015)');
    new Chart(trendCanvas, {
      type: 'line',
      data: { labels: seasonLabels, datasets: [{ label: 'Actividad', data: seasonValues, fill: true, backgroundColor: gradient, borderColor: accent, borderWidth: 3, pointBackgroundColor: '#fff', pointBorderColor: accentDark, pointBorderWidth: 3, pointRadius: 5, pointHoverRadius: 7, tension: .35 }] },
      options: { responsive: true, maintainAspectRatio: false, interaction: { intersect: false, mode: 'index' }, plugins: { legend: { display: false }, tooltip: { displayColors: false } }, scales: { x: { grid: { display: false }, border: { display: false } }, y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: gridColor }, border: { display: false } } } }
    });
  }

  const styles = ['Libre', 'Espalda', 'Pecho', 'Mariposa', 'Combinado'];
  const aliases = { 'libre': 'Libre', 'crol': 'Libre', 'espalda': 'Espalda', 'pecho': 'Pecho', 'braza': 'Pecho', 'mariposa': 'Mariposa', 'combinado': 'Combinado', 'medley': 'Combinado' };
  const styleCounts = Object.fromEntries(styles.map(style => [style, 0]));
  (data.mejores_marcas || []).forEach(record => {
    const raw = String(record.estilo || '').trim().toLowerCase();
    const style = aliases[raw] || styles.find(item => raw.includes(item.toLowerCase()));
    if (style) styleCounts[style] += 1;
  });

  const radarCanvas = document.getElementById('styleProfileChart');
  if (radarCanvas && Object.values(styleCounts).some(Boolean)) {
    new Chart(radarCanvas, {
      type: 'radar',
      data: { labels: styles, datasets: [{ label: 'Mejores marcas', data: styles.map(style => styleCounts[style]), backgroundColor: 'rgba(109,74,255,.15)', borderColor: purple, borderWidth: 2, pointBackgroundColor: accent, pointBorderColor: '#fff', pointBorderWidth: 2, pointRadius: 4 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { r: { beginAtZero: true, ticks: { display: false, precision: 0 }, grid: { color: gridColor }, angleLines: { color: gridColor }, pointLabels: { color: textColor, font: { size: 11, weight: '700' } } } } }
    });
  }
})();
