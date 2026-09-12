"""加密服务测试"""
import pytest

from app.services.crypto_service import CryptoService, decrypt, encrypt


def test_encrypt_decrypt_roundtrip():
    """加密-解密往返一致"""
    plain = "sk-1234567890abcdef-test-key"
    cipher = encrypt(plain)
    assert cipher != plain
    assert decrypt(cipher) == plain


def test_encrypt_empty_string():
    """空字符串加密返回空字符串"""
    assert encrypt("") == ""
    assert decrypt("") == ""


def test_decrypt_invalid_returns_empty():
    """无效密文返回空字符串（不抛异常）"""
    assert decrypt("not-a-valid-ciphertext") == ""


def test_crypto_service_class():
    """类方法版本"""
    plain = "test-token-12345"
    cipher = CryptoService.encrypt(plain)
    assert CryptoService.decrypt(cipher) == plain


def test_different_inputs_produce_different_outputs():
    """不同输入产生不同输出"""
    a = encrypt("token-a")
    b = encrypt("token-b")
    assert a != b