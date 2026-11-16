"""Client cho Viettel SMS Brandname API v2."""

import logging
import os
import re
import threading
from string import Formatter
from typing import Any, Dict, Iterable, List, Mapping, Optional, Union

import requests

from .exceptions import (
    AuthenticationError,
    InvalidResponseError,
    SendError,
    SMSBrandnameError,
    SMSConnectionError,
    TemplateError,
)

logger = logging.getLogger("viettel_sms")

#: Mã phản hồi thành công của Viettel.
SUCCESS_CODE = "GECO_002"
#: Mã phản hồi khi access token không hợp lệ hoặc đã hết hạn.
TOKEN_EXPIRED_CODE = "GECO_001"

Msisdn = Union[str, Iterable[str]]

_MSISDN_STRIP = re.compile(r"[\s.\-()]")


def normalize_msisdn(msisdn: Msisdn) -> List[str]:
    """Chuẩn hoá số điện thoại về định dạng ``84xxxxxxxxx``.

    - Nhận một số (``str``) hoặc danh sách số.
    - Bỏ khoảng trắng, dấu chấm, gạch ngang, ngoặc và dấu ``+`` ở đầu.
    - Đổi số ``0`` ở đầu thành ``84`` (``0912345678`` -> ``84912345678``).
    - Bỏ các số trùng nhau, giữ nguyên thứ tự.

    Raises:
        ValueError: Danh sách rỗng hoặc có số không hợp lệ.
    """
    items = [msisdn] if isinstance(msisdn, str) else list(msisdn)
    if not items:
        raise ValueError("Danh sách số điện thoại (msisdn) không được rỗng.")

    result: List[str] = []
    for raw in items:
        number = _MSISDN_STRIP.sub("", str(raw))
        if number.startswith("+"):
            number = number[1:]
        if number.startswith("0"):
            number = "84" + number[1:]
        if not number.isdigit() or not 9 <= len(number) <= 15:
            raise ValueError(f"Số điện thoại không hợp lệ: {raw!r}")
        if number not in result:
            result.append(number)
    return result


def _template_fields(template: str) -> List[str]:
    """Lấy tên các placeholder trong template (``{otp}``, ``{user.name}`` -> ``user``)."""
    fields: List[str] = []
    for _, field, _, _ in Formatter().parse(template):
        if field is None:
            continue
        root = re.split(r"[.\[]", field, maxsplit=1)[0]
        if root not in fields:
            fields.append(root)
    return fields


