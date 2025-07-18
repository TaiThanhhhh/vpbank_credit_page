# vpbank_credit_page

**Dự án hackathon VPBank 2025 (Enhance Credit Score)**

---

## Thành viên dự án:

- **Nguyễn Đức Minh**  
  AI Engineer / Data Scientist  
  bohnas.work@gmail.com  
  FPT University | Artificial Intelligence  
  [LinkedIn](https://www.linkedin.com/in/bohnas-minh/)

- **Nguyễn Thành Tài**  
  Software Engineer  
  taithanh16052002@gmail.com  
  Industry and Trade University | Software Engineering  
  [LinkedIn](https://www.linkedin.com/in/taithanh/)

- **Nguyễn Thị Hà Phương**  
  Leader - Data Scientist  
  hazel.nguyen.works@gmail.com  
  Vietnam University of Science, Vietnam National University Hanoi | Mathematics and Computer Science  
  [LinkedIn](https://www.linkedin.com/in/hazel-nguyen-4870162ba/)

- **Lê Thị Diễm My**  
  Data Scientist  
  diemmy2003204@gmail.com  
  Fulbright University Vietnam | Computer Science  
  [LinkedIn](https://www.linkedin.com/in/diem-my-le/)

- **Lê Đức Anh**  
  Data Scientist  
  ducanh08112005@gmail.com  
  Duy Tan University | Data Science  
  [LinkedIn](https://www.linkedin.com/in/đức-anh-lê-98100530a/)

---

## 🚀 Hướng Dẫn Cài Đặt và Chạy Project:

### 1. Tạo thư mục cho project:
```bash
mkdir vpbank_credit_app
cd vpbank_credit_app
```

### 2. Tạo virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Cài đặt các dependencies:
```bash
pip install Flask
pip install shap joblib boto3 pandas numpy scikit-learn google
```

### 4. Tạo cấu trúc thư mục
```bash
vpbank_credit_app/
├── app.py
├── app_enrich.py
├── requirements.txt
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── templates/
    ├── base.html
    └── index.html
```

### 5. Copy code vào các file tương ứng:
- app.py: Đưa code xử lý model, API, và Flask vào file này.

- app_enrich.py: File này sẽ xử lý tác vụ enrich dữ liệu bằng LLM (Google Search) để bổ sung thông tin người dùng còn thiếu.

- requirements.txt: Liệt kê các thư viện cần thiết cho project.

- static/css/style.css: Các stylesheet cho ứng dụng.

- static/js/main.js: Các đoạn JavaScript cho giao diện.

- templates/base.html: Giao diện cơ bản cho ứng dụng.

- templates/index.html: Trang chính để nhập dữ liệu và hiển thị kết quả.

### 6. Chạy dữ liệu
```bash
python app.py
```

### 7. Truy cập demo ở: [Link]{https://vpbank-credit-page.onrender.com/}

## 🧑‍💻 Tính Năng Chính:
- Tra cứu điểm tín dụng theo CMND/CCCD: Nhập thông tin CMND/CCCD và tra cứu điểm tín dụng.

- Hiển thị chi tiết các yếu tố ảnh hưởng: Các yếu tố như thu nhập, lịch sử tín dụng, mức chi tiêu.

- Giải thích điểm tín dụng: Cung cấp lời giải thích về cách tính điểm tín dụng.

- Xem lịch sử tra cứu: Hiển thị lịch sử các lần tra cứu trước đó.

- Tips cải thiện điểm tín dụng: Cung cấp gợi ý giúp cải thiện điểm tín dụng.

- Responsive design: Ứng dụng có thể sử dụng tốt trên các thiết bị di động và máy tính.

- Validation input: Kiểm tra tính hợp lệ của dữ liệu nhập vào.

- Error handling: Xử lý các lỗi khi nhập sai thông tin.

- Sử dụng LLM để tìm kiếm và bổ sung dữ liệu: Dự án hỗ trợ sử dụng mô hình ngôn ngữ lớn (LLM) để tự động tra cứu thông tin trên Google và bổ sung các trường dữ liệu còn thiếu (ví dụ: thông tin đầy đủ về người dùng như họ tên, địa chỉ, tuổi, v.v.).

