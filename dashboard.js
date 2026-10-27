(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {
        if (typeof Chart === "undefined") {
            console.error("Chart.js no está disponible.");
            return;
        }

        const g = window.dashboardData || {};
        const dark = document.documentElement.dataset.theme === "dark";
        const text = dark ? "#a9b8ba" : "#728184";
        const textStrong = dark ? "#eef6f6" : "#314547";
        const grid = dark
            ? "rgba(255,255,255,.07)"
            : "rgba(30,70,72,.08)";
        const accent = "#009b9d";

        Chart.defaults.font.family = "Inter, sans-serif";
        Chart.defaults.color = text;

        const baseOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 850,
                easing: "easeOutQuart"
            },
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: text
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: grid
                    },
                    ticks: {
                        color: text,
                        precision: 0
                    }
                }
            }
        };

        const chartMeses = document.getElementById("chartMeses");
        if (chartMeses) {
            new Chart(chartMeses, {
                type: "line",
                data: {
                    labels: g.meses?.labels || [],
                    datasets: [{
                        label: "Tiempos registrados",
                        data: (g.meses?.values || []).map(Number),
                        borderColor: accent,
                        backgroundColor: "rgba(0,155,157,.12)",
                        borderWidth: 3,
                        fill: true,
                        tension: 0.38,
                        pointRadius: 3,
                        pointHoverRadius: 6,
                        pointBackgroundColor: "#ffffff",
                        pointBorderColor: accent,
                        pointBorderWidth: 2
                    }]
                },
                options: {
                    ...baseOptions,
                    interaction: {
                        mode: "index",
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return `${Number(context.raw || 0).toLocaleString("es-CL")} tiempos`;
                                }
                            }
                        }
                    }
                }
            });
        }

        const chartActividad = document.getElementById("chartActividad");
        if (chartActividad) {
            new Chart(chartActividad, {
                type: "doughnut",
                data: {
                    labels: g.actividad?.labels || [],
                    datasets: [{
                        data: (g.actividad?.values || []).map(Number),
                        backgroundColor: ["#00a8aa", "#d5e0e1"],
                        borderWidth: 0,
                        hoverOffset: 5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "73%",
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return `${context.label}: ${Number(context.raw || 0).toLocaleString("es-CL")}`;
                                }
                            }
                        }
                    }
                }
            });
        }

        const chartEstilos = document.getElementById("chartEstilos");
        if (chartEstilos) {
            new Chart(chartEstilos, {
                type: "bar",
                data: {
                    labels: g.estilos?.labels || [],
                    datasets: [{
                        label: "Registros",
                        data: (g.estilos?.values || []).map(Number),
                        backgroundColor: [
                            "#009b9d",
                            "#2878c7",
                            "#e0a72f",
                            "#79519c",
                            "#16875a",
                            "#7d8b8d"
                        ],
                        borderRadius: 9,
                        borderSkipped: false,
                        maxBarThickness: 52
                    }]
                },
                options: {
                    ...baseOptions,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return `${Number(context.raw || 0).toLocaleString("es-CL")} registros`;
                                }
                            }
                        }
                    }
                }
            });
        }

        const topLabels = (g.top_nadadores?.labels || []).map(function (value) {
            return String(value || "Sin nombre");
        });
        const topValues = (g.top_nadadores?.values || []).map(function (value) {
            return Number(value) || 0;
        });
        const chartTop = document.getElementById("chartTop");

        if (chartTop) {
            new Chart(chartTop, {
                type: "bar",
                data: {
                    labels: topLabels,
                    datasets: [{
                        label: "Tiempos registrados",
                        data: topValues,
                        backgroundColor: topValues.map(function (_, index) {
                            if (index === 0) return "#d4a017";
                            if (index === 1) return "#9aa5a8";
                            if (index === 2) return "#b87333";
                            return "rgba(0,155,157,.86)";
                        }),
                        hoverBackgroundColor: topValues.map(function (_, index) {
                            if (index === 0) return "#e1ad16";
                            if (index === 1) return "#aeb8bb";
                            if (index === 2) return "#ca8144";
                            return "#007f81";
                        }),
                        borderRadius: 9,
                        borderSkipped: false,
                        barThickness: 24,
                        maxBarThickness: 29
                    }]
                },
                options: {
                    indexAxis: "y",
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 850,
                        easing: "easeOutQuart"
                    },
                    interaction: {
                        mode: "nearest",
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    const value = Number(context.raw || 0);
                                    return `${value} ${value === 1 ? "tiempo" : "tiempos"} registrados`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            suggestedMax: Math.max(...topValues, 1),
                            grid: {
                                color: grid
                            },
                            ticks: {
                                color: text,
                                precision: 0
                            },
                            title: {
                                display: true,
                                text: "Cantidad de tiempos",
                                color: text
                            }
                        },
                        y: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: text,
                                autoSkip: false,
                                font: {
                                    size: 11,
                                    weight: "600"
                                },
                                callback: function (value) {
                                    const label = this.getLabelForValue(value);
                                    return label.length > 24
                                        ? `${label.slice(0, 24)}…`
                                        : label;
                                }
                            }
                        }
                    }
                }
            });
        }

        const seasonLabels = (g.temporadas?.labels || []).map(String);
        const seasonValues = (g.temporadas?.values || []).map(function (value) {
            return Number(value) || 0;
        });
        const chartTemporadas = document.getElementById("chartTemporadas");
        const variationElement = document.getElementById("variacionTemporadas");
        const summaryElement = document.getElementById("resumenTemporadas");

        if (seasonValues.length >= 2) {
            const previous = seasonValues[seasonValues.length - 2];
            const current = seasonValues[seasonValues.length - 1];

            if (previous > 0) {
                const variation = ((current - previous) / previous) * 100;

                if (variationElement) {
                    variationElement.textContent = `${variation >= 0 ? "+" : ""}${variation.toFixed(1)}%`;
                    variationElement.style.color = variation >= 0
                        ? "#16875a"
                        : "#c84343";
                }
            }

            if (summaryElement) {
                summaryElement.textContent = `${current.toLocaleString("es-CL")} tiempos en ${seasonLabels[seasonLabels.length - 1]}`;
            }
        }

        const seasonLabelsPlugin = {
            id: "seasonLabelsPlugin",
            afterDatasetsDraw: function (chart) {
                const meta = chart.getDatasetMeta(0);
                const ctx = chart.ctx;

                ctx.save();
                ctx.font = "700 12px Inter, sans-serif";
                ctx.textAlign = "center";
                ctx.fillStyle = textStrong;

                meta.data.forEach(function (bar, index) {
                    const value = seasonValues[index] || 0;
                    ctx.fillText(
                        value.toLocaleString("es-CL"),
                        bar.x,
                        bar.y - 11
                    );
                });

                ctx.restore();
            }
        };

        if (chartTemporadas) {
            const maximum = seasonValues.length
                ? Math.max(...seasonValues)
                : 0;

            new Chart(chartTemporadas, {
                type: "bar",
                data: {
                    labels: seasonLabels,
                    datasets: [
                        {
                            type: "bar",
                            label: "Tiempos registrados",
                            data: seasonValues,
                            backgroundColor: function (context) {
                                const chart = context.chart;
                                const area = chart.chartArea;

                                if (!area) {
                                    return accent;
                                }

                                const gradient = chart.ctx.createLinearGradient(
                                    0,
                                    area.top,
                                    0,
                                    area.bottom
                                );
                                gradient.addColorStop(0, "#00b7b9");
                                gradient.addColorStop(1, "#007f81");
                                return gradient;
                            },
                            borderRadius: 12,
                            borderSkipped: false,
                            barPercentage: 0.58,
                            categoryPercentage: 0.62,
                            maxBarThickness: 120
                        },
                        {
                            type: "line",
                            label: "Tendencia",
                            data: seasonValues,
                            borderColor: "#e0a72f",
                            backgroundColor: "#e0a72f",
                            borderWidth: 3,
                            pointRadius: 5,
                            pointHoverRadius: 7,
                            pointBackgroundColor: "#ffffff",
                            pointBorderColor: "#e0a72f",
                            pointBorderWidth: 3,
                            tension: 0.28,
                            fill: false
                        }
                    ]
                },
                plugins: [seasonLabelsPlugin],
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: "index",
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: "bottom",
                            labels: {
                                usePointStyle: true,
                                boxWidth: 8,
                                padding: 18,
                                color: text,
                                font: {
                                    size: 11,
                                    weight: "600"
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return `${context.dataset.label}: ${Number(context.raw || 0).toLocaleString("es-CL")}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            offset: true,
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: text,
                                font: {
                                    size: 11,
                                    weight: "700"
                                }
                            }
                        },
                        y: {
                            beginAtZero: true,
                            suggestedMax: maximum ? maximum * 1.18 : 10,
                            grid: {
                                color: grid
                            },
                            ticks: {
                                color: text,
                                precision: 0,
                                callback: function (value) {
                                    return Number(value).toLocaleString("es-CL");
                                }
                            }
                        }
                    },
                    animation: {
                        duration: 950,
                        easing: "easeOutQuart"
                    }
                }
            });
        }

        document.querySelectorAll("[data-count]").forEach(function (element) {
            const target = Number(element.dataset.count || 0);
            if (!Number.isFinite(target) || target <= 0) return;

            const duration = 650;
            const start = performance.now();

            function animate(now) {
                const progress = Math.min((now - start) / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                element.textContent = Math.round(target * eased).toLocaleString("es-CL");

                if (progress < 1) {
                    requestAnimationFrame(animate);
                }
            }

            requestAnimationFrame(animate);
        });
    });
})();
