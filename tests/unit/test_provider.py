#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.
from unittest.mock import Mock

import pytest
from flask import Flask
from flask_multipass import AuthInfo, IdentityRetrievalFailed, Multipass
from werkzeug.datastructures import MultiDict

from flask_multipass_saml_groups.group_provider.dummy import DummyGroupProvider
from flask_multipass_saml_groups.provider import (
    DEFAULT_IDENTIFIER_FIELD,
    SAML_GRP_ATTR_NAME,
    SAMLGroupsIdentityProvider,
)

USER_EMAIL = "user@example.com"
OTHER_USER_EMAIL = "other@example.com"
GRP_NAME = "group1"
OTHER_GRP_NAME = "other"


@pytest.fixture(name="saml_attrs")
def saml_attrs_fixture():
    return {
        "_saml_nameid": USER_EMAIL,
        DEFAULT_IDENTIFIER_FIELD: f"{USER_EMAIL}@https://site",
        "email": USER_EMAIL,
        "fullname": "Foo bar",
        "openid": "https://openid",
        "userid": USER_EMAIL,
        "username": "user",
        SAML_GRP_ATTR_NAME: [GRP_NAME, OTHER_GRP_NAME],
    }


@pytest.fixture(name="saml_attrs_grp_removed")
def saml_attrs_grp_removed_fixture():
    return {
        "_saml_nameid": USER_EMAIL,
        DEFAULT_IDENTIFIER_FIELD: f"{USER_EMAIL}@https://site",
        "email": USER_EMAIL,
        "fullname": "Foo bar",
        "openid": "https://openid",
        "userid": USER_EMAIL,
        "username": "user",
        SAML_GRP_ATTR_NAME: [OTHER_GRP_NAME],
    }


@pytest.fixture(name="saml_attrs_other_user")
def saml_attrs_other_user_fixture():
    return {
        "_saml_nameid": OTHER_USER_EMAIL,
        DEFAULT_IDENTIFIER_FIELD: f"{OTHER_USER_EMAIL}@https://site",
        "email": OTHER_USER_EMAIL,
        "fullname": "Foo bar",
        "openid": "https://openid",
        "userid": OTHER_USER_EMAIL,
        "username": "other",
        SAML_GRP_ATTR_NAME: [OTHER_GRP_NAME],
    }


@pytest.fixture(name="auth_info")
def auth_info_fixture(saml_attrs):
    return AuthInfo(provider=Mock(), **saml_attrs)


@pytest.fixture(name="auth_info_grp_removed")
def auth_info_grp_removed_fixture(saml_attrs_grp_removed):
    return AuthInfo(provider=Mock(), **saml_attrs_grp_removed)


@pytest.fixture(name="auth_info_other_user")
def auth_info_other_user_fixture(saml_attrs_other_user):
    return AuthInfo(provider=Mock(), **saml_attrs_other_user)


@pytest.fixture(name="provider")
def provider_fixture():
    app = Flask("test")
    multipass = Multipass(app)

    with app.app_context():
        yield SAMLGroupsIdentityProvider(
            multipass=multipass,
            name="saml_groups",
            settings={},
            group_provider_class=DummyGroupProvider,
        )


@pytest.fixture(name="provider_custom_field")
def provider_custom_field_fixture():
    app = Flask("test")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    multipass = Multipass(app)

    with app.app_context():
        yield SAMLGroupsIdentityProvider(
            multipass=multipass,
            name="saml_groups",
            settings=dict(identifier_field="fullname"),
            group_provider_class=DummyGroupProvider,
        )


def test_get_identity_from_auth_returns_identity_info(provider, auth_info, saml_attrs):
    """
    arrange: given AuthInfo by AuthProvider
    act: call get_identity_from_auth from SAMLGroupsIdentityProvider
    assert: the returned IdentityInfo object contains the expected data from AuthInfo
    """

    identity_info = provider.get_identity_from_auth(auth_info)

    assert identity_info is not None
    assert identity_info.provider == provider
    assert identity_info.identifier == auth_info.data[DEFAULT_IDENTIFIER_FIELD]
    assert identity_info.data == MultiDict(saml_attrs)


def test_get_identity_from_auth_returns_identity_from_custom_field(
    auth_info, provider_custom_field
):
    """
    arrange: given AuthInfo by AuthProvider and provider using custom identifier_field
    act: call get_identity_from_auth from SAMLGroupsIdentityProvider
    assert: the returned IdentityInfo object uses the custom field as identifier
    """

    identity_info = provider_custom_field.get_identity_from_auth(auth_info)

    assert identity_info is not None
    assert identity_info.identifier == auth_info.data["fullname"]


def test_get_identity_from_auth_returns_identity_from_list(auth_info, provider_custom_field):
    """
    arrange: given AuthInfo by AuthProvider and provider using one element list value for identifier_field
    act: call get_identity_from_auth from SAMLGroupsIdentityProvider
    assert: the returned IdentityInfo object uses the custom field as identifier
    """
    auth_info.data["fullname"] = ["foo"]

    identity_info = provider_custom_field.get_identity_from_auth(auth_info)

    assert identity_info is not None
    assert identity_info.identifier == "foo"


