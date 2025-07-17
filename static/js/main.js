document.addEventListener("DOMContentLoaded", function () {
  const creditForm = document.getElementById("creditForm");
  const loadingSpinner = document.getElementById("loadingSpinner");
  const errorMessage = document.getElementById("errorMessage");
  const creditResult = document.getElementById("creditResult");
  let currentData = {}; // Biến để lưu dữ liệu form hiện tại

  // Form submission
  creditForm.addEventListener("submit", function (e) {
    e.preventDefault();

    const formData = new FormData(creditForm);
    currentData = {
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
      body: JSON.stringify(currentData),
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

  // Xóa lịch sử
  document
    .getElementById("clearHistoryBtn")
    .addEventListener("click", function () {
      if (confirm("Bạn có chắc muốn xóa toàn bộ lịch sử tra cứu?")) {
        fetch("/api/clear_history", {
          method: "POST",
        })
          .then((response) => response.json())
          .then((data) => {
            if (data.success) {
              alert("Đã xóa lịch sử thành công!");
              showHistory(); // Refresh modal
            } else {
              alert("Lỗi khi xóa lịch sử.");
            }
          })
          .catch((error) => {
            console.error("Error clearing history:", error);
            alert("Lỗi khi xóa lịch sử.");
          });
      }
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

    // Xóa các nút cũ nếu có
    const existingBtns = errorMessage.querySelectorAll("button");
    existingBtns.forEach((btn) => btn.remove());

    // Nếu lỗi là không tìm thấy trong individual_input.json (và có thể enrich_data), hiển thị 2 nút
    if (message.includes("Không tìm thấy thông tin người dùng")) {
      const btnContainer = document.createElement("div");
      btnContainer.style.display = "flex";
      btnContainer.style.justifyContent = "center";
      btnContainer.style.marginTop = "20px";

      const btnInternet = document.createElement("button");
      btnInternet.textContent = "Enrich from Internet";
      btnInternet.style.backgroundColor = "#007bff"; // Màu xanh dương
      btnInternet.style.color = "white";
      btnInternet.style.padding = "12px 24px";
      btnInternet.style.border = "none";
      btnInternet.style.borderRadius = "8px";
      btnInternet.style.fontSize = "16px";
      btnInternet.style.cursor = "pointer";
      btnInternet.style.margin = "0 10px";
      btnInternet.style.transition = "background-color 0.3s";
      btnInternet.onmouseover = function () {
        this.style.backgroundColor = "#0056b3";
      };
      btnInternet.onmouseout = function () {
        this.style.backgroundColor = "#007bff";
      };

      const btnFile = document.createElement("button");
      btnFile.textContent = "Enrich from File";
      btnFile.style.backgroundColor = "#28a745"; // Màu xanh lá
      btnFile.style.color = "white";
      btnFile.style.padding = "12px 24px";
      btnFile.style.border = "none";
      btnFile.style.borderRadius = "8px";
      btnFile.style.fontSize = "16px";
      btnFile.style.cursor = "pointer";
      btnFile.style.margin = "0 10px";
      btnFile.style.transition = "background-color 0.3s";
      btnFile.onmouseover = function () {
        this.style.backgroundColor = "#218838";
      };
      btnFile.onmouseout = function () {
        this.style.backgroundColor = "#28a745";
      };

      errorMessage.appendChild(document.createElement("br"));
      btnContainer.appendChild(btnInternet);
      btnContainer.appendChild(btnFile);
      errorMessage.appendChild(btnContainer);

      // Event listeners cho nút
      btnInternet.addEventListener("click", function () {
        enrichData("internet");
      });

      btnFile.addEventListener("click", function () {
        enrichData("file");
      });
    }
  }

  // Hàm xử lý enrich và gọi lại lookup
  function enrichData(type) {
    showLoading();
    const endpoint =
      type === "internet"
        ? "/api/enrich_from_internet"
        : "/api/enrich_from_file";

    fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(currentData),
    })
      .then((response) => response.json())
      .then((enrichResponse) => {
        if (enrichResponse.success) {
          // Tạo và hiển thị modal thông tin enrich
          const modal = createEnrichModal(enrichResponse.data);
          document.body.appendChild(modal);
          modal.style.display = "flex";

          // Không gọi lookup ngay, chờ user nhấn nút tiếp tục
        } else {
          hideLoading();
          showError(enrichResponse.message);
        }
      })
      .catch((error) => {
        hideLoading();
        showError("Đã xảy ra lỗi khi bổ sung dữ liệu. Vui lòng thử lại.");
        console.error("Error:", error);
      });
  }

  // Hàm tạo modal hiển thị thông tin enrich đẹp
  function createEnrichModal(data) {
    const modal = document.createElement("div");
    modal.style.position = "fixed";
    modal.style.top = "0";
    modal.style.left = "0";
    modal.style.width = "100%";
    modal.style.height = "100%";
    modal.style.backgroundColor = "rgba(0, 0, 0, 0.5)";
    modal.style.display = "none";
    modal.style.justifyContent = "center";
    modal.style.alignItems = "center";
    modal.style.zIndex = "1000";

    const modalContent = document.createElement("div");
    modalContent.style.backgroundColor = "white";
    modalContent.style.padding = "30px";
    modalContent.style.borderRadius = "12px";
    modalContent.style.boxShadow = "0 4px 20px rgba(0, 0, 0, 0.2)";
    modalContent.style.width = "50%";
    modalContent.style.maxWidth = "600px";
    modalContent.style.maxHeight = "80%";
    modalContent.style.overflowY = "auto";
    modalContent.style.fontFamily = "Arial, sans-serif";

    const title = document.createElement("h2");
    title.textContent = "Thông tin người dùng sau khi bổ sung";
    title.style.textAlign = "center";
    title.style.color = "#333";
    title.style.marginBottom = "20px";
    modalContent.appendChild(title);

    const infoList = document.createElement("ul");
    infoList.style.listStyleType = "none";
    infoList.style.padding = "0";

    // Các fields cần hiển thị
    const fields = [
      { key: "age", label: "Tuổi" },
      { key: "address", label: "Địa chỉ" },
      { key: "email_address", label: "Email" },
      { key: "phone_number", label: "Số điện thoại" },
      { key: "job_title", label: "Chức vụ" },
      { key: "current_company", label: "Công ty hiện tại" },
      { key: "educational_level", label: "Trình độ học vấn" },
      { key: "occupation", label: "Nghề nghiệp" },
      { key: "criminal_record", label: "Tiền án" },
      { key: "stock_assets", label: "Tài sản cổ phiếu" },
      { key: "source_of_information", label: "Nguồn thông tin" },
      { key: "confidence_level", label: "Mức độ tin cậy" },
    ];

    fields.forEach((field) => {
      const li = document.createElement("li");
      li.style.marginBottom = "15px";
      li.style.borderBottom = "1px solid #eee";
      li.style.paddingBottom = "10px";

      const label = document.createElement("strong");
      label.textContent = `${field.label}: `;
      label.style.color = "#555";

      const value = document.createElement("span");
      value.textContent =
        data[field.key] !== null && data[field.key] !== undefined
          ? data[field.key]
          : "Không có thông tin";
      value.style.color = "#333";

      li.appendChild(label);
      li.appendChild(value);
      infoList.appendChild(li);
    });

    modalContent.appendChild(infoList);

    // Nút tiếp tục và đóng
    const buttonContainer = document.createElement("div");
    buttonContainer.style.display = "flex";
    buttonContainer.style.justifyContent = "space-between";
    buttonContainer.style.marginTop = "30px";

    const continueBtn = document.createElement("button");
    continueBtn.textContent = "Tiếp tục tính điểm tín dụng";
    continueBtn.style.backgroundColor = "#007bff";
    continueBtn.style.color = "white";
    continueBtn.style.padding = "12px 24px";
    continueBtn.style.border = "none";
    continueBtn.style.borderRadius = "8px";
    continueBtn.style.cursor = "pointer";
    continueBtn.style.transition = "background-color 0.3s";
    continueBtn.onmouseover = function () {
      this.style.backgroundColor = "#0056b3";
    };
    continueBtn.onmouseout = function () {
      this.style.backgroundColor = "#007bff";
    };
    continueBtn.addEventListener("click", function () {
      modal.style.display = "none";
      document.body.removeChild(modal);
      // Gọi lại lookup để tính score
      fetch("/api/lookup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(currentData),
      })
        .then((response) => response.json())
        .then((lookupData) => {
          hideLoading();
          if (lookupData.success) {
            displayCreditResult(lookupData.data);
          } else {
            showError(lookupData.message);
          }
        })
        .catch((error) => {
          hideLoading();
          showError("Lỗi khi tra cứu sau khi bổ sung dữ liệu.");
          console.error("Error:", error);
        });
    });

    const closeBtn = document.createElement("button");
    closeBtn.textContent = "Đóng";
    closeBtn.style.backgroundColor = "#6c757d";
    closeBtn.style.color = "white";
    closeBtn.style.padding = "12px 24px";
    closeBtn.style.border = "none";
    closeBtn.style.borderRadius = "8px";
    closeBtn.style.cursor = "pointer";
    closeBtn.style.transition = "background-color 0.3s";
    closeBtn.onmouseover = function () {
      this.style.backgroundColor = "#5a6268";
    };
    closeBtn.onmouseout = function () {
      this.style.backgroundColor = "#6c757d";
    };
    closeBtn.addEventListener("click", function () {
      modal.style.display = "none";
      document.body.removeChild(modal);
      hideLoading(); // Ẩn loading nếu đóng modal
    });

    buttonContainer.appendChild(continueBtn);
    buttonContainer.appendChild(closeBtn);
    modalContent.appendChild(buttonContainer);

    modal.appendChild(modalContent);

    // Đóng modal khi click ngoài
    modal.addEventListener("click", function (event) {
      if (event.target === modal) {
        modal.style.display = "none";
        document.body.removeChild(modal);
        hideLoading();
      }
    });

    return modal;
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

    // Xử lý giải thích từ model
    const explanationText = document.getElementById("explanationText");
    explanationText.innerHTML = ""; // Xóa nội dung cũ
    const explanation = data.explanation.trim();

    // Tách và format giải thích thành danh sách bullet points
    if (explanation) {
      const ul = document.createElement("ul");
      ul.className = "explanation-list";

      // Tách các bullet points bằng regex (bắt đầu bằng • hoặc -)
      const bulletPoints = explanation
        .split(/•|-/)
        .map((item) => item.trim())
        .filter(
          (item) => item && !item.startsWith("The individual was classified")
        );

      bulletPoints.forEach((point) => {
        const li = document.createElement("li");
        li.textContent = point;
        ul.appendChild(li);
      });

      explanationText.appendChild(ul);
    } else {
      explanationText.textContent = "Không có giải thích chi tiết.";
    }

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
