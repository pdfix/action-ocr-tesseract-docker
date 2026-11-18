import unittest
from typing import Any

from object_filter import PAGE_OBJECT_TYPES, selects_all_page_objects


def make_template(params: list[str], statement: str = "$if", extra_query: dict[str, Any] | None = None) -> dict:
    query: dict[str, Any] = {"param": params}
    if extra_query:
        query.update(extra_query)
    return {"template": {"object_update": [{"query": query, "statement": statement}]}}


class TestSelectsAllPageObjectsRegex(unittest.TestCase):
    def test_match_all_regexes(self) -> None:
        for pattern in [".*", "", "pds_", "^pds_.*$", "pds_(text|path|image|shading|form)"]:
            with self.subTest(pattern=pattern):
                self.assertTrue(selects_all_page_objects(pattern))

    def test_partial_regexes(self) -> None:
        for pattern in ["pds_image", "^pds_image$", "pds_(text|image)", "pds_(text|path|image|shading)"]:
            with self.subTest(pattern=pattern):
                self.assertFalse(selects_all_page_objects(pattern))

    def test_invalid_regex(self) -> None:
        self.assertFalse(selects_all_page_objects("pds_(image"))


class TestSelectsAllPageObjectsTemplate(unittest.TestCase):
    def test_all_types(self) -> None:
        self.assertTrue(selects_all_page_objects(make_template(list(PAGE_OBJECT_TYPES))))

    def test_all_types_any_order(self) -> None:
        self.assertTrue(selects_all_page_objects(make_template(list(reversed(PAGE_OBJECT_TYPES)))))

    def test_missing_type(self) -> None:
        self.assertFalse(selects_all_page_objects(make_template(["pds_text", "pds_path", "pds_image", "pds_shading"])))

    def test_single_type(self) -> None:
        self.assertFalse(selects_all_page_objects(make_template(["pds_image"])))

    def test_extra_condition(self) -> None:
        template = make_template(list(PAGE_OBJECT_TYPES), extra_query={"$and": [{"$page_num": "1"}]})
        self.assertFalse(selects_all_page_objects(template))

    def test_other_statement(self) -> None:
        self.assertFalse(selects_all_page_objects(make_template(list(PAGE_OBJECT_TYPES), statement="$if_not")))

    def test_multiple_rules(self) -> None:
        rule = make_template(list(PAGE_OBJECT_TYPES))["template"]["object_update"][0]
        self.assertFalse(selects_all_page_objects({"template": {"object_update": [rule, rule]}}))

    def test_malformed(self) -> None:
        for value in [{}, {"template": []}, {"template": {"object_update": {}}}, None, 1, []]:
            with self.subTest(value=value):
                self.assertFalse(selects_all_page_objects(value))


if __name__ == "__main__":
    unittest.main()
