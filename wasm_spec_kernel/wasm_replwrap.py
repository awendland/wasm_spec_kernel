"""Wrapper for the Wasm reference interpreter's read-eval-print-loop."""
from pexpect.replwrap import REPLWrapper  # type: ignore


class WasmREPLWrapper(REPLWrapper):
    """Wrapper for a Wasm reference interpreter REPL. Extends
    pexpect.replwrap.REPLWrapper with the following changes:

    * appropriate orig_prompt and continuation_prompt values.
    * modified _expect_prompt to use regex (via pexpect.expect) instead of plain
      string matching (via pexpect.expect_exact), so that the Wasm REPL's prompt
      can be properly identified (since it can occur at the start of buffered
      input, ie. matching "^> ", or in the middle of buffered input after a
      newline, ie. matching "\r\n> ").
    * modified run_command which looks for a final prompt, not a continuation
      prompt, since the Wasm continuation prompt "  " is indistinguishable from
      the indentation the REPL uses normally when returning results, such as
      when listing the exported functions in a module.
    * modified run_command to merge all response lines with newline characters,
      instead of simply concatenating them, since the prompt is defined as having
      newlines in it and therefore will cause them to be stripped out.

    :param cmd_or_spawn: This can either be an instance of :class:`pexpect.spawn`
      in which a REPL has already been started, or a str command to start a new
      REPL process.
    :param str extra_init_cmd: Commands to do extra initialisation, such as
      disabling pagers. These will be run in the REPL via run_command.
    """

    def __init__(
        self,
        cmd_or_spawn,
        extra_init_cmd=None,
    ):
        REPLWrapper.__init__(
            self,
            cmd_or_spawn,
            u"(^|\r\n)> ",
            None,
            continuation_prompt=u"^  ",
            extra_init_cmd=extra_init_cmd,
        )

    def set_prompt(self, orig_prompt, prompt_change):
        raise TypeError("The Wasm REPL's prompt can't be changed")

    def _expect_prompt(self, timeout=-1, async_=False):
        return self.child.expect(
            [self.prompt, self.continuation_prompt], timeout=timeout, async_=async_
        )

    def run_command(self, command, timeout=-1):
        """Send a command to the REPL, wait for and return output.

        :param str command: The command to send. Trailing newlines are not needed.
          This should be a complete block of input that will trigger execution;
          if a continuation prompt is found after sending input, :exc:`ValueError`
          will be raised (TODO: raising this exception is wip).
        :param int timeout: How long to wait for the next prompt. -1 means the
          default from the :class:`pexpect.spawn` object (default 30 seconds).
          None means to wait indefinitely.
        """
        # # Split up multiline commands and feed them in bit-by-bit
        cmdlines = command.splitlines()
        # splitlines ignores trailing newlines - add it back in manually
        if command.endswith("\n"):
            cmdlines.append("")
        if not cmdlines:
            raise ValueError("No command was given")

        res = []
        self.child.sendline(cmdlines[0])
        for line in cmdlines[1:]:
            self._expect_prompt(timeout=timeout)
            if len(self.child.before) > 0:
                res.append(self.child.before)
            self.child.sendline(line)

        # Command was fully submitted, now wait for the next prompt
        # TODO: if the next prompt is a continuation prompt will this hang until
        # the timeout? Should we send a guaranteed newline at the end of every command
        # to ensure that a new prompt is always shown (the Wasm REPL will allow you to
        # end a continuation prompt by sending a blank line of input)?
        # TODO maybe we should test first to see if the response is ONLY continuation
        # prompt, with nothing else printed, and then we'll know if a continuation was
        # expected and can throw and appropriate error.
        self.child.expect(self.prompt, timeout=timeout)

        return u"\n".join(res + [self.child.before])
