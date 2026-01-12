
let reportCharts = {};

function initializeSalesReport(rawReport) {
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js is required for sales report charts.');
        return;
    }

    const report = normalizeReportData(rawReport);
    renderSalesBreakdownChart(report);
}

function normalizeReportData(rawReport) {
    if (!rawReport) {
        return {
            overall: {},
            period_data: [],
            payment_methods: [],
            cod_vs_online: { cod: {}, online: {} },
            cancellations: {}
        };
    }

    if (typeof rawReport === 'string') {
        try {
            const parsed = JSON.parse(rawReport);
            return normalizeReportData(parsed);
        } catch (e) {
            console.warn('Unable to parse report data string, using empty fallback.', e);
            return normalizeReportData(null);
        }
    }

    const report = { ...rawReport };
    report.period_data = Array.isArray(report.period_data) ? report.period_data : [];
    report.payment_methods = Array.isArray(report.payment_methods) ? report.payment_methods : [];
    report.cod_vs_online = report.cod_vs_online || { cod: {}, online: {} };
    report.cancellations = report.cancellations || {};

    report.period_data = report.period_data.map((entry) => {
        const period = entry.period || entry.date || entry.period_label;
        return {
            ...entry,
            period_label: formatPeriodLabel(period)
        };
    });

    return report;
}

function renderSalesBreakdownChart(report) {
    const canvas = document.getElementById('salesBreakdownChart');
    if (!canvas) return;

    destroyReportChart('salesBreakdownChart');

    const labels = report.period_data.map((item) => item.period_label);
    const revenue = report.period_data.map((item) => safeNumber(item.revenue));
    const orders = report.period_data.map((item) => safeNumber(item.orders));

    const resolvedLabels = labels.length ? labels : generateFallbackLabels(10);
    const resolvedRevenue = revenue.length ? revenue : Array(resolvedLabels.length).fill(0);
    const resolvedOrders = orders.length ? orders : Array(resolvedLabels.length).fill(0);

    const ctx = canvas.getContext('2d');
    const revenueGradient = ctx.createLinearGradient(0, 0, 0, 280);
    revenueGradient.addColorStop(0, 'rgba(99, 102, 241, 0.35)');
    revenueGradient.addColorStop(1, 'rgba(99, 102, 241, 0)');

    reportCharts.salesBreakdownChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: resolvedLabels,
            datasets: [
                {
                    label: 'Revenue',
                    data: resolvedRevenue,
                    borderColor: '#6366f1',
                    backgroundColor: revenueGradient,
                    borderWidth: 3,
                    tension: 0.35,
                    pointRadius: 0,
                    fill: true
                },
                {
                    label: 'Orders',
                    data: resolvedOrders,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.12)',
                    borderWidth: 2,
                    tension: 0.35,
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
                    ticks: { color: '#6b7280' }
                }
            }
        }
    });
}

function formatPeriodLabel(period) {
    if (!period) return '';
    if (period instanceof Date && !Number.isNaN(period.getTime())) {
        return period.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }

    if (typeof period === 'string') {
        const parsed = new Date(period);
        if (!Number.isNaN(parsed.getTime())) {
            return parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        }
        return period;
    }

    return String(period);
}

function generateFallbackLabels(length) {
    const labels = [];
    const today = new Date();
    for (let i = length - 1; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        labels.push(d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    }
    return labels;
}

function safeNumber(value) {
    const num = Number(value);
    return Number.isFinite(num) ? num : 0;
}

function destroyReportChart(key) {
    if (reportCharts[key]) {
        reportCharts[key].destroy();
        delete reportCharts[key];
    }
}


