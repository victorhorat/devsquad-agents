import os
import subprocess
import sys
import tempfile
from pathlib import Path

from devsquad.models import ExecutionResult

OUTPUT_TRUNCATE_CHARS = 4000
_SENSITIVE_MARKERS = ("API_KEY", "LLM_", "TOKEN", "SECRET")


def _sanitized_env() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in _SENSITIVE_MARKERS)
    }


def _run_pytest_in_dir(tmp_path: Path, timeout_seconds: int) -> ExecutionResult:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(tmp_path), "-q"],
            cwd=tmp_path,
            env=_sanitized_env(),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return ExecutionResult(
            passed=False,
            exit_code=-1,
            stdout=(exc.stdout or "")[:OUTPUT_TRUNCATE_CHARS],
            stderr=(exc.stderr or "")[:OUTPUT_TRUNCATE_CHARS],
            timed_out=True,
        )

    return ExecutionResult(
        passed=result.returncode == 0,
        exit_code=result.returncode,
        stdout=result.stdout[:OUTPUT_TRUNCATE_CHARS],
        stderr=result.stderr[:OUTPUT_TRUNCATE_CHARS],
        timed_out=False,
    )


def run_tests(code: str, tests: str, timeout_seconds: int = 30) -> ExecutionResult:
    """Executa `tests` contra `code` em um diretório temporário isolado.

    Não é um sandbox completo: o subprocesso ainda roda no mesmo SO e tem acesso
    normal à rede/filesystem, só não herda variáveis de ambiente sensíveis
    (API keys, tokens). Para isolamento forte, ver seção "Próximos passos" do README.
    """
    with tempfile.TemporaryDirectory(prefix="devsquad-run-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        (tmp_path / "solution.py").write_text(code, encoding="utf-8")
        (tmp_path / "test_solution.py").write_text(tests, encoding="utf-8")
        return _run_pytest_in_dir(tmp_path, timeout_seconds)


def run_integration_tests(
    modules: dict[str, str],
    integration_test: str,
    timeout_seconds: int = 30,
) -> ExecutionResult:
    """Executa um teste de integração contra vários módulos com nomes reais.

    `modules` mapeia nome de arquivo (ex: "cart.py") para o código daquele
    módulo. Todos são escritos no mesmo diretório temporário isolado, junto
    com `integration_test`, e o pytest roda sobre esse diretório.
    """
    with tempfile.TemporaryDirectory(prefix="devsquad-integration-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        for filename, code in modules.items():
            (tmp_path / Path(filename).name).write_text(code, encoding="utf-8")
        (tmp_path / "test_integration.py").write_text(integration_test, encoding="utf-8")
        return _run_pytest_in_dir(tmp_path, timeout_seconds)
