import json
import tempfile
import unittest
from pathlib import Path

from modules.inventory import InventoryError, load_inventory, resolve_asset_path


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        (self.root / "armario").mkdir()
        (self.root / "armario" / "prenda.png").write_bytes(b"image")
        self.inventory_path = self.root / "armario" / "inventario.json"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write_inventory(self, items):
        self.inventory_path.write_text(
            json.dumps(items, ensure_ascii=False),
            encoding="utf-8",
        )

    def test_loads_and_resolves_valid_inventory(self):
        self.write_inventory([
            {
                "id": "PR001",
                "nombre": "Camiseta",
                "categoria": "Parte Superior",
                "foto_path": "armario/prenda.png",
            }
        ])

        items, warnings = load_inventory(self.inventory_path, self.root)

        self.assertEqual([], warnings)
        self.assertTrue(items[0]["disponible"])
        self.assertEqual(
            self.root / "armario" / "prenda.png",
            Path(items[0]["foto_path_resuelto"]),
        )

    def test_rejects_duplicate_ids(self):
        item = {
            "id": "PR001",
            "nombre": "Camiseta",
            "categoria": "Parte Superior",
            "foto_path": "armario/prenda.png",
        }
        self.write_inventory([item, item])

        with self.assertRaisesRegex(InventoryError, "duplicado"):
            load_inventory(self.inventory_path, self.root)

    def test_reports_missing_asset_without_discarding_item(self):
        self.write_inventory([
            {
                "id": "PR404",
                "nombre": "Prenda ausente",
                "categoria": "Parte Superior",
                "foto_path": "armario/no-existe.png",
            }
        ])

        items, warnings = load_inventory(self.inventory_path, self.root)

        self.assertEqual(1, len(items))
        self.assertFalse(items[0]["disponible"])
        self.assertIn("PR404", warnings[0])

    def test_rejects_missing_required_fields(self):
        self.write_inventory([{"id": "PR001"}])

        with self.assertRaisesRegex(InventoryError, "no contiene"):
            load_inventory(self.inventory_path, self.root)

    def test_resolves_absolute_path_unchanged(self):
        absolute = self.root / "outside.png"
        self.assertEqual(absolute, resolve_asset_path(str(absolute), self.root))

    def test_repository_inventory_is_complete(self):
        project_root = Path(__file__).resolve().parents[1]
        items, warnings = load_inventory(
            project_root / "armario" / "inventario.json",
            project_root,
        )

        self.assertGreater(len(items), 0)
        self.assertEqual([], warnings)


if __name__ == "__main__":
    unittest.main()
