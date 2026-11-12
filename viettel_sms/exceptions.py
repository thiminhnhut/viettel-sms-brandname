class SMSBrandnameError(Exception):
    """Ngoại lệ cơ sở cho thư viện Viettel SMS"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

class AuthenticationError(SMSBrandnameError):
    """Lỗi liên quan đến xác thực (Sai user/pass, token hết hạn)"""
    pass

class ValidationError(SMSBrandnameError):
    """Lỗi dữ liệu đầu vào hoặc nghiệp vụ từ Viettel"""
    pass