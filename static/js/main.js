document.addEventListener("DOMContentLoaded", function () {
  const creditForm = document.getElementById("creditForm");
  const loadingSpinner = document.getElementById("loadingSpinner");
  const errorMessage = document.getElementById("errorMessage");
  const creditResult = document.getElementById("creditResult");

  // Form submission
  creditForm.addEventListener("submit", function (e) {
    e.preventDefault();

    const formData = new FormData(creditForm);
    const data = {
      full_name: formData.get("full_name"),
      national_id: formData.get("national_id"),
    };

    // Show loading
    showLoading();

    // Submit to API
    fetch("/api/lookup", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })
      .then((response) => response.json())
      .then((data) => {
        hideLoading();

        if (data.success) {
          displayCreditResult(data.data);
        } else {
          showError(data.message);
        }
      })
      .catch((error) => {
        hideLoading();
        showError(
          "Đã xảy ra lỗi trong quá trình tra cứu. Vui lòng thử lại sau."
        );
        console.error("Error:", error);
      });
  });

  // Modal handlers
  document.getElementById("getTipsBtn").addEventListener("click", showTips);
  document
    .getElementById("viewHistoryBtn")
    .addEventListener("click", showHistory);
  document
    .getElementById("newSearchBtn")
    .addEventListener("click", function () {
      creditResult.style.display = "none";
      creditForm.style.display = "grid"; // Thay "block" thành "grid"
      creditForm.reset();
    });

  // Close modal handlers
  document
    .getElementById("closeTipsModal")
    .addEventListener("click", function () {
      document.getElementById("tipsModal").style.display = "none";
    });

  document
    .getElementById("closeHistoryModal")
    .addEventListener("click", function () {
      document.getElementById("historyModal").style.display = "none";
    });

  // Close modal when clicking outside
  window.addEventListener("click", function (event) {
    const tipsModal = document.getElementById("tipsModal");
    const historyModal = document.getElementById("historyModal");

    if (event.target === tipsModal) {
      tipsModal.style.display = "none";
    }
    if (event.target === historyModal) {
      historyModal.style.display = "none";
    }
  });

  function showLoading() {
    loadingSpinner.style.display = "block";
    errorMessage.style.display = "none";
    creditResult.style.display = "none";
  }

  function hideLoading() {
    loadingSpinner.style.display = "none";
  }

  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = "block";
    creditResult.style.display = "none";
  }

  function displayCreditResult(data) {
    // Cập nhật hiển thị điểm số trên gauge chart
    document.getElementById("scoreNumber").textContent = data.credit_score;
    document.getElementById("scoreLabel").textContent = data.score_level;

    // Cập nhật vị trí kim của gauge chart
    const needle = document.querySelector(".gauge-needle");
    const score = data.credit_score;
    const minScore = 300;
    const maxScore = 850;
    const minAngle = -90;
    const maxAngle = 90;
    const angle =
      minAngle +
      ((score - minScore) / (maxScore - minScore)) * (maxAngle - minAngle);
    needle.style.transform = `translateX(-50%) rotate(${angle}deg)`;

    // Cập nhật các yếu tố khác
    document.getElementById("utilizationPercent").textContent =
      data.credit_card_utilization + "%";
    document.getElementById("paymentPercent").textContent =
      data.payment_history + "%";
    document.getElementById("historyYears").textContent =
      data.credit_history_years + " years";
    document.getElementById("historyMonths").textContent =
      data.credit_history_months + " months";

    // Cập nhật giải thích
    document.getElementById("explanationText").textContent = data.explanation;

    // Ẩn form và hiển thị kết quả
    creditForm.style.display = "none";
    creditResult.style.display = "block";
    errorMessage.style.display = "none";
  }

  function showTips() {
    fetch("/api/tips")
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          const tipsList = document.getElementById("tipsList");
          tipsList.innerHTML = "";

          data.data.forEach((tip) => {
            const li = document.createElement("li");
            li.textContent = tip;
            tipsList.appendChild(li);
          });

          document.getElementById("tipsModal").style.display = "flex";
        }
      })
      .catch((error) => {
        console.error("Error loading tips:", error);
        alert("Không thể tải tips. Vui lòng thử lại sau.");
      });
  }

  function showHistory() {
    fetch("/api/history")
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          const historyList = document.getElementById("historyList");
          historyList.innerHTML = "";

          data.data.forEach((item, index) => {
            const historyItem = document.createElement("div");
            historyItem.className = "history-item";
            historyItem.innerHTML = `
                        <div class="history-header">
                            <div class="history-title">Credit Scoring - Record #${
                              index + 1
                            }</div>
                            <div class="lookup-time">${item.lookup_time}</div>
                        </div>
                        <div class="history-content">
                            <div class="customer-info">
                                <div class="section-title">Customer Information</div>
                                <div class="info-row">
                                    <span class="info-label">Name</span>
                                    <span class="info-value">${
                                      item.customer_info.name
                                    }</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">Date of Birth</span>
                                    <span class="info-value">${
                                      item.customer_info.date_of_birth
                                    }</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">Occupation</span>
                                    <span class="info-value">${
                                      item.customer_info.occupation
                                    }</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">Average Monthly Income</span>
                                    <span class="info-value">${
                                      item.customer_info.average_monthly_income
                                    }</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">Credit History</span>
                                    <span class="info-value">${
                                      item.customer_info.credit_history
                                    }</span>
                                </div>
                            </div>
                            <div class="credit-score-info">
                                <div class="section-title">Credit Score & Explanation</div>
                                <div class="credit-score">${
                                  item.credit_score_explanation.credit_score
                                }</div>
                                <div class="score-label">${
                                  item.credit_score_explanation.explanation
                                }</div>
                                
                                <div class="factors-title">TOP CONTRIBUTING FACTORS</div>
                                <ul class="factors-list">
                                    ${item.credit_score_explanation.top_contributing_factors
                                      .map((factor) => `<li>• ${factor}</li>`)
                                      .join("")}
                                </ul>
                                
                                <div class="explanation-text">
                                    "${
                                      item.credit_score_explanation
                                        .detailed_explanation ||
                                      item.credit_score_explanation.explanation
                                    }"
                                </div>
                                
                                <div class="usage-level">${
                                  item.credit_score_explanation.usage_level
                                }</div>
                            </div>
                        </div>
                    `;
            historyList.appendChild(historyItem);
          });

          document.getElementById("historyModal").style.display = "flex";
        }
      })
      .catch((error) => {
        console.error("Error loading history:", error);
        alert("Không thể tải lịch sử. Vui lòng thử lại sau.");
      });
  }

  // Format national ID input
  document.getElementById("nationalId").addEventListener("input", function (e) {
    let value = e.target.value.replace(/\D/g, ""); // Remove non-digits
    if (value.length > 12) {
      value = value.slice(0, 12);
    }
    e.target.value = value;
  });

  // Format full name input
  document.getElementById("fullName").addEventListener("input", function (e) {
    let value = e.target.value.toUpperCase();
    // Remove special characters except spaces
    value = value.replace(/[^A-Z\s]/g, "");
    e.target.value = value;
  });
});
