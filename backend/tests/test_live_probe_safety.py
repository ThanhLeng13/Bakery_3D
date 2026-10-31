"""Live acceptance probes must not modify real customer orders."""
import ast
from pathlib import Path


def test_migration_checks_have_no_database_mutations():
    path = Path(__file__).with_name("test_migrations_applied.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = {"insert", "update", "delete", "upsert", "rpc"}
    calls = [node.func.attr for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
    assert not forbidden.intersection(calls)


def test_live_checks_require_opt_in_before_credential_loading():
    path = Path(__file__).with_name("test_migrations_applied.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mark = next(node for node in ast.walk(tree)
                if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets))
    condition = mark.value.args[0]
    assert isinstance(condition, ast.BoolOp) and isinstance(condition.op, ast.Or)
    assert "BAKERY_RUN_LIVE_READONLY_TESTS" in ast.unparse(condition.values[0])
    assert ast.unparse(condition.values[1]) == "not _has_credentials()"
