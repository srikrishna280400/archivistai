# Archivist AI Project Context & Standards

This document establishes development standards, environment preferences, and architecture patterns for the Archivist AI workspace.

## Environment & Dependency Management (Mandatory)

To prevent re-downloading Python packages and speed up development, **always** use the existing pre-configured virtual environments (venv) for all Python execution and dependency management.

### Virtual Environment Locations:
- **WSL / Linux Environment**: `/mnt/d/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv-wsl/`
  - **Python Executable**: `/mnt/d/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv-wsl/bin/python`
  - **Pip Executable**: `/mnt/d/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv-wsl/bin/pip`
- **Windows / PowerShell Environment**: `d:/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv/`
  - **Python Executable**: `d:/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv/Scripts/python.exe`
  - **Pip Executable**: `d:/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv/Scripts/pip.exe`

### Best Practices:
1. Always run files and install packages using the direct paths to the virtual environment executables above rather than invoking a global or unactivated `python` / `pip`.
2. Do not recreate new virtual environments or reinstall dependencies from scratch.
