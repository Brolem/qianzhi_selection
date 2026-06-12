import tempfile
import runpy
import sys
import unittest
from pathlib import Path

import pandas as pd

from src.app import (
    business_columns,
    load_table,
    map_file_for_business,
    render_map_page,
    top_rows,
)
from src.visualization.map_viz import MapProfileSpec


class FakeStreamlit:
    def __init__(self, selected_label):
        self.selected_label = selected_label
        self.headers = []
        self.errors = []
        self.warnings = []

    def header(self, text):
        self.headers.append(text)

    def selectbox(self, label, options, index=0):
        self.selectbox_label = label
        self.selectbox_options = list(options)
        self.selectbox_index = index
        return self.selected_label

    def error(self, text):
        self.errors.append(text)

    def warning(self, text):
        self.warnings.append(text)


class FakeComponents:
    def __init__(self):
        self.calls = []

    def html(self, content, height, scrolling):
        self.calls.append(
            {
                "content": content,
                "height": height,
                "scrolling": scrolling,
            }
        )


def make_map_spec(
    profile_id: str,
    profile_name: str,
    result_path: Path,
    static_html_path: Path | None,
) -> MapProfileSpec:
    return MapProfileSpec(
        profile_id=profile_id,
        profile_name=profile_name,
        template_id="community_retail",
        result_path=result_path,
        static_html_path=static_html_path,
        score_field="profile_score",
        rank_field="profile_rank",
        district_rank_field="district_profile_rank",
        competition_score_field="profile_competition_score",
        advantage_field="profile_main_advantage",
        risk_field="profile_main_risk",
        level_field="profile_recommendation_level",
        synergy_field="convenience_synergy_score",
    )


class AppHelperTests(unittest.TestCase):
    def test_business_columns_returns_exact_fields_for_supported_business_types(self):
        self.assertEqual(business_columns("社区便利店"), ("convenience_score", "rank_convenience"))
        self.assertEqual(business_columns("轻餐饮"), ("light_catering_score", "rank_light_catering"))

    def test_business_columns_rejects_unknown_business_type(self):
        with self.assertRaises(ValueError):
            business_columns("其他")

    def test_top_rows_sorts_by_rank_column_ascending(self):
        frame = pd.DataFrame(
            [
                {"grid_id": "grid_2", "rank_convenience": 2},
                {"grid_id": "grid_1", "rank_convenience": 1},
                {"grid_id": "grid_3", "rank_convenience": 3},
            ]
        )

        result = top_rows(frame, "rank_convenience", 2)

        self.assertEqual(result["grid_id"].tolist(), ["grid_1", "grid_2"])

    def test_map_file_for_business_returns_step9_html_paths(self):
        self.assertEqual(map_file_for_business("社区便利店").name, "convenience_grid_map.html")
        self.assertEqual(map_file_for_business("轻餐饮").name, "light_food_grid_map.html")

    def test_load_table_reads_csv_and_requires_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "table.csv"
            pd.DataFrame([{"region_id": "8316193"}]).to_csv(csv_path, index=False, encoding="utf-8-sig")

            loaded = load_table(csv_path)

            self.assertEqual(loaded["region_id"].astype(str).tolist(), ["8316193"])
            with self.assertRaises(FileNotFoundError):
                load_table(Path(tmp_dir) / "missing.csv")

    def test_render_map_page_uses_dynamic_profile_selector_and_st_folium(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            specs = {
                "默认｜社区便利店": make_map_spec(
                    "convenience",
                    "社区便利店",
                    base / "default.csv",
                    base / "default.html",
                ),
                "自定义｜自定义社区业态 (custom_01)": make_map_spec(
                    "custom_01",
                    "自定义社区业态",
                    base / "custom.csv",
                    None,
                ),
            }
            selected = "自定义｜自定义社区业态 (custom_01)"
            st = FakeStreamlit(selected)
            components = FakeComponents()
            rendered = []
            map_object = object()

            render_map_page(
                st,
                components,
                "社区便利店",
                profile_specs=specs,
                map_builder=lambda spec: map_object,
                st_folium_func=lambda fig, **kwargs: rendered.append((fig, kwargs)),
            )

            self.assertEqual(st.selectbox_label, "评分方案")
            self.assertEqual(st.selectbox_options, list(specs))
            self.assertEqual(rendered[0][0], map_object)
            self.assertEqual(rendered[0][1]["height"], 680)
            self.assertTrue(rendered[0][1]["use_container_width"])
            self.assertEqual(rendered[0][1]["key"], "site_map_custom_01")
            self.assertEqual(components.calls, [])

    def test_render_map_page_falls_back_to_default_static_html(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            html_path = base / "default.html"
            html_path.write_text("<p>default map</p>", encoding="utf-8")
            label = "默认｜社区便利店"
            specs = {
                label: make_map_spec(
                    "convenience",
                    "社区便利店",
                    base / "default.csv",
                    html_path,
                )
            }
            st = FakeStreamlit(label)
            components = FakeComponents()

            render_map_page(
                st,
                components,
                "社区便利店",
                profile_specs=specs,
                st_folium_func=None,
            )

            self.assertEqual(len(components.calls), 1)
            self.assertIn("default map", components.calls[0]["content"])
            self.assertEqual(components.calls[0]["height"], 680)

    def test_render_map_page_does_not_fallback_custom_profile_to_default_html(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            label = "自定义｜自定义社区业态 (custom_01)"
            specs = {
                label: make_map_spec(
                    "custom_01",
                    "自定义社区业态",
                    base / "custom.csv",
                    None,
                )
            }
            st = FakeStreamlit(label)
            components = FakeComponents()

            render_map_page(
                st,
                components,
                "社区便利店",
                profile_specs=specs,
                st_folium_func=None,
            )

            self.assertEqual(components.calls, [])
            self.assertTrue(
                any("streamlit-folium" in message for message in st.errors)
            )

    def test_app_script_imports_when_streamlit_runs_file_path(self):
        project_root = Path(__file__).resolve().parents[1]
        src_dir = project_root / "src"
        original_path = list(sys.path)
        removed_modules = {
            name: sys.modules.pop(name)
            for name in list(sys.modules)
            if name == "src"
            or name.startswith("src.")
            or name == "config"
            or name.startswith("reporting")
        }

        try:
            filtered_path = [
                entry
                for entry in original_path
                if Path(entry or ".").resolve() != project_root
            ]
            sys.path[:] = [str(src_dir), *filtered_path]

            namespace = runpy.run_path(str(src_dir / "app.py"), run_name="streamlit_app")

            self.assertTrue(callable(namespace["main"]))
        finally:
            sys.path[:] = original_path
            sys.modules.update(removed_modules)


if __name__ == "__main__":
    unittest.main()
