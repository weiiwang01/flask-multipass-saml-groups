#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.

import pytest
from flask import Flask
from flask_multipass import IdentityInfo, Multipass
from indico.core.db import db

from flask_multipass_saml_groups.group_provider.sql import SQLGroup, SQLGroupProvider
from flask_multipass_saml_groups.provider import SAMLGroupsIdentityProvider

USER_IDENTIFIER = "email@email.com"
OTHER_USER_IDENTIFIER = "other@other.com"
GRP_NAME = "group1"
OTHER_GRP_NAME = "other"


@pytest.fixture(name="provider")
def provider_fixture(app):
    multipass = Multipass(app)
    with app.app_context():
        provider = SAMLGroupsIdentityProvider(multipass=multipass, name="saml_groups", settings={})
    return provider


@pytest.fixture(name="group_provider")
def group_provider_fixture(app, provider):
    with app.app_context():
        yield SQLGroupProvider(identity_provider=provider)


@pytest.fixture(name="group")
def group_fixture(provider, app):
    return SQLGroup(provider=provider, name=GRP_NAME)


def test_get_members(group, group_provider):
    """
    arrange: given group with users
    act: call get_members
    assert: the users are contained in the returned result
    """
    group_provider.add_group_member(group_name=GRP_NAME, identifier=USER_IDENTIFIER)
    group_provider.add_group_member(group_name=GRP_NAME, identifier=OTHER_USER_IDENTIFIER)

    members = list(group.get_members())

    assert members
    assert len(members) == 2
    assert isinstance(members[0], IdentityInfo)
    assert isinstance(members[1], IdentityInfo)

    assert members[0].identifier == USER_IDENTIFIER
    assert members[1].identifier == OTHER_USER_IDENTIFIER


def test_get_members_returns_empty_list(group, group_provider):
    """
    arrange: given no users
    act: call get_members
    assert: get_members returns an empty list
    """
    group_provider.add_group(GRP_NAME)
    members = list(group.get_members())

    assert not members


def test_get_members_returns_empty_list_for_non_existing_group(group, group_provider):
    """
    arrange: given no underlying db group
    act: call get_members
    assert: get_members returns an empty list
    """
    members = list(group.get_members())

    assert not members


def test_has_member(group, group_provider):
    """
    arrange: given a user which belongs to a group
    act: call has_member
    assert: has_user returns True
    """
    group_provider.add_group_member(identifier=USER_IDENTIFIER, group_name=GRP_NAME)

    assert group.has_member(USER_IDENTIFIER)


def test_has_member_returns_false(group, group_provider):
    """
    arrange: given a user identifier which does not belong to a group
    act: call has_member
    assert: has_member returns False
    """
    group_provider.add_group_member(identifier=USER_IDENTIFIER, group_name=GRP_NAME)
    assert not group.has_member(OTHER_USER_IDENTIFIER)


def test_has_member_returns_false_for_non_existing_group(group, group_provider):
    """
    arrange: given no underlying db group
    act: call has_member
    assert: has_member returns False
    """
    assert not group.has_member(OTHER_USER_IDENTIFIER)
