// static/admin_dashboard/js/revenue-analytics.js

let revenueCharts = {};

function initializeRevenueAnalytics() {
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js is required for revenue analytics.');
        return;
    }

    const periodSelector = document.getElementById('revenuePeriod');
    const urlParams = new URLSearchParams(window.location.search);
    const initialPeriod = urlParams.get('period') || (periodSelector ? periodSelector.value : 'last_30_days');

    if (periodSelector) {
        periodSelector.value = initialPeriod;
        periodSelector.addEventListener('change', function () {
            const nextPeriod = this.value || 'last_30_days';
            const params = new URLSearchParams(window.location.search);
            params.set('period', nextPeriod);
            window.location.href = `${window.location.pathname}?${params.toString()}`;
        });
    }

    bindBreakdownTabs(initialPeriod);
    loadRevenueAnalytics(initialPeriod);
}

function bindBreakdownTabs(currentPeriod) {
    const tabButtons = document.querySelectorAll('.card-tabs .tab-btn');
    if (!tabButtons.length) return;

    tabButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            tabButtons.forEach((other) => other.classList.remove('active'));
            btn.classList.add('active');

            const days = Number(btn.dataset.period) || mapPeriodToDays(currentPeriod);
            loadRevenueAnalytics(currentPeriod, days);
        });
    });
}

async function loadRevenueAnalytics(period = 'last_30_days', daysOverride) {
    const days = daysOverride || mapPeriodToDays(period);

    try {
        const [trend, categoryData] = await Promise.all([
            fetchSalesTrend(days),
            fetchRevenueByCategory(period)
        ]);

        renderSparkline('grossRevenueSparkline', trend.labels, trend.revenue);
        renderSparkline('netRevenueSparkline', trend.labels, trend.revenue.map((v) => Math.max(0, v * 0.92)));
        renderSparkline('profitMarginSparkline', trend.labels, buildMarginSeries(trend.revenue));

        renderRevenueBreakdownChart(trend);
        renderCategoryChart(categoryData);
        renderProfitabilityChart(trend);
    } catch (error) {
        console.error('Failed to load revenue analytics data', error);
    }
}

async function fetchSalesTrend(days) {
    const fallbackLabels = generateDateLabels(days);
    const zeros = (count) => Array(count).fill(0);

    try {
        const response = await fetch(`/dashboard/api/sales-chart/?days=${days}`);
        const payload = await response.json();

        if (!payload?.success || !payload.data) {
            return { labels: fallbackLabels, revenue: zeros(days), orders: zeros(days) };
        }

        const labels = (payload.data.labels || fallbackLabels).map(formatDateLabel);

        const revenueDs = (payload.data.datasets || []).find((ds) => (ds.label || '').toLowerCase().includes('revenue')) || payload.data.datasets?.[0];
        const ordersDs = (payload.data.datasets || []).find((ds) => (ds.label || '').toLowerCase().includes('order')) || payload.data.datasets?.[1];

        const revenue = Array.isArray(revenueDs?.data) ? revenueDs.data.map((v) => Number(v) || 0) : zeros(labels.length);
        const orders = Array.isArray(ordersDs?.data) ? ordersDs.data.map((v) => Number(v) || 0) : zeros(labels.length);

        return { labels, revenue, orders };
    } catch (error) {
        console.warn('Using fallback sales trend because of an error', error);
        return { labels: fallbackLabels, revenue: zeros(days), orders: zeros(days) };
    }
}

async function fetchRevenueByCategory(period) {
    try {
        const response = await fetch(`/dashboard/api/revenue-chart/?period=${period}`);
        const payload = await response.json();

        const labels = payload?.data?.labels || [];
        const values = payload?.data?.datasets?.[0]?.data || [];

        if (!labels.length || !values.length) {
            return { labels: ['No data'], values: [0] };
        }

        return {
            labels,
            values: values.map((v) => Number(v) || 0)
        };
    } catch (error) {
        console.warn('Using fallback category revenue because of an error', error);
        return { labels: ['No data'], values: [0] };
    }
}

function renderSparkline(elementId, labels, data) {
    const canvas = document.getElementById(elementId);
    if (!canvas) return;

    destroyChart(elementId);
    const zeros = (count) => Array(count).fill(0);
    const resolvedLabels = labels && labels.length ? labels : generateDateLabels(Math.max(data.length, 14));
    const resolvedData = data && data.length ? data : zeros(resolvedLabels.length);

    revenueCharts[elementId] = new Chart(canvas, {
        type: 'line',
        data: {
            labels: resolvedLabels,
            datasets: [{
                data: resolvedData,
                borderColor: 'rgba(255, 255, 255, 0.85)',
                backgroundColor: 'rgba(255, 255, 255, 0.12)',
                tension: 0.4,
                borderWidth: 2,
                pointRadius: 0,
                fill: true
            }]
        },
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
            }
        }
    });
}

