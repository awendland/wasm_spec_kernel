# type: ignore
from pathlib import Path
import toml
from importlib.machinery import SourceFileLoader

pyproject = toml.loads(
    Path.resolve(Path(__file__).parent / ".." / "pyproject.toml").read_text()
)
module = SourceFileLoader(
    "wasm_spec_kernel",
    str(
        Path.resolve(Path(__file__).parent / ".." / "wasm_spec_kernel" / "__init__.py")
    ),
).load_module()

assert pyproject["tool"]["poetry"]["version"] == module.__version__
assert pyproject["tool"]["poetry"]["description"] == module.__doc__
