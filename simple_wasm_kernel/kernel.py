from . import __version__
from .defs import (
    ENV_LOG_FILE,
    ENV_LOG_LEVEL,
    ENV_WASM_INTERPRETER,
    LESS_THAN_OCAML_MAX_INT,
    KERNEL_IMPLEMENTATION_NAME,
    KERNEL_NAME,
)
from ipykernel.kernelbase import Kernel  # type: ignore
import os
import logging
import pexpect  # type: ignore
from .wasm_replwrap import WasmREPLWrapper
import shutil
import re
import signal
from subprocess import check_output
import sys
import traceback
from typing import Dict, Any


version_pat = re.compile(r"wasm (\d+(\.\d+)+)")
error_pat = re.compile(
    r"stdin:(\d+.\d+-\d+.\d+): (.+?): (.+)"
)  # 1=location, 2=type, 3=details

log_level = int(os.environ.get(ENV_LOG_LEVEL, str(logging.WARNING)))
log_params: Dict[str, Any] = {"encoding": "utf-8", "level": log_level}
log_path = os.environ.get(ENV_LOG_FILE)
if log_path is not None:
    log_params["filename"] = log_path
logging.basicConfig(**log_params)
logger = logging.getLogger(__name__)


class WasmKernel(Kernel):
    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        env_interpreter = os.environ.get(ENV_WASM_INTERPRETER, "wasm")
        self._interpreter_path = shutil.which(env_interpreter)
        if self._interpreter_path is None:
            raise Exception(
                "Unable to find a `%s` executable in $PATH: %s"
                % (env_interpreter, os.environ.get("PATH"))
            )
        self._start_wasm()

    implementation = KERNEL_IMPLEMENTATION_NAME
    implementation_version = __version__

    _banner = None
    _interpreter_path = None
    child = None

    @property
    def banner(self):
        if self._banner is None:
            self._banner = check_output(
                [self._interpreter_path, "-v", "-e", ""]
            ).decode("utf-8")
        return self._banner

    @property
    def language_version(self):
        m = version_pat.search(self.banner)
        return m.group(1)

    language_info = {
        "name": KERNEL_NAME,
        "codemirror_mode": "commonlisp",
        "mimetype": "text/x-common-lisp",
        "file_extension": ".wat",
    }

    def _start_wasm(self, kill_existing=False):
        logger.debug(
            "starting new wasm process" + ", 1 wasm process already exists"
            if self.child
            else ""
        )
        if kill_existing and self.child is not None:
            logger.debug("killing existing wasm process")
            try:
                self.child.terminate(force=True)
            except Exception:
                logger.debug(
                    "encountered an error while killing existing wasm process",
                    exc_info=True,
                )
        # Signal handlers are inherited by forked processes, and we can't easily
        # reset it from the subprocess. Since kernelapp ignores SIGINT except in
        # message handlers, we need to temporarily reset the SIGINT handler here
        # so that wasm is interruptible.
        sig = signal.signal(signal.SIGINT, signal.SIG_DFL)
        try:
            logger.info("using wasm interpreter at `%s`" % self._interpreter_path)
            # Use `-w 10000` to increase output width from 80 to something much larger so that
            # text wrapping is handled by the jupyter frontend instead of the wasm interpreter
            self.child = pexpect.spawn(
                self._interpreter_path,
                ["-w", LESS_THAN_OCAML_MAX_INT],
                echo=False,
                encoding="utf-8",
                codec_errors="replace",
            )
            self.wasmwrapper = WasmREPLWrapper(self.child)
        finally:
            signal.signal(signal.SIGINT, sig)

        # NOTE: use the following line to run any prep operation on the Wasm interpreter
        # self.wasmwrapper.run_command(image_setup_cmd)

    def do_execute(
        self, code, silent, store_history=True, user_expressions=None, allow_stdin=False
    ):
        logger.debug("do_execute received: ```%s```", code)
        code = code.rstrip()
        logger.debug("do_execute will run: ```%s```", code)

        self.silent = silent
        if not code:
            return {
                "status": "ok",
                "execution_count": self.execution_count,
                "payload": [],
                "user_expressions": {},
            }

        try:
            output = self.wasmwrapper.run_command(code, timeout=None)
            logger.debug("response from run_command: ```%s```" % output)

        except pexpect.EOF:
            logger.debug("pexpect.EOF raised during run_command")
            output = self.wasmwrapper.child.before + "Restarting Wasm"
            self._start_wasm()

        except KeyboardInterrupt:
            logger.debug("KeyboardInterrupt raised during run_command")
            # TODO if the wasm interpreter ever support SIGINT or some other interrupt mechanism,
            # use that instead so that the entire interpreter's state doesn't have to be thrown
            # out when a single execution is aborted.
            self.send_response(
                self.iopub_socket,
                "error",
                {
                    "ename": "interrupt",
                    "evalue": "",
                    "traceback": ["Restarting Wasm because execution was aborted"],
                },
            )
            self._start_wasm(kill_existing=True)
            return {"status": "abort", "execution_count": self.execution_count}

        except Exception:
            logger.exception("unknown error raised during run_command", exc_info=True)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_content = {
                "ename": "unknown",
                "evalue": "",
                "traceback": [
                    "Restarting Wasm due to unknown error: " + repr(exc_value) + "\n\n"
                ]
                + traceback.format_tb(exc_traceback),
            }
            self.send_response(self.iopub_socket, "error", error_content)

            self._start_wasm(kill_existing=True)

            error_content["execution_count"] = self.execution_count
            error_content["status"] = "error"
            return error_content

        wasm_error = error_pat.search(output)
        if wasm_error:
            location, errtype, details = wasm_error.groups()
            error_content = {"ename": errtype, "evalue": details, "traceback": [output]}
            self.send_response(self.iopub_socket, "error", error_content)

            error_content["execution_count"] = self.execution_count
            error_content["status"] = "error"
            return error_content

        else:
            if not self.silent:
                self.send_response(
                    self.iopub_socket, "stream", {"name": "stdout", "text": output}
                )
            return {
                "status": "ok",
                "execution_count": self.execution_count,
                "payload": [],
                "user_expressions": {},
            }

    # TODO def is_complete_request by using `wasm -d` which just runs validation

    # TODO def do_complete(self, code, cursor_pos):
    # https://github.com/wasmerio/vscode-wasm/blob/master/syntaxes/wat.json
    # https://code.visualstudio.com/api/language-extensions/language-configuration-guide
