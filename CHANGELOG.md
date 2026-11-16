# Changelog

## [1.1.0] - 2026-11-16

### Thêm mới
- `ViettelSMSClient.from_env()`: tạo client từ các biến môi trường `VIETTEL_SMS_*`.
- Dùng được với `with` (context manager), có thêm hàm `close()`. Client dùng `requests.Session` để tái sử dụng kết nối.
- Tham số mới cho client: `verify` (chứng chỉ SSL), `base_url`, `session`, `templates`.
- Số điện thoại được chuẩn hoá tự động (`0912345678` -> `84912345678`, bỏ khoảng trắng, dấu `+`, bỏ số trùng). `msisdn` nhận một chuỗi hoặc một danh sách. Có thêm hàm `normalize_msisdn()`.
- `render_template()`: xem trước nội dung tin mà không gửi.
- Ngoại lệ mới: `SendError`, `SMSConnectionError`, `InvalidResponseError`, `TemplateError`.
- Ghi log qua logger `viettel_sms` (không bao giờ ghi mật khẩu).
- Kèm `py.typed` để hỗ trợ type checker.
- Thêm unit test, GitHub Actions CI và tự publish lên PyPI khi push tag.

### Thay đổi
- **Client chỉ đăng nhập khi gửi tin lần đầu**, không còn đăng nhập ngay khi khởi tạo. Muốn kiểm tra tài khoản sớm, hãy gọi `client.login()`.
- Lỗi mạng và phản hồi không phải JSON khi gửi tin giờ được bọc thành `SMSConnectionError` và `InvalidResponseError`, thay vì lỗi gốc của `requests`.
- Lỗi template báo `TemplateError` và liệt kê đủ các tham số còn thiếu. `TemplateError` vẫn kế thừa `KeyError`.
- `ValidationError` đổi tên thành `SendError`. Tên cũ vẫn dùng được.
- Việc làm mới token an toàn khi nhiều thread cùng gửi tin.
- Yêu cầu Python >= 3.9.

### Sửa lỗi
- File `LICENSE` trước đây bị trống.
- `tests/test_client.py` trước đây gửi SMS thật khi chạy `pytest`. Đoạn code này đã chuyển sang `examples/send_otp.py`.

## [1.0.0] - 2026-11-12
- Phát hành lần đầu.
