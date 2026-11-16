"""Ví dụ gửi OTP bằng template. Lệnh này GỬI TIN THẬT và bị tính phí.

Cách chạy:
    pip install viettel-sms-brandname python-dotenv
    cp .env.example .env   # rồi điền tài khoản
    python examples/send_otp.py 0912345678
"""

import logging
import sys

from dotenv import load_dotenv

from viettel_sms import SMSBrandnameError, ViettelSMSClient

logging.basicConfig(level=logging.INFO)
load_dotenv()

if len(sys.argv) != 2:
    sys.exit("Cách dùng: python examples/send_otp.py <so_dien_thoai>")

with ViettelSMSClient.from_env() as client:
    client.set_template(
        "otp_login",
        "Ma OTP cua ban la {otp}. Ma co hieu luc trong {minutes} phut. "
        "Vui long khong chia se ma nay voi bat ky ai.",
    )
    try:
        response = client.send_template_sms(
            alias_name="MyBrand",
            msisdn=sys.argv[1],
            template_key="otp_login",
            template_params={"otp": "4892", "minutes": 5},
            convert_vn=False,
        )
        print("Gửi thành công:", response)
    except SMSBrandnameError as e:
        sys.exit(f"Gửi thất bại: {e}")
