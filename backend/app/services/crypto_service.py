"""加密服务 - API Key 等敏感数据加密存储"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from app.config import settings

_SALT = b"lingma-salt-v1"
_cipher: Fernet | None = None


def _get_cipher() -> Fernet:
    """延迟初始化加密器"""
    global _cipher
    if _cipher is None:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=_SALT,
            iterations=480_000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(settings.app_secret.encode())
        )
        _cipher = Fernet(key)
    return _cipher


class CryptoService:
    """加密/解密服务"""

    @staticmethod
    def encrypt(plaintext: str) -> str:
        """加密字符串"""
        if not plaintext:
            return ""
        return _get_cipher().encrypt(plaintext.encode()).decode()

    @staticmethod
    def decrypt(ciphertext: str) -> str:
        """解密字符串"""
        if not ciphertext:
            return ""
        try:
            return _get_cipher().decrypt(ciphertext.encode()).decode()
        except Exception:
            # 解密失败返回空（原值或损坏）
            return ""


# 便捷函数
def encrypt(plaintext: str) -> str:
    return CryptoService.encrypt(plaintext)


def decrypt(ciphertext: str) -> str:
    return CryptoService.decrypt(ciphertext)