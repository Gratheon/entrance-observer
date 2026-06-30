start:
    COMPOSE_PROJECT_NAME=gratheon docker compose up --build

install-native:
    #!/usr/bin/env bash
    set -euo pipefail

    current_python_version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    venv_python_version=""
    if [ -x .venv/bin/python ]; then
        venv_python_version="$(.venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
    fi

    if [ ! -x .venv/bin/python ] || [ "$venv_python_version" != "$current_python_version" ]; then
        rm -rf .venv
        python3 -m venv .venv
    fi

    .venv/bin/python -m pip install --upgrade pip

    if [ "$(uname -s)" = "Darwin" ]; then
        .venv/bin/python -m pip install -r requirements.macos.txt
    else
        .venv/bin/python -m pip install -r requirements.jetson.txt
    fi

start-native: install-native
    PYTHONPATH=. .venv/bin/python src/main.py

test:
    pytest tests

test-integration:
    pytest tests_integration
