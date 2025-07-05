document.addEventListener('DOMContentLoaded', function() {
    const creditForm = document.getElementById('creditForm');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const errorMessage = document.getElementById('errorMessage');
    const creditResult = document.getElementById('creditResult');
    
    // Form submission
    creditForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(creditForm);
        const data = {
            full_name: formData.get('full_name'),
            national_id: formData.get('national_id')
        };
        
        // Show loading
        showLoading();
        
        // Submit to API
        fetch('/api/lookup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            
            if (data.success) {
                displayCreditResult(data.data);
            } else {
                showError(data.message);
            }
        })
        .catch(error => {
            hideLoading();
            showError('Đã xảy ra lỗi trong quá trình tra cứu. Vui lòng thử lại sau.');
            console.error('Error:', error);
        });
    });
    
    // Modal handlers
    document.getElementById('getTipsBtn').addEventListener('click', showTips);
    document.getElementById('viewHistoryBtn').addEventListener('click', showHistory);
    document.getElementById('newSearchBtn').addEventListener('click', function() {
        creditResult.style.display = 'none';
        creditForm.style.display = 'block';
        creditForm.reset();
    });
    
    // Close modal handlers
    document.getElementById('closeTipsModal').addEventListener('click', function() {
        document.getElementById('tipsModal').style.display = 'none';
    });
    
    document.getElementById('closeHistoryModal').addEventListener('click', function() {
        document.getElementById('historyModal').style.display = 'none';
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        const tipsModal = document.getElementById('tipsModal');
        const historyModal = document.getElementById('historyModal');
        
        if (event.target === tipsModal) {
            tipsModal.style.display = 'none';
        }
        if (event.target === historyModal) {
            historyModal.style.display = 'none';
        }
    });
    
    function showLoading() {
        loadingSpinner.style.display = 'block';
        errorMessage.style.display = 'none';
        creditResult.style.display = 'none';
    }
    
    function hideLoading() {
        loadingSpinner.style.display = 'none';
    }
    
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
        creditResult.style.display = 'none';
    }
    
    function displayCreditResult(data) {
        // Update score display
        document.getElementById('scoreNumber').textContent = data.credit_score;
        document.getElementById('scoreLabel').textContent = data.score_level;
        
        // Update factors
        document.getElementById('utilizationPercent').textContent = data.credit_card_utilization + '%';
        document.getElementById('paymentPercent').textContent = data.payment_history + '%';
        document.getElementById('historyYears').textContent = data.credit_history_years + ' years';
        document.getElementById('historyMonths').textContent = data.credit_history_months + ' months';
        
        // Update explanation
        document.getElementById('explanationText').textContent = data.explanation;
        
        // Update score circle color based on score
        const scoreCircle = document.querySelector('.score-circle');
        const score = data.credit_score;
        let percentage = (score / 850) * 100;
        let color = '#4caf50'; // Green for good scores
        
        if (score < 580) {
            color = '#f44336'; // Red for poor scores
        } else if (score < 670) {
            color = '#ff9800'; // Orange for fair scores
        } else if (score < 740) {
            color = '#2196f3'; // Blue for good scores
        }
        
        scoreCircle.style.background = `conic-gradient(${color} 0deg ${percentage * 3.6}deg, #e0e0e0 ${percentage * 3.6}deg 360deg)`;
        
        // Hide form and show result
        creditForm.style.display = 'none';
        creditResult.style.display = 'block';
        errorMessage.style.display = 'none';
    }
    
    function showTips() {
        fetch('/api/tips')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const tipsList = document.getElementById('tipsList');
                    tipsList.innerHTML = '';
                    
                    data.data.forEach(tip => {
                        const li = document.createElement('li');
                        li.textContent = tip;
                        tipsList.appendChild(li);
                    });
                    
                    document.getElementById('tipsModal').style.display = 'flex';
                }
            })
            .catch(error => {
                console.error('Error loading tips:', error);
                alert('Không thể tải tips. Vui lòng thử lại sau.');
            });
    }
    
    function showHistory() {
        fetch('/api/history')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const historyList = document.getElementById('historyList');
                    historyList.innerHTML = '';
                    
                    data.data.forEach(item => {
                        const historyItem = document.createElement('div');
                        historyItem.className = 'history-item';
                        historyItem.innerHTML = `
                            <div class="date">${item.date}</div>
                            <div class="score">Điểm tín dụng: ${item.score}</div>
                            <div class="action">${item.action}</div>
                        `;
                        historyList.appendChild(historyItem);
                    });
                    
                    document.getElementById('historyModal').style.display = 'flex';
                }
            })
            .catch(error => {
                console.error('Error loading history:', error);
                alert('Không thể tải lịch sử. Vui lòng thử lại sau.');
            });
    }
    
    // Format national ID input
    document.getElementById('nationalId').addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, ''); // Remove non-digits
        if (value.length > 12) {
            value = value.slice(0, 12);
        }
        e.target.value = value;
    });
    
    // Format full name input
    document.getElementById('fullName').addEventListener('input', function(e) {
        let value = e.target.value.toUpperCase();
        // Remove special characters except spaces
        value = value.replace(/[^A-Z\s]/g, '');
        e.target.value = value;
    });
});