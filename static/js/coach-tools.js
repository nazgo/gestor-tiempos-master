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

  const dataNode = document.getElementById('coachChartData');
  const canvas = document.getElementById('coachRadar');
  if (!dataNode || !canvas || typeof Chart === 'undefined') return;

  const data = JSON.parse(dataNode.textContent);
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
          { label: 'Nadador A', data: data.a, borderColor: '#16a9a2', backgroundColor: 'rgba(22,169,162,.18)', pointBackgroundColor: '#16a9a2', borderWidth: 2, pointRadius: isMobile ? 2 : 3 },
          { label: 'Nadador B', data: data.b, borderColor: '#8e44ad', backgroundColor: 'rgba(142,68,173,.14)', pointBackgroundColor: '#8e44ad', borderWidth: 2, pointRadius: isMobile ? 2 : 3 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: isMobile ? 4 : 12 },
        scales: {
          r: {
            beginAtZero: true,
            max: 100,
            ticks: { display: false },
            grid: { color: 'rgba(120,140,150,.18)' },
            angleLines: { color: 'rgba(120,140,150,.18)' },
            pointLabels: { color: textColor, padding: isMobile ? 8 : 12, font: { size: isMobile ? 9 : 12, weight: 700 } }
          }
        },
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: textColor, usePointStyle: true, boxWidth: isMobile ? 8 : 12, padding: isMobile ? 10 : 16, font: { size: isMobile ? 10 : 12 } }
          }
        }
      }
    });
  };

  drawChart();
  if (mobileQuery.addEventListener) mobileQuery.addEventListener('change', drawChart);
  else mobileQuery.addListener(drawChart);
})();
