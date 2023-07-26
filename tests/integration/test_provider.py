#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.

from typing import List

from flask_multipass import Group, IdentityInfo

from tests.integration.common import GRP_NAME, OTHER_GRP_NAME, USER_EMAIL, USER_IDENTIFIER, login


def test_get_group(app, multipass):
    """
    arrange: given a logged in user which is a member of a group
    act: call get_group on identity provider
    assert: the group is returned and group methods work as expected
    """
    client = app.test_client()
    login(client, groups=[GRP_NAME], user_email=USER_EMAIL)

    with app.app_context():
        idp = multipass.identity_providers["ubuntu"]
        _assert_group_methods_work([idp.get_group(GRP_NAME)])


def test_get_identity_groups(app, multipass):
    """
    arrange: given a logged in user which is a member of multiple group
    act: call get_identity_groups on identity provider
    assert: the groups of the user are returned and group methods work as expected
    """
    client = app.test_client()

    login(client, groups=[GRP_NAME, OTHER_GRP_NAME], user_email=USER_EMAIL)

    with app.app_context():
        idp = multipass.identity_providers["ubuntu"]
        groups = list(idp.get_identity_groups(USER_IDENTIFIER))

        _assert_group_methods_work(groups)
        _assert_group_names(groups, [GRP_NAME, OTHER_GRP_NAME])


def test_search_groups(app, multipass):
    """
    arrange: given a logged in user which is a member of a group
    act: call search_groups on identity provider
    assert: only the matched groups of the user are returned and group methods work as expected
    """
    client = app.test_client()
    login(client, groups=["x", "xy", "z"], user_email=USER_EMAIL)

    with app.app_context():
        idp = multipass.identity_providers["ubuntu"]
        groups = list(idp.search_groups("x"))

        _assert_group_methods_work(groups)
        _assert_group_names(groups, ["x", "xy"])


def _assert_group_methods_work(groups: List[Group]):
    for g in groups:
        members = list(g.get_members())
        assert len(members) == 1
        m = members[0]
        assert isinstance(m, IdentityInfo)
        assert m.identifier == USER_IDENTIFIER

        assert g.has_member(USER_IDENTIFIER)


def _assert_group_names(groups: List[Group], expected_names: List[str]):
    assert len(groups) == len(expected_names)
    for g in groups:
        assert g.name in expected_names
