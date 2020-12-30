# Wasm Spec Kernel

A Jupyter kernel for the WebAssembly reference interpreter (see [webassembly/spec](https://github.com/WebAssembly/spec)).

You can try this kernel out in an example notebook using Binder:

[![launch Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/awendland/wasm_spec_kernel/HEAD?filepath=example_notebook.ipynb)

## Installation

### Wasm Reference Interpreter

This kernel requires a [Wasm reference interpreter](https://github.com/WebAssembly/spec/tree/master/interpreter) to be available in the environment (e.g. the Wasm interpreter is not distributed with this Python package).

You can clone a WebAssembly spec repo and build the interpreter yourself using the OCaml toolchain.

@awendland provides a pre-compiled variant of the Wasm reference interpreter with language extensions for abstract types at [awendland/webassembly-spec-abstypes](https://github.com/awendland/webassembly-spec-abstypes).

#### Configuration

Either:

- Place the interpreter in your `$PATH` with the name `wasm`, or
- Specify the interpreter's location when installing the kernel with `python -m wasm_spec_kernel.install --interpreter wherever_you_stored_the/interpreter`

### Jupyter Kernel

To install:

```shell
pip install wasm_spec_kernel
python -m wasm_spec_kernel.install
```

To use it, open up a new Jupyter notebook. For example, via:

```shell
jupyter notebook
# In the notebook interface, select Wasm from the 'New' menu
jupyter qtconsole --kernel wasm_spec
jupyter console --kernel wasm_spec
```

## Purpose

This exists because the WebAssembly reference interpreter is written in OCaml and OCaml is difficult to compile to WebAssembly (otherwise the latest reference interpreter could be hosted via v1 WebAssembly already available in evergreen web browsers). A Jupyter kernel should assist with sharing WebAssembly code samples leveraging features from the various forks of the WebAssembly specification.

## How This Works

For details of how this works, see the Jupyter docs on [wrapper kernels](http://jupyter-client.readthedocs.org/en/latest/wrapperkernels.html), and Pexpect's docs on the [replwrap module](http://pexpect.readthedocs.org/en/latest/api/replwrap.html). Note that this kernel reimplements the `pexpect.replwrap.REPLWrapper` class so that it works better with the Wasm reference interpreter.

## Acknowledgements

This was based on [bash_kernel](https://github.com/takluyver/bash_kernel) by Thomas Kluyver. Tests were adapted from [jupyter/jupyter_client](https://github.com/jupyter/jupyter_client) and [ipython/ipykernel](https://github.com/ipython/ipykernel).
