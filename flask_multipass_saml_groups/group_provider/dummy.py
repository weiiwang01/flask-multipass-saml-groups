#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.

from typing import Iterable, Iterator, Optional

from flask_multipass import Group, IdentityInfo, IdentityProvider

from flask_multipass_saml_groups.group_provider.base import GroupProvider

# Do not use in production. This module is for testing only.


class DummyGroup(Group):
    """A group from the saml groups identity provider."""

    supports_member_list = True

    def __init__(self, provider: IdentityProvider, name: str):
        """Provide the group.

        Args:
            provider: The associated identity provider
            name: The name of this group
        """
        super().__init__(provider, name)
        self._provider = provider
        self._name = name
        self._members = set()

    def get_members(self) -> Iterator[IdentityInfo]:
        """Return the members of the group.

        This can also be performed by iterating over the group.

        Returns:
            An iterator of IdentityInfo objects.
        """
        return iter(
            map(lambda i: IdentityInfo(identifier=i, provider=self._provider), self._members)
        )

    def has_member(self, identifier: str) -> bool:
        """Check if a given identity is a member of the group.

        This check can also be performed using the ``in`` operator.

        Args:
             identifier: The identifier from an IdentityInfo
                         provided by the associated identity provider.
        """
        return identifier in self._members

    def add_member(self, identifier: str):
        self._members.add(identifier)

    def remove_member(self, identifier: str):
        self._members.remove(identifier)


class DummyGroupProvider(GroupProvider):
    group_class = DummyGroup

    def __init__(self, identity_provider: IdentityProvider):
        self._identity_provider = identity_provider
        self._groups = {}

    def add_group(self, name: str):
        if name not in self._groups:
            self._groups[name] = DummyGroup(provider=self._identity_provider, name=name)

    def get_group(self, name: str) -> Optional[DummyGroup]:
        return self._groups.get(name)

    def get_groups(self) -> Iterable[DummyGroup]:
        return self._groups.values()

    def get_user_groups(self, identifier: str) -> Iterable[DummyGroup]:
        return filter(lambda g: g.has_member(identifier), self._groups.values())

    def add_group_member(self, identifier: str, group_name: str):
        g = self.get_group(group_name)
        if not g:
            g = DummyGroup(provider=self._identity_provider, name=group_name)
            self._groups[group_name] = g

        g.add_member(identifier)

    def remove_group_member(self, identifier: str, group_name: str):
        g = self.get_group(group_name)

        if g and g.has_member(identifier):
            g.remove_member(identifier)
