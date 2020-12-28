import pexpect
import signal

# from pexpect.replwrap import REPLWrapper
from simple_wasm_kernel.replwrapper import REPLWrapper

cmd = pexpect.spawn(
    "/Users/awendland/Downloads/wasm_abstypes_955f3d3a_macOS-64bit",
    ["-w", "10000"],
    encoding="utf-8",
    echo=False,
)
print(cmd.readline())
cmd.send("(1 + 1)\n")
cmd.expect(u"\r\n> ")
print(cmd.before, cmd.after)
cmd.send("(module $test)\n")
cmd.expect(u"\r\n> ")
print(cmd.before, cmd.after)
cmd.send("(module $incomplete\n")
cmd.expect([u"^> ", u"^  "])
print(cmd.before, cmd.after)
cmd.send(")\n")
cmd.expect(u"\r\n> ")
print(cmd.before, cmd.after)
cmd.kill(signal.SIGKILL)

# There is no such thing as a command sent that still wants a definite continution in the Wasm interpreter. If it puts up a
# continuation prompt and then you send a newline it will simply show the normal prompt. You will need to complete the command
# though, it doesn't reset state at that point.
cmd = pexpect.spawn(
    "/Users/awendland/Downloads/wasm_abstypes_955f3d3a_macOS-64bit",
    ["-w", "10000"],
    encoding="utf-8",
    echo=False,
)
repl = REPLWrapper(cmd, u"(^|\r\n)> ", None, continuation_prompt=u"^  ")
print(repl.run_command(u"(1 + 1)"))
print(repl.run_command(u"(module $test)"))
print(repl.run_command(u"(module $incomplete\n)"))
print(
    repl.run_command(
        """
(module $test01_m1
  (func $getNum (export "getNum") (result i32) (i32.const 4)))
(register "test01_m1" $test01_m1)
(assert_return (invoke $test01_m1 "getNum") (i32.const 3 (;should fail;)))
"""
    )
)
print(
    repl.run_command(
        """
(module $test01_m1
  (func $getNum (export "getNum") (result i32) (i32.const 4)))
(register "test01_m1" $test01_m1)
(module $test01_m2
  (type (;0;) (func (result i32)))
  (import "demo01_m1" "getNum" (func $m1_getNum (type 0)))
  (func $getNum (export "getNum") (result i32) (call $m1_getNum)))
(register "test01_m2" $test01_m2)
(assert_return (invoke $test01_m1 "getNum") (i32.const 3 (;should fail;)))
"""
    )
)
print(
    repl.run_command(
        """
(module $demo01_m1
  (func $isEven (export "isEven") (param i32)
    (result i32) ;; i32 is bool (0=false, 1=true)
    (i32.rem_u (local.get 0) (i32.const 2))
    (i32.const 0)
    (i32.eq))
)
(register "demo01_m1" $demo01_m1)
(module $demo01_m2
  (type (;0;) (func (param i32) (result i32)))
  (import "demo01_m1" "isEven" (func $isEven (type 0)))
  (func $main (export "main") (result i32)
    (i32.const 4)
    (call $isEven)
    (i32.eq (i32.const 1 (;true;))))
)
(register "demo01_m2" $demo01_m2)
(assert_return (invoke $demo01_m2 "main") (i32.const 1 (;true;)))
(assert_return (invoke $demo01_m2 "main") (i32.const 2 (;true;)))
"""
    )
)
