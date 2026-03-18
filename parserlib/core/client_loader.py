import importlib.util
import inspect
from pathlib import Path

from parserlib.core.base_client import BaseClient
from parserlib.core.registry import ClientRegistry

def _iter_client_files(clients_dir: Path) -> list[Path]:
    if not clients_dir.exists():
        return []
    return sorted(path for path in clients_dir.rglob("client.py") if path.is_file())

def _import_module_from_file(file_path: Path):
    module_name = f"parserlib_dynamic_client_{file_path.parent.name}_{file_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot create module spec for {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _extract_domains(client_class: type[BaseClient]) -> list[str]:
    raw = getattr(client_class, "base_url", [])
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    return []

def load_clients_from_dir(clients_dir: Path) -> dict[str, type[BaseClient]]:
    for file_path in _iter_client_files(clients_dir):
        module = _import_module_from_file(file_path)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls is BaseClient:
                continue
            if not issubclass(cls, BaseClient):
                continue
            domains = _extract_domains(cls)
            if not domains:
                continue
            ClientRegistry.register_client(cls, domains)

    return ClientRegistry.all()

def load_builtin_clients() -> dict[str, type[BaseClient]]:
    clients_dir = Path(__file__).resolve().parents[1] / "clients"
    return load_clients_from_dir(clients_dir)
