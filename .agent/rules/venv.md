# Universal Virtual Environment (venv) Rule

This rule ensures that for all coding-related sessions, tasks, and Python command executions, Antigravity uses the existing, pre-configured virtual environments (venv) rather than downloading or installing dependencies from scratch.

## Paths to Virtual Environments

### 1. WSL / Linux Environment (Primary for WSL sessions)
- **Path**: `/mnt/d/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv-wsl/`
- **Activation Script**: `/mnt/d/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv-wsl/bin/activate` (or `/mnt/d/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv-wsl/bin/Activate.ps1` if running PowerShell under WSL)
- **Executable**: `/mnt/d/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv-wsl/bin/python`
- **Pip**: `/mnt/d/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv-wsl/bin/pip`

### 2. Windows / PowerShell Environment
- **Path**: `d:/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv/`
- **Activation Script**: `d:/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv/Scripts/Activate.ps1`
- **Executable**: `d:/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv/Scripts/python.exe`

## Instructions & Reinforcement

1. **Prioritize Existing venv**: Before running `pip install` or standard `python` commands, always check if the packages can be run or installed within the `.venv-wsl` or `.venv` virtual environments listed above.
2. **Use Absolute Executable Paths**: Rather than executing `python` or `pip` globally, prepend the full path to the virtual environment binary/executable. For example:
   - Use `/mnt/d/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv-wsl/bin/python <args>`
   - Use `/mnt/d/My Docs/Product Management/P4/Working Code/max sophisticated/backend/.venv-wsl/bin/pip <args>`
3. **Avoid Re-downloading**: Do not install packages globally or create new environments unless specifically requested. Always leverage the pre-installed requirements from these directories.
