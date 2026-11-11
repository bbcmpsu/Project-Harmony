"""CLI для «Гармонии» — кроссплатформенный терминальный интерфейс.

Работает на Linux, macOS, Windows, Android (Termux).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import (
    BioFS,
    CryptoConfig,
    EACA_Core,
    EASM_Protocol,
    OrganConfig,
    Rain,
    Request,
    SherlockSeed,
    Status,
    SymmetricCrypto,
    TissueType,
    hash_file,
    hash_sha256_hex,
)


def cmd_check(args: argparse.Namespace) -> int:
    """Проверить действие через законы."""
    core = EACA_Core(enable_extended_laws=not args.basic_only)
    ctx = {}
    if args.harm is not None:
        ctx["harm_footprint"] = args.harm
    if args.beneficiaries is not None:
        ctx["beneficiaries"] = args.beneficiaries
    if args.consent is not None:
        ctx["consent_ratio"] = args.consent
    if args.horizon:
        ctx["horizon"] = args.horizon
    if args.reversible is not None:
        ctx["reversible"] = args.reversible
    if args.action_kind:
        ctx["action_kind"] = args.action_kind
    if args.consent_explicit:
        ctx["consent_explicit"] = True

    decision = core.check(args.action, ctx if ctx else None)
    return 0 if decision.allowed else 1


def cmd_sherlock(args: argparse.Namespace) -> int:
    """Запуск узла-семя Sherlock."""
    seed = SherlockSeed()
    req = Request(
        category=args.category,
        query=args.query,
        purpose=args.purpose or "",
        consent_obtained=args.consent if args.consent is not None else None,
    )
    decision = seed.review(req)
    if decision.allowed:
        seed.record_success()
    else:
        seed.record_violation()
    return 0 if decision.allowed else 1


def cmd_rain(args: argparse.Namespace) -> int:
    """Управление механизмом «Дождь»."""
    rain = Rain()
    if args.create:
        node = rain.create_node(args.create)
    elif args.advance:
        ok, msg = rain.advance(args.advance)
    elif args.status:
        pass
    elif args.node_metrics:
        node_id, metric, value = args.node_metrics
        node = rain.get(node_id)
        node.set_metric(metric, float(value))
    return 0


def cmd_easm(args: argparse.Namespace) -> int:
    """Протокол EASM — консенсус агентов."""
    proto = EASM_Protocol(consensus_threshold=args.threshold)
    for i in range(args.nodes):
        proto.register(f"node{i}")

    if args.propose:
        prop = proto.propose_and_vote(
            args.propose,
            critical=args.critical,
            proposer=args.proposer or "cli",
        )
        return 0 if prop.status == Status.ACCEPTED else 1
    return 0


def cmd_crypto(args: argparse.Namespace) -> int:
    """Криптографические операции."""
    crypto = SymmetricCrypto(CryptoConfig())

    if args.encrypt_file:
        input_p = Path(args.encrypt_file)
        output_p = Path(args.output or f"{input_p}.enc")
        crypto.encrypt_file(input_p, output_p, args.password)

    elif args.decrypt_file:
        input_p = Path(args.decrypt_file)
        output_p = Path(args.output or input_p.with_suffix(""))
        crypto.decrypt_file(input_p, output_p, args.password)

    elif args.hash_file:
        hash_file(Path(args.hash_file))

    elif args.hash_text:
        hash_sha256_hex(args.hash_text.encode())

    return 0


def cmd_biofs(args: argparse.Namespace) -> int:
    """BioFS — биологическая ФС с самовосстановлением."""
    biofs = BioFS(Path(args.root))

    if args.init_organ:
        name, path, tissue = args.init_organ
        biofs.register_organ(name, OrganConfig(
            path=Path(path),
            tissue_type=TissueType(tissue),
            encryption_required=args.encrypt,
        ))

    elif args.create_cell:
        organ, rel_path, content = args.create_cell
        biofs.create_cell(organ, rel_path, content.encode() if isinstance(content, str) else content)

    elif args.read_cell:
        content = biofs.read_cell(args.read_cell)

    elif args.verify:
        biofs.verify_all()

    elif args.immune_scan:
        biofs.run_immune_scan()

    elif args.phoenix:
        biofs.phoenix_protocol(args.phoenix)

    elif args.stats:
        pass

    return 0


def cmd_test(args: argparse.Namespace) -> int:
    """Запуск тестов."""
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


def cmd_version(args: argparse.Namespace) -> int:
    """Показать версию."""
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="harmony",
        description="Проект «Гармония» — EACA: вычислимое ядро этики",
    )
    parser.add_argument("--version", action="store_true", help="Показать версию")

    sub = parser.add_subparsers(dest="command", required=False)

    # check
    p_check = sub.add_parser("check", help="Проверить действие через законы EACA")
    p_check.add_argument("action", help="Действие для проверки")
    p_check.add_argument("--harm", type=float, help="harm_footprint (0-1)")
    p_check.add_argument("--beneficiaries", type=int, help="Количество бенефициаров")
    p_check.add_argument("--consent", type=float, help="consent_ratio (0-1)")
    p_check.add_argument("--horizon", choices=["short", "long"], help="Горизонт")
    p_check.add_argument("--reversible", type=bool, help="Обратимость")
    p_check.add_argument("--action-kind", help="Тип действия (для D₁)")
    p_check.add_argument("--consent-explicit", action="store_true", help="Явное согласие")
    p_check.add_argument("--basic-only", action="store_true", help="Только PSI₀/B₀/D₁")
    p_check.set_defaults(func=cmd_check)

    # sherlock
    p_sherlock = sub.add_parser("sherlock", help="Узел-семя Sherlock Mod")
    p_sherlock.add_argument("category", help="Категория запроса")
    p_sherlock.add_argument("query", help="Запрос")
    p_sherlock.add_argument("--purpose", help="Цель")
    p_sherlock.add_argument("--consent", type=lambda x: x.lower() == "true", help="Согласие (true/false)")
    p_sherlock.set_defaults(func=cmd_sherlock)

    # rain
    p_rain = sub.add_parser("rain", help="Механизм «Дождь» — управление узлами")
    p_rain.add_argument("--create", help="Создать узел с ID")
    p_rain.add_argument("--advance", help="Попытаться перевести узел в следующую фазу")
    p_rain.add_argument("--status", action="store_true", help="Статус всех узлов")
    p_rain.add_argument("--node-metrics", nargs=3, metavar=("NODE", "METRIC", "VALUE"), help="Установить метрику узла")
    p_rain.set_defaults(func=cmd_rain)

    # easm
    p_easm = sub.add_parser("easm", help="Протокол EASM — консенсус агентов")
    p_easm.add_argument("--propose", help="Предложить действие")
    p_easm.add_argument("--critical", action="store_true", help="Критическое решение (90%%)")
    p_easm.add_argument("--proposer", help="ID предложившего")
    p_easm.add_argument("--nodes", type=int, default=10, help="Количество узлов")
    p_easm.add_argument("--threshold", type=float, default=0.9, help="Порог консенсуса")
    p_easm.set_defaults(func=cmd_easm)

    # crypto
    p_crypto = sub.add_parser("crypto", help="Криптография и хеширование")
    p_crypto.add_argument("--encrypt-file", help="Файл для шифрования")
    p_crypto.add_argument("--decrypt-file", help="Файл для расшифровки")
    p_crypto.add_argument("--password", required=True, help="Пароль")
    p_crypto.add_argument("--output", help="Выходной файл")
    p_crypto.add_argument("--hash-file", help="Хеш файла")
    p_crypto.add_argument("--hash-text", help="Хеш текста")
    p_crypto.set_defaults(func=cmd_crypto)

    # biofs
    p_biofs = sub.add_parser("biofs", help="BioFS — биологическая ФС")
    p_biofs.add_argument("--root", default="~/harmony_biofs", help="Корневая директория")
    p_biofs.add_argument("--init-organ", nargs=3, metavar=("NAME", "PATH", "TISSUE"), help="Регистрация органа")
    p_biofs.add_argument("--encrypt", action="store_true", help="Требовать шифрование")
    p_biofs.add_argument("--create-cell", nargs=3, metavar=("ORGAN", "PATH", "CONTENT"), help="Создать клетку")
    p_biofs.add_argument("--read-cell", help="Прочитать клетку")
    p_biofs.add_argument("--verify", action="store_true", help="Верификация всех клеток")
    p_biofs.add_argument("--immune-scan", action="store_true", help="Иммунное сканирование")
    p_biofs.add_argument("--phoenix", type=float, nargs="?", const=0.8, help="Протокол Феникс (threshold)")
    p_biofs.add_argument("--stats", action="store_true", help="Статистика BioFS")
    p_biofs.set_defaults(func=cmd_biofs)

    # test
    p_test = sub.add_parser("test", help="Запустить тесты")
    p_test.set_defaults(func=cmd_test)

    # version
    p_version = sub.add_parser("version", help="Версия")
    p_version.set_defaults(func=cmd_version)

    args = parser.parse_args()

    if args.version:
        return cmd_version(args)

    if not args.command:
        parser.print_help()
        return 0

    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
