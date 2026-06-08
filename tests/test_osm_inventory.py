import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.osm.inventory import classify_layer_group, write_inventory_outputs


class OsmInventoryTests(unittest.TestCase):
    def test_classify_layer_group_uses_real_layer_names(self):
        self.assertEqual(classify_layer_group("gis_osm_pois_free"), "POI")
        self.assertEqual(classify_layer_group("gis_osm_pois_a_free"), "POI")
        self.assertEqual(classify_layer_group("gis_osm_roads_free"), "road/transport")
        self.assertEqual(classify_layer_group("gis_osm_transport_free"), "road/transport")
        self.assertEqual(classify_layer_group("gis_osm_landuse_a_free"), "landuse")
        self.assertEqual(classify_layer_group("gis_osm_adminareas_a_free"), "boundary/place")
        self.assertEqual(classify_layer_group("gis_osm_places_free"), "boundary/place")
        self.assertEqual(classify_layer_group("gis_osm_buildings_a_free"), "background")

    def test_write_inventory_outputs_creates_required_csv_columns_and_markdown_groups(self):
        records = [
            {
                "layer_name": "gis_osm_pois_free",
                "geometry_type": "Point",
                "row_count": 2,
                "crs": "EPSG:4326",
                "columns": "osm_id,fclass,name,geometry",
                "sample_tags_or_fields": "[{\"fclass\":\"school\"}]",
                "recommended_group": "POI",
            },
            {
                "layer_name": "gis_osm_roads_free",
                "geometry_type": "LineString",
                "row_count": 3,
                "crs": "EPSG:4326",
                "columns": "osm_id,fclass,name,geometry",
                "sample_tags_or_fields": "[{\"fclass\":\"primary\"}]",
                "recommended_group": "road/transport",
            },
            {
                "layer_name": "gis_osm_landuse_a_free",
                "geometry_type": "MultiPolygon",
                "row_count": 4,
                "crs": "EPSG:4326",
                "columns": "osm_id,fclass,name,geometry",
                "sample_tags_or_fields": "[{\"fclass\":\"residential\"}]",
                "recommended_group": "landuse",
            },
            {
                "layer_name": "gis_osm_adminareas_a_free",
                "geometry_type": "MultiPolygon",
                "row_count": 198,
                "crs": "EPSG:4326",
                "columns": "osm_id,name,geometry",
                "sample_tags_or_fields": "[{\"name\":\"贵州省\"}]",
                "recommended_group": "boundary/place",
            },
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            csv_path = base / "inventory.csv"
            md_path = base / "inventory.md"

            write_inventory_outputs(records, csv_path, md_path)

            frame = pd.read_csv(csv_path)
            required = {
                "layer_name",
                "geometry_type",
                "row_count",
                "crs",
                "columns",
                "sample_tags_or_fields",
                "recommended_group",
            }
            self.assertTrue(required.issubset(set(frame.columns)))
            markdown = md_path.read_text(encoding="utf-8")
            self.assertIn("POI", markdown)
            self.assertIn("road/transport", markdown)
            self.assertIn("landuse", markdown)
            self.assertIn("boundary/place", markdown)


if __name__ == "__main__":
    unittest.main()
