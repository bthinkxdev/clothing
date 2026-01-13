let analyticsCharts = {};
const ANALYTICS_API_BASE = '/dashboard/api';

function initializeAnalytics() {
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js is required for analytics dashboard.');
        return;
    }

    const periodSelector = document.getElementById('analyticsPeriod');
    const urlParams = new URLSearchParams(window.location.search);
    const initialPeriod = urlParams.get('period') || (periodSelector ? periodSelector.value : 'last_30_days');

    if (periodSelector) {
        periodSelector.value = initialPeriod;
        periodSelector.addEventListener('change', function () {
            const params = new URLSearchParams(window.location.search);
            params.set('period', this.value || 'last_30_days');
            window.location.href = `${window.location.pathname}?${params.toString()}`;
        });
    }

    const exportBtn = document.querySelector('.header-actions .btn-primary');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            const params = new URLSearchParams(window.location.search);
            params.set('period', periodSelector ? periodSelector.value : initialPeriod);
            params.set('format', 'csv');
            window.location.href = `/dashboard/sales-report/export/?${params.toString()}`;
        });
    }

    const tabButtons = document.querySelectorAll('.card-tabs .tab-btn');
    const activeTab = document.querySelector('.card-tabs .tab-btn.active') || tabButtons[0];
    const activeResolution = activeTab ? activeTab.dataset.tab || 'daily' : 'daily';

    bindTrendTabs(tabButtons, initialPeriod);
    loadAnalyticsData(initialPeriod, activeResolution);
}

function bindTrendTabs(tabButtons, period) {
    if (!tabButtons || !tabButtons.length) return;

    tabButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            tabButtons.forEach((other) => other.classList.remove('active'));
            btn.classList.add('active');

            const resolution = btn.dataset.tab || 'daily';
            loadAnalyticsData(period, resolution);
        });
    });
}

async function loadAnalyticsData(period = 'last_30_days', resolution = 'daily') {
    const days = mapResolutionToDays(resolution, period);

    try {
        const [trend, products] = await Promise.all([
            fetchSalesTrend(days),
            fetchProductPerformance(period)
        ]);

        const aggregatedTrend = aggregateTrendData(trend, resolution, days);

        renderRevenueTrendChart(aggregatedTrend);
        renderTrafficSourcesChart(extractTrafficSourcesFromDom());
        renderDemographicsChart();
        renderProductPerformanceChart(products, period);
    } catch (error) {
        console.error('Failed to load analytics data', error);
        const fallbackTrend = buildFallbackTrend(days);
        renderRevenueTrendChart(aggregateTrendData(fallbackTrend, resolution, days));
        renderTrafficSourcesChart(extractTrafficSourcesFromDom());
        renderDemographicsChart();
        renderProductPerformanceChart([], period);
    }
}

async function fetchSalesTrend(days) {
    const fallback = buildFallbackTrend(days);

    try {
        const response = await fetch(`${ANALYTICS_API_BASE}/sales-chart/?days=${days}`);
        const payload = await response.json();

        if (!payload?.success || !payload.data) {
            return fallback;
        }

        const labels = (payload.data.labels || []).map(formatDateLabel);
        const revenueDs = (payload.data.datasets || []).find((ds) => (ds.label || '').toLowerCase().includes('revenue')) || payload.data.datasets?.[0];
        const ordersDs = (payload.data.datasets || []).find((ds) => (ds.label || '').toLowerCase().includes('order')) || payload.data.datasets?.[1];

        const revenue = Array.isArray(revenueDs?.data) ? revenueDs.data.map(safeNumber) : [];
        const orders = Array.isArray(ordersDs?.data) ? ordersDs.data.map(safeNumber) : [];

        if (!labels.length || !revenue.length) {
            return fallback;
        }

        return { labels, revenue, orders };
    } catch (error) {
        console.warn('Using fallback sales trend because of an error', error);
        return fallback;
    }
}

async function fetchProductPerformance(period) {
    try {
        const response = await fetch(`${ANALYTICS_API_BASE}/product-performance/?period=${period}`);
        const payload = await response.json();

        if (!payload?.success || !Array.isArray(payload.data)) {
            return [];
        }

        return payload.data;
    } catch (error) {
        console.warn('Using empty product performance because of an error', error);
        return [];
    }
}

