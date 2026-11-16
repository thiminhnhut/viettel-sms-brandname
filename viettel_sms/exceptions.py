"""Các ngoại lệ của thư viện viettel-sms-brandname."""


class SMSBrandnameError(Exception):
    """Ngoại lệ cơ sở. Mọi lỗi của thư viện đều kế thừa lớp này.

    Attributes:
        code: Mã lỗi (mã của Viettel như ``GECO_xxx`` hoặc mã nội bộ như ``CONN_ERR``).
        message: Mô tả lỗi.
    """

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(code, message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class AuthenticationError(SMSBrandnameError):
    """Đăng nhập thất bại (sai username/password, tài khoản bị khóa...)."""


class SendError(SMSBrandnameError):
    """Viettel từ chối yêu cầu gửi tin (brandname sai, nội dung không hợp lệ...)."""


# Giữ tên cũ để không làm hỏng code đang dùng phiên bản 1.0.x.
ValidationError = SendError


class SMSConnectionError(SMSBrandnameError):
    """Không kết nối được tới Viettel API (mất mạng, timeout, lỗi SSL...). Mã lỗi: ``CONN_ERR``."""


class InvalidResponseError(SMSBrandnameError):
    """Viettel trả về dữ liệu không đọc được (không phải JSON). Mã lỗi: ``INVALID_RESPONSE``."""


class TemplateError(SMSBrandnameError, KeyError):
    """Template chưa được đăng ký, sai cú pháp hoặc thiếu tham số.

    Kế thừa thêm ``KeyError`` để tương thích với phiên bản 1.0.x.
    """
