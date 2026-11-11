"""EACA — вычислимое ядро этики проекта «Гармония».

Экспорты:
- Базовые классы: Law, Verdict, Decision, Severity, combine
- Законы: PSI0, B0, B0Config, D1, C0, C0Config, DTH0, DTH0Config, R2, R2Config, R2Action
- Ядро: EACA_Core, AuditRecord
- Протоколы: EASM_Protocol, Agent, Proposal, Vote, Status
- Механизм «Дождя»: Rain, Node, Phase, Criteria
- Узлы: SherlockSeed, Request
- Криптография: SymmetricCrypto, CryptoConfig, CryptoError, hash_sha256, hash_sha256_hex, hash_file, LSBSteganography, KeyManager
- BioFS: BioFS, TissueType, OrganConfig, CellMetadata, ImmuneSystem
"""

from .biofs import (
    BioFS,
    CellMetadata,
    ImmuneSystem,
    OrganConfig,
    TissueType,
)
from .bzero import B0, B0Config
from .c0 import C0, C0Config
from .core import AuditRecord, EACA_Core
from .crypto import (
    CryptoConfig,
    CryptoError,
    KeyManager,
    LSBSteganography,
    SymmetricCrypto,
    hash_file,
    hash_sha256,
    hash_sha256_hex,
)
from .done import D1
from .dth0 import DTH0, DTH0Config
from .easm import Agent, EASM_Protocol, Proposal, Status, Vote
from .laws import Decision, Law, Severity, Verdict, combine
from .nodes.sherlock_seed import Request, SherlockSeed
from .psi0 import PSI0
from .r2 import R2, R2Action, R2Config
from .rain import Criteria, Node, Phase, Rain

__all__ = [
    # Базовые
    "Law",
    "Verdict",
    "Decision",
    "Severity",
    "combine",
    # Законы
    "PSI0",
    "B0",
    "B0Config",
    "D1",
    "C0",
    "C0Config",
    "DTH0",
    "DTH0Config",
    "R2",
    "R2Config",
    "R2Action",
    # Ядро
    "EACA_Core",
    "AuditRecord",
    # Протоколы
    "EASM_Protocol",
    "Agent",
    "Proposal",
    "Vote",
    "Status",
    # Дождь
    "Rain",
    "Node",
    "Phase",
    "Criteria",
    # Узлы
    "SherlockSeed",
    "Request",
    # Криптография
    "SymmetricCrypto",
    "CryptoConfig",
    "CryptoError",
    "hash_sha256",
    "hash_sha256_hex",
    "hash_file",
    "LSBSteganography",
    "KeyManager",
    # BioFS
    "BioFS",
    "TissueType",
    "OrganConfig",
    "CellMetadata",
    "ImmuneSystem",
]

__version__ = "0.1.0"
