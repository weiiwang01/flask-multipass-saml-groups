#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.
#
"""SAML Groups Identity Provider."""
import operator
from typing import Dict, Iterable, Optional

from flask_multipass import (
    AuthInfo,
    Group,
    IdentityInfo,
    IdentityProvider,
    IdentityRetrievalFailed,
    Multipass,
)

from flask_multipass_saml_groups.group_provider.base import GroupProvider
from flask_multipass_saml_groups.group_provider.sql import SQLGroupProvider

DEFAULT_IDENTIFIER_FIELD = "_saml_nameid_qualified"

SAML_GRP_ATTR_NAME = "urn:oasis:names:tc:SAML:2.0:profiles:attribute:DCE:groups"


class SAMLGroupsIdentityProvider(IdentityProvider):
    """Provides identity information using SAML and supports groups."""

    #: If the provider supports getting identity information based from
    #: an identifier
    supports_get = False
    #: If the provider also provides groups and membership information
    supports_groups = True
    #: If the provider supports getting the list of groups an identity belongs to
    supports_get_identity_groups = True

    group_class = Group

    def __init__(
        self,
        multipass: Multipass,
        name: str,
        settings: Dict,
        group_provider_class=SQLGroupProvider,
    ):
        """Provide the identity provider.

        Args:
            multipass: The Flask-Multipass instance
            name: The name of this identity provider instance
            settings: The settings dictionary for this identity
                             provider instance
        """
        super().__init__(multipass=multipass, name=name, settings=settings)
        self.id_field = self.settings.setdefault("identifier_field", DEFAULT_IDENTIFIER_FIELD)
        self._group_provider: GroupProvider = group_provider_class(identity_provider=self)
        self.group_class = self._group_provider.group_class

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

        grp_names = auth_info.data.get(SAML_GRP_ATTR_NAME)

        if grp_names:
            if isinstance(grp_names, str):
                # If only one group is returned, it is returned as a string by saml auth provider
                grp_names = [grp_names]

            user_groups = self._group_provider.get_user_groups(identifier=identifier)
            for group in user_groups:
                if group.name not in grp_names:
                    self._group_provider.remove_group_member(
                        group_name=group.name, identifier=identifier
                    )

            for grp_name in grp_names:
                self._group_provider.add_group_member(group_name=grp_name, identifier=identifier)

        return identity_info

    def get_group(self, name: str) -> Optional[Group]:
        """
        Return a specific group.

        Args:
            name: The name of the group.

        Returns:
            group: An instance of group_class or None if the group does not exist.

        """
        return self._group_provider.get_group(name)

    def search_groups(self, name: str, exact=False) -> Iterable[Group]:
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
        for group in self._group_provider.get_groups():
            if compare(group.name, name):
                yield group

    def get_identity_groups(self, identifier: str) -> Iterable[Group]:
        """Retrieve the groups a user identity belongs to

        Args:
            identifier: The unique user identifier used by the
                           provider.
        Returns:
             iterable: An iterable of groups
        """
        return self._group_provider.get_user_groups(identifier=identifier)
