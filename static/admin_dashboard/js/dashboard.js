// static/admin_dashboard/js/dashboard.js

let charts = {};

function initializeDashboard(data) {
    // Initialize all charts
    initializeSparklines();
    initializeSalesChart();
    initializeOrderStatusChart();
    initializeRevenueCategoryChart();
    
    // Period selector
    const periodSelector = document.getElementById('periodSelector');
    if (periodSelector) {
        const urlParams = new URLSearchParams(window.location.search);
        const currentPeriod = urlParams.get('period') || 'last_30_days';
        periodSelector.value = currentPeriod;

        // When changed, reload the page with new period parameter
        periodSelector.addEventListener('change', function() {
            const selectedPeriod = this.value;
            window.location.href = `${window.location.pathname}?period=${selectedPeriod}`;
        });
    }
    
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
    const salesTrend = window.dashboardData?.salesTrend || [];
    const customerTrend = window.dashboardData?.customerTrend || [];
    const trendLabels = salesTrend.length ? buildTrendLabels(salesTrend) : [];
    const customerLabels = customerTrend.length ? buildTrendLabels(customerTrend) : [];

    const revenueSeries = salesTrend.map(item => Number(item.revenue) || 0);
    const ordersSeries = salesTrend.map(item => Number(item.orders) || 0);
    const avgOrderSeries = salesTrend.map(item => {
        const orders = Number(item.orders) || 0;
        const revenue = Number(item.revenue) || 0;
        return orders > 0 ? Math.round(revenue / orders) : 0;
    });
    const customerSeries = customerTrend.map(item => Number(item.count) || 0);

    const zeros = (length) => Array(length).fill(0);
    const salesLabels = trendLabels.length ? trendLabels : generateDateLabels(30);
    const salesLength = trendLabels.length || 30;
    const customerLength = customerTrend.length ? customerTrend.length : salesLength;
    const resolvedCustomerLabels = customerLabels.length ? customerLabels : salesLabels;

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
                labels: salesLabels,
                datasets: [{
                    data: revenueSeries.length ? revenueSeries : zeros(salesLength),
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
                labels: salesLabels,
                datasets: [{
                    data: ordersSeries.length ? ordersSeries : zeros(salesLength),
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
                labels: resolvedCustomerLabels,
                datasets: [{
                    data: customerSeries.length ? customerSeries : zeros(customerLength),
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
                labels: salesLabels,
                datasets: [{
                    data: avgOrderSeries.length ? avgOrderSeries : zeros(salesLength),
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
    const labels = buildTrendLabels(salesData);
    const revenueData = salesData.map(item => parseFloat(item.revenue) || 0);
    const ordersData = salesData.map(item => parseInt(item.orders) || 0);
    const fallbackLength = labels.length || 30;
    const fallbackLabels = labels.length ? labels : generateDateLabels(fallbackLength);
    const zeros = (length) => Array(length).fill(0);

    const gradient1 = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
    gradient1.addColorStop(0, 'rgba(102, 126, 234, 0.4)');
    gradient1.addColorStop(1, 'rgba(102, 126, 234, 0)');
    
    const gradient2 = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
    gradient2.addColorStop(0, 'rgba(118, 75, 162, 0.4)');
    gradient2.addColorStop(1, 'rgba(118, 75, 162, 0)');
    
    charts.salesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: fallbackLabels,
            datasets: [
                {
                    label: 'Revenue',
                    data: revenueData.length > 0 ? revenueData : zeros(fallbackLength),
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
                    data: ordersData.length > 0 ? ordersData : zeros(fallbackLength),
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
    const hasData = statusLabels.length > 0 && statusData.some(value => Number(value) > 0);
    
    charts.orderStatusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: hasData ? statusLabels : ['No data'],
            datasets: [{
                data: hasData ? statusData : [0],
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
    if (legendContainer && hasData) {
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
    const hasData = categoryValues.some(v => v > 0);
    const chartCard = ctx.closest('.chart-card');
    const cardBody = chartCard ? chartCard.querySelector('.card-body') : null;
    // Ensure the chart has a bounded height to avoid unbounded growth
    if (cardBody && !cardBody.style.height) {
        cardBody.style.height = '360px';
    }
    if (!ctx.style.height) {
        ctx.style.height = '280px';
    }
    if (!hasData && cardBody && !cardBody.querySelector('.no-revenue-data')) {
        cardBody.insertAdjacentHTML(
            'beforeend',
            '<p class="text-muted text-center no-revenue-data" style="margin-top:12px;">No revenue data for this period</p>'
        );
    }
    
    charts.revenueCategoryChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hasData ? categoryLabels : ['No data'],
            datasets: [{
                label: 'Revenue',
                data: hasData ? categoryValues : [0],
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
                            const val = Number(context.parsed.y || 0);
                            return '₹' + val.toLocaleString('en-IN', {maximumFractionDigits: 2});
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

// Three-dot actions (kebab menus)
function initializeChartMenus() {
    const buttons = document.querySelectorAll('.chart-card .btn-icon');
    buttons.forEach((btn) => {
        let menu = btn.parentElement.querySelector('.chart-menu');
        if (!menu) {
            menu = document.createElement('div');
            menu.className = 'chart-menu';
            menu.style.position = 'absolute';
            menu.style.top = '36px';
            menu.style.right = '8px';
            menu.style.background = '#fff';
            menu.style.border = '1px solid #e5e7eb';
            menu.style.borderRadius = '8px';
            menu.style.boxShadow = '0 10px 30px rgba(0,0,0,0.08)';
            menu.style.padding = '8px 0';
            menu.style.display = 'none';
            menu.style.zIndex = '10';
            menu.innerHTML = `
                <button class="chart-menu-item" data-action="refresh" style="display:block;width:100%;padding:8px 14px;background:none;border:none;text-align:left;font-size:13px;cursor:pointer;">Refresh</button>
                <button class="chart-menu-item" data-action="download" style="display:block;width:100%;padding:8px 14px;background:none;border:none;text-align:left;font-size:13px;cursor:pointer;">Download (CSV)</button>
            `;
            btn.parentElement.style.position = 'relative';
            btn.parentElement.appendChild(menu);
        }

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
        });

        menu.addEventListener('click', (e) => {
            e.stopPropagation();
            const action = e.target.dataset.action;
            if (action === 'refresh') {
                window.location.reload();
            }
            if (action === 'download') {
                // Placeholder hook for future export
                alert('Download coming soon.'); // ensure button visibly works
            }
            menu.style.display = 'none';
        });
    });

    document.addEventListener('click', () => {
        document.querySelectorAll('.chart-menu').forEach((menu) => {
            menu.style.display = 'none';
        });
    });
}

// Helper Functions
function buildTrendLabels(trend) {
    return trend.map(item => {
        const date = new Date(item.date);
        if (Number.isNaN(date.getTime())) {
            return '';
        }
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
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
    initializeChartMenus();
});