def test_get_identity_from_auth_raises_exc_for_multi_val_identifier(
    auth_info, provider_custom_field
):
    """
    arrange: given AuthInfo by AuthProvider and provider using custom identifier_field with multiple values
    act: call get_identity_from_auth from SAMLGroupsIdentityProvider
    assert: an exception is raised
    """

    auth_info.data["fullname"] = ["foo", "bar"]

    with pytest.raises(IdentityRetrievalFailed):
        provider_custom_field.get_identity_from_auth(auth_info)


def test_get_identity_from_auth_raises_exc_for_no_identifier(auth_info, provider):
    """
    arrange: given AuthInfo by AuthProvider and provider does not provide value for identifier field
    act: call get_identity_from_auth from SAMLGroupsIdentityProvider
    assert: an exception is raised
    """

    del auth_info.data[DEFAULT_IDENTIFIER_FIELD]

    with pytest.raises(IdentityRetrievalFailed):
        provider.get_identity_from_auth(auth_info)


def test_get_identity_from_auth_adds_user_to_group(auth_info, provider):
    """
    arrange: given AuthInfo by AuthProvider
    act: call get_identity_from_auth from SAMLGroupsIdentityProvider
    assert: the user is added to the groups
    """
    provider.get_identity_from_auth(auth_info)

    group = provider.get_group(GRP_NAME)
    members = list(group.get_members())
    assert members
    assert members[0].identifier == auth_info.data[DEFAULT_IDENTIFIER_FIELD]

    group = provider.get_group(OTHER_GRP_NAME)
    members = list(group.get_members())
    assert members
    assert members[0].identifier == auth_info.data[DEFAULT_IDENTIFIER_FIELD]


def test_get_identity_from_auth_adds_user_to_existing_group(
    auth_info, auth_info_other_user, provider
):
    """
    arrange: given AuthInfo of two users by AuthProvider
    act: call get_identity_from_auth from SAMLGroupsIdentityProvider twice and second time with another user
    assert: the user is added to the existing group
    """
    provider.get_identity_from_auth(auth_info)
    provider.get_identity_from_auth(auth_info_other_user)

    group = provider.get_group(GRP_NAME)
    members = list(group.get_members())
    assert members
    assert members[0].identifier == auth_info.data[DEFAULT_IDENTIFIER_FIELD]

    group = provider.get_group(OTHER_GRP_NAME)
    members = list(group.get_members())
    assert len(members) == 2
    expected_identifiers = {
        auth_info.data[DEFAULT_IDENTIFIER_FIELD],
        auth_info_other_user.data[DEFAULT_IDENTIFIER_FIELD],
    }
    assert members[0].identifier in expected_identifiers
    assert members[1].identifier in expected_identifiers


def test_get_identity_from_auth_removes_user_from_group(
    auth_info, auth_info_grp_removed, provider
):
    """
    arrange: given AuthInfo by AuthProvider
    act: call get_identity_from_auth from SAMLGroupsIdentityProvider and afterwards again with a group removed
    assert: the user is removed from the group
    """
    provider.get_identity_from_auth(auth_info)

    group = provider.get_group(GRP_NAME)
    members = list(group.get_members())
    assert members
    assert members[0].identifier == auth_info.data[DEFAULT_IDENTIFIER_FIELD]

    provider.get_identity_from_auth(auth_info_grp_removed)

    group = provider.get_group(GRP_NAME)
    members = list(group.get_members())
    assert not members

    group = provider.get_group(OTHER_GRP_NAME)
    members = list(group.get_members())
    assert members
    assert members[0].identifier == auth_info.data[DEFAULT_IDENTIFIER_FIELD]


def test_get_group_returns_specific_group(auth_info, provider):
    """
    arrange: given AuthInfo by AuthProvider
    act: call get_identity_from_auth and afterwards get_group from SAMLGroupsIdentityProvider with a specific group name
    assert: the returned group name is the one requested
    """
    provider.get_identity_from_auth(auth_info)
    group = provider.get_group(GRP_NAME)

    assert group.name == GRP_NAME


def test_get_group_returns_none_if_no_auth_handled(provider):
    """
    arrange: given only an AuthProvider whose methods have never been called
    act: call get_group from SAMLGroupsIdentityProvider with a specific group name
    assert: the result is None
    """
    group = provider.get_group(GRP_NAME)

    assert group is None


def test_search_groups_returns_all_matched_groups(auth_info, provider):
    """
    arrange: given AuthInfo by AuthProvider
    act: call get_identity_from_auth and afterwards search_groups from SAMLGroupsIdentityProvider
    assert: the returned list of groups contains all the groups the user belongs to
    """
    provider.get_identity_from_auth(auth_info)
    groups = list(provider.search_groups(GRP_NAME, exact=True))

    assert len(groups) == 1
    assert groups[0].name == GRP_NAME


def test_search_groups_non_exact_returns_all_matched_groups(auth_info, provider):
    """
    arrange: given AuthInfo by AuthProvider
    act: call get_identity_from_auth and afterwards search_groups using exact=False from SAMLGroupsIdentityProvider
    assert: the returned list of groups contains all the groups the user belongs to
    """
    provider.get_identity_from_auth(auth_info)
    groups = list(provider.search_groups(GRP_NAME[:-1], exact=False))

    assert len(groups) == 1
    assert groups[0].name == GRP_NAME
