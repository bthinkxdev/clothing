// static/admin_dashboard/js/dashboard.js

let charts = {};

function initializeDashboard(data) {
    // Initialize all charts
    initializeSparklines();
    initializeSalesChart();
    initializeOrderStatusChart();
    initializeRevenueCategoryChart();
    
    // Period selector
    const urlParams = new URLSearchParams(window.location.search);
    const currentPeriod = urlParams.get('period') || 'last_30_days';
    periodSelector.value = currentPeriod;

    // When changed, reload the page with new period parameter
    periodSelector.addEventListener('change', function() {
        const selectedPeriod = this.value;
        window.location.href = `${window.location.pathname}?period=${selectedPeriod}`;
    });
    
    // Tab buttons
    const tabButtons = document.querySelectorAll('.btn-tab');
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            const period = this.dataset.period;
            updateSalesChart(period);
        });
    });
}

// Sparkline Charts
function initializeSparklines() {
    const sparklineConfig = {
        type: 'line',
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            },
            scales: {
                x: { display: false },
                y: { display: false }
            },
            elements: {
                line: {
                    borderWidth: 2,
                    tension: 0.4
                },
                point: { radius: 0 }
            }
        }
    };
    
    // Revenue Sparkline
    const revenueCtx = document.getElementById('revenueSparkline');
    if (revenueCtx) {
        charts.revenueSparkline = new Chart(revenueCtx, {
            ...sparklineConfig,
            data: {
                labels: Array(30).fill(''),
                datasets: [{
                    data: generateSparklineData(30, 5000, 15000),
                    borderColor: 'rgba(255, 255, 255, 0.8)',
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    fill: true
                }]
            }
        });
    }
    
    // Orders Sparkline
    const ordersCtx = document.getElementById('ordersSparkline');
    if (ordersCtx) {
        charts.ordersSparkline = new Chart(ordersCtx, {
            ...sparklineConfig,
            data: {
                labels: Array(30).fill(''),
                datasets: [{
                    data: generateSparklineData(30, 50, 150),
                    borderColor: 'rgba(255, 255, 255, 0.8)',
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    fill: true
                }]
            }
        });
    }
    
    // Customers Sparkline
    const customersCtx = document.getElementById('customersSparkline');
    if (customersCtx) {
        charts.customersSparkline = new Chart(customersCtx, {
            ...sparklineConfig,
            data: {
                labels: Array(30).fill(''),
                datasets: [{
                    data: generateSparklineData(30, 10, 50),
                    borderColor: 'rgba(255, 255, 255, 0.8)',
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    fill: true
                }]
            }
        });
    }
    
    // Avg Order Sparkline
    const avgOrderCtx = document.getElementById('avgOrderSparkline');
    if (avgOrderCtx) {
        charts.avgOrderSparkline = new Chart(avgOrderCtx, {
            ...sparklineConfig,
            data: {
                labels: Array(30).fill(''),
                datasets: [{
                    data: generateSparklineData(30, 800, 1500),
                    borderColor: 'rgba(255, 255, 255, 0.8)',
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    fill: true
                }]
            }
        });
    }
}

// Sales Overview Chart
function initializeSalesChart() {
    const ctx = document.getElementById('salesChart');
    if (!ctx) return;
    
    // Get real data from backend
    const salesData = window.dashboardData?.salesTrend || [];
    const labels = salesData.map(item => {
        const date = new Date(item.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const revenueData = salesData.map(item => parseFloat(item.revenue) || 0);
    const ordersData = salesData.map(item => parseInt(item.orders) || 0);

    const gradient1 = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
    gradient1.addColorStop(0, 'rgba(102, 126, 234, 0.4)');
    gradient1.addColorStop(1, 'rgba(102, 126, 234, 0)');
    
    const gradient2 = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
    gradient2.addColorStop(0, 'rgba(118, 75, 162, 0.4)');
    gradient2.addColorStop(1, 'rgba(118, 75, 162, 0)');
    
    charts.salesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels.length > 0 ? labels : generateDateLabels(30),
            datasets: [
                {
                    label: 'Revenue',
                    data: revenueData.length > 0 ? revenueData : generateSparklineData(30, 8000, 25000),
                    borderColor: '#667eea',
                    backgroundColor: gradient1,
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: '#667eea',
                    pointHoverBorderColor: '#fff',
                    pointHoverBorderWidth: 2
                },
                {
                    label: 'Orders',
                    data: ordersData.length > 0 ? ordersData : generateSparklineData(30, 50, 200),
                    borderColor: '#764ba2',
                    backgroundColor: gradient2,
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: '#764ba2',
                    pointHoverBorderColor: '#fff',
                    pointHoverBorderWidth: 2,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: {
                        boxWidth: 12,
                        boxHeight: 12,
                        borderRadius: 6,
                        useBorderRadius: true,
                        padding: 15,
                        font: {
                            size: 13,
                            weight: '500'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    padding: 12,
                    borderColor: '#334155',
                    borderWidth: 1,
                    titleFont: {
                        size: 13,
                        weight: '600'
                    },
                    bodyFont: {
                        size: 13
                    },
                    displayColors: true,
                    boxWidth: 10,
                    boxHeight: 10,
                    boxPadding: 6,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.datasetIndex === 0) {
                                label += '₹' + context.parsed.y.toLocaleString('en-IN');
                            } else {
                                label += context.parsed.y + ' orders';
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 12
                        },
                        color: '#64748b'
                    }
                },
                y: {
                    position: 'left',
                    grid: {
                        color: '#f1f5f9',
                        drawBorder: false
                    },
                    ticks: {
                        font: {
                            size: 12
                        },
                        color: '#64748b',
                        callback: function(value) {
                            return '₹' + (value / 1000) + 'k';
                        }
                    }
                },
                y1: {
                    position: 'right',
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 12
                        },
                        color: '#64748b'
                    }
                }
            }
        }
    });
}

