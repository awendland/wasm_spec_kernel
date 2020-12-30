from ipykernel.kernelapp import IPKernelApp  # type: ignore
from .kernel import WasmKernel

IPKernelApp.launch_instance(kernel_class=WasmKernel)
