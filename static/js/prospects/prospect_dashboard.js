(function () {
    function parseJsonScript(id) {
        const el = document.getElementById(id);
        if (!el) {
            return {};
        }
        try {
            return JSON.parse(el.textContent || '{}');
        } catch (error) {
            console.error('Invalid JSON script for', id, error);
            return {};
        }
    }

    function truncateLabel(label, maxLength) {
        if (typeof label !== 'string') {
            return label;
        }
        if (label.length > maxLength) {
            return label.slice(0, maxLength - 3) + '...';
        }
        return label;
    }

    function getConfigCounts() {
        const config = document.getElementById('prospect-dashboard-config');
        if (!config) {
            return { onlineCount: 0, inPersonCount: 0 };
        }

        const onlineCount = parseInt(config.dataset.onlineCount || '0', 10);
        const inPersonCount = parseInt(config.dataset.inPersonCount || '0', 10);

        return {
            onlineCount: Number.isFinite(onlineCount) ? onlineCount : 0,
            inPersonCount: Number.isFinite(inPersonCount) ? inPersonCount : 0
        };
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (typeof window.Chart === 'undefined') {
            return;
        }

        const conversionsData = parseJsonScript('conversions-data');
        const coursesData = parseJsonScript('courses-data');
        const activitiesData = parseJsonScript('activities-data');
        const sourcesData = parseJsonScript('sources-data');
        const counts = getConfigCounts();

        const globalOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        font: { size: 12 },
                        padding: 15,
                        usePointStyle: true,
                        color: '#666'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: { size: 12, weight: 'bold' },
                    bodyFont: { size: 11 }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#666',
                        font: { size: 11 }
                    },
                    grid: { color: '#f0f0f0' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#666', font: { size: 10 } }
                }
            }
        };

        const conversionsChart = document.getElementById('conversionsChart');
        if (conversionsChart) {
            if (Object.values(conversionsData).some(function (value) { return value > 0; })) {
                new window.Chart(conversionsChart, {
                    type: 'line',
                    data: {
                        labels: Object.keys(conversionsData),
                        datasets: [{
                            label: 'Conversions',
                            data: Object.values(conversionsData),
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            borderWidth: 3,
                            fill: true,
                            pointRadius: 5,
                            pointBackgroundColor: '#10b981',
                            pointHoverRadius: 7,
                            tension: 0.4
                        }]
                    },
                    options: globalOptions
                });
            } else if (conversionsChart.parentElement) {
                conversionsChart.parentElement.innerHTML = '<p class="text-center text-gray-500 py-8">Aucune conversion enregistree sur les 12 derniers mois</p>';
            }
        }

        const modalityChart = document.getElementById('modalityChart');
        if (modalityChart) {
            new window.Chart(modalityChart, {
                type: 'doughnut',
                data: {
                    labels: ['En Ligne', 'Presentiel'],
                    datasets: [{
                        data: [counts.onlineCount, counts.inPersonCount],
                        backgroundColor: ['rgba(34, 197, 94, 0.8)', 'rgba(59, 130, 246, 0.8)'],
                        borderColor: ['rgb(34, 197, 94)', 'rgb(59, 130, 246)'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'bottom',
                            labels: {
                                font: { size: 12 },
                                padding: 15,
                                usePointStyle: true,
                                color: '#666'
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            titleFont: { size: 12, weight: 'bold' },
                            bodyFont: { size: 11 }
                        }
                    }
                }
            });
        }

        const coursesChart = document.getElementById('coursesChart');
        if (coursesChart) {
            const coursesNames = Object.keys(coursesData).slice(0, 10);
            const coursesValues = Object.values(coursesData).slice(0, 10);
            new window.Chart(coursesChart, {
                type: 'bar',
                data: {
                    labels: coursesNames,
                    datasets: [{
                        label: 'Demandes',
                        data: coursesValues,
                        backgroundColor: 'rgba(59, 130, 246, 0.7)',
                        borderColor: 'rgb(59, 130, 246)',
                        borderWidth: 2,
                        borderRadius: 6
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            callbacks: {
                                title: function (context) {
                                    return context[0].label;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            ticks: { color: '#666', font: { size: 11 } },
                            grid: { color: '#f0f0f0' }
                        },
                        y: {
                            ticks: {
                                color: '#666',
                                font: { size: 9 },
                                callback: function (value) {
                                    const label = this.getLabelForValue(value);
                                    return truncateLabel(label, 45);
                                }
                            },
                            grid: { display: false }
                        }
                    }
                }
            });
        }

        const activitiesChart = document.getElementById('activitiesChart');
        if (activitiesChart) {
            const activitiesNames = Object.keys(activitiesData).slice(0, 10);
            const activitiesValues = Object.values(activitiesData).slice(0, 10);
            new window.Chart(activitiesChart, {
                type: 'bar',
                data: {
                    labels: activitiesNames,
                    datasets: [{
                        label: 'Demandes',
                        data: activitiesValues,
                        backgroundColor: 'rgba(168, 85, 247, 0.7)',
                        borderColor: 'rgb(168, 85, 247)',
                        borderWidth: 2,
                        borderRadius: 6
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            callbacks: {
                                title: function (context) {
                                    return context[0].label;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            ticks: { color: '#666', font: { size: 11 } },
                            grid: { color: '#f0f0f0' }
                        },
                        y: {
                            ticks: {
                                color: '#666',
                                font: { size: 10 },
                                callback: function (value) {
                                    const label = this.getLabelForValue(value);
                                    return truncateLabel(label, 40);
                                }
                            },
                            grid: { display: false }
                        }
                    }
                }
            });
        }

        const sourcesChart = document.getElementById('sourcesChart');
        if (sourcesChart) {
            new window.Chart(sourcesChart, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(sourcesData),
                    datasets: [{
                        data: Object.values(sourcesData),
                        backgroundColor: [
                            'rgba(59, 130, 246, 0.8)',
                            'rgba(34, 197, 94, 0.8)',
                            'rgba(245, 158, 11, 0.8)',
                            'rgba(239, 68, 68, 0.8)',
                            'rgba(168, 85, 247, 0.8)',
                            'rgba(236, 72, 153, 0.8)',
                            'rgba(14, 165, 233, 0.8)',
                            'rgba(251, 146, 60, 0.8)'
                        ],
                        borderColor: 'white',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'bottom',
                            labels: {
                                font: { size: 12 },
                                padding: 15,
                                usePointStyle: true,
                                color: '#666'
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            titleFont: { size: 12, weight: 'bold' },
                            bodyFont: { size: 11 }
                        }
                    }
                }
            });
        }
    });
})();
