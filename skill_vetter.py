"""Skill Vetter: Analyze Jupyter notebooks to assess demonstrated Python skills."""

import ast
import json
import os
import re
import sys


TRACKED_BUILTINS = {"list", "filter", "map", "range", "len", "sorted", "zip", "enumerate"}

# Skill definitions: each skill has a name, category, and detection function
SKILL_DEFINITIONS = [
    # --- Fundamentals ---
    {
        "name": "Variable Assignment",
        "category": "Fundamentals",
        "detect": lambda code, tree: any(
            isinstance(node, ast.Assign) for node in ast.walk(tree)
        ),
    },
    {
        "name": "Print Output",
        "category": "Fundamentals",
        "detect": lambda code, tree: any(
            isinstance(node, ast.Call)
            and isinstance(getattr(node, "func", None), ast.Name)
            and node.func.id == "print"
            for node in ast.walk(tree)
        ),
    },
    {
        "name": "Type Checking",
        "category": "Fundamentals",
        "detect": lambda code, tree: any(
            isinstance(node, ast.Call)
            and isinstance(getattr(node, "func", None), ast.Name)
            and node.func.id == "type"
            for node in ast.walk(tree)
        ),
    },
    {
        "name": "Comments",
        "category": "Fundamentals",
        "detect": lambda code, tree: bool(re.search(r"#.*\S", code)),
    },
    {
        "name": "Multi-line Strings",
        "category": "Fundamentals",
        "detect": lambda code, tree: bool(
            re.search(r"('''|\"\"\")", code)
        ),
    },
    # --- Control Flow ---
    {
        "name": "If/Else Statements",
        "category": "Control Flow",
        "detect": lambda code, tree: any(
            isinstance(node, ast.If) for node in ast.walk(tree)
        ),
    },
    {
        "name": "For Loops",
        "category": "Control Flow",
        "detect": lambda code, tree: any(
            isinstance(node, ast.For) for node in ast.walk(tree)
        ),
    },
    {
        "name": "Nested Loops",
        "category": "Control Flow",
        "detect": lambda code, tree: any(
            isinstance(node, ast.For)
            and any(
                isinstance(child, ast.For)
                for child in ast.walk(node)
                if child is not node
            )
            for node in ast.walk(tree)
        ),
    },
    {
        "name": "Comparison Operators",
        "category": "Control Flow",
        "detect": lambda code, tree: any(
            isinstance(node, ast.Compare) for node in ast.walk(tree)
        ),
    },
    # --- Data Structures ---
    {
        "name": "Lists",
        "category": "Data Structures",
        "detect": lambda code, tree: any(
            isinstance(node, ast.List) for node in ast.walk(tree)
        ),
    },
    {
        "name": "List Slicing",
        "category": "Data Structures",
        "detect": lambda code, tree: any(
            isinstance(node, ast.Subscript)
            and isinstance(getattr(node, "slice", None), ast.Slice)
            for node in ast.walk(tree)
        ),
    },
    {
        "name": "Dictionaries",
        "category": "Data Structures",
        "detect": lambda code, tree: any(
            isinstance(node, ast.Dict) for node in ast.walk(tree)
        ),
    },
    {
        "name": "Dict Comprehensions",
        "category": "Data Structures",
        "detect": lambda code, tree: any(
            isinstance(node, ast.DictComp) for node in ast.walk(tree)
        ),
    },
    # --- Functions ---
    {
        "name": "Function Definitions",
        "category": "Functions",
        "detect": lambda code, tree: any(
            isinstance(node, ast.FunctionDef) for node in ast.walk(tree)
        ),
    },
    {
        "name": "Return Statements",
        "category": "Functions",
        "detect": lambda code, tree: any(
            isinstance(node, ast.Return) for node in ast.walk(tree)
        ),
    },
    {
        "name": "Built-in Functions",
        "category": "Functions",
        "detect": lambda code, tree: any(
            isinstance(node, ast.Call)
            and isinstance(getattr(node, "func", None), ast.Name)
            and node.func.id in TRACKED_BUILTINS
            for node in ast.walk(tree)
        ),
    },
    # --- Modules & Imports ---
    {
        "name": "Import Statements",
        "category": "Modules",
        "detect": lambda code, tree: any(
            isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree)
        ),
    },
    {
        "name": "NumPy Usage",
        "category": "Data Science",
        "detect": lambda code, tree: bool(re.search(r"\bnp\b|\bnumpy\b", code)),
    },
    {
        "name": "Pandas Usage",
        "category": "Data Science",
        "detect": lambda code, tree: bool(re.search(r"\bpd\b|\bpandas\b", code)),
    },
    {
        "name": "Matplotlib Usage",
        "category": "Data Science",
        "detect": lambda code, tree: bool(re.search(r"\bplt\b|\bmatplotlib\b", code)),
    },
    {
        "name": "Data Cleaning",
        "category": "Data Science",
        "detect": lambda code, tree: bool(re.search(r"\.fillna\(|\.dropna\(|\.isnull\(", code)),
    },
    # --- Arithmetic ---
    {
        "name": "Arithmetic Operations",
        "category": "Fundamentals",
        "detect": lambda code, tree: any(
            isinstance(node, ast.BinOp) for node in ast.walk(tree)
        ),
    },
]


