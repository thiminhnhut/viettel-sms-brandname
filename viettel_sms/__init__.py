"""Thư viện Python gửi SMS Brandname qua Viettel API v2."""

from .client import SUCCESS_CODE, TOKEN_EXPIRED_CODE, ViettelSMSClient, normalize_msisdn
from .exceptions import (
    AuthenticationError,
    InvalidResponseError,
    SendError,
    SMSBrandnameError,
    SMSConnectionError,
    TemplateError,
    ValidationError,
)

__version__ = "1.1.0"

__all__ = [
    "ViettelSMSClient",
    "normalize_msisdn",
    "SUCCESS_CODE",
    "TOKEN_EXPIRED_CODE",
    "SMSBrandnameError",
    "AuthenticationError",
    "SendError",
    "ValidationError",
    "SMSConnectionError",
    "InvalidResponseError",
    "TemplateError",
]
