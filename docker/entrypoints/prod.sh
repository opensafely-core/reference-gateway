#!/bin/bash
set -euo pipefail

/opt/venv/bin/python manage.py migrate

exec "$@"
