"""Unit test cho ViettelSMSClient. Không gọi API thật: mọi request đi qua FakeSession."""

import pickle
import threading

import pytest
import requests

from viettel_sms import (
    AuthenticationError,
    InvalidResponseError,
    SendError,
    SMSBrandnameError,
    SMSConnectionError,
    TemplateError,
    ValidationError,
    ViettelSMSClient,
    normalize_msisdn,
)

BASE = ViettelSMSClient.ENDPOINTS["public"]
LOGIN = BASE + ViettelSMSClient.LOGIN_PATH
REFRESH = BASE + ViettelSMSClient.REFRESH_PATH
SEND = BASE + ViettelSMSClient.SEND_MT_PATH

LOGIN_OK = {"code": "GECO_002", "data": {"access_token": "at-1", "refresh_token": "rt-1"}}
SEND_OK = {"code": "GECO_002", "message": "Success"}
TOKEN_EXPIRED = {"code": "GECO_001", "message": "Token expired"}


class FakeResponse:
    def __init__(self, body, status_code=200):
        self._body = body
        self.status_code = status_code
        self.text = body if isinstance(body, str) else repr(body)

    def json(self):
        if isinstance(self._body, str):
            raise ValueError("not json")
        return self._body


class FakeSession:
    """Trả lần lượt các phản hồi đã đăng ký cho từng URL và ghi lại mọi request."""

    def __init__(self):
        self.routes = {}
        self.calls = []
        self.closed = False
        self._lock = threading.Lock()

    def add(self, url, *bodies):
        self.routes.setdefault(url, []).extend(bodies)

    def post(self, url, json=None, headers=None, timeout=None, verify=None):
        with self._lock:
            self.calls.append(
                {"url": url, "json": json, "headers": headers or {}, "verify": verify}
            )
            queue = self.routes.get(url)
            if not queue:
                raise AssertionError(f"Request không mong đợi tới {url}")
            body = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(body, Exception):
            raise body
        return FakeResponse(body)

    def close(self):
        self.closed = True

    def urls(self):
        return [c["url"] for c in self.calls]


@pytest.fixture
def session():
    return FakeSession()


@pytest.fixture
def client(session):
    return ViettelSMSClient("user", "secret", session=session)


# ------------------------------------------------------------ Khởi tạo


def test_init_does_not_call_network(session):
    ViettelSMSClient("user", "secret", session=session)
    assert session.calls == []


def test_invalid_env():
    with pytest.raises(ValueError):
        ViettelSMSClient("user", "secret", env="staging")


def test_missing_credentials():
    with pytest.raises(ValueError):
        ViettelSMSClient("", "secret")


def test_custom_base_url_and_verify(session):
    session.add("https://example.test/api/v1/auth/ws/login", LOGIN_OK)
    c = ViettelSMSClient("u", "p", base_url="https://example.test/", verify=False, session=session)
    c.login()
    assert session.calls[0]["verify"] is False


def test_repr_hides_password(client):
    assert "secret" not in repr(client)


def test_from_env(monkeypatch, session):
    monkeypatch.setenv("VIETTEL_SMS_USERNAME", "env-user")
    monkeypatch.setenv("VIETTEL_SMS_PASSWORD", "env-pass")
    monkeypatch.setenv("VIETTEL_SMS_ENV", "ip")
    c = ViettelSMSClient.from_env(session=session)
    assert c.username == "env-user"
    assert c.base_url == ViettelSMSClient.ENDPOINTS["ip"]


def test_from_env_missing(monkeypatch):
    monkeypatch.delenv("VIETTEL_SMS_USERNAME", raising=False)
    monkeypatch.delenv("VIETTEL_SMS_PASSWORD", raising=False)
    with pytest.raises(ValueError, match="VIETTEL_SMS_USERNAME"):
        ViettelSMSClient.from_env()


def test_context_manager_closes_own_session(monkeypatch):
    closed = []
    monkeypatch.setattr(requests.Session, "close", lambda self: closed.append(self))
    with ViettelSMSClient("u", "p") as c:
        own = c._session
    assert closed == [own]


def test_context_manager_keeps_external_session(session):
    with ViettelSMSClient("u", "p", session=session):
        pass
    assert session.closed is False


# ------------------------------------------------------------ Gửi tin


def test_send_logs_in_lazily_and_sends(client, session):
    session.add(LOGIN, LOGIN_OK)
    session.add(SEND, SEND_OK)

    result = client.send_cskh_sms("MyBrand", ["0912 345 678"], "Xin chao", convert_vn=False)

    assert result == SEND_OK
    assert session.urls() == [LOGIN, SEND]
    send = session.calls[1]
    assert send["headers"]["Authorization"] == "Bearer at-1"
    assert send["json"] == {
        "aliasName": "MyBrand",
        "msisdn": ["84912345678"],
        "content": "Xin chao",
        "convertVN": 0,
    }


def test_login_only_once(client, session):
    session.add(LOGIN, LOGIN_OK)
    session.add(SEND, SEND_OK)
    client.send_cskh_sms("B", "84912345678", "a")
    client.send_cskh_sms("B", "84912345678", "b")
    assert session.urls().count(LOGIN) == 1


def test_token_expired_refreshes_and_retries(client, session):
    session.add(LOGIN, LOGIN_OK)
    session.add(SEND, TOKEN_EXPIRED, SEND_OK)
    session.add(REFRESH, {"code": "GECO_002", "data": {"access_token": "at-2"}})

    client.send_cskh_sms("B", "84912345678", "hi")

    assert session.urls() == [LOGIN, SEND, REFRESH, SEND]
    assert session.calls[2]["headers"] == {"refresh-token": "rt-1"}
    assert session.calls[3]["headers"]["Authorization"] == "Bearer at-2"
    assert client.refresh_token == "rt-1"


