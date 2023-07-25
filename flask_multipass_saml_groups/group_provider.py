#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.

from typing import Iterable, Iterator, Optional

from flask_multipass import Group as MultipassGroup
from flask_multipass import IdentityInfo, IdentityProvider
from indico.core.db import db

from flask_multipass_saml_groups.models.saml_groups import SAMLGroup as DBGroup
from flask_multipass_saml_groups.models.saml_groups import SAMLUser


class SAMLGroup(MultipassGroup):
    """A group from the saml groups identity provider."""

    supports_member_list = True

    def __init__(self, provider: IdentityProvider, name: str):
        """Provide the group.

        Args:
            provider: The associated identity provider
            name: The name of this group
        """
        super().__init__(provider, name)
        self.provider = provider
        self.name = name

    def get_members(self) -> Iterator[IdentityInfo]:
        """Return the members of the group.

        This can also be performed by iterating over the group.

        Returns:
            An iterator of IdentityInfo objects.
        """
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

    def add_group(self, name: str):
        grp = DBGroup.query.filter_by(name=name).first()
        if not grp:
            db.session.add(DBGroup(name=name))
            db.session.commit()

    def get_group(self, name: str) -> Optional[SAMLGroup]:
        grp = DBGroup.query.filter_by(name=name).first()
        if grp:
            return SAMLGroup(provider=self._identity_provider, name=grp.name)

    def get_groups(self) -> Iterable[SAMLGroup]:
        return map(
            lambda g: SAMLGroup(provider=self._identity_provider, name=g.name),
            DBGroup.query.all(),
        )

    def get_user_groups(self, identifier: str) -> Iterable[SAMLGroup]:
        u = SAMLUser.query.filter_by(identifier=identifier).first()
        if u:
            return map(
                lambda g: SAMLGroup(name=g.name, provider=self._identity_provider),
                u.groups,
            )
        return []

    def add_group_member(self, identifier: str, group_name: str):
        u = SAMLUser.query.filter_by(identifier=identifier).first()
        g = DBGroup.query.filter_by(name=group_name).first()

        if not u:
            u = SAMLUser(identifier=identifier)
            db.session.add(u)
        if not g:
            g = DBGroup(name=group_name)
            db.session.add(g)

        if u not in g.members:
            g.members.append(u)
        db.session.commit()

    def remove_group_member(self, identifier: str, group_name: str):
        u = SAMLUser.query.filter_by(identifier=identifier).first()
        g = DBGroup.query.filter_by(name=group_name).first()

        if g and u in g.members:
            g.members.remove(u)
        db.session.commit()
