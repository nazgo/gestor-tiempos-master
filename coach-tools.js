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
        error.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else {
        error.hidden = true;
      }
    });
  }

  document.querySelectorAll('[data-coach-tab]').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('[data-coach-tab]').forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
      const target = document.getElementById(button.dataset.coachTab);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  const dataNode = document.getElementById('coachChartData');
  const namesNode = document.getElementById('coachNames');
  const canvas = document.getElementById('coachRadar');
  if (!dataNode || !canvas || typeof Chart === 'undefined') return;

  const data = JSON.parse(dataNode.textContent);
  const names = namesNode ? JSON.parse(namesNode.textContent) : { a: 'Nadador A', b: 'Nadador B' };
  const mobileQuery = window.matchMedia('(max-width: 600px)');
  let chart;

  const drawChart = () => {
    const isMobile = mobileQuery.matches;
    const styles = getComputedStyle(document.documentElement);
    const textColor = styles.getPropertyValue('--text-color').trim() || styles.getPropertyValue('--text-primary').trim() || '#52616b';
    if (chart) chart.destroy();
    chart = new Chart(canvas, {
      type: 'radar',
      data: {
        labels: data.labels,
        datasets: [
          { label: names.a, data: data.a, borderColor: '#08979c', backgroundColor: 'rgba(8,151,156,.17)', pointBackgroundColor: '#08979c', pointBorderColor: '#fff', pointBorderWidth: 2, borderWidth: 2.5, pointRadius: isMobile ? 2.5 : 4 },
          { label: names.b, data: data.b, borderColor: '#1671d9', backgroundColor: 'rgba(22,113,217,.13)', pointBackgroundColor: '#1671d9', pointBorderColor: '#fff', pointBorderWidth: 2, borderWidth: 2.5, pointRadius: isMobile ? 2.5 : 4 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 700, easing: 'easeOutQuart' },
        layout: { padding: isMobile ? 2 : 10 },
        scales: { r: { beginAtZero: true, max: 100, ticks: { display: false }, grid: { color: 'rgba(120,140,150,.18)' }, angleLines: { color: 'rgba(120,140,150,.18)' }, pointLabels: { color: textColor, padding: isMobile ? 7 : 11, font: { size: isMobile ? 9 : 11, weight: 700 } } } },
        plugins: { legend: { position: 'bottom', labels: { color: textColor, usePointStyle: true, boxWidth: 9, padding: isMobile ? 9 : 15, font: { size: isMobile ? 9 : 11 } } }, tooltip: { backgroundColor: 'rgba(9,31,43,.94)', padding: 10, usePointStyle: true } }
      }
    });
  };

  drawChart();
  if (mobileQuery.addEventListener) mobileQuery.addEventListener('change', drawChart);
  else mobileQuery.addListener(drawChart);
})();
