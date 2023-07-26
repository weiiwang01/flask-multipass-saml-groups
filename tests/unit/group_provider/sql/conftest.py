#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.
import pytest
from flask import Flask

from tests.common import setup_sqlite


@pytest.fixture(name="app")
def app_fixture():
    app = Flask("test")
    setup_sqlite(app)
    return app
