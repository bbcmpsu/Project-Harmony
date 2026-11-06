"""Криптография и стеганография для «Гармонии».

Реализует базовые примитивы из PDF:
- AES-256-GCM — симметричное шифрование с аутентификацией
- SHA-256 — хеширование
- LSB стеганография — встраивание в изображения
- Устойчивость к сжатию и анализу
"""

from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


@dataclass
class CryptoConfig:
    """Конфигурация криптографии."""
    # Итерации PBKDF2
    pbkdf2_iterations: int = 100_000
    # Длина ключа (байты)
    key_length: int = 32
    # Размер nonce для AES-GCM
    nonce_length: int = 12
    # Размер тега аутентификации
    tag_length: int = 16


class CryptoError(Exception):
    """Ошибка криптографических операций."""
    pass


class SymmetricCrypto:
    """Симметричное шифрование AES-256-GCM."""

    def __init__(self, config: CryptoConfig | None = None) -> None:
        if not CRYPTO_AVAILABLE:
            raise CryptoError("cryptography library not available. Install: pip install cryptography")
        self.config = config or CryptoConfig()

    def derive_key(self, password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
        """Вывести ключ из пароля через PBKDF2."""
        if salt is None:
            salt = secrets.token_bytes(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.config.key_length,
            salt=salt,
            iterations=self.config.pbkdf2_iterations,
        )
        key = kdf.derive(password.encode())
        return key, salt

    def encrypt(self, plaintext: bytes, key: bytes, associated_data: bytes = b"") -> tuple[bytes, bytes]:
        """Зашифровать данные. Возвращает (nonce, ciphertext+tag)."""
        nonce = secrets.token_bytes(self.config.nonce_length)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
        return nonce, ciphertext

    def decrypt(self, nonce: bytes, ciphertext: bytes, key: bytes, associated_data: bytes = b"") -> bytes:
        """Расшифровать данные."""
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, associated_data)

    def encrypt_file(self, input_path: Path, output_path: Path, password: str) -> None:
        """Зашифровать файл."""
        key, salt = self.derive_key(password)
        with open(input_path, "rb") as f:
            plaintext = f.read()
        nonce, ciphertext = self.encrypt(plaintext, key)
        # Формат: salt(16) + nonce(12) + ciphertext
        with open(output_path, "wb") as f:
            f.write(salt + nonce + ciphertext)

    def decrypt_file(self, input_path: Path, output_path: Path, password: str) -> None:
        """Расшифровать файл."""
        with open(input_path, "rb") as f:
            data = f.read()
        salt = data[:16]
        nonce = data[16:28]
        ciphertext = data[28:]
        key, _ = self.derive_key(password, salt)
        plaintext = self.decrypt(nonce, ciphertext, key)
        with open(output_path, "wb") as f:
            f.write(plaintext)


def hash_sha256(data: bytes) -> bytes:
    """SHA-256 хеш."""
    return hashlib.sha256(data).digest()


def hash_sha256_hex(data: bytes) -> str:
    """SHA-256 хеш в hex."""
    return hashlib.sha256(data).hexdigest()


def hash_file(path: Path) -> str:
    """Хеш файла SHA-256."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class LSBSteganography:
    """LSB стеганография — встраивание в младшие биты пикселей."""

    def __init__(self) -> None:
        if not PIL_AVAILABLE:
            raise CryptoError("PIL/Pillow not available. Install: pip install pillow")

    def _bytes_to_bits(self, data: bytes) -> list[int]:
        """Преобразовать байты в список бит."""
        bits = []
        for byte in data:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)
        return bits

    def _bits_to_bytes(self, bits: list[int]) -> bytes:
        """Преобразовать биты в байты."""
        out = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(bits):
                    byte = (byte << 1) | bits[i + j]
            out.append(byte)
        return bytes(out)

    def embed(self, carrier_path: Path, payload: bytes, output_path: Path, bit_depth: int = 1) -> dict[str, Any]:
        """Встроить данные в изображение."""
        img = Image.open(carrier_path)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        width, height = img.size
        max_capacity = (width * height * 3 * bit_depth) // 8  # байт

        # Добавляем длину payload (4 байта) + payload
        payload_len = len(payload)
        if payload_len > max_capacity - 4:
            raise CryptoError(f"Payload too large: {payload_len} bytes, max {max_capacity - 4}")

        full_payload = payload_len.to_bytes(4, "big") + payload
        bits = self._bytes_to_bits(full_payload)

        pixels = img.load()
        bit_idx = 0

        for y in range(height):
            for x in range(width):
                if bit_idx >= len(bits):
                    break
                r, g, b = pixels[x, y][:3]
                if bit_depth == 1:
                    r = (r & 0xFE) | bits[bit_idx]; bit_idx += 1
                    if bit_idx < len(bits):
                        g = (g & 0xFE) | bits[bit_idx]; bit_idx += 1
                    if bit_idx < len(bits):
                        b = (b & 0xFE) | bits[bit_idx]; bit_idx += 1
                pixels[x, y] = (r, g, b)
            if bit_idx >= len(bits):
                break

        img.save(output_path)
        return {
            "carrier": str(carrier_path),
            "output": str(output_path),
            "payload_bytes": payload_len,
            "capacity_bytes": max_capacity,
            "bit_depth": bit_depth,
        }

    def extract(self, stego_path: Path) -> bytes:
        """Извлечь данные из изображения."""
        img = Image.open(stego_path)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        width, height = img.size
        pixels = img.load()
        bits = []

        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y][:3]
                bits.append(r & 1)
                bits.append(g & 1)
                bits.append(b & 1)

        # Первые 32 бита = длина payload
        if len(bits) < 32:
            raise CryptoError("Image too small to contain payload length")

        payload_len = 0
        for i in range(32):
            payload_len = (payload_len << 1) | bits[i]

        total_bits_needed = 32 + payload_len * 8
        if len(bits) < total_bits_needed:
            raise CryptoError("Image does not contain full payload")

        payload_bits = bits[32:total_bits_needed]
        return self._bits_to_bytes(payload_bits)


class KeyManager:
    """Управление ключами — изоляция в памяти."""

    def __init__(self) -> None:
        self._keys: dict[str, bytes] = {}

    def store(self, key_id: str, key: bytes) -> None:
        """Сохранить ключ (только в памяти)."""
        self._keys[key_id] = key

    def get(self, key_id: str) -> bytes | None:
        """Получить ключ."""
        return self._keys.get(key_id)

    def delete(self, key_id: str) -> bool:
        """Удалить ключ."""
        if key_id in self._keys:
            del self._keys[key_id]
            return True
        return False

    def clear(self) -> None:
        """Очистить все ключи."""
        self._keys.clear()

    def __del__(self):
        self.clear()
