#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.
import pytest
from flask import Flask
from indico.core.db import db


@pytest.fixture(name="app")
def app_fixture():
    app = Flask("test")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    with app.app_context():
        db.init_app(app)
        db.session.execute("attach ':memory:' as plugin_saml_groups;")
        db.session.execute(
            "CREATE TABLE plugin_saml_groups.saml_users (id INTEGER PRIMARY KEY, identifier TEXT UNIQUE);"
        )
        db.session.execute(
            "CREATE TABLE plugin_saml_groups.saml_groups (id INTEGER PRIMARY KEY, name TEXT UNIQUE);"
        )
        db.session.execute(
            "CREATE TABLE plugin_saml_groups.saml_group_members (group_id INTEGER, user_id INTEGER);"
        )
        db.session.commit()
    return app