function aggregateTrendData(trend, resolution, fallbackDays) {
    const items = (trend.labels || []).map((label, idx) => ({
        date: parseDate(label),
        revenue: safeNumber(trend.revenue?.[idx]),
        orders: safeNumber(trend.orders?.[idx])
    })).filter((item) => !isNaN(item.date));

    if (!items.length) {
        const days = typeof fallbackDays === 'number'
            ? fallbackDays
            : mapResolutionToDays(resolution, 'last_30_days');
        return buildFallbackTrend(days);
    }

    const buckets = {};

    items.forEach((item) => {
        const key = buildBucketKey(item.date, resolution);
        const existing = buckets[key] || { revenue: 0, orders: 0, date: item.date };
        existing.revenue += item.revenue;
        existing.orders += item.orders;
        if (item.date < existing.date) {
            existing.date = item.date;
        }
        buckets[key] = existing;
    });

    const sortedKeys = Object.keys(buckets).sort((a, b) => new Date(a) - new Date(b));

    return {
        labels: sortedKeys.map((key) => formatBucketLabel(buckets[key].date, resolution)),
        revenue: sortedKeys.map((key) => buckets[key].revenue),
        orders: sortedKeys.map((key) => buckets[key].orders)
    };
}

function renderRevenueTrendChart(trend) {
    const canvas = document.getElementById('revenueTrendChart');
    if (!canvas) return;

    destroyChart('revenueTrendChart');

    const labels = trend.labels && trend.labels.length ? trend.labels : generateDateLabels(30);
    const revenue = trend.revenue && trend.revenue.length ? trend.revenue : Array(labels.length).fill(0);
    const orders = trend.orders && trend.orders.length ? trend.orders : Array(labels.length).fill(0);

    const ctx = canvas.getContext('2d');
    const revenueGradient = ctx.createLinearGradient(0, 0, 0, 280);
    revenueGradient.addColorStop(0, 'rgba(102, 126, 234, 0.35)');
    revenueGradient.addColorStop(1, 'rgba(102, 126, 234, 0)');

    analyticsCharts.revenueTrendChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Revenue',
                    data: revenue,
                    borderColor: '#667eea',
                    backgroundColor: revenueGradient,
                    tension: 0.35,
                    borderWidth: 3,
                    pointRadius: 0,
                    fill: true
                },
                {
                    label: 'Orders',
                    data: orders,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.12)',
                    tension: 0.3,
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false,
                    yAxisID: 'y1'
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
                    ticks: { callback: (value) => `₹${(value / 1000).toFixed(0)}k` }
                },
                y1: {
                    position: 'right',
                    grid: { display: false },
                    ticks: { color: '#64748b' }
                }
            }
        }
    });
}

function renderTrafficSourcesChart(sources) {
    const canvas = document.getElementById('trafficSourcesChart');
    if (!canvas) return;

    destroyChart('trafficSourcesChart');

    const hasData = sources.some((s) => safeNumber(s.value) > 0);
    const labels = hasData ? sources.map((s) => s.label) : ['No data'];
    const values = hasData ? sources.map((s) => safeNumber(s.value)) : [0];
    const colors = sources.map((s, i) => s.color || paletteColor(i, 0.9));

    analyticsCharts.trafficSourcesChart = new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#0f172a',
                    borderColor: '#1f2937',
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        label(context) {
                            return `${context.label}: ${context.parsed}%`;
                        }
                    }
                }
            }
        }
    });
}

function renderDemographicsChart() {
    const canvas = document.getElementById('demographicsChart');
    if (!canvas) return;

    destroyChart('demographicsChart');

    const data = (window.analyticsData && window.analyticsData.demographics) || [
        { label: '18-24', value: 24 },
        { label: '25-34', value: 34 },
        { label: '35-44', value: 22 },
        { label: '45-54', value: 12 },
        { label: '55+', value: 8 }
    ];

    const labels = data.map((d) => d.label);
    const values = data.map((d) => safeNumber(d.value));
    const hasData = values.some((v) => v > 0);

    analyticsCharts.demographicsChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: hasData ? labels : ['No data'],
            datasets: [{
                label: 'Customers',
                data: hasData ? values : [0],
                backgroundColor: labels.map((_, i) => paletteColor(i, 0.8)),
                borderRadius: 8,
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
                    borderWidth: 1
                }
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    grid: { color: '#f3f4f6', drawBorder: false },
                    ticks: { precision: 0 }
                }
            }
        }
    });
}

