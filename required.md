# 📘 User Stories - Hệ thống Giám sát IoT sử dụng Flask, SQLite và Docker trên Raspberry Pi

---

## ✅ User Stories

---

### 1. 📍 Xem danh sách các node

**Title**: Xem danh sách các node trên bản đồ  
**As a** người dùng  
**I want** xem danh sách các node được triển khai  
**So that** tôi có thể biết vị trí và các chỉ số cảm biến của từng node

**Acceptance Criteria**:
- Trả về danh sách node có `longitude`, `latitude`, `nodeId`
- Bao gồm dữ liệu cảm biến: `tds`, `ph`, `humidity`, `temp`

---

### 2. 🔎 Xem chi tiết dữ liệu một node

**Title**: Xem dữ liệu chi tiết của node  
**As a** người dùng  
**I want** xem chi tiết dữ liệu cảm biến và trạng thái của một node cụ thể  
**So that** tôi có thể giám sát thông tin từng node

**Acceptance Criteria**:
- Trả về `nodeId`, `time`, `status`, `sensor` data
- Cho phép xem lịch sử hoặc dữ liệu gần nhất

---

### 3. 📊 Dashboard tổng hợp nhiều node

**Title**: Hiển thị dashboard nhiều node  
**As a** quản trị viên  
**I want** xem tổng quan dữ liệu từ nhiều node cùng lúc  
**So that** tôi có thể giám sát toàn bộ hệ thống một cách trực quan

**Acceptance Criteria**:
- Dashboard hiển thị dữ liệu của ít nhất 20 node
- Bao gồm: `nodeId`, `status`, `time`, `sensor` data

---

### 4. 🧪 Bật / Tắt chế độ Dummy Data

**Title**: Bật / Tắt chế độ giả lập dữ liệu (Dumb Data)  
**As a** developer hoặc tester  
**I want** bật/tắt chức năng tự tạo dữ liệu giả mỗi 1 giây  
**So that** tôi có thể kiểm tra hệ thống mà không cần cảm biến thật

**Acceptance Criteria**:
- Có API bật: `POST /api/dumb-data/enable`
- Có API tắt: `POST /api/dumb-data/disable`
- Khi bật, hệ thống sinh dữ liệu mẫu mỗi giây cho từng node

---

### 5. ⏱️ Tự động tạo dữ liệu mỗi 1 giây

**Title**: Sinh dữ liệu mẫu định kỳ  
**As a** hệ thống  
**I want** tạo dữ liệu cảm biến mỗi giây  
**So that** hệ thống luôn có dữ liệu mới để test và xử lý

**Acceptance Criteria**:
- Mỗi node sẽ được tạo dữ liệu `tds`, `ph`, `humidity`, `temp` mới mỗi 1s
- Dữ liệu được lưu tạm thời trong RAM hoặc SQLite

---

### 6. 🔁 Cronjob kiểm tra trạng thái node

**Title**: Tự động kiểm tra status node mỗi 30 giây  
**As a** hệ thống  
**I want** kiểm tra xem node nào chưa có `status`  
**So that** có thể gửi dữ liệu cảm biến đến API xử lý (hiện giả lập `status = GOOD`)

**Acceptance Criteria**:
- Cronjob chạy mỗi 30 giây
- Kiểm tra bảng dữ liệu node
- Nếu node chưa có `status`, gửi dữ liệu cảm biến đến API (mock) và cập nhật `status = GOOD`

---

### 7. 🗺️ Xem tổng quan node trên bản đồ Leaflet

**Title**: Xem tổng quan node trên bản đồ Leaflet  
**As a** người dùng  
**I want** xem tổng quan các node trên bản đồ sử dụng Leaflet  
**So that** tôi có thể dễ dàng quan sát vị trí và thông tin nhanh của từng node

**Acceptance Criteria**:
- Tích hợp bản đồ Leaflet để hiển thị vị trí các node
- Mỗi node được hiển thị bằng một marker trên bản đồ
- Khi di chuột (hover) vào marker, hiển thị tooltip với thông tin chi tiết: `nodeId`, `status`, `temp`, `humidity`, `ph`, `tds`
- Có thể phóng to/thu nhỏ và di chuyển bản đồ để xem các node khác

---

## 📝 Ghi chú kỹ thuật:

- **Backend**: Flask (Python)
- **Database**: SQLite / LiteSQL (file-based, đơn giản cho Raspberry Pi)
- **Docker**: Triển khai trên Raspberry Pi bằng Docker container
- **Tạo dữ liệu giả**: thông qua thread Python
- **Lập lịch tự động**: sử dụng `thread` hoặc thư viện `APScheduler`

---

