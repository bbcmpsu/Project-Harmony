"""BioFS — биологическая файловая система с самовосстановлением.

Метафора из PDF:
- Файлы — клетки
- Папки — ткани
- Диски — органы
- Сеть — кровеносная система
- Механизмы восстановления — иммунная система

Компоненты:
- Пассивная защита: шифрование, контрольные суммы, журналирование
- Активная защита: обнаружение ошибок, восстановление, замена компонентов
- Протокол «Феникс» — аварийное восстановление
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from .crypto import SymmetricCrypto, CryptoConfig, CryptoError, hash_sha256


class TissueType(str, Enum):
    """Типы тканей (папок)."""
    EPITHELIAL = "epithelial"      # граничные/защитные (конфиги, логи)
    CONNECTIVE = "connective"      # соединительные (данные, кэш)
    MUSCLE = "muscle"              # исполняемые (скрипты, бинарники)
    NERVOUS = "nervous"            # сигнальные (IPC, сокеты, очереди)


@dataclass
class CellMetadata:
    """Метаданные клетки (файла)."""
    path: str
    size: int
    checksum: str
    tissue_type: TissueType
    created_at: float
    modified_at: float
    access_count: int = 0
    encrypted: bool = False
    backup_count: int = 0
    last_verified: float = 0
    verified_ok: bool = True


@dataclass
class OrganConfig:
    """Конфигурация органа (диска/тома)."""
    path: Path
    tissue_type: TissueType
    max_cells: int = 10000
    backup_interval: float = 3600  # секунды
    redundancy: int = 2  # количество копий
    encryption_required: bool = False


class ImmuneSystem:
    """Иммунная система — детекторы и агенты восстановления."""

    def __init__(self, crypto: SymmetricCrypto | None = None) -> None:
        self.crypto = crypto
        self.detectors: list[Callable[[CellMetadata], tuple[bool, str]]] = []
        self.healing_agents: list[Callable[[CellMetadata], bool]] = []
        self._register_default_detectors()
        self._register_default_healers()

    def _register_default_detectors(self) -> None:
        # Детектор повреждения контрольной суммы
        def checksum_detector(cell: CellMetadata) -> tuple[bool, str]:
            if not cell.verified_ok:
                return True, f"checksum_mismatch: {cell.path}"
            return False, ""
        self.detectors.append(checksum_detector)

        # Детектор аномального размера
        def size_anomaly_detector(cell: CellMetadata) -> tuple[bool, str]:
            if cell.size == 0 and cell.access_count > 0:
                return True, f"zero_size_active_cell: {cell.path}"
            return False, ""
        self.detectors.append(size_anomaly_detector)

        # Детектор устаревшего бэкапа
        def stale_backup_detector(cell: CellMetadata) -> tuple[bool, str]:
            if cell.backup_count == 0 and time.time() - cell.modified_at > 86400:
                return True, f"no_backup_24h: {cell.path}"
            return False, ""
        self.detectors.append(stale_backup_detector)

    def _register_default_healers(self) -> None:
        # Агент восстановления из бэкапа
        def restore_from_backup(cell: CellMetadata) -> bool:
            # В реальной реализации: найти бэкап и восстановить
            return False
        self.healing_agents.append(restore_from_backup)

    def scan(self, cells: list[CellMetadata]) -> list[tuple[CellMetadata, str]]:
        """Сканировать клетки на наличие повреждений."""
        threats = []
        for cell in cells:
            for detector in self.detectors:
                threat, msg = detector(cell)
                if threat:
                    threats.append((cell, msg))
        return threats

    def heal(self, cell: CellMetadata, threat_msg: str) -> bool:
        """Попытаться исцелить клетку."""
        for healer in self.healing_agents:
            if healer(cell):
                return True
        return False


class BioFS:
    """Биологическая файловая система."""

    def __init__(
        self,
        root: Path,
        crypto: SymmetricCrypto | None = None,
        crypto_config: CryptoConfig | None = None,
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.crypto = crypto or (SymmetricCrypto(crypto_config) if crypto_config else None)
        self.immune = ImmuneSystem(self.crypto)
        self.registry: dict[str, CellMetadata] = {}
        self.organs: dict[str, OrganConfig] = {}
        self._load_registry()

    def _registry_path(self) -> Path:
        return self.root / ".biofs_registry.json"

    def _load_registry(self) -> None:
        reg_path = self._registry_path()
        if reg_path.exists():
            try:
                with open(reg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for path, meta in data.items():
                    self.registry[path] = CellMetadata(**meta)
            except Exception:
                pass

    def _save_registry(self) -> None:
        reg_path = self._registry_path()
        data = {path: meta.__dict__ for path, meta in self.registry.items()}
        with open(reg_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def register_organ(self, name: str, config: OrganConfig) -> None:
        """Зарегистрировать орган (том)."""
        config.path.mkdir(parents=True, exist_ok=True)
        self.organs[name] = config

    def create_cell(
        self,
        organ_name: str,
        relative_path: str,
        content: bytes = b"",
        tissue_type: TissueType | None = None,
    ) -> CellMetadata:
        """Создать клетку (файл)."""
        if organ_name not in self.organs:
            raise ValueError(f"Organ {organ_name} not registered")
        organ = self.organs[organ_name]
        if tissue_type is None:
            tissue_type = organ.tissue_type

        cell_path = organ.path / relative_path
        cell_path.parent.mkdir(parents=True, exist_ok=True)

        # Шифрование если требуется
        stored_content = content
        encrypted = False
        if organ.encryption_required and self.crypto:
            # Используем временный ключ (в реальности — из KeyManager)
            key = hashlib.sha256(b"biofs_default_key").digest()[:32]
            nonce, stored_content = self.crypto.encrypt(content, key)
            encrypted = True

        cell_path.write_bytes(stored_content)

        checksum = hash_sha256(stored_content).hex()
        now = time.time()
        meta = CellMetadata(
            path=str(cell_path.relative_to(self.root)),
            size=len(stored_content),
            checksum=checksum,
            tissue_type=tissue_type,
            created_at=now,
            modified_at=now,
            encrypted=encrypted,
        )
        self.registry[meta.path] = meta
        self._save_registry()
        return meta

    def read_cell(self, path: str) -> bytes:
        """Прочитать клетку."""
        if path not in self.registry:
            raise KeyError(f"Cell {path} not found")
        meta = self.registry[path]
        full_path = self.root / path
        content = full_path.read_bytes()

        # Проверка контрольной суммы
        actual_checksum = hash_sha256(content).hex()
        if actual_checksum != meta.checksum:
            meta.verified_ok = False
            self._save_registry()
            raise CryptoError(f"Checksum mismatch for {path}")

        meta.access_count += 1
        meta.last_verified = time.time()
        meta.verified_ok = True
        self._save_registry()

        # Расшифровка если нужно
        if meta.encrypted and self.crypto:
            key = hashlib.sha256(b"biofs_default_key").digest()[:32]
            # Формат: nonce(12) + ciphertext
            nonce = content[:12]
            ciphertext = content[12:]
            content = self.crypto.decrypt(nonce, ciphertext, key)

        return content

    def update_cell(self, path: str, content: bytes) -> CellMetadata:
        """Обновить клетку."""
        if path not in self.registry:
            raise KeyError(f"Cell {path} not found")
        meta = self.registry[path]
        full_path = self.root / path

        stored_content = content
        encrypted = meta.encrypted
        if encrypted and self.crypto:
            key = hashlib.sha256(b"biofs_default_key").digest()[:32]
            nonce, stored_content = self.crypto.encrypt(content, key)

        full_path.write_bytes(stored_content)

        meta.size = len(stored_content)
        meta.checksum = hash_sha256(stored_content).hex()
        meta.modified_at = time.time()
        meta.verified_ok = True
        self._save_registry()
        return meta

    def verify_all(self) -> dict[str, Any]:
        """Верификация всех клеток."""
        results = {"total": 0, "ok": 0, "corrupted": 0, "missing": 0, "details": []}
        for path, meta in self.registry.items():
            results["total"] += 1
            full_path = self.root / path
            if not full_path.exists():
                results["missing"] += 1
                results["details"].append({"path": path, "status": "missing"})
                continue
            try:
                content = full_path.read_bytes()
                actual = hash_sha256(content).hex()
                if actual == meta.checksum:
                    results["ok"] += 1
                    results["details"].append({"path": path, "status": "ok"})
                else:
                    results["corrupted"] += 1
                    results["details"].append({"path": path, "status": "corrupted", "expected": meta.checksum, "actual": actual})
            except Exception as e:
                results["corrupted"] += 1
                results["details"].append({"path": path, "status": "error", "error": str(e)})
        return results

    def run_immune_scan(self) -> dict[str, Any]:
        """Запуск иммунного сканирования."""
        cells = list(self.registry.values())
        threats = self.immune.scan(cells)
        healed = 0
        for cell, msg in threats:
            if self.immune.heal(cell, msg):
                healed += 1
        return {
            "scanned": len(cells),
            "threats_found": len(threats),
            "healed": healed,
            "threats": [{"path": c.path, "threat": t} for c, t in threats],
        }

    def phoenix_protocol(self, threshold: float = 0.8) -> dict[str, Any]:
        """Протокол «Феникс» — аварийное восстановление.

        Активируется при:
        - потере консенсуса > 33%
        - критическом снижении стабильности < 80%
        - нарушении PSI₀
        """
        verification = self.verify_all()
        stability = verification["ok"] / max(verification["total"], 1)

        if stability >= threshold:
            return {
                "activated": False,
                "reason": f"stability {stability:.1%} >= threshold {threshold:.1%}",
                "stability": stability,
            }

        # Восстановление из эталонных копий (здесь упрощено)
        restored = 0
        for detail in verification["details"]:
            if detail["status"] in ("corrupted", "missing"):
                # В реальности: восстановить из backup/эталонной копии V₀
                pass

        return {
            "activated": True,
            "reason": f"stability {stability:.1%} < threshold {threshold:.1%}",
            "stability": stability,
            "restored": restored,
            "verification": verification,
        }

    def stats(self) -> dict[str, Any]:
        """Статистика BioFS."""
        by_tissue: dict[str, int] = {}
        encrypted = 0
        for meta in self.registry.values():
            by_tissue[meta.tissue_type.value] = by_tissue.get(meta.tissue_type.value, 0) + 1
            if meta.encrypted:
                encrypted += 1
        return {
            "root": str(self.root),
            "total_cells": len(self.registry),
            "by_tissue": by_tissue,
            "encrypted_cells": encrypted,
            "organs": list(self.organs.keys()),
        }
