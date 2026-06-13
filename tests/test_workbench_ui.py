import unittest

from src.ui.workbench import (
    BRAND_TITLE,
    WORKBENCH_CSS,
    apply_workbench_theme,
    render_brand_bar,
    render_inline_legend,
    render_metric_cards,
    render_page_header,
    render_workflow_steps,
)


class FakeStreamlit:
    def __init__(self):
        self.html_calls = []

    def html(self, body):
        self.html_calls.append(body)


class WorkbenchUiTests(unittest.TestCase):
    def test_theme_uses_stable_selectors_and_required_tokens(self):
        self.assertIn('[data-testid="stApp"]', WORKBENCH_CSS)
        self.assertIn('[data-testid="stSidebar"]', WORKBENCH_CSS)
        self.assertIn('[data-testid="stSidebarNavLink"]', WORKBENCH_CSS)
        self.assertIn('[data-testid="stDataFrame"]', WORKBENCH_CSS)
        self.assertIn("#132238", WORKBENCH_CSS)
        self.assertIn("#2563EB", WORKBENCH_CSS)
        self.assertIn("#F3F5F8", WORKBENCH_CSS)
        self.assertIn("#FFFFFF", WORKBENCH_CSS)
        self.assertIn("padding-top: 4rem", WORKBENCH_CSS)
        self.assertIn("justify-content: center", WORKBENCH_CSS)
        self.assertIn("min-height: 64px", WORKBENCH_CSS)
        self.assertIn("font-size: 24px", WORKBENCH_CSS)
        self.assertIn("@media (max-width: 900px)", WORKBENCH_CSS)
        self.assertIn("flex: 1 1 100% !important", WORKBENCH_CSS)
        self.assertIn("@media (max-width: 600px)", WORKBENCH_CSS)
        self.assertIn("font-size: 16px", WORKBENCH_CSS)
        self.assertIn(".st-key-report-content", WORKBENCH_CSS)
        self.assertIn(
            '.st-key-report-content [data-testid="stMarkdownContainer"] h1',
            WORKBENCH_CSS,
        )
        self.assertIn("font-size: 24px", WORKBENCH_CSS)

    def test_theme_has_no_external_assets_gradients_or_javascript(self):
        lowered = WORKBENCH_CSS.lower()
        self.assertNotIn("@import", lowered)
        self.assertNotIn("http://", lowered)
        self.assertNotIn("https://", lowered)
        self.assertNotIn("gradient", lowered)
        self.assertNotIn("<script", lowered)

    def test_apply_theme_and_brand_bar_render_static_html(self):
        st = FakeStreamlit()

        apply_workbench_theme(st)
        render_brand_bar(st)

        self.assertEqual(len(st.html_calls), 2)
        self.assertTrue(st.html_calls[0].startswith("<style>"))
        self.assertIn(BRAND_TITLE, st.html_calls[1])
        self.assertIn("workbench-brand-bar", st.html_calls[1])

    def test_page_header_escapes_dynamic_text(self):
        st = FakeStreamlit()

        render_page_header(
            st,
            '<script>alert("x")</script>',
            "说明 <b>不能执行</b>",
        )

        content = st.html_calls[0]
        self.assertNotIn("<script>", content)
        self.assertIn("&lt;script&gt;", content)
        self.assertIn("&lt;b&gt;不能执行&lt;/b&gt;", content)

    def test_metric_cards_render_exact_four_values_and_escape_text(self):
        st = FakeStreamlit()
        metrics = [
            ("目标区县", 3, "贵阳市首版范围"),
            ("空间评价网格", 790, "完整空间底板"),
            ("POI 类别", 15, "统一关键词口径"),
            ("活跃推荐网格", 41, "<需保留审计边界>"),
        ]

        render_metric_cards(st, metrics)

        content = st.html_calls[0]
        self.assertEqual(content.count("workbench-metric-card"), 4)
        for value in ("3", "790", "15", "41"):
            self.assertIn(f">{value}<", content)
        self.assertIn("&lt;需保留审计边界&gt;", content)

    def test_inline_legend_uses_equal_swatch_and_escaped_labels(self):
        st = FakeStreamlit()

        render_inline_legend(
            st,
            [
                ("社区便利店", "#176B4A"),
                ("轻餐饮<script>", "#D98252"),
            ],
        )

        content = st.html_calls[0]
        self.assertEqual(content.count("workbench-legend-item"), 2)
        self.assertEqual(content.count("workbench-legend-swatch"), 2)
        self.assertIn("社区便利店", content)
        self.assertIn("轻餐饮&lt;script&gt;", content)

    def test_workflow_renders_four_steps_and_marks_step_three_active(self):
        st = FakeStreamlit()

        render_workflow_steps(st, active_step=3)

        content = st.html_calls[0]
        self.assertEqual(content.count('class="workbench-flow-step'), 4)
        self.assertEqual(content.count("is-active"), 1)
        self.assertIn("选择应用场景", content)
        self.assertIn("设置分析参数", content)
        self.assertIn("查看推荐结果", content)
        self.assertIn("生成报告", content)
        self.assertIn('data-step="3"', content)


if __name__ == "__main__":
    unittest.main()
