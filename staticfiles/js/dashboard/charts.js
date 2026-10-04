/* ==========================================================
   FinSync AI Dashboard Charts
========================================================== */

Chart.defaults.color = "#A1A1AA";
Chart.defaults.borderColor = "rgba(255,255,255,.08)";
Chart.defaults.font.family = "Inter";

/* ==========================================================
   Dashboard Data
========================================================== */

const dashboardData = window.dashboardData || {};

const expenseTrend = dashboardData.expenseTrend || [];

const cashFlow = dashboardData.cashFlow || {
    labels: [],
    income: [],
    expense: []
};

const categoryBreakdown = dashboardData.categoryBreakdown || {
    labels: [],
    values: []
};

const budgetPercentage = dashboardData.budgetPercentage || 0;

/* ==========================================================
   Helper
========================================================== */

function emptyChartMessage(canvasId) {

    const canvas = document.getElementById(canvasId);

    if (!canvas) return;

    const parent = canvas.parentElement;

    canvas.style.display = "none";

    const empty = document.createElement("div");

    empty.className = "chart-empty";

    empty.innerHTML = `
        <i class="fa-solid fa-chart-column"></i>

        <h3>No Data Available</h3>

        <p>
            Add your first transaction to unlock
            financial analytics.
        </p>
    `;

    parent.appendChild(empty);

}

/* ==========================================================
   Expense Trend
========================================================== */

const expenseCanvas = document.getElementById("expenseChart");

if (expenseCanvas) {

    if (expenseTrend.length === 0) {

        emptyChartMessage("expenseChart");

    }

    else {

        new Chart(expenseCanvas, {

            type: "line",

            data: {

                labels: expenseTrend.map(item => item.label),

                datasets: [

                    {

                        label: "Expenses",

                        data: expenseTrend.map(item => item.value),

                        borderColor: "#8B5CF6",

                        backgroundColor: "rgba(139,92,246,.15)",

                        fill: true,

                        borderWidth: 3,

                        tension: .4,

                        pointRadius: 4

                    }

                ]

            },

            options: {

                responsive: true,

                maintainAspectRatio: false,

                plugins: {

                    legend: {

                        display: false

                    }

                }

            }

        });

    }

}

/* ==========================================================
   Category Breakdown
========================================================== */

const categoryCanvas = document.getElementById("categoryChart");

if (categoryCanvas) {

    if (categoryBreakdown.labels.length === 0) {

        emptyChartMessage("categoryChart");

    }

    else {

        new Chart(categoryCanvas, {

            type: "doughnut",

            data: {

                labels: categoryBreakdown.labels,

                datasets: [

                    {

                        data: categoryBreakdown.values,

                        backgroundColor: [

                            "#8B5CF6",
                            "#22C55E",
                            "#3B82F6",
                            "#F59E0B",
                            "#EF4444",
                            "#14B8A6",
                            "#EC4899"

                        ],

                        borderWidth: 0

                    }

                ]

            },

            options: {

                cutout: "72%",

                plugins: {

                    legend: {

                        position: "bottom"

                    }

                }

            }

        });

    }

}

/* ==========================================================
   Cash Flow
========================================================== */

const cashCanvas = document.getElementById("cashFlowChart");

if (cashCanvas) {

    if (cashFlow.labels.length === 0) {

        emptyChartMessage("cashFlowChart");

    }

    else {

        new Chart(cashCanvas, {

            type: "bar",

            data: {

                labels: cashFlow.labels,

                datasets: [

                    {

                        label: "Income",

                        data: cashFlow.income,

                        backgroundColor: "#22C55E"

                    },

                    {

                        label: "Expense",

                        data: cashFlow.expense,

                        backgroundColor: "#8B5CF6"

                    }

                ]

            },

            options: {

                responsive: true,

                maintainAspectRatio: false

            }

        });

    }

}

/* ==========================================================
   Budget Progress
========================================================== */

const budgetCanvas = document.getElementById("budgetChart");

if (budgetCanvas) {

    new Chart(budgetCanvas, {

        type: "doughnut",

        data: {

            datasets: [

                {

                    data: [

                        budgetPercentage,

                        100 - budgetPercentage

                    ],

                    backgroundColor: [

                        "#8B5CF6",

                        "#2A2A35"

                    ],

                    borderWidth: 0

                }

            ]

        },

        options: {

            cutout: "78%",

            plugins: {

                legend: {

                    display: false

                }

            },

            responsive: true,

            maintainAspectRatio: false

        }

    });

}

/* ==========================================================
   Analytics Period Filter
========================================================== */

const periodFilter = document.getElementById("chartPeriod");

if (periodFilter) {

    periodFilter.addEventListener("change", function () {

        const url = new URL(window.location.href);

        url.searchParams.set("period", this.value);

        window.location.href = url.toString();

    });

}