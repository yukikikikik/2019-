"""Tests for the skill vetter module."""

import json
import os
import tempfile

from skill_vetter import (
    detect_skills,
    extract_code_cells,
    format_report,
    vet_directory,
    vet_notebook,
)


def _make_notebook(code_cells, path):
    """Helper to create a minimal .ipynb file."""
    notebook = {
        "cells": [
            {"cell_type": "code", "source": [code], "metadata": {}, "outputs": []}
            for code in code_cells
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            }
        },
        "nbformat": 4,
        "nbformat_minor": 2,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(notebook, f)


def test_extract_code_cells_basic():
    with tempfile.NamedTemporaryFile(suffix=".ipynb", mode="w", delete=False) as f:
        path = f.name
        notebook = {
            "cells": [
                {"cell_type": "code", "source": ["x = 1"], "metadata": {}, "outputs": []},
                {"cell_type": "markdown", "source": ["# Title"], "metadata": {}},
                {"cell_type": "code", "source": ["y = 2"], "metadata": {}, "outputs": []},
                {"cell_type": "code", "source": [""], "metadata": {}, "outputs": []},
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 2,
        }
        json.dump(notebook, f)
    try:
        cells = extract_code_cells(path)
        assert len(cells) == 2
        assert cells[0] == "x = 1"
        assert cells[1] == "y = 2"
    finally:
        os.unlink(path)


def test_extract_code_cells_empty_notebook():
    with tempfile.NamedTemporaryFile(suffix=".ipynb", mode="w", delete=False) as f:
        path = f.name
        json.dump({"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 2}, f)
    try:
        cells = extract_code_cells(path)
        assert cells == []
    finally:
        os.unlink(path)


def test_detect_skills_variable_assignment():
    cells = ["x = 42"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Variable Assignment"] is True


def test_detect_skills_print():
    cells = ["print('hello')"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Print Output"] is True


def test_detect_skills_if_else():
    cells = ["if True:\n    pass\nelse:\n    pass"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["If/Else Statements"] is True


def test_detect_skills_for_loops():
    cells = ["for i in range(10):\n    pass"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["For Loops"] is True


def test_detect_skills_nested_loops():
    cells = ["for i in range(3):\n    for j in range(3):\n        pass"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Nested Loops"] is True


def test_detect_skills_list_slicing():
    cells = ["a = [1,2,3]\nb = a[::2]"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["List Slicing"] is True


def test_detect_skills_function_def():
    cells = ["def foo():\n    return 1"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Function Definitions"] is True
    assert skill_map["Return Statements"] is True


def test_detect_skills_comments():
    cells = ["# this is a comment\nx = 1"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Comments"] is True


def test_detect_skills_imports():
    cells = ["import os"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Import Statements"] is True


def test_detect_skills_numpy():
    cells = ["import numpy as np\nnp.array([1,2])"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["NumPy Usage"] is True


def test_detect_skills_pandas():
    cells = ["import pandas as pd\npd.DataFrame()"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Pandas Usage"] is True


def test_detect_skills_data_cleaning():
    cells = ["df.fillna(method='ffill')"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Data Cleaning"] is True


def test_detect_skills_dict_comprehension():
    cells = ["{k: v for k, v in items.items()}"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Dict Comprehensions"] is True


def test_detect_skills_builtin_functions():
    cells = ["list(filter(lambda x: x > 0, nums))"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Built-in Functions"] is True


def test_detect_skills_empty_code():
    cells = []
    results = detect_skills(cells)
    assert all(not s["found"] for s in results)


def test_vet_notebook():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.ipynb")
        _make_notebook(["x = 1\nprint(x)", "for i in range(3):\n    pass"], path)
        result = vet_notebook(path)
        assert result["notebook"] == "test.ipynb"
        assert result["summary"]["skills_demonstrated"] > 0
        assert result["summary"]["skills_checked"] > 0
        skill_map = {s["name"]: s["found"] for s in result["skills"]}
        assert skill_map["Variable Assignment"] is True
        assert skill_map["Print Output"] is True
        assert skill_map["For Loops"] is True


def test_vet_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        _make_notebook(["x = 1"], os.path.join(tmpdir, "a.ipynb"))
        _make_notebook(["import os"], os.path.join(tmpdir, "b.ipynb"))
        # Non-notebook file should be ignored
        with open(os.path.join(tmpdir, "readme.txt"), "w") as f:
            f.write("not a notebook")
        results = vet_directory(tmpdir)
        assert len(results) == 2
        assert results[0]["notebook"] == "a.ipynb"
        assert results[1]["notebook"] == "b.ipynb"


def test_vet_directory_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        results = vet_directory(tmpdir)
        assert results == []


def test_format_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.ipynb")
        _make_notebook(["x = 1\nprint(x)"], path)
        assessments = [vet_notebook(path)]
        report = format_report(assessments)
        assert "SKILL VETTER REPORT" in report
        assert "OVERALL SKILLS SUMMARY" in report
        assert "test.ipynb" in report
        assert "Variable Assignment" in report


def test_format_report_multi_notebooks():
    with tempfile.TemporaryDirectory() as tmpdir:
        path1 = os.path.join(tmpdir, "first.ipynb")
        path2 = os.path.join(tmpdir, "second.ipynb")
        _make_notebook(["x = 1"], path1)
        _make_notebook(["import os"], path2)
        assessments = [vet_notebook(path1), vet_notebook(path2)]
        report = format_report(assessments)
        assert "first.ipynb" in report
        assert "second.ipynb" in report
        assert "Total Skills Demonstrated:" in report


def test_detect_skills_type_checking():
    cells = ["type(42)"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Type Checking"] is True


def test_detect_skills_multiline_strings():
    cells = ["'''\nmultiline\n'''"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Multi-line Strings"] is True


def test_detect_skills_arithmetic():
    cells = ["result = 2 + 3"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Arithmetic Operations"] is True


def test_detect_skills_matplotlib():
    cells = ["import matplotlib.pyplot as plt\nplt.show()"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Matplotlib Usage"] is True


def test_detect_skills_comparison():
    cells = ["if x == 1:\n    pass"]
    results = detect_skills(cells)
    skill_map = {s["name"]: s["found"] for s in results}
    assert skill_map["Comparison Operators"] is True