function renderProductPerformanceChart(products, period) {
    const canvas = document.getElementById('productPerformanceChart');
    if (!canvas) return;

    destroyChart('productPerformanceChart');

    const topProducts = (products || []).slice(0, 8);
    const hasData = topProducts.some((p) => safeNumber(p.revenue) > 0 || safeNumber(p.units_sold) > 0);

    const labels = hasData ? topProducts.map((p) => p.variant__product__name || 'Product') : ['No data'];
    const revenue = hasData ? topProducts.map((p) => safeNumber(p.revenue)) : [0];
    const units = hasData ? topProducts.map((p) => safeNumber(p.units_sold || p.quantity || p.order_count)) : [0];

    analyticsCharts.productPerformanceChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Revenue',
                    data: revenue,
                    backgroundColor: paletteColor(0, 0.8),
                    borderRadius: 10,
                    borderSkipped: false
                },
                {
                    label: 'Units Sold',
                    data: units,
                    backgroundColor: paletteColor(3, 0.35),
                    borderRadius: 10,
                    borderSkipped: false,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'top', align: 'end' },
                tooltip: {
                    backgroundColor: '#0f172a',
                    borderColor: '#1f2937',
                    borderWidth: 1,
                    callbacks: {
                        label(context) {
                            if (context.dataset.label === 'Revenue') {
                                return `Revenue: ₹${(context.parsed.y || 0).toLocaleString('en-IN')}`;
                            }
                            return `Units: ${context.parsed.y || 0}`;
                        }
                    }
                }
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    grid: { color: '#f3f4f6', drawBorder: false },
                    ticks: { callback: (value) => `₹${(value / 1000).toFixed(0)}k` }
                },
                y1: {
                    position: 'right',
                    grid: { display: false },
                    ticks: { precision: 0 }
                }
            }
        }
    });
}

function extractTrafficSourcesFromDom() {
    const items = Array.from(document.querySelectorAll('.traffic-item'));
    if (!items.length) {
        return [
            { label: 'Direct', value: 42, color: '#667eea' },
            { label: 'Social Media', value: 28, color: '#764ba2' },
            { label: 'Search Engine', value: 18, color: '#ec4899' },
            { label: 'Referral', value: 12, color: '#f59e0b' }
        ];
    }

    return items.map((el, idx) => {
        const label = el.querySelector('.traffic-label')?.textContent?.trim() || `Source ${idx + 1}`;
        const valueText = el.querySelector('.traffic-value')?.textContent || '0';
        const value = parseFloat(valueText.replace('%', '').trim()) || 0;
        const dot = el.querySelector('.traffic-dot');
        const color = dot?.style?.background || paletteColor(idx, 0.9);
        return { label, value, color };
    });
}

function buildFallbackTrend(days) {
    return {
        labels: generateDateLabels(days),
        revenue: Array(days).fill(0),
        orders: Array(days).fill(0)
    };
}

function buildBucketKey(date, resolution) {
    if (resolution === 'weekly') {
        const start = startOfWeek(date);
        return start.toISOString().slice(0, 10);
    }
    if (resolution === 'monthly') {
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-01`;
    }
    return date.toISOString().slice(0, 10);
}

function formatBucketLabel(date, resolution) {
    if (resolution === 'weekly') {
        const start = startOfWeek(date);
        const end = new Date(start);
        end.setDate(end.getDate() + 6);
        return `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${end.toLocaleDateString('en-US', { day: 'numeric' })}`;
    }
    if (resolution === 'monthly') {
        return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    }
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatDateLabel(value) {
    const date = parseDate(value);
    return isNaN(date) ? value : date.toISOString().slice(0, 10);
}

function generateDateLabels(days) {
    const labels = [];
    const today = new Date();
    for (let i = days - 1; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        labels.push(d.toISOString().slice(0, 10));
    }
    return labels;
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

function mapResolutionToDays(resolution, period) {
    const periodDays = mapPeriodToDays(period);
    if (resolution === 'weekly') return Math.max(28, periodDays);
    if (resolution === 'monthly') return Math.max(180, periodDays);
    return periodDays;
}

function destroyChart(name) {
    if (analyticsCharts[name]) {
        analyticsCharts[name].destroy();
        delete analyticsCharts[name];
    }
}

function paletteColor(index, alpha = 1) {
    const colors = [
        [102, 126, 234],
        [118, 75, 162],
        [236, 72, 153],
        [16, 185, 129],
        [245, 158, 11],
        [239, 68, 68],
        [14, 165, 233],
        [139, 92, 246],
        [59, 130, 246],
        [34, 197, 94]
    ];
    const [r, g, b] = colors[index % colors.length];
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function startOfWeek(date) {
    const d = new Date(date);
    const day = d.getDay(); // 0 (Sun) - 6 (Sat)
    const diff = (day === 0 ? -6 : 1) - day; // move to Monday
    d.setDate(d.getDate() + diff);
    d.setHours(0, 0, 0, 0);
    return d;
}

function parseDate(value) {
    const d = new Date(value);
    return d;
}

function safeNumber(value) {
    const num = Number(value);
    return isNaN(num) ? 0 : num;
}

