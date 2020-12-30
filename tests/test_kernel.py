import pytest
import os
import sys
import json
from tempfile import TemporaryDirectory
import time

from traitlets.config.loader import Config  # type: ignore
from jupyter_client import KernelManager  # type: ignore
from jupyter_core import paths  # type: ignore
from subprocess import PIPE

TIMEOUT = 30
TEST_KERNEL_NAME = "test_wasm"


def execute_ok(kc, cmd):
    """run code on the kernel and check that the response was 'ok'

    Adapted from https://github.com/jupyter/jupyter_client/blob/284914b/jupyter_client/tests/test_kernelmanager.py#L135
    """
    request_id = kc.execute(cmd)
    while True:
        reply = kc.get_shell_msg(TIMEOUT)
        if reply["parent_header"]["msg_id"] == request_id:
            break
    content = reply["content"]
    assert content["status"] == "ok"
    return content


def assemble_output(iopub):
    """assemble stdout/err from an execution

    Adapted from https://github.com/ipython/ipykernel/blob/b682d100/ipykernel/tests/utils.py#L138
    """
    stdout = ""
    stderr = ""
    while True:
        msg = iopub.get_msg(block=True, timeout=1)
        msg_type = msg["msg_type"]
        content = msg["content"]
        if msg_type == "status" and content["execution_state"] == "idle":
            # idle message signals end of output
            break
        elif msg["msg_type"] == "stream":
            if content["name"] == "stdout":
                stdout += content["text"]
            elif content["name"] == "stderr":
                stderr += content["text"]
            else:
                raise KeyError("bad stream: %r" % content["name"])
        else:
            # other output, ignored
            pass
    return stdout, stderr


