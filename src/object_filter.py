import re
from typing import Any

# Page object type names used by PDFix SDK template queries (pdf_doc_knowledge_base.h).
PAGE_OBJECT_TYPES: tuple[str, ...] = ("pds_text", "pds_path", "pds_image", "pds_shading", "pds_form")

DEFAULT_OBJECT_TYPES: str = ".*"


def selects_all_page_objects(object_types: Any) -> bool:
    """
    Check whether the object filter provably selects every page object.

    In that case filtering is a no-op and the faster full-page OCR flow gives the same result
    without enumerating page content. Anything that cannot be proven (complex template, invalid
    regex, extra query conditions) returns False so the filtered flow is used.

    Args:
        object_types (Any): Regex string or template dictionary from params.

    Returns:
        True if all page object types are selected.
    """
    if isinstance(object_types, str):
        return _regex_selects_all(object_types)
    if isinstance(object_types, dict):
        return _template_selects_all(object_types)
    return False


def _regex_selects_all(pattern: str) -> bool:
    """
    SDK tests the regex with search (not full match) against the object type name.

    Args:
        pattern (str): ECMAScript regex from params.

    Returns:
        True if the regex matches every page object type name.
    """
    try:
        regex: re.Pattern[str] = re.compile(pattern)
    except re.error:
        return False
    return all(regex.search(name) for name in PAGE_OBJECT_TYPES)


def _template_selects_all(template: dict[str, Any]) -> bool:
    """
    Recognize only the plain template: one `$if` rule whose query lists all types in `param`.

    Args:
        template (dict[str, Any]): Template with `template.object_update` rules.

    Returns:
        True if the template selects every page object type without other conditions.
    """
    inner: Any = template.get("template")
    if not isinstance(inner, dict):
        return False
    rules: Any = inner.get("object_update")
    if not isinstance(rules, list) or len(rules) != 1 or not isinstance(rules[0], dict):
        return False
    rule: dict[str, Any] = rules[0]
    if rule.get("statement") != "$if":
        return False
    query: Any = rule.get("query")
    if not isinstance(query, dict) or set(query.keys()) != {"param"}:
        return False
    params: Any = query["param"]
    if not isinstance(params, list):
        return False
    return set(PAGE_OBJECT_TYPES).issubset(params)
