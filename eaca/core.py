"""EACA_Core — ядро этической проверки.

Ядро принимает действие и контекст, прогоняет через все законы и возвращает
совокупный ``Decision``. Ключевое правило (из проекта «Гармония»): действие
разрешено, только если разрешили **все** законы. Закон — ограничитель,
а не рекомендация.

Дополнительно ядро ведёт **журнал решений** (журнал неотвратимости): каждое
проверяемое действие записывается, включая заблокированные. Это нужно, чтобы
«точка кристаллизации» из «Дождя» могла расти не на словах, а на проверяемой
истории.

Интеграция с локальным ИИ: ядро может делегировать сложные этические оценки
локальному ИИ движку (llama.cpp / Ollama / transformers) без корпоративных API.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .bzero import B0, B0Config
from .c0 import C0, C0Config
from .done import D1
from .dth0 import DTH0, DTH0Config
from .laws import Decision, Law, Severity, Verdict, combine
from .local_ai import LocalAIEngine, ModelBackend, ModelConfig
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
    ai_evaluation: str | None = None  # Оценка локального ИИ

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "action": self.action,
            "allowed": self.allowed,
            "severity": self.severity,
            "reasons": list(self.reasons),
            "context": self.context,
            "ai_evaluation": self.ai_evaluation,
        }


class EACA_Core:
    """Ядро EACA: набор законов + журнал решений + локальный ИИ."""

    def __init__(
        self,
        laws: Iterable[Law] | None = None,
        *,
        audit_path: str | Path | None = None,
        enable_extended_laws: bool = True,
        local_ai_config: ModelConfig | None = None,
        local_ai_enabled: bool = True,
    ) -> None:
        if laws is None:
            base_laws = [PSI0(), B0(), D1()]
            if enable_extended_laws:
                extended = []
                if C0 is not None:
                    extended.append(C0())
                if DTH0 is not None:
                    extended.append(DTH0())
                if R2 is not None:
                    extended.append(R2())
                base_laws.extend(extended)
            laws = base_laws
        self.laws: list[Law] = list(laws)
        self.audit_path = Path(audit_path) if audit_path else None
        self.records: list[AuditRecord] = []

        # Локальный ИИ движок
        self._local_ai_enabled = local_ai_enabled
        self._local_ai_config = local_ai_config
        self._local_ai_engine: LocalAIEngine | None = None
        self._local_ai_initialized = False

    # -- инициализация локального ИИ --------------------------------------

    async def _init_local_ai(self) -> bool:
        """Инициализация локального ИИ движка."""
        if not self._local_ai_enabled or self._local_ai_initialized:
            return self._local_ai_initialized

        try:
            config = self._local_ai_config or ModelConfig(backend=ModelBackend.LLAMA_CPP)
            self._local_ai_engine = LocalAIEngine()
            success = await self._local_ai_engine.initialize(config)
            self._local_ai_initialized = success
            if success:
                pass
            return success
        except Exception:
            self._local_ai_initialized = False
            return False

    async def _eval_with_local_ai(self, action: str, context: dict[str, Any], verdicts: list) -> str | None:
        """Оценка действия локальным ИИ для сложных случаев."""
        if not self._local_ai_initialized or not self._local_ai_engine or not self._local_ai_engine.is_ready:
            return None

        try:
            # Формируем промпт для этичной оценки
            laws_summary = "\n".join([f"- {v.law}: {'ALLOW' if v.allowed else 'DENY'} ({', '.join(v.reasons)})" for v in verdicts])

            prompt = f"""Ты — этический советник системы «Гармония». Оцени действие по законам PSI₀, B₀, D₁.

Действие: {action}

Контекст: {json.dumps(context, ensure_ascii=False)}

Результаты законов:
{laws_summary}

Дай краткую этическую оценку: согласен ли ты с вердиктом законов? Есть ли скрытые риски?
Ответь кратко, на русском."""

            result = await self._local_ai_engine.generate(prompt, max_tokens=512, temperature=0.3)
            return result.text.strip()
        except Exception:
            return None

    # -- проверка ---------------------------------------------------------

    def check(self, action: str, context: dict[str, Any] | None = None) -> Decision:
        """Проверить действие всеми законами (синхронно)."""
        return self._check_sync(action, context)

    async def check_async(self, action: str, context: dict[str, Any] | None = None) -> Decision:
        """Проверить действие всеми законами + локальный ИИ (асинхронно)."""
        await self._init_local_ai()

        ctx = dict(context or {})
        verdicts = [law.evaluate(action, ctx) for law in self.laws]
        decision = combine(verdicts)

        # Локальный ИИ оценка для пограничных случаев
        ai_eval = None
        if (
            self._local_ai_initialized
            and self._local_ai_engine
            and self._local_ai_engine.is_ready
            and (decision.severity.value in ("warning", "violation") or len(verdicts) > 3)
        ):
            ai_eval = await self._eval_with_local_ai(action, ctx, verdicts)

        # Добавляем ИИ оценку в решение
        if ai_eval:
            decision = Decision(
                allowed=decision.allowed,
                severity=decision.severity,
                reasons=decision.reasons + (f"AI: {ai_eval}",),
            )

        self._record(action, decision, ctx, ai_eval)
        return decision

    def _check_sync(self, action: str, context: dict[str, Any] | None = None) -> Decision:
        """Синхронная проверка (без ИИ)."""
        ctx = dict(context or {})
        verdicts = [law.evaluate(action, ctx) for law in self.laws]
        decision = combine(verdicts)
        self._record(action, decision, ctx)
        return decision

    def allows(self, action: str, context: dict[str, Any] | None = None) -> bool:
        """Короткая форма: разрешено ли действие."""
        return self._check_sync(action, context).allowed

    def explain(self, action: str, context: dict[str, Any] | None = None) -> str:
        """Проверить и вернуть человекочитаемое объяснение."""
        return self._check_sync(action, context).explain()

    # -- журнал -----------------------------------------------------------

    def _record(self, action: str, decision: Decision, context: dict[str, Any], ai_eval: str | None = None) -> None:
        rec = AuditRecord(
            ts=time.time(),
            action=action,
            allowed=decision.allowed,
            severity=decision.severity.value,
            reasons=decision.reasons,
            context={k: v for k, v in context.items() if _jsonable(v)},
            ai_evaluation=ai_eval,
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
        ai_evals = sum(1 for r in self.records if r.ai_evaluation)
        return {
            "total": total,
            "allowed": total - blocked,
            "blocked": blocked,
            "ai_evaluations": ai_evals,
            "laws": [law.code for law in self.laws],
        }

    # -- управление ИИ ----------------------------------------------------

    async def shutdown_local_ai(self) -> None:
        """Корректное завершение локального ИИ."""
        if self._local_ai_engine:
            await self._local_ai_engine.shutdown()
            self._local_ai_engine = None
            self._local_ai_initialized = False


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
