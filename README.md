<div align="center">

# Viettel SMS Brandname

**Gửi SMS Brandname qua Viettel API v2 bằng Python, chỉ vài dòng code.**

Thư viện tự đăng nhập, tự làm mới token, soạn tin bằng template và chuẩn hoá số điện thoại, nên bạn chỉ cần lo phần nghiệp vụ.

[![PyPI version](https://img.shields.io/pypi/v/viettel-sms-brandname?color=blue&logo=pypi&logoColor=white)](https://pypi.org/project/viettel-sms-brandname/)
[![Python](https://img.shields.io/pypi/pyversions/viettel-sms-brandname?logo=python&logoColor=white)](https://pypi.org/project/viettel-sms-brandname/)
[![Downloads](https://static.pepy.tech/badge/viettel-sms-brandname/month)](https://pepy.tech/project/viettel-sms-brandname)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

---

## Tính năng

| Tính năng | Mô tả |
| --- | --- |
| **Tự động xác thực** | Tự đăng nhập ở lần gửi đầu tiên, không cần gọi API login. |
| **Tự làm mới token** | Khi token hết hạn (`GECO_001`), thư viện dùng refresh token để lấy token mới rồi gửi lại. Nếu refresh token cũng hết hạn, thư viện đăng nhập lại. Không gửi trùng tin. |
| **An toàn với nhiều thread** | Dùng chung một client trong web server hay worker mà không bị làm mới token nhiều lần. |
| **Template tin nhắn** | Đăng ký mẫu một lần rồi chỉ cần truyền `{otp}`, `{name}`... Nếu thiếu tham số, thư viện báo rõ là thiếu tham số nào. |
| **Chuẩn hoá số điện thoại** | `0912 345 678`, `+84912345678` và `84912345678` đều được đổi về cùng một dạng. Số trùng bị bỏ để không tốn tiền gửi hai lần. |
| **Nhiều môi trường** | `public`, `ip`, `internal` hoặc `base_url` tuỳ chỉnh. Có tuỳ chọn chứng chỉ SSL (`verify`). |
| **Ngoại lệ rõ ràng** | Mỗi loại lỗi có một ngoại lệ riêng, kèm `code` và `message`. |
| **Nhẹ, có type hints** | Chỉ phụ thuộc vào `requests`. Có kèm `py.typed`. |

## Cài đặt

```bash
pip install viettel-sms-brandname
```

Yêu cầu Python 3.9 trở lên.

## Bắt đầu nhanh

```python
from viettel_sms import ViettelSMSClient

with ViettelSMSClient(username="your_username", password="your_password") as client:
    client.send_cskh_sms(
        alias_name="MyBrand",  # Brandname đã đăng ký với Viettel
        msisdn="0912345678",  # Một số hoặc danh sách số
        content="Cam on ban da su dung dich vu cua chung toi!",
    )
```

## Hướng dẫn sử dụng

### 1. Cấu hình bằng biến môi trường (khuyến nghị)

Không nên ghi thẳng tài khoản vào code. Hãy đặt các biến môi trường sau, hoặc khai báo trong file `.env` (xem [.env.example](.env.example)):

```dotenv
VIETTEL_SMS_USERNAME=your_username_here
VIETTEL_SMS_PASSWORD=your_password_here
VIETTEL_SMS_ENV=public
```

```python
from dotenv import load_dotenv  # pip install python-dotenv
from viettel_sms import ViettelSMSClient

load_dotenv()
client = ViettelSMSClient.from_env()  # có thể truyền thêm timeout=..., verify=...
```

### 2. Gửi tin bằng template (ví dụ: OTP)

```python
client.set_template(
    "otp_login",
    "Ma OTP cua ban la {otp}. Ma co hieu luc trong {minutes} phut. "
    "Vui long khong chia se ma nay voi bat ky ai.",
)

client.send_template_sms(
    alias_name="MyBrand",
    msisdn="0912345678",
    template_key="otp_login",
    template_params={"otp": "4892", "minutes": 5},
    convert_vn=False,
)
```

Muốn xem trước nội dung mà không gửi, dùng `client.render_template("otp_login", {...})`. Cũng có thể đăng ký nhiều template ngay khi tạo client:

```python
client = ViettelSMSClient.from_env(
    templates={
        "otp_login": "Ma OTP cua ban la {otp}",
        "welcome": "Chao mung {name} den voi MyBrand!",
    }
)
```

### 3. Gửi cho nhiều số cùng lúc

```python
client.send_cskh_sms(
    alias_name="MyBrand",
    msisdn=["0912 345 678", "+84987654321", "0912345678"],  # → 2 số, đã bỏ trùng
    content="Thong bao: he thong bao tri tu 22h-23h toi nay.",
)
```

### 4. Kiểm tra tài khoản khi khởi động ứng dụng

Client chỉ đăng nhập khi gửi tin lần đầu. Nếu muốn phát hiện sai tài khoản ngay lúc khởi động, hãy gọi `login()`:

```python
client = ViettelSMSClient.from_env()
client.login()  # báo AuthenticationError nếu sai tài khoản
```

### 5. Bật log

```python
import logging

logging.getLogger("viettel_sms").setLevel(logging.DEBUG)
```

Thư viện ghi log khi đăng nhập, làm mới token và gửi tin. Mật khẩu không bao giờ được ghi ra.

## Môi trường

| `env` | Endpoint | Khi nào dùng |
| --- | --- | --- |
| `public` *(mặc định)* | `https://apismsbrandname.viettelai.vn:8000` | Kết nối qua Internet bằng tên miền |
| `ip` | `https://171.234.245.145:8000` | Kết nối trực tiếp bằng IP public |
| `internal` | `https://10.208.67.177:8000` | Kết nối từ mạng nội bộ |

> Khi kết nối bằng IP (`ip`, `internal`), chứng chỉ SSL có thể không khớp. Nên truyền file CA bằng `verify="/path/to/ca.pem"`. Chỉ dùng `verify=False` khi bạn hiểu rủi ro.

## API Reference

### `ViettelSMSClient(username, password, env="public", timeout=10, verify=True, base_url=None, session=None, templates=None)`

| Tham số | Kiểu | Mô tả |
| --- | --- | --- |
| `username`, `password` | `str` | Tài khoản Viettel SMS Brandname |
| `env` | `str` | `"public"`, `"ip"` hoặc `"internal"` |
| `timeout` | `float` | Thời gian chờ mỗi request, tính bằng giây |
| `verify` | `bool \| str` | Kiểm tra SSL: `True`, `False` hoặc đường dẫn file CA |
| `base_url` | `str` | URL API tuỳ chỉnh, dùng thay cho `env` |
| `session` | `requests.Session` | Session có sẵn (ví dụ để cấu hình proxy hoặc retry) |
| `templates` | `dict` | Các template đăng ký sẵn |

| Phương thức | Mô tả |
| --- | --- |
| `ViettelSMSClient.from_env(prefix="VIETTEL_SMS_", **kwargs)` | Tạo client từ biến môi trường |
| `send_cskh_sms(alias_name, msisdn, content, convert_vn=True)` | Gửi tin CSKH, trả về phản hồi gốc (`dict`) của Viettel |
| `send_template_sms(alias_name, msisdn, template_key, template_params=None, convert_vn=True)` | Ghép tham số vào template rồi gửi |
| `set_template(key, content)` | Thêm hoặc cập nhật template (cú pháp `str.format`) |
| `render_template(key, params=None)` | Trả về nội dung tin đã ghép tham số, không gửi |
| `login()` | Đăng nhập ngay |
| `close()` | Đóng kết nối (tự gọi khi dùng `with`) |

Hàm tiện ích: `normalize_msisdn("0912 345 678")` trả về `["84912345678"]`.

## Xử lý lỗi

Mọi lỗi từ thư viện đều kế thừa `SMSBrandnameError` và có hai thuộc tính `code` và `message`.

```python
from viettel_sms import (
    AuthenticationError,
    SendError,
    SMSBrandnameError,
    SMSConnectionError,
    TemplateError,
)

try:
    client.send_template_sms("MyBrand", "0912345678", "otp_login", {"otp": "4892"})
except TemplateError as e:
    print(f"Template sai hoặc thiếu tham số: {e}")
except AuthenticationError as e:
    print(f"Sai tài khoản: [{e.code}] {e.message}")
except SendError as e:
    print(f"Viettel từ chối gửi tin: [{e.code}] {e.message}")
except SMSConnectionError as e:
    print(f"Lỗi mạng, có thể thử lại sau: {e}")
except SMSBrandnameError as e:
    print(f"Lỗi khác: {e}")
```

| Ngoại lệ | Mã | Khi nào xảy ra |
| --- | --- | --- |
| `AuthenticationError` | mã của Viettel | Đăng nhập thất bại |
| `SendError` | mã của Viettel | Viettel từ chối gửi tin (brandname sai, nội dung không hợp lệ...) |
| `SMSConnectionError` | `CONN_ERR` | Mất mạng, timeout, lỗi SSL |
| `InvalidResponseError` | `INVALID_RESPONSE` | Viettel trả về dữ liệu không phải JSON (ví dụ lỗi 502) |
| `TemplateError` | `TEMPLATE_*` | Template chưa đăng ký, sai cú pháp hoặc thiếu tham số |
| `ValueError` | | Brandname hoặc nội dung rỗng, số điện thoại không hợp lệ |

Mã phản hồi của Viettel: `GECO_002` là thành công, `GECO_001` là token hết hạn (thư viện tự xử lý).

> Tên `ValidationError` của bản 1.0 vẫn dùng được; nó là tên khác của `SendError`.

## Phát triển

```bash
git clone https://github.com/thiminhnhut/viettel-sms-brandname
cd viettel-sms-brandname
pip install -e ".[dev]"

pytest              # unit test, không gọi API thật
ruff check . && ruff format .
```

Muốn gửi thử tin thật, chạy [examples/send_otp.py](examples/send_otp.py). Lưu ý là lệnh này bị tính phí.

## Đóng góp

Mọi đóng góp đều được chào đón: báo lỗi, đề xuất tính năng hoặc gửi pull request. Xem lịch sử thay đổi tại [CHANGELOG.md](CHANGELOG.md).

## License

Phát hành theo giấy phép [MIT](LICENSE). Đây là thư viện không chính thức, không do Viettel phát triển hay bảo trợ.

<div align="center">

Nếu thư viện có ích cho bạn, hãy tặng repo một star trên [GitHub](https://github.com/thiminhnhut/viettel-sms-brandname)!

</div>
