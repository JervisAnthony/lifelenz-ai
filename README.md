# LifeLenz-AI

LifeLenz-AI is an AI-powered personal wellness intelligence platform intended to help people bring together wellness data, understand personal patterns, and receive explainable insights over time.

## Project status

The project is in its initial foundation stage. The repository currently provides an installable Python package and development tooling; wellness-domain capabilities have not yet been implemented.

## Development setup

LifeLenz-AI requires Python 3.13 or later. From PowerShell on Windows, create and activate a virtual environment, then install the package and development tools:

```powershell
py -3.13 -m venv lifelenz-env
.\lifelenz-env\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the test suite:

```powershell
python -m pytest
```

Run lint checks and verify formatting:

```powershell
python -m ruff check .
python -m ruff format --check .
```

LifeLenz provides wellness intelligence and is not a medical diagnostic system. Its output should not replace advice from qualified healthcare professionals.

## License

This project is licensed under the [MIT License](LICENSE).

