# 🚀 Hướng dẫn Chạy Standalone (Không Docker)

Tài liệu này hướng dẫn cách build và chạy hệ thống Máy Chấm Công dưới dạng file thực thi (.exe) trên Windows.

## 1. Yêu cầu Hệ thống
- **Python 3.12+** và **uv** (để build).
- **Node.js & npm** (để build frontend).
- **ODBC Driver 18 for SQL Server** (để kết nối database).

## 2. Cách Build (Tạo file .exe)

Tôi đã tạo sẵn file `build_standalone.bat`. Bạn chỉ cần chạy nó:

1. Mở Terminal (PowerShell hoặc CMD) tại thư mục gốc của dự án.
2. Chạy lệnh:
   ```cmd
   .\build_standalone.bat
   ```
3. Sau khi chạy xong, thư mục `dist\TimeAttendance` sẽ chứa toàn bộ ứng dụng.

## 3. Cách Chạy Ứng dụng

Vào thư mục `dist\TimeAttendance` và chạy file `TimeAttendance.exe`.

### Chạy với Port tùy chỉnh
Bạn có thể chỉ định Port bằng tham số `--port`:
```cmd
# Chạy ở port 9000
cd dist\TimeAttendance
.\TimeAttendance.exe --port 9000
```

### Chạy với Host tùy chỉnh
```cmd
.\TimeAttendance.exe --host 0.0.0.0 --port 8080
```

## 4. Cấu hình Quan trọng

Khi chạy standalone, ứng dụng sẽ đọc các file sau trong thư mục `dist\TimeAttendance`:

- **`backend\.env`**: Cấu hình kết nối SQL Server (IP, DB Name, User/Pass).
- **`machines.txt`**: Danh sách IP các máy chấm công.
- **`employee_work_shift.xlsx`**: File Excel lịch làm việc.
- **`audio/`**: Thư mục chứa các file âm thanh (Bạn tự copy thư mục này vào cạnh file .exe).

> [!IMPORTANT]
> - Nếu bạn di chuyển thư mục `dist\TimeAttendance` sang server khác, hãy đảm bảo đã cài đặt **ODBC Driver 18** trên server đó.
> - Thư mục **audio** phải nằm cùng cấp với file **TimeAttendance.exe** thì âm thanh thông báo mới hoạt động.

## 5. Cấu trúc thư mục Distribution
```text
dist/TimeAttendance/
├── TimeAttendance.exe      <-- File chạy chính
├── _internal/              <-- Thư viện hệ thống
├── backend/
│   └── .env                <-- Cấu hình Database
├── audio/                  <-- [BẠN TỰ COPY VÀO ĐÂY]
├── machines.txt            <-- Danh sách máy
└── employee_work_shift.xlsx <-- Dữ liệu ca làm việc
```
