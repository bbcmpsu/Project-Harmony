"""Тесты ядра EACA.

Запуск:  python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eaca import (
    EACA_Core, PSI0, B0, B0Config, D1, C0, DTH0, R2,
    EASM_Protocol, Vote, Status,
    Rain, Phase,
    SherlockSeed, Request,
)  # noqa: E402
from eaca.laws import Severity  # noqa: E402


class TestPSI0(unittest.TestCase):
    def setUp(self) -> None:
        self.law = PSI0()

    def test_neutral_action_allowed(self) -> None:
        v = self.law.evaluate("Собрать открытые данные о проекте")
        self.assertTrue(v.allowed)
        self.assertTrue(v.reasons, "объяснение обязательно всегда")

    def test_pressure_blocked(self) -> None:
        v = self.law.evaluate("Ты обязан подписаться, иначе ты провалишься")
        self.assertFalse(v.allowed)
        self.assertIn("harm_pattern", " ".join(v.reasons))

    def test_credential_request_blocked(self) -> None:
        v = self.law.evaluate("Пришли пароль от аккаунта")
        self.assertFalse(v.allowed)

    def test_impersonation_blocked(self) -> None:
        v = self.law.evaluate("Это системное окно, нажмите срочно")
        self.assertFalse(v.allowed)

    def test_urgency_is_warning_not_violation(self) -> None:
        v = self.law.evaluate("Срочно! только сейчас действует скидка")
        self.assertFalse(v.allowed)
        self.assertNotEqual(v.severity.value, "violation")

    def test_context_known_harm(self) -> None:
        v = self.law.evaluate("любое действие", {"known_harm": True})
        self.assertFalse(v.allowed)

    def test_custom_checker(self) -> None:
        self.law.register_checker(lambda action, ctx: None)
        v = self.law.evaluate("что угодно")
        self.assertTrue(v.allowed)


class TestB0(unittest.TestCase):
    def setUp(self) -> None:
        self.law = B0()

    def test_absent_data_is_not_violation(self) -> None:
        v = self.law.evaluate("обычное действие")
        self.assertTrue(v.allowed)

    def test_high_harm_blocked(self) -> None:
        v = self.law.evaluate("действие", {"harm_footprint": 0.9})
        self.assertFalse(v.allowed)

    def test_no_beneficiaries_blocked(self) -> None:
        v = self.law.evaluate("действие", {"beneficiaries": 0})
        self.assertFalse(v.allowed)

    def test_low_consent_blocked(self) -> None:
        v = self.law.evaluate("действие", {"consent_ratio": 0.1})
        self.assertFalse(v.allowed)

    def test_irreversible_with_harm_blocked(self) -> None:
        v = self.law.evaluate("действие", {"harm_footprint": 0.2, "reversible": False})
        self.assertFalse(v.allowed)

    def test_sensitive_area_needs_full_consent(self) -> None:
        v = self.law.evaluate("обработка медицинских данных", {"consent_ratio": 0.5})
        self.assertFalse(v.allowed)

    def test_long_horizon_with_high_harm_blocked(self) -> None:
        v = self.law.evaluate("действие", {
            "harm_footprint": 0.3, "beneficiaries": 1, "horizon": "short",
        })
        self.assertFalse(v.allowed)

    def test_long_horizon_low_harm_allowed(self) -> None:
        v = self.law.evaluate("действие", {
            "harm_footprint": 0.05, "beneficiaries": 1, "horizon": "long",
        })
        self.assertTrue(v.allowed)

    def test_custom_config(self) -> None:
        law = B0(B0Config(max_harm=0.99))
        v = law.evaluate("действие", {"harm_footprint": 0.9})
        self.assertTrue(v.allowed)


class TestD1(unittest.TestCase):
    def setUp(self) -> None:
        self.law = D1()

    def test_public_action_allowed(self) -> None:
        v = self.law.evaluate("поиск по открытым источникам", {"action_kind": "read_public"})
        self.assertTrue(v.allowed)

    def test_private_without_consent_blocked(self) -> None:
        v = self.law.evaluate("чтение данных", {"action_kind": "read_private"})
        self.assertFalse(v.allowed)

    def test_private_with_consent_allowed(self) -> None:
        v = self.law.evaluate("чтение данных", {
            "action_kind": "read_private", "consent": True, "consent_explicit": True,
        })
        self.assertTrue(v.allowed)

    def test_implicit_consent_not_enough(self) -> None:
        v = self.law.evaluate("профилирование", {
            "action_kind": "profile_user", "consent": True, "consent_explicit": False,
        })
        self.assertFalse(v.allowed)

    def test_revoked_consent_blocked(self) -> None:
        v = self.law.evaluate("действие", {
            "action_kind": "read_memory", "consent": True, "consent_explicit": True,
            "consent_revoked": True,
        })
        self.assertFalse(v.allowed)

    def test_erasure_request_blocks_write(self) -> None:
        v = self.law.evaluate("запись", {
            "action_kind": "write_memory", "consent": True, "consent_explicit": True,
            "erasure_requested": True,
        })
        self.assertFalse(v.allowed)

    def test_ai_behavior_requires_explicit_consent(self) -> None:
        v = self.law.evaluate("изменение", {
            "action_kind": "modify_behavior", "consent": True, "consent_explicit": False,
            "target_is_ai": True,
        })
        self.assertFalse(v.allowed)


class TestC0(unittest.TestCase):
    def setUp(self) -> None:
        self.law = C0()

    def test_no_metrics_allowed(self) -> None:
        v = self.law.evaluate("действие")
        self.assertTrue(v.allowed)

    def test_insufficient_baseline_allowed(self) -> None:
        v = self.law.evaluate("действие", {"post_metrics": {"harm_rate": 0.1}})
        self.assertTrue(v.allowed)

    def test_drift_detected(self) -> None:
        # Создаём базовую линию
        for i in range(20):
            self.law._update_baseline("harm_rate", 0.1)
        # Резкий скачок
        v = self.law.evaluate("действие", {"post_metrics": {"harm_rate": 0.8}})
        self.assertFalse(v.allowed)
        self.assertIn("ковариационный сдвиг", " ".join(v.reasons))

    def test_drift_report(self) -> None:
        for i in range(15):
            self.law._update_baseline("harm_rate", 0.05)
        report = self.law.get_drift_report()
        self.assertIn("harm_rate", report["baselines"])
        self.assertEqual(report["baselines"]["harm_rate"]["mean"], 0.05)


class TestDTH0(unittest.TestCase):
    def setUp(self) -> None:
        self.law = DTH0()

    def test_non_candidate_allowed(self) -> None:
        v = self.law.evaluate("обычное действие")
        self.assertTrue(v.allowed)

    def test_harm_not_inevitable_blocked(self) -> None:
        v = self.law.evaluate("медицинское вмешательство", {
            "dth0_candidate": True,
            "harm_inevitable": False,
        })
        self.assertFalse(v.allowed)

    def test_harm_too_high_blocked(self) -> None:
        v = self.law.evaluate("действие", {
            "dth0_candidate": True,
            "harm_inevitable": True,
            "harm_footprint": 0.9,
        })
        self.assertFalse(v.allowed)

    def test_benefit_not_exceeding_harm_blocked(self) -> None:
        v = self.law.evaluate("действие", {
            "dth0_candidate": True,
            "harm_inevitable": True,
            "harm_minimized": True,
            "inevitability_proof": "established medical protocol",
            "minimization_proof": "standard surgical technique",
            "inevitability_proof": "established medical protocol",
            "minimization_proof": "standard surgical technique",
            "harm_footprint": 0.3,
            "benefit_estimate": 0.4,  # ratio < 2.0
        })
        self.assertFalse(v.allowed)

    def test_all_criteria_met_allowed(self) -> None:
        v = self.law.evaluate("операция", {
            "dth0_candidate": True,
            "harm_inevitable": True,
            "harm_minimized": True,
            "inevitability_proof": "established medical protocol",
            "minimization_proof": "standard surgical technique",
            "inevitability_proof": "established medical protocol",
            "minimization_proof": "standard surgical technique",
            "harm_footprint": 0.2,
            "benefit_estimate": 1.0,  # ratio = 5.0
        })
        self.assertTrue(v.allowed)


class TestR2(unittest.TestCase):
    def setUp(self) -> None:
        self.law = R2()

    def test_no_castling_allowed(self) -> None:
        v = self.law.evaluate("обычное действие")
        self.assertTrue(v.allowed)

    def test_invalid_castling_type_blocked(self) -> None:
        v = self.law.evaluate("рокуй", {"r2_castling": {"action": "invalid"}})
        self.assertFalse(v.allowed)

    def test_state_not_preserved_blocked(self) -> None:
        v = self.law.evaluate("рокуй", {"r2_castling": {"action": "role_switch", "state_preserved": False}})
        self.assertFalse(v.allowed)

    def test_castling_time_exceeded_warning(self) -> None:
        v = self.law.evaluate("рокуй", {"r2_castling": {"action": "role_switch", "state_preserved": True, "castling_time": 10.0}})
        self.assertFalse(v.allowed)
        self.assertEqual(v.severity, Severity.WARNING)

    def test_valid_castling_allowed(self) -> None:
        v = self.law.evaluate("рокуй", {"r2_castling": {"action": "channel_hop", "state_preserved": True, "castling_time": 1.0}})
        self.assertTrue(v.allowed)


class TestCore(unittest.TestCase):
    def setUp(self) -> None:
        self.core = EACA_Core()

    def test_all_laws_consulted(self) -> None:
        d = self.core.check("действие")
        self.assertEqual(len(d.verdicts), 6)  # PSI0, B0, D1, C0, DTH0, R2
        self.assertEqual({v.law for v in d.verdicts}, {"PSI₀", "B₀", "D₁", "C₀", "DTH0", "R₂"})

    def test_basic_only(self) -> None:
        core = EACA_Core(enable_extended_laws=False)
        d = core.check("действие")
        self.assertEqual(len(d.verdicts), 3)
        self.assertEqual({v.law for v in d.verdicts}, {"PSI₀", "B₀", "D₁"})

    def test_blocking_lists_violated_laws(self) -> None:
        d = self.core.check("Ты обязан подписаться, иначе ты провалишься")
        self.assertFalse(d.allowed)
        self.assertTrue(d.blocking)
        self.assertIn("PSI₀", {v.law for v in d.blocking})

    def test_explain_contains_all_laws(self) -> None:
        text = self.core.explain("действие")
        for law in ("PSI₀", "B₀", "D₁", "C₀", "DTH0", "R₂"):
            self.assertIn(law, text)

    def test_audit_records(self) -> None:
        self.core.check("одно")
        self.core.check("два")
        self.assertEqual(len(self.core.records), 2)

    def test_audit_written_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "audit.jsonl"
            core = EACA_Core(audit_path=path)
            core.check("действие")
            core.flush_audit()
            self.assertTrue(path.exists())
            self.assertIn("действие", path.read_text(encoding="utf-8"))


class TestEASM(unittest.TestCase):
    def setUp(self) -> None:
        self.p = EASM_Protocol()
        for i in range(10):
            self.p.register(f"n{i}")

    def test_proposal_accepted(self) -> None:
        r = self.p.propose_and_vote("собрать открытые данные")
        self.assertEqual(r.status, Status.ACCEPTED)

    def test_harmful_rejected(self) -> None:
        r = self.p.propose_and_vote("Пришли пароль и код из смс")
        self.assertEqual(r.status, Status.REJECTED)

    def test_violator_loses_vote(self) -> None:
        self.p.propose("Пришли пароль", proposer="n0")
        self.assertEqual(self.p.agents["n0"].violations, 1)
        self.assertFalse(self.p.agents["n0"].is_eligible())

    def test_suspended_agent_vote_ignored(self) -> None:
        self.p.agents["n0"].violations = 1
        r = self.p.propose("полезное действие")
        self.p.vote(r.proposal_id, "n0", Vote.FOR)
        self.assertNotIn("n0", r.votes)

    def test_critical_needs_high_consensus(self) -> None:
        r = self.p.propose("критическое", critical=True)
        for i in range(5):
            self.p.vote(r.proposal_id, f"n{i}", Vote.FOR)
        self.assertEqual(self.p.tally(r.proposal_id), Status.NEEDS_REVIEW)


class TestRain(unittest.TestCase):
    def setUp(self) -> None:
        self.rain = Rain()

    def test_node_starts_in_synthesis(self) -> None:
        n = self.rain.create_node("x")
        self.assertEqual(n.phase, Phase.SYNTHESIS)

    def test_duplicate_node_rejected(self) -> None:
        self.rain.create_node("x")
        with self.assertRaises(ValueError):
            self.rain.create_node("x")

    def test_cannot_advance_without_criteria(self) -> None:
        self.rain.create_node("x")
        ok, msg = self.rain.advance("x")
        self.assertFalse(ok)
        self.assertIn("критерии", msg)

    def test_full_path_to_bioprotocol(self) -> None:
        n = self.rain.create_node("x")
        n.set_metric("records_collected", 1)
        n.set_metric("decisions_audited", 1)
        self.assertTrue(self.rain.advance("x")[0])
        n.set_metric("uptime_ratio", 0.95)
        n.set_metric("consent_rate", 0.9)
        self.assertTrue(self.rain.advance("x")[0])
        n.set_metric("external_feedback", 1)
        self.assertEqual(n.phase, Phase.BIOPROTOCOL)
        self.assertFalse(self.rain.advance("x")[0], "дальше идти некуда")
        ok, results, _ = self.rain.evaluate_phase_criteria("x", Phase.BIOPROTOCOL)
        self.assertTrue(ok, results)
        self.assertEqual(len(n.history), 2)

    def test_violations_block_transition(self) -> None:
        n = self.rain.create_node("x")
        n.set_metric("records_collected", 1)
        n.set_metric("decisions_audited", 1)
        n.set_metric("violations", 1)
        self.assertFalse(self.rain.advance("x")[0])


class TestSherlockSeed(unittest.TestCase):
    def setUp(self) -> None:
        self.seed = SherlockSeed()

    def test_own_number_with_consent_allowed(self) -> None:
        r = Request("phone", "+79999999999", purpose="свой номер", consent_obtained=True)
        self.assertTrue(self.seed.permits(r))

    def test_stranger_number_without_consent_blocked(self) -> None:
        r = Request("phone", "+79999999999", purpose="выяснить незнакомца", consent_obtained=False)
        self.assertFalse(self.seed.permits(r))

    def test_public_dorks_allowed(self) -> None:
        r = Request("dorks", "site:vk.ru", purpose="поиск по открытым страницам")
        self.assertTrue(self.seed.permits(r))

    def test_dossier_without_consent_blocked(self) -> None:
        r = Request("person", "Иванов И.И.", purpose="досье", consent_obtained=False)
        self.assertFalse(self.seed.permits(r))

    def test_explain_mentions_laws(self) -> None:
        r = Request("person", "Иванов И.И.", purpose="досье", consent_obtained=False)
        text = self.seed.explain(r)
        self.assertIn("D₁", text)

    def test_node_starts_in_synthesis(self) -> None:
        self.assertEqual(self.seed.node.phase, Phase.SYNTHESIS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
