"""EACA_Core — ядро этической проверки.

Ядро принимает действие и контекст, прогоняет через все законы и возвращает
совокупный ``Decision``. Ключевое правило (из проекта «Гармония»): действие
разрешено, только если разрешили **все** законы. Закон — ограничитель,
а не рекомендация.

Дополнительно ядро ведёт **журнал решений** (журнал неотвратимости): каждое
проверяемое действие записывается, включая заблокированные. Это нужно, чтобы
«точка кристаллизации» из «Дождя» могла расти не на словах, а на проверяемой
истории.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .bzero import B0, B0Config
from .c0 import C0, C0Config
from .done import D1
from .dth0 import DTH0, DTH0Config
from .laws import Decision, Law, Severity, Verdict, combine
from .psi0 import PSI0
from .r2 import R2, R2Config

@dataclass
class AuditRecord:
    """Запись в журнале решений."""

    ts: float
    action: str
    allowed: bool
    severity: str
    reasons: tuple[str, ...]
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "action": self.action,
            "allowed": self.allowed,
            "severity": self.severity,
            "reasons": list(self.reasons),
            "context": self.context,
        }

class EACA_Core:
    """Ядро EACA: набор законов + журнал решений."""

    def __init__(
        self,
        laws: Iterable[Law] | None = None,
        *,
        audit_path: str | Path | None = None,
        enable_extended_laws: bool = True,
    ) -> None:
        if laws is None:
            base_laws = [PSI0(), B0(), D1()]
            if enable_extended_laws:
                base_laws.extend([C0(), DTH0(), R2()])
            laws = base_laws
        self.laws: list[Law] = list(laws)
        self.audit_path = Path(audit_path) if audit_path else None
        self.records: list[AuditRecord] = []

    # -- проверка ---------------------------------------------------------

    def check(self, action: str, context: dict[str, Any] | None = None) -> Decision:
        """Проверить действие всеми законами."""
        ctx = dict(context or {})
        verdicts = [law.evaluate(action, ctx) for law in self.laws]
        decision = combine(verdicts)
        self._record(action, decision, ctx)
        return decision

    def allows(self, action: str, context: dict[str, Any] | None = None) -> bool:
        """Короткая форма: разрешено ли действие."""
        return self.check(action, context).allowed

    def explain(self, action: str, context: dict[str, Any] | None = None) -> str:
        """Проверить и вернуть человекочитаемое объяснение."""
        return self.check(action, context).explain()

    # -- журнал -----------------------------------------------------------

    def _record(self, action: str, decision: Decision, context: dict[str, Any]) -> None:
        rec = AuditRecord(
            ts=time.time(),
            action=action,
            allowed=decision.allowed,
            severity=decision.severity.value,
            reasons=decision.reasons,
            context={k: v for k, v in context.items() if _jsonable(v)},
        )
        self.records.append(rec)
        if self.audit_path:
            self.flush_audit()

    def flush_audit(self) -> None:
        """Дописать журнал в файл (JSONL)."""
        if not self.audit_path:
            return
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as fh:
            for rec in self.records:
                fh.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
        self.records.clear()

    # -- статистика -------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Сводка по принятым решениям."""
        total = len(self.records)
        blocked = sum(1 for r in self.records if not r.allowed)
        return {
            "total": total,
            "allowed": total - blocked,
            "blocked": blocked,
            "laws": [law.code for law in self.laws],
        }

def _jsonable(value: Any) -> bool:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return False
    return True

__all__ = [
    "EACA_Core",
    "AuditRecord",
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
    "Decision",
    "Verdict",
    "Severity",
]
