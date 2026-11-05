from devsquad.runner import run_integration_tests, run_tests

PASSING_CODE = "def add(a: int, b: int) -> int:\n    return a + b\n"
PASSING_TESTS = "from solution import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"

FAILING_CODE = "def add(a: int, b: int) -> int:\n    return a - b\n"
FAILING_TESTS = "from solution import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"

HANGING_CODE = "def slow() -> int:\n    import time\n    time.sleep(10)\n    return 1\n"
HANGING_TESTS = "from solution import slow\n\ndef test_slow():\n    assert slow() == 1\n"


def test_passing_tests_report_success():
    result = run_tests(PASSING_CODE, PASSING_TESTS, timeout_seconds=30)
    assert result.passed is True
    assert result.exit_code == 0
    assert result.timed_out is False


def test_failing_tests_report_failure_with_output():
    result = run_tests(FAILING_CODE, FAILING_TESTS, timeout_seconds=30)
    assert result.passed is False
    assert result.exit_code != 0
    assert "test_add" in result.stdout


def test_hanging_tests_time_out():
    result = run_tests(HANGING_CODE, HANGING_TESTS, timeout_seconds=1)
    assert result.timed_out is True
    assert result.passed is False


def test_sanitized_env_strips_llm_api_key(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "super-secret")
    code = "def noop() -> None:\n    return None\n"
    tests = (
        "import os\n"
        "from solution import noop\n\n"
        "def test_no_api_key_in_env():\n"
        "    assert os.environ.get('LLM_API_KEY') is None\n"
        "    noop()\n"
    )
    result = run_tests(code, tests, timeout_seconds=30)
    assert result.passed is True


def test_run_integration_tests_with_real_cross_module_import():
    modules = {
        "a.py": "def double(x: int) -> int:\n    return x * 2\n",
        "b.py": "def increment(x: int) -> int:\n    return x + 1\n",
    }
    integration_test = (
        "from a import double\nfrom b import increment\n\n\n"
        "def test_compose():\n    assert increment(double(3)) == 7\n"
    )
    result = run_integration_tests(modules, integration_test, timeout_seconds=30)
    assert result.passed is True


def test_run_integration_tests_reports_real_failure():
    modules = {
        "a.py": "def double(x: int) -> int:\n    return x * 2\n",
        "b.py": "def increment(x: int) -> int:\n    return x - 1\n",
    }
    integration_test = (
        "from a import double\nfrom b import increment\n\n\n"
        "def test_compose():\n    assert increment(double(3)) == 7\n"
    )
    result = run_integration_tests(modules, integration_test, timeout_seconds=30)
    assert result.passed is False
    assert "test_compose" in result.stdout
