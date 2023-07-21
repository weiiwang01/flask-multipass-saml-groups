#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.
from unittest.mock import Mock

import pytest
from flask import Flask
from flask_multipass import IdentityInfo, Multipass

from src.saml_groups_provider import SAMLGroup, SAMLGroupsIdentityProvider

USER_IDENTIFIER = "email@email.com"
OTHER_USER_IDENTIFIER = "other@other.com"


@pytest.fixture(name="provider")
def provider_fixture():
    app = Flask("test")
    multipass = Multipass(app)
    with app.app_context():
        provider = SAMLGroupsIdentityProvider(multipass=multipass, name="saml_groups", settings={})
    return provider


@pytest.fixture(name="group")
def group_fixture(provider):
    return SAMLGroup(provider=provider, name="group1")


@pytest.fixture(name="user")
def user_fixture(provider):
    return IdentityInfo(provider=provider, identifier=USER_IDENTIFIER)


@pytest.fixture(name="other_user")
def other_user_fixture(provider):
    return IdentityInfo(provider=provider, identifier=OTHER_USER_IDENTIFIER)


def test_add_member(group, user):
    """
    arrange: given a user identifier
    act: call add_member
    assert: the user can be retrieved calling get_members
    """
    group.add_member(user)

    members = list(group.get_members())

    assert members
    assert len(members) == 1
    assert members[0].identifier == USER_IDENTIFIER


def test_get_members(group, user, other_user):
    """
    arrange: given user identifiers
    act: call add_member for those users
    assert: the users can be retrieved calling get_members
    """
    group.add_member(user)
    group.add_member(other_user)

    members = list(group.get_members())

    assert members
    assert len(members) == 2
    assert members[0].identifier == USER_IDENTIFIER
    assert members[1].identifier == OTHER_USER_IDENTIFIER


def test_get_members_returns_empty_list(group):
    """
    arrange: given no users
    act: call get_members
    assert: get_members returns an empty list
    """
    members = list(group.get_members())

    assert not members


def test_has_member(group, user):
    """
    arrange: given a user identifier
    act: call add_member and has_user afterwards
    assert: has_user returns True
    """
    group.add_member(user)

    assert group.has_member(user.identifier)


def test_has_member_returns_false(group, user):
    """
    arrange: given a user identifier
    act: call has_user
    assert: has_user returns False
    """
    assert not group.has_member(user.identifier)