def test_refresh_rejected_falls_back_to_login(client, session):
    session.add(
        LOGIN,
        LOGIN_OK,
        {"code": "GECO_002", "data": {"access_token": "at-3", "refresh_token": "rt-3"}},
    )
    session.add(SEND, TOKEN_EXPIRED, SEND_OK)
    session.add(REFRESH, {"code": "GECO_001"})

    client.send_cskh_sms("B", "84912345678", "hi")

    assert session.urls() == [LOGIN, SEND, REFRESH, LOGIN, SEND]
    assert session.calls[-1]["headers"]["Authorization"] == "Bearer at-3"


def test_refresh_network_error_falls_back_to_login(client, session):
    session.add(LOGIN, LOGIN_OK, {"code": "GECO_002", "data": {"access_token": "at-3"}})
    session.add(SEND, TOKEN_EXPIRED, SEND_OK)
    session.add(REFRESH, requests.ConnectionError("boom"))

    client.send_cskh_sms("B", "84912345678", "hi")
    assert session.urls() == [LOGIN, SEND, REFRESH, LOGIN, SEND]


def test_concurrent_expiry_refreshes_once(client, session):
    session.add(LOGIN, LOGIN_OK)
    session.add(REFRESH, {"code": "GECO_002", "data": {"access_token": "at-2"}})
    client.login()

    # Cả hai thread đều thấy token cũ "at-1" hết hạn; chỉ một thread được làm mới.
    client._refresh_if_stale("at-1")
    client._refresh_if_stale("at-1")
    assert session.urls().count(REFRESH) == 1


def test_send_rejected_raises_send_error(client, session):
    session.add(LOGIN, LOGIN_OK)
    session.add(SEND, {"code": "ALIAS_INVALID", "message": "Brandname không hợp lệ"})

    with pytest.raises(SendError) as info:
        client.send_cskh_sms("Wrong", "84912345678", "hi")
    assert info.value.code == "ALIAS_INVALID"
    assert isinstance(info.value, ValidationError)  # tên cũ vẫn bắt được


def test_send_validates_input(client, session):
    with pytest.raises(ValueError):
        client.send_cskh_sms("", "84912345678", "hi")
    with pytest.raises(ValueError):
        client.send_cskh_sms("B", "84912345678", "")
    with pytest.raises(ValueError):
        client.send_cskh_sms("B", [], "hi")
    assert session.calls == []


# ------------------------------------------------------------ Lỗi


def test_login_failure(client, session):
    session.add(LOGIN, {"code": "SI_007", "message": "Sai mật khẩu"})
    with pytest.raises(AuthenticationError) as info:
        client.login()
    assert info.value.code == "SI_007"
    assert str(info.value) == "[SI_007] Sai mật khẩu"


def test_login_success_without_token_is_error(client, session):
    session.add(LOGIN, {"code": "GECO_002", "data": {}})
    with pytest.raises(AuthenticationError):
        client.login()


def test_connection_error(client, session):
    session.add(LOGIN, requests.Timeout("timeout"))
    with pytest.raises(SMSConnectionError) as info:
        client.login()
    assert info.value.code == "CONN_ERR"
    assert isinstance(info.value, SMSBrandnameError)


def test_non_json_response(client, session):
    session.add(LOGIN, LOGIN_OK)
    session.add(SEND, "<html>502 Bad Gateway</html>")
    with pytest.raises(InvalidResponseError) as info:
        client.send_cskh_sms("B", "84912345678", "hi")
    assert "502" in info.value.message


def test_exceptions_are_picklable():
    err = pickle.loads(pickle.dumps(SendError("X", "y")))
    assert (err.code, err.message) == ("X", "y")


# ------------------------------------------------------------ Template


def test_send_template_sms(client, session):
    session.add(LOGIN, LOGIN_OK)
    session.add(SEND, SEND_OK)
    client.set_template("otp", "Ma OTP {otp}, hieu luc {minutes} phut")

    client.send_template_sms("B", "84912345678", "otp", {"otp": "1234", "minutes": 5})
    assert session.calls[-1]["json"]["content"] == "Ma OTP 1234, hieu luc 5 phut"


def test_templates_in_constructor(session):
    c = ViettelSMSClient("u", "p", session=session, templates={"hi": "Chao {name}"})
    assert c.render_template("hi", {"name": "An"}) == "Chao An"


def test_template_not_found_is_key_error(client):
    with pytest.raises(TemplateError) as info:
        client.render_template("missing")
    assert isinstance(info.value, KeyError)
    assert info.value.code == "TEMPLATE_NOT_FOUND"


def test_template_missing_params_lists_all(client):
    client.set_template("t", "{a} {b} {c}")
    with pytest.raises(TemplateError, match="b, c"):
        client.render_template("t", {"a": 1})


def test_template_invalid_syntax(client):
    with pytest.raises(TemplateError):
        client.set_template("bad", "Ma OTP {otp")


# ------------------------------------------------------------ Số điện thoại


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("0912345678", ["84912345678"]),
        ("+84 912.345.678", ["84912345678"]),
        ("84912345678", ["84912345678"]),
        (["0912345678", "84912345678", "0987-654-321"], ["84912345678", "84987654321"]),
        (("0912345678",), ["84912345678"]),
    ],
)
def test_normalize_msisdn(raw, expected):
    assert normalize_msisdn(raw) == expected


@pytest.mark.parametrize("raw", ["abc", "0912x45678", "123", []])
def test_normalize_msisdn_invalid(raw):
    with pytest.raises(ValueError):
        normalize_msisdn(raw)
