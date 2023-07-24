#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.
from typing import Dict, Iterable, Iterator, List, Optional

import flask
from flask import Flask
from flask_multipass import Group as MultipassGroup
from flask_multipass import IdentityInfo, IdentityProvider
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped

db = SQLAlchemy()

group_members_table = db.Table(
    "saml_group_members",
    db.metadata,
    db.Column(
        "group_id",
        db.Integer,
        db.ForeignKey("saml_groups.id"),
        primary_key=True,
        nullable=False,
        index=True,
    ),
    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("saml_users.id"),
        primary_key=True,
        nullable=False,
        index=True,
    ),
)


class DBGroup(db.Model):
    __tablename__ = "saml_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True, index=True)
    members = db.relationship(
        "User",
        secondary=group_members_table,
        back_populates="groups",
    )


class User(db.Model):
    __tablename__ = "saml_users"

    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String, nullable=False, index=True, unique=True)
    groups: Mapped[List[DBGroup]] = db.relationship(
        secondary=group_members_table,
        back_populates="members",
    )


class SAMLGroup(MultipassGroup):
    """A group from the saml groups identity provider."""

    supports_member_list = True

    def __init__(self, provider: IdentityProvider, name: str, app: Flask):
        """Provide the group.

        Args:
            provider: The associated identity provider
            name: The name of this group
        """
        super().__init__(provider, name)
        self.provider = provider
        self.name = name
        self._app = app

    def get_members(self) -> Iterator[IdentityInfo]:
        """Return the members of the group.

        This can also be performed by iterating over the group.

        Returns:
            An iterator of IdentityInfo objects.
        """
        with self._app.app_context():
            db_group = DBGroup.query.filter_by(name=self.name).first()
            if db_group:
                return iter(
                    map(
                        lambda m: IdentityInfo(provider=self.provider, identifier=m.identifier),
                        db_group.members,
                    )
                )
            return iter([])

    def has_member(self, identifier: str) -> bool:
        """Check if a given identity is a member of the group.

        This check can also be performed using the ``in`` operator.

        Args:
             identifier: The identifier from an IdentityInfo
                         provided by the associated identity provider.
        """
        with self._app.app_context():
            return (
                DBGroup.query.filter_by(name=self.name)
                .join(DBGroup.members)
                .filter_by(identifier=identifier)
                .first()
                is not None
            )


class SQLGroupProvider:
    """Provide access to Groups using SQLAlchemy"""

    group_class = SAMLGroup

    def __init__(self, identity_provider: IdentityProvider, app=None):
        self._identity_provider = identity_provider
        self._app = app or flask.current_app
        db.create_all()
        db.session.commit()

    def init_app(self, app):
        db.init_app(app)

    def add_group(self, name: str):
        with self._app.app_context():
            grp = DBGroup.query.filter_by(name=name).first()
            if not grp:
                db.session.add(DBGroup(name=name))
                db.session.commit()

    def get_group(self, name: str) -> Optional[SAMLGroup]:
        with self._app.app_context():
            grp = DBGroup.query.filter_by(name=name).first()
            if grp:
                return SAMLGroup(provider=self._identity_provider, name=grp.name, app=self._app)

    def get_groups(self) -> Iterable[SAMLGroup]:
        with self._app.app_context():
            return map(
                lambda g: SAMLGroup(provider=self._identity_provider, name=g.name, app=self._app),
                DBGroup.query.all(),
            )

    def get_user_groups(self, identifier: str) -> Iterable[SAMLGroup]:
        with self._app.app_context():
            u = User.query.filter_by(identifier=identifier).first()
            if u:
                return map(
                    lambda g: SAMLGroup(
                        name=g.name, provider=self._identity_provider, app=self._app
                    ),
                    u.groups,
                )
            return []

    def add_group_member(self, identifier: str, group_name: str):
        with self._app.app_context():
            u = User.query.filter_by(identifier=identifier).first()
            g = DBGroup.query.filter_by(name=group_name).first()

            if not u:
                u = User(identifier=identifier)
                db.session.add(u)
            if not g:
                g = DBGroup(name=group_name)
                db.session.add(g)

            if u not in g.members:
                g.members.append(u)
            db.session.commit()

    def remove_group_member(self, identifier: str, group_name: str):
        with self._app.app_context():
            u = User.query.filter_by(identifier=identifier).first()
            g = DBGroup.query.filter_by(name=group_name).first()

            if g and u in g.members:
                g.members.remove(u)
            db.session.commit()