// Order Status Doughnut Chart
function initializeOrderStatusChart() {
    const ctx = document.getElementById('orderStatusChart');
    if (!ctx) return;

    // Get real data from backend
    const orderStatus = window.dashboardData?.orderStatus || {};
    const statusLabels = Object.keys(orderStatus);
    const statusData = Object.values(orderStatus);
    
    charts.orderStatusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: statusLabels.length > 0 ? statusLabels : ['Delivered', 'Shipped', 'Processing', 'Cancelled'],
            datasets: [{
                data: statusData.length > 0 ? statusData : [52, 21, 14, 13],
                backgroundColor: [
                    '#667eea',
                    '#764ba2',
                    '#f59e0b',
                    '#ef4444'
                ],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    padding: 12,
                    borderColor: '#334155',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            return context.label + ': ' + context.parsed + '%';
                        }
                    }
                }
            }
        }
    });
    // Generate custom legend with real data
    const legendContainer = document.getElementById('orderStatusLegend');
    if (legendContainer && statusLabels.length > 0) {
        const total = statusData.reduce((a, b) => a + b, 0);
        const colors = ['#667eea', '#764ba2', '#f59e0b', '#ef4444', '#10b981', '#8b5cf6'];
        
        legendContainer.innerHTML = statusLabels.map((label, i) => {
            const value = statusData[i];
            const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
            const color = colors[i % colors.length];
            
            return `
                <div class="legend-item">
                    <span class="legend-dot" style="background: ${color};"></span>
                    <span class="legend-label">${label.charAt(0).toUpperCase() + label.slice(1)}</span>
                    <span class="legend-value">${percentage}%</span>
                </div>
            `;
        }).join('');
    }
}

// Revenue by Category Bar Chart
function initializeRevenueCategoryChart() {
    const ctx = document.getElementById('revenueCategoryChart');
    if (!ctx) return;

    // Get real data from backend
    const categoryData = window.dashboardData?.categoryRevenue || [];
    const categoryLabels = categoryData.map(item => item.variant__product__category__name || 'Unknown');
    const categoryValues = categoryData.map(item => parseFloat(item.revenue) || 0);
    
    charts.revenueCategoryChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: categoryLabels,
            datasets: [{
                label: 'Revenue',
                data: categoryValues,
                backgroundColor: [
                    'rgba(102, 126, 234, 0.8)',
                    'rgba(118, 75, 162, 0.8)',
                    'rgba(236, 72, 153, 0.8)',
                    'rgba(245, 158, 11, 0.8)',
                    'rgba(59, 130, 246, 0.8)',
                    'rgba(168, 85, 247, 0.8)'
                ],
                borderRadius: 8,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    padding: 12,
                    borderColor: '#334155',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            return '₹' + context.parsed.y.toLocaleString('en-IN');
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 12
                        },
                        color: '#64748b'
                    }
                },
                y: {
                    grid: {
                        color: '#f1f5f9',
                        drawBorder: false
                    },
                    ticks: {
                        font: {
                            size: 12
                        },
                        color: '#64748b',
                        callback: function(value) {
                            return '₹' + (value / 1000) + 'k';
                        }
                    }
                }
            }
        }
    });
}

// Helper Functions
function generateSparklineData(count, min, max) {
    const data = [];
    let prev = (min + max) / 2;
    
    for (let i = 0; i < count; i++) {
        const change = (Math.random() - 0.5) * (max - min) * 0.3;
        prev = Math.max(min, Math.min(max, prev + change));
        data.push(Math.round(prev));
    }
    
    return data;
}

function generateDateLabels(days) {
    const labels = [];
    const today = new Date();
    
    for (let i = days - 1; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    }
    
    return labels;
}

function updateSalesChart(days) {
    if (!charts.salesChart) return;
    
    // had some hardcoded datas that affected the chart, is removed and replaced with dynamic code
    
    // Fetch real data from API
    fetch(`/dashboard/api/sales-chart/?days=${days}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                charts.salesChart.data.labels = data.data.labels;
                charts.salesChart.data.datasets[0].data = data.data.datasets[0].data;
                charts.salesChart.data.datasets[1].data = data.data.datasets[1].data;
                charts.salesChart.update('active');
            }
        })
        .catch(error => {
            console.error('Error fetching sales chart data:', error);
        });
}

// broken functions removed

// Fixed the initialization
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});