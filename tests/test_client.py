import os
from dotenv import load_dotenv
from viettel_sms import ViettelSMSClient

load_dotenv()

# Khởi tạo client (Ẩn hoàn toàn URL phức tạp)
client = ViettelSMSClient(
    username=os.getenv("VIETTEL_SMS_USERNAME"),
    password=os.getenv("VIETTEL_SMS_PASSWORD"),
    env="public" # Tùy chọn: 'public', 'ip', hoặc 'internal'
)

# Đăng ký template mẫu
client.set_template(
    "otp_login", 
    "Nhap ma OTP {otp} de xac thuc tai khoan cua ban tren ung dung EasyFarm. De dam bao an toan ban vui long khong chia se ma xac thuc nay voi bat ky ai"
)

# Gửi tin nhắn qua template
response = client.send_template_sms(
    alias_name="EasyFarm",
    msisdn=["84825077239"],
    template_key="otp_login",
    template_params={"otp": "4892"},
    convert_vn=0
)

print("Gửi thành công:", response)