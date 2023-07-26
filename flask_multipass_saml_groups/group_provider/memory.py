#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.

"""A simple group provider for testing which stores data in memory. Do not use in production."""
from typing import Dict, Iterable, Iterator, Optional, Set

from flask_multipass import Group, IdentityInfo, IdentityProvider

from flask_multipass_saml_groups.group_provider.base import GroupProvider


class MemoryGroup(Group):
    """A simple group for testing. Do not use in production.

    The members of the group are stored in memory.

    Attrs:
        supports_member_list (bool): If the group supports getting the list of members
    """

    supports_member_list = True

    def __init__(self, provider: IdentityProvider, name: str):
        """Initialize the group.

        Args:
            provider: The associated identity provider
            name: The name of this group
        """
        super().__init__(provider, name)
        self._provider = provider
        self._name = name
        self._members: Set[str] = set()

    def get_members(self) -> Iterator[IdentityInfo]:  # noqa: D102,DCO010 docstring in base class
        return iter(
            map(lambda i: IdentityInfo(identifier=i, provider=self._provider), self._members)
        )

    def has_member(self, identifier: str) -> bool:  # noqa: D102,DCO010 docstring in base class
        return identifier in self._members

    def add_member(self, identifier: str) -> None:
        """Add a member to the group.

        Args:
            identifier: The identifier from an IdentityInfo
        """
        self._members.add(identifier)

    def remove_member(self, identifier: str) -> None:
        """Remove a member from the group.

        Args:
            identifier: The identifier from an IdentityInfo
        """
        self._members.remove(identifier)


class MemoryGroupProvider(GroupProvider):
    """A simple group provider for testing. Do not use in production.

    The groups are stored in memory.

    Attrs:
        group_class (type): The class to use for groups.
    """

    group_class = MemoryGroup

    def __init__(self, identity_provider: IdentityProvider):
        """Initialize the group provider.

        Args:
            identity_provider: The associated identity provider
        """
        self._identity_provider = identity_provider
        self._groups: Dict[str, MemoryGroup] = {}

    def add_group(self, name: str) -> None:  # noqa: D102,DCO010 same docstring as base class
        if name not in self._groups:
            self._groups[name] = MemoryGroup(provider=self._identity_provider, name=name)

    def get_group(self, name: str) -> Optional[MemoryGroup]:  # noqa: D102,DCO010
        return self._groups.get(name)

    def get_groups(self) -> Iterable[MemoryGroup]:  # noqa: D102,DCO010
        return self._groups.values()

    def get_user_groups(self, identifier: str) -> Iterable[MemoryGroup]:  # noqa: D102,DCO010
        return filter(lambda g: g.has_member(identifier), self._groups.values())

    def add_group_member(self, identifier: str, group_name: str) -> None:  # noqa: D102,DCO010
        grp = self.get_group(group_name)
        if not grp:
            grp = MemoryGroup(provider=self._identity_provider, name=group_name)
            self._groups[group_name] = grp

        grp.add_member(identifier)

    def remove_group_member(self, identifier: str, group_name: str) -> None:  # noqa: D102,DCO010
        grp = self.get_group(group_name)

        if grp and grp.has_member(identifier):
            grp.remove_member(identifier)
