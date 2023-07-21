#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.
#
"""SAML Groups Identity Provider."""
import operator
from typing import Dict, Iterable, Iterator, Optional

from flask_multipass import (
    AuthInfo,
    Group,
    IdentityInfo,
    IdentityProvider,
    IdentityRetrievalFailed,
    Multipass,
)

DEFAULT_IDENTIFIER_FIELD = "_saml_nameid_qualified"

SAML_GRP_ATTR_NAME = "urn:oasis:names:tc:SAML:2.0:profiles:attribute:DCE:groups"


class SAMLGroup(Group):
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
        self._members: Dict[str:IdentityProvider] = dict()

    def add_member(self, identity_info: IdentityInfo):
        """Add a member to the group.

        Args:
            identity_info: The identity_info provided by the associated identity provider.
        """
        self._members[identity_info.identifier] = identity_info

    def get_members(self) -> Iterator[IdentityInfo]:
        """Return the members of the group.

        This can also be performed by iterating over the group.

        Returns:
            An iterator of IdentityInfo objects.
        """
        return iter(self._members.values())

    def has_member(self, identifier) -> bool:
        """Check if a given identity is a member of the group.

        This check can also be performed using the ``in`` operator.

        Args:
             identifier: The identifier from an IdentityInfo
                         provided by the associated identity provider.
        """
        return identifier in self._members


class SAMLGroupsIdentityProvider(IdentityProvider):
    """Provides identity information using SAML and supports groups."""

    supports_get = False
    #: If the provider also provides groups and membership information
    supports_groups = True

    group_class = SAMLGroup

    def __init__(self, multipass: Multipass, name: str, settings: Dict):
        """Provide the identity provider.

        Args:
            multipass: The Flask-Multipass instance
            name: The name of this identity provider instance
            settings: The settings dictionary for this identity
                             provider instance
        """
        super().__init__(multipass=multipass, name=name, settings=settings)
        self.id_field = self.settings.setdefault("identifier_field", DEFAULT_IDENTIFIER_FIELD)
        self._groups = dict()

    def get_identity_from_auth(self, auth_info: AuthInfo) -> IdentityInfo:
        """Retrieve identity information after authentication.

        Args:
            auth_info: An AuthInfo instance from an auth provider.

        Returns:
            IdentityInfo: An IdentityInfo instance containing identity information
                          or None if no identity was found.

        """
        identifier = auth_info.data.get(self.id_field)
        if isinstance(identifier, list):
            if len(identifier) != 1:
                raise IdentityRetrievalFailed("Identifier has multiple elements", provider=self)
            identifier = identifier[0]
        if not identifier:
            raise IdentityRetrievalFailed("Identifier missing in saml response", provider=self)

        identity_info = IdentityInfo(self, identifier=identifier, **auth_info.data)

        groups = auth_info.data.get(SAML_GRP_ATTR_NAME)
        if groups:
            for g in groups:
                if g not in self._groups:
                    self._groups[g] = self.group_class(provider=self, name=g)
                self._groups[g].add_member(identity_info)

        return identity_info

    def get_group(self, name: str) -> Optional[SAMLGroup]:
        """
        Return a specific group.

        Args:
            name: The name of the group.

        Returns:
            group: An instance of SAMLGroup.

        """
        return self._groups.get(name)

    def search_groups(self, name: str, exact=False) -> Iterable[SAMLGroup]:
        """
        Search groups by name.

        Args:
            name: The name to search for.
            exact (bool, optional): If True, the name needs to match exactly,
                                    i.e., no substring matches are performed.

        Returns:
            iterable: An iterable of matching group_class objects.

        """
        compare = operator.eq if exact else operator.contains
        for group_name in self._groups:
            if compare(group_name, name):
                yield self.group_class(self, group_name)
