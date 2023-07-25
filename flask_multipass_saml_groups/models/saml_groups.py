#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.
from typing import List

from indico.core.db import db
from sqlalchemy.orm import Mapped

SCHEMA = "plugin_saml_groups"
group_members_table = db.Table(
    "saml_group_members",
    db.metadata,
    db.Column(
        "group_id",
        db.Integer,
        db.ForeignKey(f"{SCHEMA}.saml_groups.id"),
        primary_key=True,
        nullable=False,
        index=True,
    ),
    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey(f"{SCHEMA}.saml_users.id"),
        primary_key=True,
        nullable=False,
        index=True,
    ),
    schema=SCHEMA,
)


class SAMLGroup(db.Model):
    __tablename__ = "saml_groups"
    __table_args__ = {"schema": SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True, index=True)


class SAMLUser(db.Model):
    __tablename__ = "saml_users"
    __table_args__ = {"schema": SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String, nullable=False, unique=True, index=True)
    groups: Mapped[List[SAMLGroup]] = db.relationship(
        SAMLGroup,
        secondary=group_members_table,
        back_populates="members",
    )


SAMLGroup.members = db.relationship(
    SAMLUser,
    secondary=group_members_table,
    back_populates="groups",
)
