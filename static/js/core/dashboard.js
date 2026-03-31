(function () {
  const payload = document.getElementById("dashboard-data");
  if (!payload) {
    return;
  }

  function parseJsonAttr(name, fallback) {
    try {
      const raw = payload.dataset[name];
      return raw ? JSON.parse(raw) : fallback;
    } catch (error) {
      console.error("Dashboard data parse error:", name, error);
      return fallback;
    }
  }

  const monthlyData = parseJsonAttr("monthly", []);
  const quarterlyData = parseJsonAttr("quarterly", {});
  const registrationFees = Number(payload.dataset.registrationFees || 0);
  const academicIncome = Number(payload.dataset.academicIncome || 0);
  const languagesIncome = parseJsonAttr("languagesIncome", {});
  const modalityIncome = parseJsonAttr("modalityIncome", {});
  const typeIncome = parseJsonAttr("typeIncome", {});
  const selectedYearId = String(payload.dataset.selectedYearId || "");
  const paidRegistrationsCount = Number(payload.dataset.paidRegistrations || 0);

  const monthlyDataObj = {};
  const quartValues = {};

  monthlyData.forEach((item) => {
    monthlyDataObj[item.name] = item.value;
  });

  Object.keys(quarterlyData).forEach((quarter) => {
    quartValues[quarter] = quarterlyData[quarter];
  });

  const globalOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: "bottom",
        labels: {
          font: { size: 12 },
          padding: 15,
          usePointStyle: true,
          color: "#666",
        },
      },
      tooltip: {
        backgroundColor: "rgba(0, 0, 0, 0.8)",
        padding: 12,
        titleFont: { size: 12, weight: "bold" },
        bodyFont: { size: 11 },
        callbacks: {
          label(context) {
            const label = context.dataset.label || "";
            const value = context.parsed.y || context.parsed;
            return label + ": " + value.toLocaleString("fr-DZ") + " DZD";
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback(value) {
            return value.toLocaleString("fr-DZ") + " DZD";
          },
          color: "#666",
          font: { size: 11 },
        },
        grid: { color: "#f0f0f0" },
      },
      x: {
        grid: { display: false },
        ticks: { color: "#666", font: { size: 10 } },
      },
    },
  };

  let monthlyChart;
  let quarterlyChart;

  function updateDashboard() {
    const yearFilter = document.getElementById("yearFilter");
    const languageFilter = document.getElementById("languageFilter");
    const modalityFilter = document.getElementById("modalityFilter");
    const typeFilter = document.getElementById("typeFilter");

    const yearId = yearFilter ? yearFilter.value : "";
    const language = languageFilter ? languageFilter.value : "";
    const modality = modalityFilter ? modalityFilter.value : "";
    const type = typeFilter ? typeFilter.value : "";

    const url = new URL(window.location.href);
    if (yearId) {
      url.searchParams.set("year", yearId);
    }

    if (language) {
      url.searchParams.set("language", language);
    } else {
      url.searchParams.delete("language");
    }

    if (modality) {
      url.searchParams.set("modality", modality);
    } else {
      url.searchParams.delete("modality");
    }

    if (type) {
      url.searchParams.set("type", type);
    } else {
      url.searchParams.delete("type");
    }

    window.location.href = url.toString();
  }

  function resetFilters() {
    const yearFilter = document.getElementById("yearFilter");
    const languageFilter = document.getElementById("languageFilter");
    const modalityFilter = document.getElementById("modalityFilter");
    const typeFilter = document.getElementById("typeFilter");

    if (yearFilter) {
      yearFilter.value = selectedYearId;
    }
    if (languageFilter) {
      languageFilter.value = "";
    }
    if (modalityFilter) {
      modalityFilter.value = "";
    }
    if (typeFilter) {
      typeFilter.value = "";
    }

    updateDashboard();
  }

  function switchPeriod(period) {
    document.querySelectorAll(".period-btn").forEach((btn) => {
      btn.classList.remove("active", "bg-blue-600", "text-white");
      btn.classList.add("bg-gray-100", "text-gray-700");
      if (btn.dataset.period === period) {
        btn.classList.add("active", "bg-blue-600", "text-white");
      }
    });

    const labels = {
      month: "Mois",
      quarter: "Trimestre",
      year: "Année",
    };

    const periodLabel = document.getElementById("period-label");
    if (periodLabel) {
      periodLabel.textContent = labels[period] || "Mois";
    }

    const monthlyContainer = document.getElementById("monthlyChartContainer");
    const quarterlyContainer = document.getElementById("quarterlyChartContainer");

    if (monthlyContainer) {
      monthlyContainer.style.display = period === "month" ? "block" : "none";
    }
    if (quarterlyContainer) {
      quarterlyContainer.style.display = period === "quarter" ? "block" : "none";
    }

    if (period === "month" && monthlyChart) {
      window.setTimeout(function () {
        monthlyChart.resize();
      }, 100);
    }

    if (period === "quarter" && quarterlyChart) {
      window.setTimeout(function () {
        quarterlyChart.resize();
      }, 100);
    }
  }

  function calculateRevenueStats() {
    const values = Object.values(monthlyDataObj);
    if (!values.length) {
      return;
    }

    const maxValue = Math.max(...values);
    const maxMonth = Object.keys(monthlyDataObj)[values.indexOf(maxValue)];
    const firstValue = values[0] || 0;
    const lastValue = values[values.length - 1] || 0;
    const growth = firstValue > 0 ? (((lastValue - firstValue) / firstValue) * 100).toFixed(1) : 0;

    const bestMonth = document.getElementById("bestMonth");
    const growthLabel = document.getElementById("growth");
    if (bestMonth) {
      bestMonth.textContent = maxMonth + " (" + maxValue.toLocaleString("fr-DZ") + " DZD)";
    }
    if (growthLabel) {
      growthLabel.textContent = (growth >= 0 ? "+" : "") + growth + "%";
    }
  }

  function calculateFeesStats() {
    const totalStudents = paidRegistrationsCount + Math.max(1, Math.ceil(paidRegistrationsCount * 0.15));
    const unpaidCount = totalStudents - paidRegistrationsCount;
    const collectRate = paidRegistrationsCount > 0 ? ((paidRegistrationsCount / totalStudents) * 100).toFixed(1) : "0";

    const unpaidLabel = document.getElementById("unpaidCount");
    const collectRateLabel = document.getElementById("collectRate");

    if (unpaidLabel) {
      unpaidLabel.textContent = String(unpaidCount);
    }
    if (collectRateLabel) {
      collectRateLabel.textContent = collectRate;
    }
  }

  function toggleChart(id) {
    const element = document.getElementById(id);
    if (!element) {
      return;
    }

    element.classList.toggle("hidden");

    if (id === "revenueDetail" && !element.classList.contains("hidden")) {
      calculateRevenueStats();
    }

    if (id === "feesDetail" && !element.classList.contains("hidden")) {
      calculateFeesStats();
    }
  }

  function initCharts() {
    const monthlyCtx = document.getElementById("monthlyChart").getContext("2d");
    monthlyChart = new Chart(monthlyCtx, {
      type: "line",
      data: {
        labels: Object.keys(monthlyDataObj),
        datasets: [{
          label: "Revenus",
          data: Object.values(monthlyDataObj),
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          borderWidth: 3,
          fill: true,
          pointRadius: 5,
          pointBackgroundColor: "#10b981",
          pointHoverRadius: 7,
          pointBorderColor: "#fff",
          pointBorderWidth: 2,
          tension: 0.4,
        }],
      },
      options: {
        ...globalOptions,
        onClick(event, elements) {
          if (!elements.length) {
            return;
          }
          const monthIdx = elements[0].index;
          const monthName = Object.keys(monthlyDataObj)[monthIdx];
          const value = Object.values(monthlyDataObj)[monthIdx];
          alert("📊 " + monthName + "\nRevenus: " + value.toLocaleString("fr-DZ") + " DZD");
        },
      },
    });

    const quarterlyCtx = document.getElementById("quarterlyChart").getContext("2d");
    quarterlyChart = new Chart(quarterlyCtx, {
      type: "bar",
      data: {
        labels: Object.keys(quartValues),
        datasets: [{
          label: "Revenus par Trimestre",
          data: Object.values(quartValues),
          backgroundColor: [
            "rgba(59, 130, 246, 0.7)",
            "rgba(34, 197, 94, 0.7)",
            "rgba(245, 158, 11, 0.7)",
            "rgba(168, 85, 247, 0.7)",
          ],
          borderColor: ["rgb(59, 130, 246)", "rgb(34, 197, 94)", "rgb(245, 158, 11)", "rgb(168, 85, 247)"],
          borderWidth: 2,
          borderRadius: 6,
        }],
      },
      options: {
        ...globalOptions,
        onClick(event, elements) {
          if (!elements.length) {
            return;
          }
          const qIdx = elements[0].index;
          const quarterName = Object.keys(quartValues)[qIdx];
          const value = Object.values(quartValues)[qIdx];
          alert("📊 " + quarterName + "\nRevenus: " + value.toLocaleString("fr-DZ") + " DZD");
        },
      },
    });

    const comparisonCtx = document.getElementById("comparisonChart").getContext("2d");
    new Chart(comparisonCtx, {
      type: "bar",
      data: {
        labels: ["Frais", "Revenus Cours"],
        datasets: [{
          label: "Collecte (DZD)",
          data: [registrationFees, academicIncome],
          backgroundColor: ["rgba(251, 191, 36, 0.7)", "rgba(52, 211, 153, 0.7)"],
          borderColor: ["rgb(251, 191, 36)", "rgb(52, 211, 153)"],
          borderWidth: 2,
          borderRadius: 6,
        }],
      },
      options: globalOptions,
    });

    const languageNames = Object.keys(languagesIncome);
    const languageValues = Object.values(languagesIncome);
    const languageCtx = document.getElementById("languageChart").getContext("2d");

    new Chart(languageCtx, {
      type: "bar",
      data: {
        labels: languageNames,
        datasets: [{
          label: "Revenus par Langue",
          data: languageValues,
          backgroundColor: [
            "rgba(59, 130, 246, 0.7)",
            "rgba(34, 197, 94, 0.7)",
            "rgba(245, 158, 11, 0.7)",
            "rgba(239, 68, 68, 0.7)",
            "rgba(168, 85, 247, 0.7)",
            "rgba(236, 72, 153, 0.7)",
            "rgba(14, 165, 233, 0.7)",
            "rgba(34, 197, 94, 0.7)",
            "rgba(251, 146, 60, 0.7)",
            "rgba(107, 114, 128, 0.7)",
          ].slice(0, languageNames.length),
          borderColor: [
            "rgb(59, 130, 246)",
            "rgb(34, 197, 94)",
            "rgb(245, 158, 11)",
            "rgb(239, 68, 68)",
            "rgb(168, 85, 247)",
            "rgb(236, 72, 153)",
            "rgb(14, 165, 233)",
            "rgb(34, 197, 94)",
            "rgb(251, 146, 60)",
            "rgb(107, 114, 128)",
          ].slice(0, languageNames.length),
          borderWidth: 2,
          borderRadius: 6,
        }],
      },
      options: {
        ...globalOptions,
        indexAxis: "y",
      },
    });

    const modalityCtx = document.getElementById("modalityChart").getContext("2d");
    new Chart(modalityCtx, {
      type: "bar",
      data: {
        labels: Object.keys(modalityIncome),
        datasets: [{
          label: "Revenus",
          data: Object.values(modalityIncome),
          backgroundColor: ["rgba(59, 130, 246, 0.7)", "rgba(34, 197, 94, 0.7)"],
          borderColor: ["rgb(59, 130, 246)", "rgb(34, 197, 94)"],
          borderWidth: 2,
          borderRadius: 6,
        }],
      },
      options: globalOptions,
    });

    const typeCtx = document.getElementById("typeChart").getContext("2d");
    new Chart(typeCtx, {
      type: "bar",
      data: {
        labels: Object.keys(typeIncome),
        datasets: [{
          label: "Revenus",
          data: Object.values(typeIncome),
          backgroundColor: ["rgba(168, 85, 247, 0.7)", "rgba(239, 68, 68, 0.7)"],
          borderColor: ["rgb(168, 85, 247)", "rgb(239, 68, 68)"],
          borderWidth: 2,
          borderRadius: 6,
        }],
      },
      options: globalOptions,
    });
  }

  document.addEventListener("change", function (event) {
    if (event.target.matches("[data-dashboard-filter='true']")) {
      updateDashboard();
    }
  });

  document.addEventListener("click", function (event) {
    const periodBtn = event.target.closest("[data-dashboard-period]");
    if (periodBtn) {
      switchPeriod(periodBtn.dataset.dashboardPeriod);
      return;
    }

    if (event.target.closest("[data-dashboard-reset='true']")) {
      resetFilters();
      return;
    }

    const toggleBtn = event.target.closest("[data-dashboard-toggle]");
    if (toggleBtn) {
      toggleChart(toggleBtn.dataset.dashboardToggle);
    }
  });

  initCharts();
  switchPeriod("month");
})();
