import pytest


@pytest.fixture(scope="module")
def test_wasm_path():
    """Retrieve the path for the wasm interpreter that should be used for testing"""
    from shutil import which
    from os import environ

    # default to using 'wasm' from the $PATH, if it's available
    wasm_path = which("wasm")
    if wasm_path is not None:
        return wasm_path
    # since 'wasm' isn't available, require the user to provide an explicit path
    wasm_path = environ.get("TEST_WASM_PATH")
    if wasm_path is None:
        raise Exception(
            "You must provide an environment variable called TEST_WASM_PATH with a path to a valid wasm interpreter binary."
        )
    if which(wasm_path) is None:
        raise Exception("Unable to find a valid wasm interpreter at '%s'" % wasm_path)
    return wasm_path
