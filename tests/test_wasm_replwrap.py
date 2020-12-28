import pytest
import pexpect  # type: ignore
import os
from simple_wasm_kernel.wasm_replwrap import WasmREPLWrapper
from simple_wasm_kernel.defs import LESS_THAN_OCAML_MAX_INT


@pytest.fixture
def new_repl():
    wasm_path = os.environ.get("TEST_WASM_PATH")
    if wasm_path is None:
        raise Exception(
            "You must provide an environment variable called TEST_WASM_PATH with a path to a valid wasm interpreter binary."
        )
    return WasmREPLWrapper(
        pexpect.spawn(
            wasm_path, ["-w", LESS_THAN_OCAML_MAX_INT], encoding="utf-8", echo=False
        )
    )


@pytest.mark.parametrize(
    "wasm_code, stdout",
    [
        ("(module $empty)", "module $empty :"),
        ("(module $newline\n)", "module $newline :"),
        ("(module $incomplete_newline\n", ""),
        (
            """(module $Export1 (func $getNum (export "getNum") (result i32) (i32.const 4)))""",
            """module $Export1 :\r\n  export func "getNum" : [] -> [i32]""",
        ),
        (
            """(module $Export1TrailingLF (func $getNum (export "getNum") (result i32) (i32.const 4)))\n""",
            """module $Export1TrailingLF :\r\n  export func "getNum" : [] -> [i32]\n""",
        ),
        (
            """(module $Export1TrailingLFLF (func $getNum (export "getNum") (result i32) (i32.const 4)))\n\n""",
            """module $Export1TrailingLFLF :\r\n  export func "getNum" : [] -> [i32]\n""",
        ),
        (
            """(module $Export1TrailingCRLF (func $getNum (export "getNum") (result i32) (i32.const 4)))\r\n""",
            """module $Export1TrailingCRLF :\r\n  export func "getNum" : [] -> [i32]\n""",
        ),
        (
            """\
(module $MLExport1
  (func $getNum (export "getNum") (result i32) (i32.const 4))
)""",
            """module $MLExport1 :\r\n  export func "getNum" : [] -> [i32]""",
        ),
        (
            """\
(module $MLExport1TrailingLF
  (func $getNum (export "getNum") (result i32) (i32.const 4))
)
""",
            """module $MLExport1TrailingLF :\r\n  export func "getNum" : [] -> [i32]\n""",
        ),
        (
            """\
(module $MLExport1TrailingLFLF
  (func $getNum (export "getNum") (result i32) (i32.const 4))

)

""",
            """module $MLExport1TrailingLFLF :\r\n  export func "getNum" : [] -> [i32]\n""",
        ),
        (
            """
(module $MLExport1LeadingLF
  (func $getNum (export "getNum") (result i32) (i32.const 4))
)""",
            """module $MLExport1LeadingLF :\r\n  export func "getNum" : [] -> [i32]""",
        ),
        (
            """\
(module $MLExport1Commented
  (func $getNum (export "getNum") (result i32) (i32.const 4)) ;; a newline terminated comment
)""",
            """module $MLExport1Commented :\r\n  export func "getNum" : [] -> [i32]""",
        ),
        (
            """\
(module $MLExport1_register
  (func $getNum (export "getNum") (result i32) (i32.const 4))
)
(register "$MLExport1" $MLExport1_register)""",
            """module $MLExport1_register :\r\n  export func "getNum" : [] -> [i32]\n""",
        ),
        (
            """\
(module $MLExport1_registerTrailingLF
  (func $getNum (export "getNum") (result i32) (i32.const 4))
)
(register "$MLExport1" $MLExport1_registerTrailingLF)
""",
            """module $MLExport1_registerTrailingLF :\r\n  export func "getNum" : [] -> [i32]\n""",
        ),
        (
            """\
(module $Export1_assert (func $getNum (export "getNum") (result i32) (i32.const 4)))
(assert_return (invoke $Export1_assert "getNum") (i32.const 4))
""",
            """module $Export1_assert :\r\n  export func "getNum" : [] -> [i32]\n""",
        ),
        (
            """\
(module $MLExport1Commented_assert
  (func $getNum (export "getNum") (result i32) (i32.const 4)) ;; a comment
)
(assert_return (invoke $MLExport1Commented_assert "getNum") (i32.const 4))
""",
            """module $MLExport1Commented_assert :\r\n  export func "getNum" : [] -> [i32]\n""",
        ),
        (
            """\
(module $Export1_assertF (func $getNum (export "getNum") (result i32) (i32.const 4)))
(assert_return (invoke $Export1_assertF "getNum") (i32.const 3))
""",
            """\
module $Export1_assertF :\r
  export func "getNum" : [] -> [i32]
Result: 4 : i32\r
Expect: 3 : i32\r
stdin:2.1-2.65: assertion failure: wrong return values
""",
        ),
        ("1 + 1", "stdin:1.1-1.2: syntax error: unexpected token"),
        ("\n", ""),
    ],
)
def test_run_command(new_repl, wasm_code, stdout):
    """These parametrized tests are primarily focused on documenting how whitespace is
    being handled.
    """
    assert new_repl.run_command(wasm_code) == stdout
