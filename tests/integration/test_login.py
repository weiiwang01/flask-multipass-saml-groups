#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.
from typing import List

from tests.integration.common import GRP_NAME, OTHER_GRP_NAME, USER_EMAIL, USER_IDENTIFIER, login


def test_login_extracts_groups_from_saml_attributes(app, multipass):
    """
    arrange: given an app
    act: call login with a user that has groups in the SAML attributes
    assert: the user is logged in and the groups are assigned to the user
    """
    client = app.test_client()

    login(client, groups=[GRP_NAME, OTHER_GRP_NAME], user_email=USER_EMAIL)

    _assert_user_only_in_groups([GRP_NAME, OTHER_GRP_NAME], app, multipass)


def test_relogin_removes_previous_groups(app, multipass):
    """
    arrange: given an app and a user with groups
    act: call login with a user and recall login with the same user but differing groups
    assert: the user is logged in and the invalid group membership from first login is removed
    """
    client = app.test_client()

    login(client, groups=[GRP_NAME, OTHER_GRP_NAME], user_email=USER_EMAIL)
    login(client, groups=[OTHER_GRP_NAME], user_email=USER_EMAIL)

    _assert_user_only_in_groups([OTHER_GRP_NAME], app, multipass)


def test_login_with_no_groups(app, multipass):
    """
    arrange: given an app
    act: call login with a user that has no groups in the SAML attributes
    assert: the user is logged in and no groups are assigned to the user
    """
    client = app.test_client()

    login(client, groups=[], user_email=USER_EMAIL)

    _assert_user_only_in_groups([], app, multipass)


def test_login_with_multiple_identical_groups(app, multipass):
    """
    arrange: given an app
    act: call login with a user that has duplicate group names in the SAML attributes
    assert: the user is logged in and the duplicate group names are not counted
    """
    client = app.test_client()

    login(client, groups=[GRP_NAME, GRP_NAME], user_email=USER_EMAIL)

    with app.app_context():
        idp = multipass.identity_providers["ubuntu"]

        grps = list(idp.get_identity_groups(USER_IDENTIFIER))
        assert len(grps) == 1


def _assert_user_only_in_groups(groups: List[str], app, multipass):
    with app.app_context():
        idp = multipass.identity_providers["ubuntu"]

        grps = list(idp.get_identity_groups(USER_IDENTIFIER))
        assert len(grps) == len(groups)

        for g in grps:
            assert g.name in groups
            assert isinstance(g, idp.group_class)
            assert g.has_member(USER_IDENTIFIER)
