A Jupyter kernel for the WebAssembly reference interpreter (see [webassembly/spec](https://github.com/WebAssembly/spec)).

This requires IPython 3.

To install:

```shell
pip install wasm_kernel
python -m wasm_kernel.install
```

To use it, run one of:

```shell
jupyter notebook
# In the notebook interface, select Wasm from the 'New' menu
jupyter qtconsole --kernel wasm
jupyter console --kernel wasm
```

For details of how this works, see the Jupyter docs on [wrapper kernels](http://jupyter-client.readthedocs.org/en/latest/wrapperkernels.html), and Pexpect's docs on the [replwrap module](http://pexpect.readthedocs.org/en/latest/api/replwrap.html).

This was based on [bash_kernel](https://github.com/takluyver/bash_kernel) by Thomas Kluyver.
