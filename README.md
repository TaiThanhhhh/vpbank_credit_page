# vpbank_credit_page
dự án hackathon vpbank 2025 (enhace credit score)
THÀNH VIÊN DỰ ÁN: 
Nguyễn Đức Minh | AI engineer / Data Scientist | bohnas.work@gmail.com | FPT university | Artificial Intelligence | https://www.linkedin.com/in/bohnas-minh/

Nguyễn Thành Tài | Software Engineer | taithanh16052002@gmail.com | Industry and Trade University | Software Engineering | https://www.linkedin.com/in/taithanh/

Nguyễn Thị Hà Phương | Leader - Data Scientist | hazel.nguyen.works@gmail.com | Vietnam University of Science, Vietnam National University Hanoi | Mathematics and Computer Science | https://www.linkedin.com/in/hazel-nguyen-4870162ba/

Lê Thị Diễm My | Data Scientist | diemmy2003204@gmail.com | Fulbright University Vietnam | Computer Science | https://www.linkedin.com/in/diem-my-le/

Lê Đức Anh | Data Scientist | ducanh08112005@gmail.com | Duy Tan University | Data Science | https://www.linkedin.com/in/đức-anh-lê-98100530a/



HƯỚNG DẪN CÀI ĐẶT VÀ CHẠY PROJECT:

1. Tạo thư mục project:
   mkdir vpbank_credit_app
   cd vpbank_credit_app

2. Tạo virtual environment:
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows

3. Cài đặt dependencies:
   pip install Flask

4. Tạo cấu trúc thư mục:
   vpbank_credit_app/
   ├── app.py
   ├── requirements.txt
   ├── static/
   │   ├── css/
   │   │   └── style.css
   │   └── js/
   │       └── main.js
   └── templates/
       ├── base.html
       └── index.html

5. Copy code vào các file tương ứng

6. Chạy application:
   python app.py

7. Truy cập: http://localhost:5000

TÍNH NĂNG CHÍNH:
- Tra cứu điểm tín dụng theo CMND/CCCD
- Hiển thị chi tiết các yếu tố ảnh hưởng
- Giải thích điểm tín dụng
- Xem lịch sử tra cứu
- Tips cải thiện điểm tín dụng
- Responsive design
- Validation input
- Error handling

API ENDPOINTS:
- POST /api/lookup - Tra cứu điểm tín dụng
- GET /api/history - Lấy lịch sử tra cứu
- GET /api/tips - Lấy tips cải thiện điểm tín dụng

DỮ LIỆU MẪU:
Tên: Huynh Quoc G
CCCD: 640602618404
Tên: Hoang Bao A
CCCD: 880997244659
Tên: Phan Hong B
CCCD: 008846790847
Tên: Vo Anh J
CCCD: 061458585968
Tên: Dang Bao C
CCCD: 668649444847
Tên: Tran Van H
CCCD: 600852358063
Tên: Vo Hong H
CCCD: 629277046950
Tên: Phan Dinh I
CCCD: 139425203922
Tên: Nguyen Bao J
CCCD: 998991272339
Tên: Pham Anh I
CCCD: 827911066063

Các CMND khác báo lỗi do không nằm trong bộ dữ liệu
