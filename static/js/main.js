document.addEventListener("DOMContentLoaded", function () {
  const creditForm = document.getElementById("creditForm");
  const loadingSpinner = document.getElementById("loadingSpinner");
  const errorMessage = document.getElementById("errorMessage");
  const creditResult = document.getElementById("creditResult");
  let currentData = {}; // Biến để lưu dữ liệu form hiện tại

  // Hàm cleanup để remove listeners và nullify
  function cleanupListeners(element, event, handler) {
    if (element && handler) {
      element.removeEventListener(event, handler);
    }
  }

  // Form submission
  const submitHandler = function (e) {
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
  };
  creditForm.addEventListener("submit", submitHandler);

  // Modal handlers
  const getTipsHandler = showTips;
  document
    .getElementById("getTipsBtn")
    .addEventListener("click", getTipsHandler);
  const viewHistoryHandler = showHistory;
  document
    .getElementById("viewHistoryBtn")
    .addEventListener("click", viewHistoryHandler);
  const newSearchHandler = function () {
    creditResult.style.display = "none";
    creditForm.style.display = "grid"; // Thay "block" thành "grid"
    creditForm.reset();
  };
  document
    .getElementById("newSearchBtn")
    .addEventListener("click", newSearchHandler);

  // Close modal handlers
  const closeTipsHandler = function () {
    document.getElementById("tipsModal").style.display = "none";
  };
  document
    .getElementById("closeTipsModal")
    .addEventListener("click", closeTipsHandler);

  const closeHistoryHandler = function () {
    document.getElementById("historyModal").style.display = "none";
  };
  document
    .getElementById("closeHistoryModal")
    .addEventListener("click", closeHistoryHandler);

  // Xóa lịch sử
  const clearHistoryHandler = function () {
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
  };
  document
    .getElementById("clearHistoryBtn")
    .addEventListener("click", clearHistoryHandler);

  // Close modal when clicking outside
  const windowClickHandler = function (event) {
    const tipsModal = document.getElementById("tipsModal");
    const historyModal = document.getElementById("historyModal");

    if (event.target === tipsModal) {
      tipsModal.style.display = "none";
    }
    if (event.target === historyModal) {
      historyModal.style.display = "none";
    }
  };
  window.addEventListener("click", windowClickHandler);

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
      const enrichInternetHandler = function () {
        enrichData("internet");
      };
      btnInternet.addEventListener("click", enrichInternetHandler);

      const enrichFileHandler = function () {
        enrichData("file");
      };
      btnFile.addEventListener("click", enrichFileHandler);

      // Cleanup buttons khi error hide (thêm ở showError end)
      // Nhưng để đơn giản, khi showError gọi lại sẽ remove existingBtns
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
    modal.style.backgroundColor = "rgba(0, 0, 0, 0.6)";
    modal.style.display = "none";
    modal.style.justifyContent = "center";
    modal.style.alignItems = "center";
    modal.style.zIndex = "1000";
    modal.style.backdropFilter = "blur(5px)";

    const modalContent = document.createElement("div");
    modalContent.style.backgroundColor = "#ffffff";
    modalContent.style.padding = "0";
    modalContent.style.borderRadius = "16px";
    modalContent.style.boxShadow = "0 20px 60px rgba(0, 0, 0, 0.15)";
    modalContent.style.width = "90%";
    modalContent.style.maxWidth = "700px";
    modalContent.style.maxHeight = "90vh";
    modalContent.style.overflowY = "auto";
    modalContent.style.fontFamily =
      "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
    modalContent.style.position = "relative";

    // Header with VPBank colors
    const header = document.createElement("div");
    header.style.background =
      "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)";
    header.style.padding = "25px 30px";
    header.style.borderRadius = "16px 16px 0 0";
    header.style.position = "relative";
    header.style.overflow = "hidden";

    // VPBank accent pattern
    const accent = document.createElement("div");
    accent.style.position = "absolute";
    accent.style.top = "0";
    accent.style.right = "0";
    accent.style.width = "100px";
    accent.style.height = "100px";
    accent.style.background = "linear-gradient(45deg, #f39c12, #e67e22)";
    accent.style.borderRadius = "50%";
    accent.style.transform = "translate(50%, -50%)";
    accent.style.opacity = "0.1";
    header.appendChild(accent);

    const title = document.createElement("h2");
    title.textContent = "Enriched User Information";
    title.style.color = "#ffffff";
    title.style.margin = "0";
    title.style.fontSize = "24px";
    title.style.fontWeight = "600";
    title.style.textShadow = "0 2px 4px rgba(0, 0, 0, 0.2)";
    title.style.position = "relative";
    title.style.zIndex = "1";
    header.appendChild(title);

    modalContent.appendChild(header);

    // Content area
    const contentArea = document.createElement("div");
    contentArea.style.padding = "30px";
    contentArea.style.backgroundColor = "#fafbfc";

    const infoGrid = document.createElement("div");
    infoGrid.style.display = "grid";
    infoGrid.style.gridTemplateColumns = "repeat(auto-fit, minmax(300px, 1fr))";
    infoGrid.style.gap = "20px";
    infoGrid.style.marginBottom = "30px";

    // Function to format currency
    function formatCurrency(value) {
      if (
        !value ||
        value === "Không có thông tin" ||
        value === "No information"
      ) {
        return "No information";
      }
      // Remove any existing formatting
      const numericValue = value.toString().replace(/[^\d]/g, "");
      if (!numericValue || numericValue === "0") {
        return "No information";
      }
      // Format with dots every 3 digits
      return numericValue.replace(/\B(?=(\d{3})+(?!\d))/g, ".") + " VND";
    }

    // Function to format links
    function formatLinks(value) {
      if (
        !value ||
        value === "Không có thông tin" ||
        value === "No information"
      ) {
        return "No information";
      }
      // Split by comma and create clickable links
      const links = value.split(",").map((link) => {
        const trimmedLink = link.trim();
        if (trimmedLink.startsWith("http")) {
          return `<a href="${trimmedLink}" target="_blank" style="color: #1e3c72; text-decoration: none; word-break: break-all;">${trimmedLink}</a>`;
        }
        return trimmedLink;
      });
      return links.join(", ");
    }

    // Updated fields in English
    const fields = [
      { key: "age", label: "Age", type: "text" },
      { key: "address", label: "Address", type: "text" },
      { key: "email_address", label: "Email Address", type: "text" },
      { key: "phone_number", label: "Phone Number", type: "text" },
      { key: "job_title", label: "Job Title", type: "text" },
      { key: "current_company", label: "Current Company", type: "text" },
      { key: "educational_level", label: "Education Level", type: "text" },
      { key: "occupation", label: "Occupation", type: "text" },
      { key: "criminal_record", label: "Criminal Record", type: "text" },
      { key: "stock_assets", label: "Stock Assets", type: "currency" },
      {
        key: "source_of_information",
        label: "Information Source",
        type: "links",
      },
      { key: "confidence_level", label: "Confidence Level", type: "text" },
    ];

    fields.forEach((field) => {
      const fieldContainer = document.createElement("div");
      fieldContainer.style.backgroundColor = "#ffffff";
      fieldContainer.style.padding = "20px";
      fieldContainer.style.borderRadius = "12px";
      fieldContainer.style.border = "1px solid #e1e8ed";
      fieldContainer.style.boxShadow = "0 2px 8px rgba(0, 0, 0, 0.05)";
      fieldContainer.style.transition = "all 0.3s ease";
      fieldContainer.style.position = "relative";

      // Hover effect
      fieldContainer.onmouseover = function () {
        this.style.boxShadow = "0 4px 16px rgba(30, 60, 114, 0.1)";
        this.style.transform = "translateY(-2px)";
      };
      fieldContainer.onmouseout = function () {
        this.style.boxShadow = "0 2px 8px rgba(0, 0, 0, 0.05)";
        this.style.transform = "translateY(0)";
      };

      // VPBank accent line
      const accentLine = document.createElement("div");
      accentLine.style.position = "absolute";
      accentLine.style.top = "0";
      accentLine.style.left = "0";
      accentLine.style.width = "4px";
      accentLine.style.height = "100%";
      accentLine.style.background = "linear-gradient(180deg, #1e3c72, #f39c12)";
      accentLine.style.borderRadius = "0 0 8px 8px";
      fieldContainer.appendChild(accentLine);

      const label = document.createElement("div");
      label.textContent = field.label;
      label.style.color = "#1e3c72";
      label.style.fontSize = "14px";
      label.style.fontWeight = "600";
      label.style.marginBottom = "8px";
      label.style.textTransform = "uppercase";
      label.style.letterSpacing = "0.5px";

      const value = document.createElement("div");
      let displayValue;

      if (
        data[field.key] !== null &&
        data[field.key] !== undefined &&
        data[field.key] !== "Không có thông tin"
      ) {
        switch (field.type) {
          case "currency":
            displayValue = formatCurrency(data[field.key]);
            break;
          case "links":
            displayValue = formatLinks(data[field.key]);
            break;
          default:
            displayValue = data[field.key];
        }
      } else {
        displayValue = "No information";
      }

      if (field.type === "links") {
        value.innerHTML = displayValue;
      } else {
        value.textContent = displayValue;
      }

      value.style.color = "#2c3e50";
      value.style.fontSize = "16px";
      value.style.fontWeight = "500";
      value.style.lineHeight = "1.4";
      value.style.wordBreak = "break-word";

      fieldContainer.appendChild(label);
      fieldContainer.appendChild(value);
      infoGrid.appendChild(fieldContainer);
    });

    contentArea.appendChild(infoGrid);

    // Button container
    const buttonContainer = document.createElement("div");
    buttonContainer.style.display = "flex";
    buttonContainer.style.gap = "15px";
    buttonContainer.style.justifyContent = "center";
    buttonContainer.style.paddingTop = "20px";
    buttonContainer.style.borderTop = "1px solid #e1e8ed";

    // Continue button
    const continueBtn = document.createElement("button");
    continueBtn.textContent = "Continue Credit Scoring";
    continueBtn.style.background =
      "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)";
    continueBtn.style.color = "white";
    continueBtn.style.padding = "14px 28px";
    continueBtn.style.border = "none";
    continueBtn.style.borderRadius = "10px";
    continueBtn.style.cursor = "pointer";
    continueBtn.style.fontSize = "16px";
    continueBtn.style.fontWeight = "600";
    continueBtn.style.transition = "all 0.3s ease";
    continueBtn.style.boxShadow = "0 4px 12px rgba(30, 60, 114, 0.3)";
    continueBtn.style.textTransform = "uppercase";
    continueBtn.style.letterSpacing = "0.5px";
    continueBtn.style.minWidth = "200px";

    continueBtn.onmouseover = function () {
      this.style.transform = "translateY(-2px)";
      this.style.boxShadow = "0 6px 20px rgba(30, 60, 114, 0.4)";
    };
    continueBtn.onmouseout = function () {
      this.style.transform = "translateY(0)";
      this.style.boxShadow = "0 4px 12px rgba(30, 60, 114, 0.3)";
    };

    const continueBtnHandler = function () {
      modal.style.display = "none";
      document.body.removeChild(modal);
      // Continue with credit scoring
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
          showError("Error during credit scoring lookup.");
          console.error("Error:", error);
        });
      // Cleanup
      cleanupListeners(continueBtn, "click", continueBtnHandler);
      cleanupListeners(closeBtn, "click", closeBtnHandler);
      cleanupListeners(modal, "click", modalClickHandler);
      modal = null;
    };
    continueBtn.addEventListener("click", continueBtnHandler);

    // Close button
    const closeBtn = document.createElement("button");
    closeBtn.textContent = "Close";
    closeBtn.style.background =
      "linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%)";
    closeBtn.style.color = "white";
    closeBtn.style.padding = "14px 28px";
    closeBtn.style.border = "none";
    closeBtn.style.borderRadius = "10px";
    closeBtn.style.cursor = "pointer";
    closeBtn.style.fontSize = "16px";
    closeBtn.style.fontWeight = "600";
    closeBtn.style.transition = "all 0.3s ease";
    closeBtn.style.boxShadow = "0 4px 12px rgba(149, 165, 166, 0.3)";
    closeBtn.style.textTransform = "uppercase";
    closeBtn.style.letterSpacing = "0.5px";
    closeBtn.style.minWidth = "120px";

    closeBtn.onmouseover = function () {
      this.style.transform = "translateY(-2px)";
      this.style.boxShadow = "0 6px 20px rgba(149, 165, 166, 0.4)";
    };
    closeBtn.onmouseout = function () {
      this.style.transform = "translateY(0)";
      this.style.boxShadow = "0 4px 12px rgba(149, 165, 166, 0.3)";
    };

    const closeBtnHandler = function () {
      modal.style.display = "none";
      document.body.removeChild(modal);
      hideLoading();
      // Cleanup
      cleanupListeners(continueBtn, "click", continueBtnHandler);
      cleanupListeners(closeBtn, "click", closeBtnHandler);
      cleanupListeners(modal, "click", modalClickHandler);
      modal = null;
    };
    closeBtn.addEventListener("click", closeBtnHandler);

    buttonContainer.appendChild(continueBtn);
    buttonContainer.appendChild(closeBtn);
    contentArea.appendChild(buttonContainer);

    modalContent.appendChild(contentArea);
    modal.appendChild(modalContent);

    // Close modal when clicking outside
    const modalClickHandler = function (event) {
      if (event.target === modal) {
        modal.style.display = "none";
        document.body.removeChild(modal);
        hideLoading();
        // Cleanup
        cleanupListeners(continueBtn, "click", continueBtnHandler);
        cleanupListeners(closeBtn, "click", closeBtnHandler);
        cleanupListeners(modal, "click", modalClickHandler);
        modal = null;
      }
    };
    modal.addEventListener("click", modalClickHandler);

    // Responsive design
    const mediaQuery = window.matchMedia("(max-width: 768px)");
    function handleResponsive(e) {
      if (e.matches) {
        // Mobile styles
        modalContent.style.width = "95%";
        modalContent.style.maxHeight = "95vh";
        contentArea.style.padding = "20px";
        header.style.padding = "20px";
        infoGrid.style.gridTemplateColumns = "1fr";
        infoGrid.style.gap = "15px";
        buttonContainer.style.flexDirection = "column";
        buttonContainer.style.gap = "10px";
        continueBtn.style.minWidth = "100%";
        closeBtn.style.minWidth = "100%";
      } else {
        // Desktop styles
        modalContent.style.width = "90%";
        modalContent.style.maxHeight = "90vh";
        contentArea.style.padding = "30px";
        header.style.padding = "25px 30px";
        infoGrid.style.gridTemplateColumns =
          "repeat(auto-fit, minmax(300px, 1fr))";
        infoGrid.style.gap = "20px";
        buttonContainer.style.flexDirection = "row";
        buttonContainer.style.gap = "15px";
        continueBtn.style.minWidth = "200px";
        closeBtn.style.minWidth = "120px";
      }
    }

    mediaQuery.addListener(handleResponsive);
    handleResponsive(mediaQuery);

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
  const nationalIdInputHandler = function (e) {
    let value = e.target.value.replace(/\D/g, ""); // Remove non-digits
    if (value.length > 12) {
      value = value.slice(0, 12);
    }
    e.target.value = value;
  };
  document
    .getElementById("nationalId")
    .addEventListener("input", nationalIdInputHandler);

  // Format full name input
  const fullNameInputHandler = function (e) {
    let value = e.target.value.toUpperCase();
    // Remove special characters except spaces
    value = value.replace(/[^A-Z\s]/g, "");
    e.target.value = value;
  };
  document
    .getElementById("fullName")
    .addEventListener("input", fullNameInputHandler);

  // Cleanup khi trang unload (tùy chọn, để tránh leak nếu SPA)
  window.addEventListener("beforeunload", function () {
    cleanupListeners(creditForm, "submit", submitHandler);
    cleanupListeners(
      document.getElementById("getTipsBtn"),
      "click",
      getTipsHandler
    );
    cleanupListeners(
      document.getElementById("viewHistoryBtn"),
      "click",
      viewHistoryHandler
    );
    cleanupListeners(
      document.getElementById("newSearchBtn"),
      "click",
      newSearchHandler
    );
    cleanupListeners(
      document.getElementById("closeTipsModal"),
      "click",
      closeTipsHandler
    );
    cleanupListeners(
      document.getElementById("closeHistoryModal"),
      "click",
      closeHistoryHandler
    );
    cleanupListeners(
      document.getElementById("clearHistoryBtn"),
      "click",
      clearHistoryHandler
    );
    cleanupListeners(window, "click", windowClickHandler);
    cleanupListeners(
      document.getElementById("nationalId"),
      "input",
      nationalIdInputHandler
    );
    cleanupListeners(
      document.getElementById("fullName"),
      "input",
      fullNameInputHandler
    );
    currentData = null;
  });
});
