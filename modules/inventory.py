"""Carga y validación del inventario local de prendas."""

from __future__ import annotations

import json
from pathlib import Path


REQUIRED_FIELDS = {"id", "nombre", "categoria", "foto_path"}


class InventoryError(ValueError):
    """El inventario no tiene una estructura utilizable por la aplicación."""


def resolve_asset_path(path: str, project_root: Path) -> Path:
    """Resuelve una ruta del inventario sin depender del directorio de arranque."""
    asset_path = Path(path)
    return asset_path if asset_path.is_absolute() else project_root / asset_path


def load_inventory(inventory_path: Path, project_root: Path) -> tuple[list[dict], list[str]]:
    """Carga el JSON, valida su esquema mínimo y avisa de activos ausentes."""
    if not inventory_path.exists():
        raise InventoryError(f"No existe el inventario: {inventory_path}")

    try:
        with inventory_path.open(encoding="utf-8-sig") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryError(f"No se pudo leer el inventario: {exc}") from exc

    if not isinstance(data, list):
        raise InventoryError("El inventario debe ser una lista de prendas.")

    seen_ids: set[str] = set()
    warnings: list[str] = []
    validated: list[dict] = []

    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise InventoryError(f"La entrada {index} no es un objeto JSON.")

        missing = sorted(REQUIRED_FIELDS - item.keys())
        if missing:
            raise InventoryError(
                f"La entrada {index} no contiene: {', '.join(missing)}."
            )

        item_id = str(item["id"]).strip()
        if not item_id:
            raise InventoryError(f"La entrada {index} tiene un id vacío.")
        if item_id in seen_ids:
            raise InventoryError(f"El id {item_id!r} está duplicado.")
        seen_ids.add(item_id)

        photo_path = resolve_asset_path(str(item["foto_path"]), project_root)
        normalized = dict(item)
        normalized["id"] = item_id
        normalized["foto_path_resuelto"] = str(photo_path)
        normalized["disponible"] = photo_path.is_file()
        validated.append(normalized)

        if not photo_path.is_file():
            warnings.append(
                f"{item_id} ({item['nombre']}): no existe {item['foto_path']}."
            )

    return validated, warnings
