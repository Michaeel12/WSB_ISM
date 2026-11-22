# ai-generated: 100% - Copilot drafted the SARIF matching implementation; reviewed against CI-SPEC.md P-14-P-22
"""bakeoff.py - scanner SARIF + a labels file -> a per-tool confusion matrix (CI-SPEC.md P-23).

    python3 bakeoff.py --labels labels.json a.sarif b.sarif > bakeoff.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.parse import unquote


CLASSES = {
    "secret": {259, 260, 321, 798},
    "injection": {74, 77, 78, 79, 80, 88, 89, 90, 91, 94, 95, 96, 611, 776, 917, 943, 1336},
    "deserialization": {502},
    "weak-crypto": {261, 326, 327, 328, 330, 331, 338, 759, 760, 916},
    "insecure-transport": {295, 297, 319, 322, 757},
    "path-traversal": {22, 23, 35, 36, 73},
    "ssrf": {918},
    "vulnerable-dependency": {937, 1035, 1104, 1395},
    "misconfiguration": {16, 215, 250, 489, 668, 732, 1188},
    "access-control": {284, 285, 639, 862, 863},
}
CLASS_NAMES = set(CLASSES)


def get_tool_id(name):
    if not isinstance(name, str):
        return "unknown"
    name = name.strip()
    if not name:
        return "unknown"
    lower = name.lower()
    aliases = {
        "trivy": "trivy",
        "grype": "grype",
        "osv-scanner": "osv-scanner",
        "gitleaks": "gitleaks",
        "semgrep": "semgrep",
        "semgrep oss": "semgrep",
        "semgrep ce": "semgrep",
        "semgrep community edition": "semgrep",
        "semgrep pro": "semgrep",
    }
    if lower in aliases:
        return aliases[lower]
    return re.sub(r"[^a-z0-9]+", "-", lower).strip("-") or "unknown"


def is_json_integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def suppressions_empty(value):
    if value is None:
        return True
    if isinstance(value, (list, dict)):
        return len(value) == 0
    if value is False or value == "" or value == 0:
        return True
    return False


def string_array(value):
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def find_matching_rule(run, rule_id):
    tool = run.get("tool")
    if not isinstance(tool, dict):
        return None
    driver = tool.get("driver")
    if not isinstance(driver, dict):
        return None
    rules = driver.get("rules")
    if not isinstance(rules, list):
        return None
    for rule in rules:
        if isinstance(rule, dict) and rule.get("id") == rule_id:
            return rule
    return None


def rule_tags(rule):
    if not isinstance(rule, dict):
        return []
    properties = rule.get("properties")
    if not isinstance(properties, dict):
        return []
    return string_array(properties.get("tags"))


def result_tags(result):
    properties = result.get("properties")
    if not isinstance(properties, dict):
        return []
    return string_array(properties.get("tags"))


def get_result_classes(tool_id, run, result, rule):
    properties = result.get("properties")
    own_class = properties.get("class") if isinstance(properties, dict) else None
    if isinstance(own_class, str) and own_class in CLASS_NAMES:
        return {own_class}

    if tool_id == "gitleaks":
        return {"secret"}
    if tool_id in ("grype", "osv-scanner"):
        return {"vulnerable-dependency"}
    if tool_id == "trivy":
        tags = {tag.lower() for tag in rule_tags(rule)}
        classes = set()
        if "vulnerability" in tags:
            classes.add("vulnerable-dependency")
        if "secret" in tags:
            classes.add("secret")
        if "misconfiguration" in tags:
            classes.add("misconfiguration")
        if classes:
            return classes

    found = set()
    pattern = re.compile(r"(?<![A-Za-z0-9])CWE-(\d+)", re.IGNORECASE)
    for tag in result_tags(result) + rule_tags(rule):
        for value in pattern.findall(tag):
            number = int(value)
            for class_name, cwe_numbers in CLASSES.items():
                if number in cwe_numbers:
                    found.add(class_name)
    return found if found else {"other"}


def normalized_path(uri, set_root):
    path = unquote(uri)
    if path.lower().startswith("file://"):
        path = path[7:]
    if path.startswith("./"):
        path = path[2:]
    components = path.split("/")
    indices = [i for i, component in enumerate(components) if component == set_root]
    if not indices:
        return None
    return "/".join(components[indices[-1]:])


def normalize_package(package):
    return re.sub(r"[-_.]+", "-", package.lower())


def package_tokens(text):
    for token in re.findall(r"[A-Za-z0-9._-]+", text):
        token = token.strip("._-")
        if token:
            yield token


def result_names_package(result, package):
    message = result.get("message")
    if not isinstance(message, dict):
        return False
    text = message.get("text")
    if not isinstance(text, str):
        return False
    expected = normalize_package(package)
    return any(normalize_package(token) == expected for token in package_tokens(text))


def get_location(result):
    locations = result.get("locations")
    if not isinstance(locations, list) or not locations:
        return None, None
    first = locations[0]
    if not isinstance(first, dict):
        return None, None
    physical = first.get("physicalLocation")
    if not isinstance(physical, dict):
        return None, None
    artifact = physical.get("artifactLocation")
    if not isinstance(artifact, dict):
        return None, None
    uri = artifact.get("uri")
    if not isinstance(uri, str) or uri == "":
        return None, None

    region = physical.get("region")
    lines = None
    if isinstance(region, dict):
        start = region.get("startLine")
        if is_json_integer(start) and start >= 1:
            end = region.get("endLine")
            if not is_json_integer(end) or end < start:
                end = start
            lines = (start, end)
    return uri, lines


def result_matches_defect(result, classes, lines, defect):
    if defect["class"] not in classes:
        return False
    if defect["class"] == "vulnerable-dependency":
        return result_names_package(result, defect["package"])
    if lines is None:
        return False
    start, end = lines
    return start <= defect["end_line"] and defect["start_line"] <= end


def confusion_matrix(labels, sarif_documents):
    set_root = labels["set"]
    defects = labels["defects"]
    tools = {}

    for document in sarif_documents:
        if not isinstance(document, dict):
            continue
        runs = document.get("runs")
        if not isinstance(runs, list):
            continue
        for run in runs:
            if not isinstance(run, dict):
                continue
            tool_object = run.get("tool")
            driver = tool_object.get("driver") if isinstance(tool_object, dict) else None
            name = driver.get("name") if isinstance(driver, dict) else None
            tid = get_tool_id(name)
            tool = tools.setdefault(tid, {"results": []})

            results = run.get("results")
            if not isinstance(results, list):
                continue
            for result in results:
                if not isinstance(result, dict):
                    continue
                kind = result.get("kind")
                if kind is not None and kind != "fail":
                    continue
                suppressions = result.get("suppressions")
                if not suppressions_empty(suppressions):
                    continue

                uri, lines = get_location(result)
                if uri is None:
                    continue
                file_name = normalized_path(uri, set_root)
                if file_name is None:
                    continue

                rule_id = result.get("ruleId")
                rule = find_matching_rule(run, rule_id)
                classes = get_result_classes(tid, run, result, rule)
                tool["results"].append({
                    "result": result,
                    "file": file_name,
                    "lines": lines,
                    "classes": classes,
                    "ruleId": rule_id if isinstance(rule_id, str) else None,
                })

    matrix_tools = {}
    for tid, tool in tools.items():
        matched_defect_ids = set()
        false_positives = set()

        for result_entry in tool["results"]:
            matched = False
            for defect in defects:
                if (result_entry["file"] == defect["file"]
                        and result_matches_defect(
                            result_entry["result"],
                            result_entry["classes"],
                            result_entry["lines"],
                            defect,
                        )):
                    matched_defect_ids.add(defect["id"])
                    matched = True
            if not matched:
                lines = result_entry["lines"]
                if lines is None:
                    start = None
                    end = None
                else:
                    start, end = lines
                false_positives.add((
                    result_entry["ruleId"],
                    result_entry["file"],
                    start,
                    end,
                ))

        tp = len(matched_defect_ids)
        fn = len(defects) - tp
        fp = len(false_positives)
        precision = tp / (tp + fp) if tp + fp != 0 else None
        recall = tp / len(defects) if defects else None
        f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) != 0 else None
        matrix_tools[tid] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    return {
        "set": set_root,
        "defects": len(defects),
        "tools": matrix_tools,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="per-tool confusion matrix of SARIF against labels (CI-SPEC.md P-23)")
    parser.add_argument("--labels", required=True, help="the labels file (P-14)")
    parser.add_argument("sarif", nargs="+", help="SARIF 2.1.0 files")
    args = parser.parse_args(argv)
    with open(args.labels, encoding="utf-8") as fh:
        labels = json.load(fh)
    documents = []
    for path in args.sarif:
        with open(path, encoding="utf-8") as fh:
            documents.append(json.load(fh))
    json.dump(confusion_matrix(labels, documents), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
