# 2019-

## Skill Vetter

A Python tool that analyzes Jupyter notebooks to assess demonstrated Python skills.

### Usage

Vet all notebooks in the current directory:

```bash
python skill_vetter.py
```

Vet all notebooks in a specific directory:

```bash
python skill_vetter.py /path/to/notebooks
```

Vet a single notebook:

```bash
python skill_vetter.py notebook.ipynb
```

### Skills Detected

The skill vetter checks for the following skill categories:

- **Fundamentals** — Variable assignment, print output, type checking, comments, multi-line strings, arithmetic
- **Control Flow** — If/else statements, for loops, nested loops, comparison operators
- **Data Structures** — Lists, list slicing, dictionaries, dict comprehensions
- **Functions** — Function definitions, return statements, built-in functions
- **Modules** — Import statements
- **Data Science** — NumPy, Pandas, Matplotlib, data cleaning

### Running Tests

```bash
python -m pytest test_skill_vetter.py -v
```
