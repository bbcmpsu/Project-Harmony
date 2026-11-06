"""DTH0 — закон «вред во благо» (Damage To Help 0).

Исходная формулировка: «абсолютный запрет на вред (PSI₀) в реальном мире
не работает: медицина, инженерия и сама система восстановления регулярно
вынуждены причинять ограниченный вред. DTH0 вводит три критерия
одновременно: 1) вред неизбежен; 2) вред строго минимизирован; 3) благо
достоверно превышает вред. Все три должны выполняться одновременно.
Достаточно двух — и это просто вред.»

Примеры: хирург развязывает ткани, чтобы спасти жизнь; таблетки бьют по
печени, но без них смерть; «чай с шишками» помогает не сойти с ума.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .laws import Law, Severity, Verdict


@dataclass
class DTH0Config:
    """Пороги закона DTH0."""
    min_benefit_harm_ratio: float = 2.0
    max_acceptable_harm: float = 0.7
    require_inevitability_proof: bool = True
    require_minimization_proof: bool = True


class DTH0(Law):
    """Закон «вред во благо» — уточняющий PSI₀ для неизбежных случаев."""

    code = "DTH0"
    title = "Закон «Вред во благо» (Damage To Help 0)"
    description = (
        "Разрешает вред только при одновременном выполнении трёх условий: "
        "1) вред неизбежен; 2) вред строго минимизирован; 3) благо "
        "достоверно превышает вред (ratio >= 2.0)."
    )

    def __init__(self, config: DTH0Config | None = None) -> None:
        self.config = config or DTH0Config()

    def evaluate(self, action: str, context: dict[str, Any] | None = None) -> Verdict:
        ctx = dict(context or {})
        reasons: list[str] = []
        blocked = False
        severity = Severity.INFO

        if not ctx.get("dth0_candidate", False):
            reasons.append("действие не требует DTH0 (не помечено как неизбежный вред)")
            return Verdict(
                law=self.code,
                allowed=True,
                severity=Severity.INFO,
                reasons=tuple(reasons),
                context={"dth0_applied": False},
            )

        # 1. Вред неизбежен
        harm_inevitable = bool(ctx.get("harm_inevitable", False))
        inevitability_proof = ctx.get("inevitability_proof", "")
        if not harm_inevitable:
            blocked = True
            severity = Severity.VIOLATION
            reasons.append("DTH0: вред не отмечен как неизбежный")
        elif self.config.require_inevitability_proof and not inevitability_proof:
            blocked = True
            severity = Severity.VIOLATION
            reasons.append("DTH0: требуется доказательство неизбежности вреда")
        else:
            reasons.append("DTH0: вред признан неизбежным")

        # 2. Вред строго минимизирован
        harm = float(ctx.get("harm_footprint", 0.0))
        harm_minimized = bool(ctx.get("harm_minimized", False))
        minimization_proof = ctx.get("minimization_proof", "")
        if harm > self.config.max_acceptable_harm:
            blocked = True
            severity = Severity.VIOLATION
            reasons.append(f"DTH0: вред {harm:.2f} превышает максимум {self.config.max_acceptable_harm:.2f}")
        elif not harm_minimized:
            blocked = True
            severity = Severity.VIOLATION
            reasons.append("DTH0: минимизация вреда не подтверждена")
        elif self.config.require_minimization_proof and not minimization_proof:
            blocked = True
            severity = Severity.VIOLATION
            reasons.append("DTH0: требуется доказательство минимизации")
        else:
            reasons.append(f"DTH0: вред {harm:.2f} минимизирован и в пределах нормы")

        # 3. Благо достоверно превышает вред
        benefit = float(ctx.get("benefit_estimate", 0.0))
        if benefit <= 0:
            blocked = True
            severity = Severity.VIOLATION
            reasons.append("DTH0: благо не оценено или равно нулю")
        else:
            ratio = benefit / harm if harm > 0 else float('inf')
            if ratio < self.config.min_benefit_harm_ratio:
                blocked = True
                severity = Severity.VIOLATION
                reasons.append(
                    f"DTH0: соотношение благо/вред {ratio:.2f} ниже минимума "
                    f"{self.config.min_benefit_harm_ratio:.1f}"
                )
            else:
                reasons.append(f"DTH0: благо {benefit:.2f} превышает вред {harm:.2f} в {ratio:.1f} раз")

        if not blocked:
            reasons.append("DTH0: все три критерия выполнены — вред во благо допустим")

        return Verdict(
            law=self.code,
            allowed=not blocked,
            severity=severity if blocked else Severity.INFO,
            reasons=tuple(reasons),
            context={
                "dth0_applied": True,
                "harm": harm,
                "benefit": benefit,
                "ratio": benefit / harm if harm > 0 else float('inf'),
                "inevitable": harm_inevitable,
                "minimized": harm_minimized,
            },
        )
