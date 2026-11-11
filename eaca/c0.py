"""C₀ — закон контроля ковариационных сдвигов.

Исходная формулировка: «система должна обнаруживать и ограничивать
непредвиденные последствия своих решений, когда изменение одной переменной
вызывает каскад смещений в смежных».

Ковариационный сдвиг — это ситуация, когда действие, прошедшее проверку
законов в момент принятия, порождает побочные эффекты, которые не были
учтены в контексте. C₀ — страховка на случай, когда «всё по правилам»,
но результат вреден.

Методика: мониторинг дельт ключевых метрик после действия. Если метрики
уходят за пороговое отклонение от базовой линии — действие откатывается
или блокируется до разбора.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .laws import Law, Severity, Verdict


@dataclass
class C0Config:
    """Пороги закона C₀."""
    max_drift: float = 0.3
    min_baseline_samples: int = 10
    sensitive_metrics: tuple[str, ...] = field(
        default_factory=lambda: (
            "harm_rate", "consent_violation_rate", "autonomy_score",
            "trust_index", "cooperation_level", "resource_fairness"
        )
    )
    watched_metrics: tuple[str, ...] = field(
        default_factory=lambda: (
            "harm_rate", "consent_violation_rate", "autonomy_score",
            "trust_index", "cooperation_level", "resource_fairness",
            "decision_latency", "error_rate"
        )
    )


class C0(Law):
    """Закон контроля ковариационных сдвигов."""

    code = "C₀"
    title = "Закон контроля ковариационных сдвигов"
    description = (
        "Система обнаруживает и ограничивает непредвиденные последствия "
        "решений: ковариационные сдвиги метрик за пороговые значения."
    )

    def __init__(self, config: C0Config | None = None) -> None:
        self.config = config or C0Config()
        self._baselines: dict[str, list[float]] = {}
        self._drift_history: list[dict[str, Any]] = []

    def _update_baseline(self, metric: str, value: float) -> None:
        if metric not in self._baselines:
            self._baselines[metric] = []
        self._baselines[metric].append(value)
        if len(self._baselines[metric]) > 1000:
            self._baselines[metric] = self._baselines[metric][-1000:]

    def _get_baseline_stats(self, metric: str) -> tuple[float, float] | None:
        values = self._baselines.get(metric, [])
        if len(values) < self.config.min_baseline_samples:
            return None
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        return mean, std

    def _check_drift(self, metric: str, current: float) -> tuple[bool, str | None]:
        stats = self._get_baseline_stats(metric)
        if stats is None:
            return False, None
        mean, std = stats
        if std == 0:
            # Если std=0, проверяем относительное изменение
            rel_change = abs(current - mean) / abs(mean) if mean != 0 else float('inf')
            if rel_change > self.config.max_drift:
                return True, (
                    f"ковариационный сдвиг {metric}: rel_change={rel_change:.2%} "
                    f"(порог {self.config.max_drift:.0%}), mean={mean:.4f}, "
                    f"current={current:.4f}"
                )
            return False, None
        z_score = abs(current - mean) / std
        threshold_z = 3.0
        threshold_rel = self.config.max_drift
        rel_change = abs(current - mean) / abs(mean) if mean != 0 else float('inf')
        if z_score > threshold_z or rel_change > threshold_rel:
            return True, (
                f"ковариационный сдвиг {metric}: z={z_score:.2f} "
                f"(порог {threshold_z}), rel_change={rel_change:.2%} "
                f"(порог {threshold_rel:.0%}), mean={mean:.4f}, "
                f"current={current:.4f}"
            )
        return False, None

    def record_metrics(self, metrics: dict[str, float]) -> None:
        for metric, value in metrics.items():
            if metric in self.config.watched_metrics:
                self._update_baseline(metric, value)

    def evaluate(self, action: str, context: dict[str, Any] | None = None) -> Verdict:
        ctx = dict(context or {})
        reasons: list[str] = []
        blocked = False
        severity = Severity.INFO

        post_metrics = ctx.get("post_metrics", {})
        if not post_metrics:
            reasons.append("post_metrics не предоставлены — C₀ не проверяется")
        else:
            for metric, value in post_metrics.items():
                if metric not in self.config.watched_metrics:
                    continue
                drift, msg = self._check_drift(metric, float(value))
                if drift:
                    blocked = True
                    severity = Severity.VIOLATION
                    if msg is not None:
                        reasons.append(msg)
                    else:
                        reasons.append(f"ковариационный сдвиг {metric}: значение {value} за пределами допуска")
                    self._drift_history.append({
                        "action": action,
                        "metric": metric,
                        "value": value,
                        "timestamp": ctx.get("timestamp"),
                    })

        if not blocked:
            self.record_metrics(post_metrics)
            reasons.append("C₀: ковариационных сдвигов не обнаружено, базовые линии обновлены")

        return Verdict(
            law=self.code,
            allowed=not blocked,
            severity=severity if blocked else Severity.INFO,
            reasons=tuple(reasons),
            context={"checked_metrics": list(post_metrics.keys()), "baselines_ready": list(self._baselines.keys())},
        )

    def get_drift_report(self) -> dict[str, Any]:
        report = {}
        for metric in self.config.watched_metrics:
            stats = self._get_baseline_stats(metric)
            if stats:
                mean, std = stats
                report[metric] = {"mean": mean, "std": std, "samples": len(self._baselines[metric])}
        return {
            "baselines": report,
            "drift_events": len(self._drift_history),
            "recent_drifts": self._drift_history[-10:] if self._drift_history else [],
        }
