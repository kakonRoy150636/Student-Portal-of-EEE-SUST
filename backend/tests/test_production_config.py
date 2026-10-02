import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("key,origins", [
    ("dev_secret_key_change_in_production_sust_eee_256bit", '["https://portal.example.com"]'),
    ("a" * 64, '["http://localhost.attacker.example"]'),
    ("a" * 64, '["*"]'),
])
def test_production_rejects_unsafe_config(key, origins):
    env = {**os.environ, "ENVIRONMENT": "production", "SECRET_KEY": key, "CORS_ORIGINS": origins}
    result = subprocess.run([sys.executable, "-c", "import app.core.config"], env=env, capture_output=True)
    assert result.returncode != 0
    assert b"RuntimeError" in result.stderr


def test_production_accepts_https_origin():
    env = {**os.environ, "ENVIRONMENT": "production", "SECRET_KEY": "a" * 64, "CORS_ORIGINS": '["https://portal.example.com"]'}
    result = subprocess.run([sys.executable, "-c", "import app.core.config"], env=env, capture_output=True)
    assert result.returncode == 0, result.stderr.decode()