class TestKernel:
    ############
    # Fixtures #
    ############

    @pytest.fixture
    def temp_jupyter_env(self, monkeypatch):
        """Configure Jupyter to work with a temporary directory which will be destroyed at
        the end of the test cycle.

        Adapted from https://github.com/jupyter/jupyter_client/blob/284914b/jupyter_client/tests/utils.py#L18
        """
        td = TemporaryDirectory()
        monkeypatch.setenv("JUPYTER_CONFIG_DIR", os.path.join(td.name, "jupyter"))
        monkeypatch.setenv("JUPYTER_DATA_DIR", os.path.join(td.name, "jupyter_data"))
        monkeypatch.setenv(
            "JUPYTER_RUNTIME_DIR", os.path.join(td.name, "jupyter_runtime")
        )
        monkeypatch.setenv("IPYTHONDIR", os.path.join(td.name, "ipython"))
        yield
        td.cleanup()

    @pytest.fixture(params=["tcp", "ipc"])
    def os_safe_transport(self, request):
        """Determine which transport types to test, given the test host's platform.

        Adapted from https://github.com/jupyter/jupyter_client/blob/284914b/jupyter_client/tests/test_kernelmanager.py#L40
        """
        if sys.platform == "win32" and request.param == "ipc":  #
            pytest.skip("Transport 'ipc' not supported on Windows.")
        return request.param

    @pytest.fixture
    def kernel_manager(self, os_safe_transport):
        """Prepare a KernelManager for the given transports.

        Adapted from:
        - https://github.com/jupyter/jupyter_client/blob/284914b/jupyter_client/tests/test_kernelmanager.py#L47
        - https://github.com/jupyter/jupyter_client/blob/284914b/jupyter_client/tests/test_kernelmanager.py#L79
        """
        km_config = Config()
        km_config.KernelManager.transport = os_safe_transport
        if os_safe_transport == "ipc":
            km_config.KernelManager.ip = "test"
        return KernelManager(config=km_config)

    @pytest.fixture
    def install_kernel(self, test_wasm_path):
        """Install the test kernel to Jupyter.

        Adapted from https://github.com/jupyter/jupyter_client/blob/284914b/jupyter_client/tests/test_kernelmanager.py#L56
        """
        kernel_dir = os.path.join(paths.jupyter_data_dir(), "kernels", TEST_KERNEL_NAME)
        os.makedirs(kernel_dir, exist_ok=True)
        with open(os.path.join(kernel_dir, "kernel.json"), "w") as f:
            f.write(
                json.dumps(
                    {
                        "argv": [
                            sys.executable,
                            "-m",
                            "wasm_spec_kernel",
                            "-f",
                            "{connection_file}",
                        ],
                        "display_name": "Test Wasm",
                        "env": {"WASM_INTERPRETER": test_wasm_path},
                    }
                )
            )

    @pytest.fixture
    def start_kernel(self):
        """Start a new kernel and return its Manager and Client.

        Adapted from:
        - https://github.com/jupyter/jupyter_client/blob/284914b/jupyter_client/manager.py#780
        - https://github.com/jupyter/jupyter_client/blob/284914b/jupyter_client/tests/test_kernelmanager.py#L47
        """
        km = KernelManager(kernel_name=TEST_KERNEL_NAME)
        km.start_kernel()
        kc = km.client()
        kc.start_channels()
        try:
            kc.wait_for_ready(timeout=60)
        except RuntimeError:
            kc.stop_channels()
            km.shutdown_kernel()
            raise

        yield km, kc
        kc.stop_channels()
        km.shutdown_kernel()
        assert km.context.closed

    #########
    # Tests #
    #########

    def test_lifecycle(self, kernel_manager):
        """
        Test adapted from https://github.com/jupyter/jupyter_client/blob/284914b/jupyter_client/tests/test_kernelmanager.py#L110
        """
        kernel_manager.start_kernel(stdout=PIPE, stderr=PIPE)
        assert kernel_manager.is_alive()
        kernel_manager.restart_kernel(now=True)
        assert kernel_manager.is_alive()
        kernel_manager.interrupt_kernel()
        assert isinstance(kernel_manager, KernelManager)
        kernel_manager.shutdown_kernel(now=True)
        assert kernel_manager.context.closed

    def test_get_connect_info(self, kernel_manager):
        """
        Test adapted from https://github.com/jupyter/jupyter_client/blob/284914b/jupyter_client/tests/test_kernelmanager.py#L120
        """
        cinfo = kernel_manager.get_connection_info()
        keys = sorted(cinfo.keys())
        expected = sorted(
            [
                "ip",
                "transport",
                "hb_port",
                "shell_port",
                "stdin_port",
                "iopub_port",
                "control_port",
                "key",
                "signature_scheme",
            ]
        )
        assert keys == expected

    def test_start_new_kernel(self, install_kernel, start_kernel):
        """
        Test adapted from https://github.com/jupyter/jupyter_client/blob/284914b/jupyter_client/tests/test_kernelmanager.py#L170
        """
        km, kc = start_kernel
        assert km.is_alive()
        assert kc.is_alive()
        assert km.context.closed is False

    def test_execute(self, install_kernel, start_kernel):
        """
        Test adapted from https://github.com/jupyter/jupyter_client/blob/284914b/jupyter_client/tests/test_kernelmanager.py#L170
        """
        km, kc = start_kernel
        execute_ok(kc, "(module $empty)")
        stdout, stderr = assemble_output(kc.iopub_channel)
        assert stdout == "module $empty :"

    def test_execute_trailing(self, install_kernel, start_kernel):
        """
        Test adapted from https://github.com/jupyter/jupyter_client/blob/284914b/jupyter_client/tests/test_kernelmanager.py#L170
        """
        km, kc = start_kernel
        execute_ok(kc, "(module $empty)\n")
        stdout, stderr = assemble_output(kc.iopub_channel)
        assert stdout == "module $empty :"

    def test_stop_kernel_execution(self, install_kernel, start_kernel):
        """
        Test adapted from https://github.com/jupyter/jupyter_client/blob/284914b/jupyter_client/tests/test_kernelmanager.py#L131
        """
        km, kc = start_kernel
        # check that kernel is running
        execute_ok(kc, "(module $valid)")
        # start a job on the kernel to be interrupted
        kc.execute("(module $incomplete")
        # wait for the command to be running before sending an interrupt
        time.sleep(0.1)
        km.interrupt_kernel()
        reply = kc.get_shell_msg(TIMEOUT)
        assert reply["content"]["status"] == "abort"
        # check that subsequent commands work
        execute_ok(kc, "(module $valid)")
