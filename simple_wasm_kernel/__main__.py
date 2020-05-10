# import argparse, sys

# parser = argparse.ArgumentParser()
# parser.add_argument("--interpreter")
# (wasm_args, ipython_args) = parser.parse_known_args(sys.argv)


from ipykernel.kernelapp import IPKernelApp
from .kernel import WasmKernel

IPKernelApp.launch_instance(
    kernel_class=WasmKernel
)  # , argv=ipython_args, **vars(wasm_args))
