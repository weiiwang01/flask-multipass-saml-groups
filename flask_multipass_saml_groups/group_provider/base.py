#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.
from abc import ABCMeta
from typing import Iterable, Optional

from flask_multipass import Group


class GroupProvider(metaclass=ABCMeta):
    group_class = Group

    def add_group(self, name: str):  # pragma: no cover
        pass

    def get_group(self, name: str) -> Optional[Group]:  # pragma: no cover
        return None

    def get_groups(self) -> Iterable[Group]:  # pragma: no cover
        return []

    def get_user_groups(self, identifier: str) -> Iterable[Group]:  # pragma: no cover
        return []

    def add_group_member(self, identifier: str, group_name: str):  # pragma: no cover
        pass

    def remove_group_member(self, identifier: str, group_name: str):  # pragma: no cover
        pass
