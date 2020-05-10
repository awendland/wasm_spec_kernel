from ipykernel.kernelbase import Kernel
from pexpect import replwrap, EOF
import pexpect

from subprocess import check_output
import os.path

import re
import signal

__version__ = '0.1.0'

version_pat = re.compile(r'wasm (\d+(\.\d+)+)')
error_pat = re.compile(r'stdin:(\d+.\d+-\d+.\d+): (.+?): (.+)') # 1=location, 2=type, 3=details

class WasmKernel(Kernel):
    implementation = 'wasm_kernel'
    implementation_version = __version__

    @property
    def language_version(self):
        m = version_pat.search(self.banner)
        return m.group(1)

    _banner = None

    @property
    def banner(self):
        if self._banner is None:
            self._banner = check_output(['wasm', '-v', '-e', '']).decode('utf-8')
        return self._banner

    language_info = {'name': 'wasm',
                     'codemirror_mode': 'commonlisp',
                     'mimetype': 'text/x-common-lisp',
                     'file_extension': '.wat'}

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self._start_wasm()

    def _start_wasm(self):
        # Signal handlers are inherited by forked processes, and we can't easily
        # reset it from the subprocess. Since kernelapp ignores SIGINT except in
        # message handlers, we need to temporarily reset the SIGINT handler here
        # so that wasm is interruptible.
        # TODO this was the case for the bash_kernel, is this the case for wasm?
        sig = signal.signal(signal.SIGINT, signal.SIG_DFL)
        try:
            child = pexpect.spawn("wasm", ['-w', '10000'], echo=False,
                                  encoding='utf-8', codec_errors='replace')
            # Using IREPLWrapper to get incremental output
            self.wasmwrapper = replwrap.REPLWrapper(child, u'\n> ', None)
        finally:
            signal.signal(signal.SIGINT, sig)

        # NOTE: use the following line to run any prep operation on the Wasm interpreter
        # self.wasmwrapper.run_command(image_setup_cmd)

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        self.silent = silent
        if not code.strip():
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}}

        interrupted = False
        try:
            output = self.wasmwrapper.run_command(code.rstrip(), timeout=None)
        except KeyboardInterrupt:
            self.wasmwrapper.child.sendintr()
            interrupted = True
            self.wasmwrapper._expect_prompt()
            output = self.wasmwrapper.child.before
        except EOF:
            output = self.wasmwrapper.child.before + 'Restarting Wasm'
            self._start_wasm()

        error = error_pat.search(output)
        if error:
            location, errtype, details = error.groups()
            error_content = {
                'ename': errtype,
                'evalue': details,
                'traceback': [output]
            }
            self.send_response(self.iopub_socket, 'error', error_content)

            error_content['execution_count'] = self.execution_count
            error_content['status'] = 'error'
            return error_content
        
        if not self.silent:
            # Send standard output
            stream_content = {'name': 'stdout', 'text': output}
            self.send_response(self.iopub_socket, 'stream', stream_content)
            # TODO review the bash_kernel source to review how images were
            #      specially handled

        if interrupted:
            return {'status': 'abort', 'execution_count': self.execution_count}
        
        return {'status': 'ok', 'execution_count': self.execution_count,
                'payload': [], 'user_expressions': {}}

    # TODO def is_complete_request by using `wasm -d` which just runs validation

    # TODO def do_complete(self, code, cursor_pos):
        # https://github.com/wasmerio/vscode-wasm/blob/master/syntaxes/wat.json
        # https://code.visualstudio.com/api/language-extensions/language-configuration-guide