function renderRevenueBreakdownChart(trend) {
    const canvas = document.getElementById('revenueBreakdownChart');
    if (!canvas) return;

    destroyChart('revenueBreakdownChart');

    const labels = trend.labels && trend.labels.length ? trend.labels : generateDateLabels(30);
    const revenue = trend.revenue && trend.revenue.length ? trend.revenue : Array(labels.length).fill(0);
    const orders = trend.orders && trend.orders.length ? trend.orders : Array(labels.length).fill(0);

    const ctx = canvas.getContext('2d');
    const revenueGradient = ctx.createLinearGradient(0, 0, 0, 280);
    revenueGradient.addColorStop(0, 'rgba(99, 102, 241, 0.35)');
    revenueGradient.addColorStop(1, 'rgba(99, 102, 241, 0)');

    revenueCharts.revenueBreakdownChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Revenue',
                    data: revenue,
                    borderColor: '#6366f1',
                    backgroundColor: revenueGradient,
                    tension: 0.4,
                    borderWidth: 3,
                    pointRadius: 0,
                    fill: true
                },
                {
                    label: 'Orders',
                    data: orders,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.12)',
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    align: 'end'
                },
                tooltip: {
                    backgroundColor: '#0f172a',
                    borderColor: '#1f2937',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label(context) {
                            if (context.dataset.label === 'Revenue') {
                                return `Revenue: ₹${(context.parsed.y || 0).toLocaleString('en-IN')}`;
                            }
                            return `Orders: ${context.parsed.y || 0}`;
                        }
                    }
                }
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    grid: { color: '#f3f4f6', drawBorder: false },
                    ticks: {
                        callback: (value) => `₹${(value / 1000).toFixed(0)}k`
                    }
                }
            }
        }
    });
}

function renderCategoryChart(categoryData) {
    const canvas = document.getElementById('categoryRevenueChart');
    if (!canvas) return;

    destroyChart('categoryRevenueChart');

    const labels = categoryData.labels || [];
    const values = categoryData.values || [];
    const hasData = values.some((v) => v > 0);

    revenueCharts.categoryRevenueChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: hasData ? labels : ['No data'],
            datasets: [{
                label: 'Revenue',
                data: hasData ? values : [0],
                backgroundColor: labels.map((_, i) => paletteColor(i, 0.8)),
                borderRadius: 10,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#0f172a',
                    borderColor: '#1f2937',
                    borderWidth: 1,
                    callbacks: {
                        label(context) {
                            return `₹${(context.parsed.y || 0).toLocaleString('en-IN')}`;
                        }
                    }
                }
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    grid: { color: '#f3f4f6', drawBorder: false },
                    ticks: {
                        callback: (value) => `₹${(value / 1000).toFixed(0)}k`
                    }
                }
            }
        }
    });
}

function renderProfitabilityChart(trend) {
    const canvas = document.getElementById('profitabilityChart');
    if (!canvas) return;

    destroyChart('profitabilityChart');

    const labels = trend.labels && trend.labels.length ? trend.labels : generateDateLabels(30);
    const revenue = trend.revenue && trend.revenue.length ? trend.revenue : Array(labels.length).fill(0);

    const estimatedCosts = revenue.map((value) => Math.max(0, value * 0.65));
    const profit = revenue.map((value, idx) => Math.max(0, value - estimatedCosts[idx]));

    revenueCharts.profitabilityChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Revenue',
                    data: revenue,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    borderWidth: 3,
                    tension: 0.35,
                    pointRadius: 0,
                    fill: true
                },
                {
                    label: 'Estimated Costs',
                    data: estimatedCosts,
                    borderColor: '#f97316',
                    backgroundColor: 'rgba(249, 115, 22, 0.1)',
                    borderWidth: 2,
                    tension: 0.35,
                    pointRadius: 0,
                    fill: true
                },
                {
                    label: 'Estimated Profit',
                    data: profit,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    tension: 0.35,
                    pointRadius: 0,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: true, position: 'top', align: 'end' },
                tooltip: {
                    backgroundColor: '#0f172a',
                    borderColor: '#1f2937',
                    borderWidth: 1,
                    callbacks: {
                        label(context) {
                            return `${context.dataset.label}: ₹${(context.parsed.y || 0).toLocaleString('en-IN')}`;
                        }
                    }
                }
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    grid: { color: '#f3f4f6', drawBorder: false },
                    ticks: {
                        callback: (value) => `₹${(value / 1000).toFixed(0)}k`
                    }
                }
            }
        }
    });
}

function buildMarginSeries(revenueSeries) {
    if (!revenueSeries || !revenueSeries.length) return [];

    const baseMargin = 0.32;
    const variation = 0.06;
    const maxMargin = 0.6;
    const minMargin = 0.12;

    return revenueSeries.map((value, index) => {
        const normalized = revenueSeries.length > 1 ? (index / (revenueSeries.length - 1)) - 0.5 : 0;
        const adjusted = baseMargin + normalized * variation;
        const clamped = Math.max(minMargin, Math.min(maxMargin, adjusted));
        return Math.round(clamped * 100);
    });
}

function mapPeriodToDays(period) {
    const lookup = {
        today: 1,
        yesterday: 1,
        last_7_days: 7,
        last_30_days: 30,
        last_90_days: 90,
        this_year: 365
    };
    return lookup[period] || 30;
}

function generateDateLabels(days) {
    const labels = [];
    const today = new Date();
    for (let i = days - 1; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        labels.push(d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    }
    return labels;
}

function formatDateLabel(value) {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return String(value || '');
    return parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function paletteColor(index, alpha = 1) {
    const colors = [
        [99, 102, 241],
        [139, 92, 246],
        [236, 72, 153],
        [16, 185, 129],
        [59, 130, 246],
        [249, 115, 22],
        [34, 197, 94],
        [6, 182, 212],
        [234, 179, 8],
        [239, 68, 68]
    ];
    const [r, g, b] = colors[index % colors.length];
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function destroyChart(key) {
    if (revenueCharts[key]) {
        revenueCharts[key].destroy();
        delete revenueCharts[key];
    }
}


