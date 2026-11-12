import requests
from typing import List, Dict, Any, Optional
from .exceptions import SMSBrandnameError, AuthenticationError, ValidationError

class ViettelSMSClient:
    ENDPOINTS = {
        "public": "https://apismsbrandname.viettelai.vn:8000",
        "ip": "https://171.234.245.145:8000",
        "internal": "https://10.208.67.177:8000"
    }

    def __init__(
        self, 
        username: str, 
        password: str, 
        env: str = "public",
        timeout: int = 10
    ):
        if env not in self.ENDPOINTS:
            raise ValueError(f"Environment '{env}' không hợp lệ. Chọn: {list(self.ENDPOINTS.keys())}")
        
        self.base_url = self.ENDPOINTS[env]
        self.username = username
        self.password = password
        self.timeout = timeout
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.templates: Dict[str, str] = {}
        
        # Đăng nhập lấy token khi khởi tạo
        self.login()

    def login(self):
        url = f"{self.base_url}/api/v1/auth/ws/login"
        try:
            response = requests.post(
                url, 
                json={"username": self.username, "password": self.password},
                timeout=self.timeout
            )
            data = response.json()
        except requests.RequestException as e:
            raise SMSBrandnameError("CONN_ERR", f"Lỗi kết nối mạng đến Viettel API: {str(e)}")

        if data.get("code") == "GECO_002":
            token_data = data.get("data", {})
            self.access_token = token_data.get("access_token")
            self.refresh_token = token_data.get("refresh_token")
        else:
            raise AuthenticationError(data.get("code", "SI_007"), data.get("message", "Đăng nhập thất bại"))

    def refresh_access_token(self):
        """Tự động làm mới token hoặc đăng nhập lại nếu refresh token hết hạn"""
        url = f"{self.base_url}/api/v1/auth/refresh-token"
        headers = {"refresh-token": self.refresh_token} if self.refresh_token else {}
        
        try:
            response = requests.post(url, headers=headers, timeout=self.timeout)
            data = response.json()
            if data.get("code") == "GECO_002":
                self.access_token = data.get("data", {}).get("access_token")
                return
        except Exception:
            pass
        
        # Nếu refresh token lỗi, fallback gọi lại login()
        self.login()

    def set_template(self, key: str, content: str):
        """Thêm hoặc cập nhật template mẫu tin nhắn"""
        self.templates[key] = content

    def _request_with_retry(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Hàm helper gửi request có cơ chế tự động xử lý hết hạn token (GECO_001)"""
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        headers["Content-Type"] = "application/json"
        kwargs["headers"] = headers
        kwargs["timeout"] = self.timeout

        response = requests.request(method, url, **kwargs)
        result = response.json()

        # Nếu token không hợp lệ hoặc hết hạn -> Refresh rồi gọi lại 1 lần duy nhất
        if result.get("code") == "GECO_001":
            self.refresh_access_token()
            headers["Authorization"] = f"Bearer {self.access_token}"
            response = requests.request(method, url, **kwargs)
            result = response.json()

        return result

    def send_cskh_sms(
        self, 
        alias_name: str, 
        msisdn: List[str], 
        content: str, 
        convert_vn: int = 1
    ) -> Dict[str, Any]:
        endpoint = "/api/v1/ws/sent-mt"
        payload = {
            "aliasName": alias_name,
            "msisdn": msisdn,
            "content": content,
            "convertVN": convert_vn
        }
        
        result = self._request_with_retry("POST", endpoint, json=payload)
        if result.get("code") != "GECO_002":
            raise ValidationError(result.get("code", "ERR"), result.get("message", "Lỗi gửi tin CSKH"))
        return result

    def send_template_sms(
        self, 
        alias_name: str, 
        msisdn: List[str], 
        template_key: str, 
        template_params: Dict[str, Any], 
        convert_vn: int = 1
    ) -> Dict[str, Any]:
        if template_key not in self.templates:
            raise KeyError(f"Template key '{template_key}' chưa được cấu hình. Sử dụng set_template() trước.")
        
        content = self.templates[template_key].format(**template_params)
        return self.send_cskh_sms(alias_name=alias_name, msisdn=msisdn, content=content, convert_vn=convert_vn)