def extract_code_cells(notebook_path):
    """Extract code cell sources from a Jupyter notebook file.

    Args:
        notebook_path: Path to a .ipynb file.

    Returns:
        A list of strings, each being the source code of a code cell.
    """
    with open(notebook_path, "r", encoding="utf-8") as f:
        notebook = json.load(f)

    cells = notebook.get("cells", [])
    code_cells = []
    for cell in cells:
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", []))
            if source.strip():
                code_cells.append(source)
    return code_cells


def detect_skills(code_cells):
    """Detect which skills are demonstrated in a list of code cells.

    Args:
        code_cells: List of code cell source strings.

    Returns:
        A list of dicts with 'name', 'category', and 'found' keys.
    """
    combined_code = "\n".join(code_cells)

    # Try to parse the combined code; fall back to parsing cells individually
    trees = []
    for cell in code_cells:
        try:
            trees.append(ast.parse(cell))
        except SyntaxError:
            pass

    # Build a combined tree from individual cell trees
    combined_body = []
    for tree in trees:
        combined_body.extend(tree.body)
    combined_tree = ast.Module(body=combined_body, type_ignores=[])

    results = []
    for skill in SKILL_DEFINITIONS:
        try:
            found = skill["detect"](combined_code, combined_tree)
        except Exception:
            found = False
        results.append({
            "name": skill["name"],
            "category": skill["category"],
            "found": bool(found),
        })
    return results


def vet_notebook(notebook_path):
    """Vet a single notebook and return its skill assessment.

    Args:
        notebook_path: Path to a .ipynb file.

    Returns:
        Dict with 'notebook', 'skills', and 'summary' keys.
    """
    code_cells = extract_code_cells(notebook_path)
    skills = detect_skills(code_cells)
    found_count = sum(1 for s in skills if s["found"])
    total_count = len(skills)
    return {
        "notebook": os.path.basename(notebook_path),
        "skills": skills,
        "summary": {
            "skills_demonstrated": found_count,
            "skills_checked": total_count,
        },
    }


def vet_directory(directory):
    """Vet all notebooks in a directory.

    Args:
        directory: Path to a directory containing .ipynb files.

    Returns:
        List of assessment dicts from vet_notebook.
    """
    results = []
    for fname in sorted(os.listdir(directory)):
        if fname.endswith(".ipynb"):
            path = os.path.join(directory, fname)
            results.append(vet_notebook(path))
    return results


def format_report(assessments):
    """Format assessment results into a human-readable report.

    Args:
        assessments: List of assessment dicts from vet_notebook.

    Returns:
        A formatted string report.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("SKILL VETTER REPORT")
    lines.append("=" * 60)

    all_skills = {}
    for assessment in assessments:
        lines.append("")
        lines.append(f"Notebook: {assessment['notebook']}")
        lines.append("-" * 40)

        # Group by category
        categories = {}
        for skill in assessment["skills"]:
            cat = skill["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(skill)

        for category, skills in categories.items():
            lines.append(f"  {category}:")
            for skill in skills:
                status = "✓" if skill["found"] else "✗"
                lines.append(f"    [{status}] {skill['name']}")
                # Track overall
                if skill["name"] not in all_skills:
                    all_skills[skill["name"]] = {
                        "category": skill["category"],
                        "found": False,
                    }
                if skill["found"]:
                    all_skills[skill["name"]]["found"] = True

        summary = assessment["summary"]
        lines.append(
            f"  Score: {summary['skills_demonstrated']}/{summary['skills_checked']}"
        )

    # Overall summary
    lines.append("")
    lines.append("=" * 60)
    lines.append("OVERALL SKILLS SUMMARY")
    lines.append("=" * 60)

    categories = {}
    for name, info in all_skills.items():
        cat = info["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({"name": name, "found": info["found"]})

    total_found = 0
    total_count = 0
    for category, skills in categories.items():
        lines.append(f"  {category}:")
        for skill in skills:
            status = "✓" if skill["found"] else "✗"
            lines.append(f"    [{status}] {skill['name']}")
            total_count += 1
            if skill["found"]:
                total_found += 1

    lines.append("")
    lines.append(f"Total Skills Demonstrated: {total_found}/{total_count}")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    """Main entry point for the skill vetter CLI."""
    if len(sys.argv) < 2:
        directory = "."
    else:
        directory = sys.argv[1]

    if os.path.isfile(directory) and directory.endswith(".ipynb"):
        assessments = [vet_notebook(directory)]
    elif os.path.isdir(directory):
        assessments = vet_directory(directory)
    else:
        print(f"Error: '{directory}' is not a valid notebook or directory.")
        sys.exit(1)

    if not assessments:
        print("No Jupyter notebooks found.")
        sys.exit(1)

    report = format_report(assessments)
    print(report)


if __name__ == "__main__":
    main()
