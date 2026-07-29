(() => {
  const form = document.getElementById('compareForm');
  if (form) {
    form.addEventListener('submit', (event) => {
      const a = document.getElementById('athleteA').value;
      const b = document.getElementById('athleteB').value;
      const error = document.getElementById('compareError');
      if (!a || !b || a === b) {
        event.preventDefault();
        error.hidden = false;
      } else {
        error.hidden = true;
      }
    });
  }

  const dataNode = document.getElementById('coachChartData');
  const canvas = document.getElementById('coachRadar');
  if (!dataNode || !canvas || typeof Chart === 'undefined') return;
  const data = JSON.parse(dataNode.textContent);
  const styles = getComputedStyle(document.documentElement);
  const textColor = styles.getPropertyValue('--text-color').trim() || '#52616b';
  new Chart(canvas, {
    type: 'radar',
    data: {
      labels: data.labels,
      datasets: [
        { label: 'Nadador A', data: data.a, borderColor: '#16a9a2', backgroundColor: 'rgba(22,169,162,.18)', pointBackgroundColor: '#16a9a2', borderWidth: 2 },
        { label: 'Nadador B', data: data.b, borderColor: '#8e44ad', backgroundColor: 'rgba(142,68,173,.14)', pointBackgroundColor: '#8e44ad', borderWidth: 2 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { r: { beginAtZero: true, max: 100, ticks: { display: false }, grid: { color: 'rgba(120,140,150,.18)' }, angleLines: { color: 'rgba(120,140,150,.18)' }, pointLabels: { color: textColor, font: { weight: 700 } } } },
      plugins: { legend: { labels: { color: textColor, usePointStyle: true } } }
    }
  });
})();