class ViettelSMSClient:
    """Client gửi SMS Brandname qua Viettel API v2.

    Client tự đăng nhập ở lần gửi đầu tiên, tự làm mới token khi hết hạn
    và an toàn khi dùng chung giữa nhiều thread.

    Example:
        >>> with ViettelSMSClient.from_env() as client:
        ...     client.send_cskh_sms("MyBrand", "0912345678", "Xin chao!")
    """

    ENDPOINTS = {
        "public": "https://apismsbrandname.viettelai.vn:8000",
        "ip": "https://171.234.245.145:8000",
        "internal": "https://10.208.67.177:8000",
    }

    LOGIN_PATH = "/api/v1/auth/ws/login"
    REFRESH_PATH = "/api/v1/auth/refresh-token"
    SEND_MT_PATH = "/api/v1/ws/sent-mt"

    def __init__(
        self,
        username: str,
        password: str,
        env: str = "public",
        timeout: float = 10,
        verify: Union[bool, str] = True,
        base_url: Optional[str] = None,
        session: Optional[requests.Session] = None,
        templates: Optional[Mapping[str, str]] = None,
    ):
        """
        Args:
            username: Tài khoản Viettel SMS Brandname.
            password: Mật khẩu.
            env: ``"public"``, ``"ip"`` hoặc ``"internal"``. Bị bỏ qua nếu truyền ``base_url``.
            timeout: Thời gian chờ mỗi request (giây).
            verify: Kiểm tra chứng chỉ SSL. Truyền đường dẫn file CA, hoặc ``False``
                khi kết nối bằng IP mà chứng chỉ không khớp.
            base_url: URL API tuỳ chỉnh, dùng thay cho ``env``.
            session: ``requests.Session`` có sẵn (ví dụ để cấu hình proxy).
                Nếu không truyền, client tự tạo và tự đóng session.
            templates: Các template đăng ký sẵn, dạng ``{key: content}``.
        """
        if not username or not password:
            raise ValueError("Cần cung cấp username và password.")
        if base_url is None:
            if env not in self.ENDPOINTS:
                raise ValueError(f"Environment '{env}' không hợp lệ. Chọn: {list(self.ENDPOINTS)}")
            base_url = self.ENDPOINTS[env]

        self.env = env
        self.base_url = base_url.rstrip("/")
        self.username = username
        self._password = password
        self.timeout = timeout
        self.verify = verify

        self._session = session if session is not None else requests.Session()
        self._owns_session = session is None
        self._lock = threading.RLock()

        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.templates: Dict[str, str] = {}
        for key, content in (templates or {}).items():
            self.set_template(key, content)

    @classmethod
    def from_env(cls, prefix: str = "VIETTEL_SMS_", **kwargs: Any) -> "ViettelSMSClient":
        """Tạo client từ biến môi trường.

        Đọc ``{prefix}USERNAME``, ``{prefix}PASSWORD`` và ``{prefix}ENV`` (mặc định ``public``).
        Các tham số khác (``timeout``, ``verify``...) truyền qua ``kwargs``.
        """
        username = os.getenv(f"{prefix}USERNAME")
        password = os.getenv(f"{prefix}PASSWORD")
        missing = [
            name
            for name, value in ((f"{prefix}USERNAME", username), (f"{prefix}PASSWORD", password))
            if not value
        ]
        if missing:
            raise ValueError(f"Thiếu biến môi trường: {', '.join(missing)}")
        kwargs.setdefault("env", os.getenv(f"{prefix}ENV") or "public")
        return cls(username, password, **kwargs)  # type: ignore[arg-type]

    def __repr__(self) -> str:
        return f"{type(self).__name__}(username={self.username!r}, base_url={self.base_url!r})"

    def __enter__(self) -> "ViettelSMSClient":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def close(self) -> None:
        """Đóng session HTTP nếu do client tự tạo."""
        if self._owns_session:
            self._session.close()

    # ------------------------------------------------------------------ HTTP

    def _post_json(
        self,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self._session.post(
                url, json=payload, headers=headers, timeout=self.timeout, verify=self.verify
            )
        except requests.RequestException as exc:
            raise SMSConnectionError(
                "CONN_ERR", f"Lỗi kết nối mạng đến Viettel API: {exc}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise InvalidResponseError(
                "INVALID_RESPONSE",
                f"Viettel trả về dữ liệu không phải JSON (HTTP {response.status_code}): "
                f"{response.text[:200]}",
            ) from exc
        if not isinstance(data, dict):
            raise InvalidResponseError(
                "INVALID_RESPONSE", f"Phản hồi không đúng định dạng: {data!r}"
            )
        return data

    # ------------------------------------------------------------------ Auth

    def login(self) -> None:
        """Đăng nhập để lấy access token và refresh token.

        Thường không cần gọi trực tiếp: client tự đăng nhập ở lần gửi đầu tiên.
        Gọi hàm này khi muốn kiểm tra tài khoản ngay lúc khởi động ứng dụng.

        Raises:
            AuthenticationError: Sai tài khoản hoặc Viettel không trả về token.
        """
        with self._lock:
            logger.debug("Đăng nhập Viettel SMS Brandname với user %r", self.username)
            data = self._post_json(
                self.LOGIN_PATH, {"username": self.username, "password": self._password}
            )
            token_data = data.get("data") or {}
            access_token = token_data.get("access_token")
            if data.get("code") != SUCCESS_CODE or not access_token:
                raise AuthenticationError(
                    data.get("code") or "SI_007", data.get("message") or "Đăng nhập thất bại"
                )
            self.access_token = access_token
            self.refresh_token = token_data.get("refresh_token")

    def refresh_access_token(self) -> None:
        """Làm mới access token. Nếu refresh token đã hết hạn thì đăng nhập lại."""
        with self._lock:
            if self.refresh_token and self._try_refresh():
                return
            self.login()

    def _try_refresh(self) -> bool:
        try:
            data = self._post_json(self.REFRESH_PATH, headers={"refresh-token": self.refresh_token})
        except SMSBrandnameError as exc:
            logger.warning("Làm mới token thất bại (%s), chuyển sang đăng nhập lại", exc)
            return False

        token_data = data.get("data") or {}
        access_token = token_data.get("access_token")
        if data.get("code") != SUCCESS_CODE or not access_token:
            logger.info(
                "Refresh token không còn hiệu lực (code=%s), chuyển sang đăng nhập lại",
                data.get("code"),
            )
            return False

        self.access_token = access_token
        self.refresh_token = token_data.get("refresh_token") or self.refresh_token
        return True

    def _ensure_token(self) -> str:
        if self.access_token is None:
            with self._lock:
                if self.access_token is None:
                    self.login()
        return self.access_token  # type: ignore[return-value]

    def _refresh_if_stale(self, stale_token: str) -> None:
        with self._lock:
            # Một thread khác có thể đã làm mới token trong lúc chờ khoá.
            if self.access_token == stale_token:
                self.refresh_access_token()

    def _authorized_post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Gửi request có token. Nếu token hết hạn thì làm mới và gửi lại đúng một lần.

        Gửi lại không bị trùng tin: với mã ``GECO_001`` Viettel đã từ chối request đầu.
        """
        token = self._ensure_token()
        result = self._post_json(path, payload, {"Authorization": f"Bearer {token}"})
        if result.get("code") == TOKEN_EXPIRED_CODE:
            logger.info("Access token hết hạn, đang làm mới và gửi lại")
            self._refresh_if_stale(token)
            result = self._post_json(
                path, payload, {"Authorization": f"Bearer {self.access_token}"}
            )
        return result

    # -------------------------------------------------------------- Template

    def set_template(self, key: str, content: str) -> None:
        """Thêm hoặc cập nhật template. Placeholder dùng cú pháp ``str.format``: ``{otp}``.

        Raises:
            TemplateError: Template sai cú pháp (ví dụ thiếu dấu ``}``).
        """
        try:
            _template_fields(content)
        except ValueError as exc:
            raise TemplateError("TEMPLATE_INVALID", f"Template '{key}' sai cú pháp: {exc}") from exc
        self.templates[key] = content

    def render_template(
        self, template_key: str, template_params: Optional[Mapping[str, Any]] = None
    ) -> str:
        """Ghép tham số vào template và trả về nội dung tin nhắn (không gửi).

        Raises:
            TemplateError: Template chưa đăng ký hoặc thiếu tham số.
        """
        if template_key not in self.templates:
            raise TemplateError(
                "TEMPLATE_NOT_FOUND",
                f"Template '{template_key}' chưa được cấu hình. Hãy gọi set_template() trước.",
            )
        template = self.templates[template_key]
        params = dict(template_params or {})

        missing = [name for name in _template_fields(template) if name and name not in params]
        if missing:
            raise TemplateError(
                "TEMPLATE_MISSING_PARAMS",
                f"Template '{template_key}' thiếu tham số: {', '.join(missing)}",
            )
        try:
            return template.format(**params)
        except (KeyError, IndexError, AttributeError, ValueError) as exc:
            raise TemplateError(
                "TEMPLATE_RENDER_ERROR", f"Không ghép được template '{template_key}': {exc!r}"
            ) from exc

    # ------------------------------------------------------------------ Send

    def send_cskh_sms(
        self,
        alias_name: str,
        msisdn: Msisdn,
        content: str,
        convert_vn: Union[bool, int] = True,
    ) -> Dict[str, Any]:
        """Gửi tin CSKH.

        Args:
            alias_name: Brandname đã đăng ký với Viettel.
            msisdn: Một số hoặc danh sách số. Số được chuẩn hoá tự động
                (``0912345678`` -> ``84912345678``) và bỏ trùng.
            content: Nội dung tin nhắn.
            convert_vn: Giá trị ``convertVN`` gửi cho Viettel (``True``/``1`` hoặc ``False``/``0``).

        Returns:
            Phản hồi gốc của Viettel.

        Raises:
            ValueError: Thiếu brandname, nội dung hoặc số điện thoại không hợp lệ.
            AuthenticationError: Không đăng nhập được.
            SendError: Viettel từ chối gửi tin.
            SMSConnectionError: Lỗi kết nối mạng.
            InvalidResponseError: Phản hồi không đọc được.
        """
        if not alias_name:
            raise ValueError("alias_name (brandname) không được rỗng.")
        if not content:
            raise ValueError("Nội dung tin nhắn không được rỗng.")

        payload = {
            "aliasName": alias_name,
            "msisdn": normalize_msisdn(msisdn),
            "content": content,
            "convertVN": int(convert_vn),
        }
        logger.debug("Gửi tin tới %d số với brandname %r", len(payload["msisdn"]), alias_name)

        result = self._authorized_post(self.SEND_MT_PATH, payload)
        if result.get("code") != SUCCESS_CODE:
            raise SendError(
                result.get("code") or "SEND_FAILED",
                result.get("message") or "Gửi tin CSKH thất bại",
            )
        return result

    def send_template_sms(
        self,
        alias_name: str,
        msisdn: Msisdn,
        template_key: str,
        template_params: Optional[Mapping[str, Any]] = None,
        convert_vn: Union[bool, int] = True,
    ) -> Dict[str, Any]:
        """Ghép tham số vào template rồi gửi như :meth:`send_cskh_sms`.

        Raises:
            TemplateError: Template chưa đăng ký hoặc thiếu tham số.
            Và các lỗi giống :meth:`send_cskh_sms`.
        """
        content = self.render_template(template_key, template_params)
        return self.send_cskh_sms(
            alias_name=alias_name, msisdn=msisdn, content=content, convert_vn=convert_vn
        )
