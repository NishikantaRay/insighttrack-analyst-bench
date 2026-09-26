"""The ported rules, case by case — mirrors InsightTrack's correlationService tests."""
from insighttrack_bench import rules


def f(**kw):
    base = {"keyword": "kw", "citation_change": "unchanged", "domain_is_cited": False,
            "features_added": [], "features_removed": []}
    base.update(kw)
    return base


class TestDetectChange:
    def test_real_drop_clears_both_floors(self):
        d = rules.detect_change([600, 616, 413])
        assert d["significant"] and d["direction"] == "drop"
        assert d["change_pct"] == -33.0

    def test_big_percent_on_tiny_numbers_is_noise(self):
        assert not rules.detect_change([5, 6, 12])["significant"]  # +100% but only 6 views

    def test_many_views_small_percent_is_noise(self):
        assert not rules.detect_change([1000, 1000, 1100])["significant"]  # 100 views but 10%

    def test_exact_floors_count(self):
        assert rules.detect_change([0, 100, 120])["significant"]  # exactly 20% and 20 views
        assert not rules.detect_change([0, 200, 219])["significant"]  # 19 views

    def test_from_zero(self):
        d = rules.detect_change([0, 0, 25])
        assert d["significant"] and d["change_pct"] == 100.0

    def test_js_rounding_of_half(self):
        # JS Math.round rounds .5 up; Python round() would give banker's rounding.
        assert rules._js_round1(-12.25) == -12.2
        assert rules._js_round1(12.25) == 12.3

    def test_exclude_partial_drops_last_week(self):
        assert rules.detect_change([100, 100, 30], exclude_partial=True)["significant"] is False


class TestAttribution:
    def test_rank_slide(self):
        assert rules.attribute_keyword(f(previous_position=3, position=6), "drop") == ["rank_drop"]

    def test_jitter_is_not_a_cause(self):
        assert rules.attribute_keyword(f(previous_position=3, position=5), "drop") == []

    def test_new_ai_answer_quoting_rivals(self):
        c = rules.attribute_keyword(f(previous_position=3, position=3, citation_change="new_overview"), "drop")
        assert c == ["ai_overview_displacement"]

    def test_new_ai_answer_quoting_you_is_not_a_cause(self):
        c = rules.attribute_keyword(
            f(previous_position=3, position=3, citation_change="new_overview", domain_is_cited=True), "drop")
        assert c == []

    def test_lost_citation(self):
        assert rules.attribute_keyword(f(previous_position=3, position=3, citation_change="lost"), "drop") == ["ai_citation_lost"]

    def test_upside_only_counts_on_a_spike(self):
        g = f(previous_position=8, position=2, citation_change="gained", domain_is_cited=True)
        assert sorted(rules.attribute_keyword(g, "spike")) == ["ai_citation_gained", "rank_gain"]
        assert rules.attribute_keyword(g, "drop") == []

    def test_page_one_exit_without_rank_drop(self):
        assert rules.attribute_keyword(f(previous_position=9, position=11), "drop") == ["page_one_exit"]
        assert rules.attribute_keyword(f(previous_position=8, position=None), "drop") == ["page_one_exit"]

    def test_feature_added_only_on_page_one_and_only_for_a_drop(self):
        assert rules.attribute_keyword(f(previous_position=3, position=3, features_added=["videos"]), "drop") == ["serp_feature_added"]
        assert rules.attribute_keyword(f(previous_position=30, position=30, features_added=["videos"]), "drop") == []
        assert rules.attribute_keyword(f(previous_position=3, position=3, features_added=["videos"]), "spike") == []

    def test_feature_removed_only_for_a_spike(self):
        g = f(previous_position=3, position=3, features_removed=["shopping"])
        assert rules.attribute_keyword(g, "spike") == ["serp_feature_removed"]
        assert rules.attribute_keyword(g, "drop") == []


class TestDerivation:
    def test_citation_transitions(self):
        d = "me.com"
        assert rules.citation_change({"ai_answer": False}, {"ai_answer": True, "ai_quotes": ["x.com"]}, d)[0] == "new_overview"
        assert rules.citation_change({"ai_answer": True, "ai_quotes": ["me.com"]}, {"ai_answer": True, "ai_quotes": []}, d)[0] == "lost"
        assert rules.citation_change({"ai_answer": True, "ai_quotes": []}, {"ai_answer": True, "ai_quotes": ["blog.me.com"]}, d) == ("gained", True)
        assert rules.citation_change({"ai_answer": False}, {"ai_answer": False}, d)[0] == "unchanged"

    def test_ai_overview_is_not_a_displacing_feature(self):
        diff = rules.serp_diff({"features": []}, {"features": ["ai_overview", "videos"]})
        assert diff["features_added"] == ["videos"]

    def test_subdomains_match_but_lookalikes_do_not(self):
        assert rules.domain_matches("www.blog.me.com", "me.com")
        assert not rules.domain_matches("notme.com", "me.com")


class TestDiagnose:
    def test_not_significant_has_no_causes(self):
        assert rules.diagnose([5, 6, 12], [f(previous_position=3, position=30)]) == \
            {"significant": False, "direction": None, "causes": []}

    def test_significant_with_no_serp_change_is_unexplained(self):
        g = rules.diagnose([400, 400, 250], [f(previous_position=4, position=5)])
        assert g == {"significant": True, "direction": "drop", "causes": ["unexplained_by_serp"]}

    def test_causes_are_deduplicated_and_sorted(self):
        g = rules.diagnose([400, 400, 250], [f(previous_position=4, position=15), f(previous_position=2, position=12)])
        assert g["causes"] == ["page_one_exit", "rank_drop"]
