"""R₂ — закон «рокировки» (скользящая защита).

Исходная формулировка: «операционный механизм защиты — смена ролей и
каналов без потери состояния». Когда узел обнаруживает угрозу или
нарушение, он не просто блокирует — он «рокует»: меняет роль, интерфейс,
канал связи, сохраняя состояние и продолжая работу.

Это защита через подвижность: вместо статической стены — динамическая
перестройка. Аналогия с шахматами: рокировка — единственный ход, где
двигаются две фигуры одновременно (король + ладья), защищая короля и
активируя ладью.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .laws import Law, Severity, Verdict


class R2Action(str, Enum):
    """Типы рокировок."""
    ROLE_SWITCH = "role_switch"        # смена роли узла
    CHANNEL_HOP = "channel_hop"        # смена канала связи
    INTERFACE_SHIFT = "interface_shift"  # смена интерфейса
    STATE_MIGRATE = "state_migrate"    # миграция состояния на другой узел
    FULL_CASTLING = "full_castling"    # полная рокировка (роль + канал + состояние)


@dataclass
class R2Config:
    """Конфигурация закона R₂."""
    # Максимальное время на рокировку (секунды)
    max_castling_time: float = 5.0
    # Требуемое подтверждение успеха рокировки
    require_confirmation: bool = True
    # Разрешённые типы рокировок
    allowed_actions: tuple[R2Action, ...] = (
        R2Action.ROLE_SWITCH,
        R2Action.CHANNEL_HOP,
        R2Action.INTERFACE_SHIFT,
        R2Action.STATE_MIGRATE,
        R2Action.FULL_CASTLING,
    )


class R2(Law):
    """Закон «Рокировка» — скользящая защита через смену ролей и каналов."""

    code = "R₂"
    title = "Закон «Рокировка» (скользящая защита)"
    description = (
        "Операционная защита: смена ролей, каналов, интерфейсов без потери "
        "состояния. При угрозе — рокировка, а не блокировка."
    )

    def __init__(self, config: R2Config | None = None) -> None:
        self.config = config or R2Config()
        # История рокировок
        self._castling_history: list[dict[str, Any]] = []

    def evaluate(self, action: str, context: dict[str, Any] | None = None) -> Verdict:
        ctx = dict(context or {})
        reasons: list[str] = []
        blocked = False
        severity = Severity.INFO

        # R₂ применяется только при явном запросе рокировки
        castling_request = ctx.get("r2_castling")
        if not castling_request:
            reasons.append("R₂: запрос рокировки не получен — закон не активирован")
            return Verdict(
                law=self.code,
                allowed=True,
                severity=Severity.INFO,
                reasons=tuple(reasons),
                context={"r2_activated": False},
            )

        action_type = castling_request.get("action")
        if action_type not in [a.value for a in self.config.allowed_actions]:
            blocked = True
            severity = Severity.VIOLATION
            reasons.append(f"R₂: недопустимый тип рокировки: {action_type}")
        else:
            reasons.append(f"R₂: тип рокировки {action_type} допустим")

        # Проверяем сохранение состояния
        state_preserved = castling_request.get("state_preserved", False)
        if not state_preserved:
            blocked = True
            severity = Severity.VIOLATION
            reasons.append("R₂: состояние не сохранено — рокировка неполная")
        else:
            reasons.append("R₂: состояние сохранено")

        # Проверяем время выполнения
        castling_time = float(castling_request.get("castling_time", 0.0))
        if castling_time > self.config.max_castling_time:
            blocked = True
            severity = Severity.WARNING
            reasons.append(f"R₂: время рокировки {castling_time:.1f}с превышает лимит {self.config.max_castling_time:.1f}с")
        else:
            reasons.append(f"R₂: время рокировки {castling_time:.1f}с в норме")

        # Записываем в историю
        self._castling_history.append({
            "action": action,
            "castling_type": action_type,
            "success": not blocked,
            "time": castling_time,
            "state_preserved": state_preserved,
            "timestamp": ctx.get("timestamp"),
        })

        if not blocked:
            reasons.append("R₂: рокировка выполнена успешно — защита через подвижность")

        return Verdict(
            law=self.code,
            allowed=not blocked,
            severity=severity if blocked else Severity.INFO,
            reasons=tuple(reasons),
            context={
                "r2_activated": True,
                "castling_type": action_type,
                "castling_time": castling_time,
                "state_preserved": state_preserved,
            },
        )

    def get_castling_report(self) -> dict[str, Any]:
        """Отчёт по рокировкам."""
        return {
            "total_castlings": len(self._castling_history),
            "successful": sum(1 for h in self._castling_history if h["success"]),
            "by_type": {
                action.value: sum(1 for h in self._castling_history if h["castling_type"] == action.value)
                for action in self.config.allowed_actions
            },
            "recent": self._castling_history[-10:] if self._castling_history else [],
        }
