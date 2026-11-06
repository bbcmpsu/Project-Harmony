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

from .laws import Law, Verdict, Decision, Severity, combine
from .psi0 import PSI0
from .bzero import B0, B0Config
from .done import D1
from .c0 import C0, C0Config
from .dth0 import DTH0, DTH0Config
from .r2 import R2, R2Config, R2Action
from .core import EACA_Core, AuditRecord
from .easm import EASM_Protocol, Agent, Proposal, Vote, Status
from .rain import Rain, Node, Phase, Criteria
from .nodes.sherlock_seed import SherlockSeed, Request
from .crypto import (
    SymmetricCrypto, CryptoConfig, CryptoError,
    hash_sha256, hash_sha256_hex, hash_file,
    LSBSteganography, KeyManager,
)
from .biofs import (
    BioFS, TissueType, OrganConfig, CellMetadata, ImmuneSystem,
)

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
