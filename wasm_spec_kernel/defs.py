# The max int size for OCaml on 32-bit systems should be 2^31 (since 1 bit is
# reserved by the runtime)
LESS_THAN_OCAML_MAX_INT = str(2 ^ 30)

KERNEL_NAME = "wasm_spec"
KERNEL_IMPLEMENTATION_NAME = KERNEL_NAME + "_kernel"

# Environment Variables
ENV_LOG_FILE = "WASM_KERNEL_LOG_FILE"
ENV_LOG_LEVEL = "WASM_KERNEL_LOG_LEVEL"
ENV_WASM_INTERPRETER = "WASM_INTERPRETER"
