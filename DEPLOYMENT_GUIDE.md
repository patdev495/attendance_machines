# Hướng dẫn Triển khai Time Attendance System lên Render.com (Miễn phí)

Tài liệu này hướng dẫn cách đưa toàn bộ hệ thống (Frontend + Backend + Database) lên Render bằng **1 Web Service duy nhất** để chạy chế độ **Demo Portfolio**.

## Điểm nổi bật của bản Demo
1. **1 URL duy nhất**: Không lo lỗi CORS, không cần quản lý nhiều service.
2. **Demo Mode (SQLite)**: Tự động chuyển DB sang SQLite, không cần thuê server MSSQL đắt đỏ.
3. **Dữ liệu thật (Snapshot)**: Sử dụng chính dữ liệu của công ty bạn (200 nhân viên) được trích xuất để làm demo, rất chân thực.
4. **Live Monitor Simulator**: Tự động phát sinh sự kiện chấm công (WebSocket) mỗi 10-25 giây từ các IP thật để màn hình Live Dashboard "nhảy" liên tục như đang chạy thật ở nhà máy.

---

## Các bước chuẩn bị dữ liệu (Làm tại máy local)
Trước khi push code lên GitHub, bạn cần tạo một bản sao (snapshot) dữ liệu thật sang SQLite:
1. Mở Terminal tại thư mục gốc của project.
2. Chạy lệnh clone dữ liệu:
   ```bash
   uv run python backend/scripts/migrate_to_sqlite.py
   ```
3. Lệnh này sẽ tạo ra file `demo_data/attendance.db`. File này đã được thêm vào `.gitignore` dưới dạng ngoại lệ (whitelist) để có thể push lên GitHub. File cấu hình `machines.txt` cũng được tự động cập nhật các IP thật.
4. Build lại frontend để cập nhật giao diện mới nhất:
   ```bash
   cd frontend
   npm run build
   cd ..
   ```

---

## Các bước triển khai (1 Click Deploy)

### Bước 1: Đẩy Code lên GitHub
1. Mở Terminal, commit toàn bộ code bao gồm cả file `demo_data/attendance.db` và thư mục `backend/static/` (chứa frontend đã build).
   ```bash
   git add .
   git commit -m "Prepare demo deployment with real data snapshot"
   git push origin main
   ```

### Bước 2: Tạo Service trên Render
1. Đăng nhập vào [Render.com](https://render.com/).
2. Chọn **New** -> **Blueprints**.
3. Kết nối với GitHub Repository của bạn.
4. Render sẽ tự động đọc file `render.yaml` và tạo ra Web Service tên là `attendance-demo`.
5. Chọn **Apply** để bắt đầu quá trình deploy.

### Quá trình Render Build diễn ra như thế nào?
Theo file `render.yaml`, Render sẽ tự động chạy:
```bash
pip install -r requirements_render.txt
```
- Lệnh này cài đặt Python (bỏ qua các thư viện phần cứng như `pyzk` để tránh lỗi trên Linux).

Khi chạy (`startCommand`):
```bash
python backend/src/main.py --host 0.0.0.0 --port $PORT
```
- FastAPI sẽ khởi động ở chế độ `DEMO_MODE=true` (được cấu hình trong `render.yaml`), phục vụ API tại `/api/*` và phục vụ giao diện tại `/`. Nó sẽ đọc trực tiếp từ file `attendance.db` mà bạn đã push lên.

---

## Kiểm tra sau khi Deploy
1. Sau khoảng 5-7 phút, Render sẽ báo **Live**.
2. Bấm vào đường link của Render (ví dụ: `https://attendance-demo.onrender.com`).
3. Truy cập màn hình **Theo dõi trực tiếp (Live Monitor)**:
   - Bạn sẽ thấy status của các máy thật (ví dụ: `192.168.209.21`) là `Connected`.
   - Các bản ghi chấm công ảo sẽ liên tục được tự động thêm vào dựa trên các nhân viên có thật trong DB.
4. Truy cập **Bảng công ngày**: Chọn khoảng thời gian có dữ liệu (ví dụ: tháng 4/2026) để xem bảng công đã được tính toán đầy đủ giờ làm, giờ tăng ca.

## Lưu ý về Render Miễn Phí
- Render Free Tier sẽ **"ngủ đông" (sleep)** nếu không có request nào trong vòng 15 phút.
- Khi truy cập lại sau khi ngủ đông, hệ thống sẽ mất khoảng 30-50 giây để khởi động lại máy chủ (Cold Start).
- Vì Render Free không cung cấp Persistent Disk, mỗi lần máy chủ khởi động lại sau 1 thời gian dài, nó sẽ **khôi phục DB về trạng thái gốc của file `attendance.db` trên GitHub**. Điều này đảm bảo database demo của bạn không bao giờ bị phình to hoặc bị người lạ phá hoại (ví dụ xóa/sửa bậy bạ), hệ thống luôn tự làm mới lại dữ liệu y như lúc bạn vừa deploy!
