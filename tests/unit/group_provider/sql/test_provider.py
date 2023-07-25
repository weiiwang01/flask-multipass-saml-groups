#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.

from unittest.mock import Mock

import pytest
from flask import Flask
from flask_multipass import IdentityProvider, Multipass
from indico.core.db import db

from flask_multipass_saml_groups.group_provider.sql import SQLGroup, SQLGroupProvider
from flask_multipass_saml_groups.models.saml_groups import SAMLGroup as DBGroup
from flask_multipass_saml_groups.models.saml_groups import SAMLUser, group_members_table

USER_IDENTIFIER = "user1"
OTHER_USER_IDENTIFIER = "user2"
NOT_EXISTING_USER_IDENTIFIER = "user3"
GRP_NAME = "group1"
OTHER_GRP_NAME = "other"
NOT_EXISTING_GRP_NAME = "not_existing"


@pytest.fixture(name="group_provider")
def group_provider_fixture(app):
    with app.app_context():
        multipass = Multipass(app=app)
        gp = SQLGroupProvider(
            identity_provider=IdentityProvider(
                multipass=multipass, name="saml_groups", settings={}
            ),
        )
        u1 = SAMLUser(identifier=USER_IDENTIFIER)
        db.session.add(u1)
        u2 = SAMLUser(identifier=OTHER_USER_IDENTIFIER)
        db.session.add(u2)
        g1 = DBGroup(name=GRP_NAME)
        g1.members.append(u1)
        db.session.add(g1)
        db.session.add(DBGroup(name=OTHER_GRP_NAME))
        db.session.commit()

        yield gp


def test_get_group(group_provider):
    """
    arrange: given a GroupProvider instance
    act: call get_group with a specific group name
    assert: returns a SQLGroup instance with the same name
    """
    grp = group_provider.get_group(GRP_NAME)
    assert isinstance(grp, SQLGroup)
    assert grp.name == GRP_NAME


def test_get_group_not_found(group_provider):
    """
    arrange: given a GroupProvider instance
    act: call get_group with a non existing group name
    assert: returns None
    """
    grp = group_provider.get_group("non-existing")
    assert grp is None


def test_get_groups(group_provider):
    """
    arrange: given a GroupProvider instance
    act: call get_groups
    assert: returns a list of all groups
    """
    grps = list(group_provider.get_groups())
    assert grps
    assert len(grps) == 2
    assert grps[0].name == GRP_NAME
    assert grps[1].name == OTHER_GRP_NAME


def test_get_user_groups(group_provider):
    """
    arrange: given a user identifier
    act: call get_user_groups
    assert: returns a list of groups the user belongs to
    """
    grps = list(group_provider.get_user_groups(USER_IDENTIFIER))
    assert grps
    assert len(grps) == 1
    assert grps[0].name == GRP_NAME


def test_get_user_groups_without_groups(group_provider):
    """
    arrange: given a user identifier for a user who belongs to no groups
    act: call get_user_groups
    assert: returns empty list
    """
    grps = list(group_provider.get_user_groups(OTHER_USER_IDENTIFIER))
    assert not grps


def test_get_user_groups_for_non_existing_user(group_provider):
    """
    arrange: given a user identifier for a non existing user
    act: call get_user_groups
    assert: returns empty list
    """
    grps = list(group_provider.get_user_groups(NOT_EXISTING_USER_IDENTIFIER))
    assert not grps


def test_add_group(group_provider):
    """
    arrange: given a GroupProvider instance
    act: call add_group with a group name
    assert: the group can be retrieved calling get_group
    """
    group_provider.add_group(NOT_EXISTING_GRP_NAME)
    grp = group_provider.get_group(NOT_EXISTING_GRP_NAME)
    assert isinstance(grp, SQLGroup)
    assert grp.name == NOT_EXISTING_GRP_NAME


def test_add_group_group_already_existing(group_provider):
    """
    arrange: given a GroupProvider instance
    act: call add_group with a group name that already exists
    assert: the group can be retrieved calling get_group
    """
    group_provider.add_group(NOT_EXISTING_GRP_NAME)
    group_provider.add_group(NOT_EXISTING_GRP_NAME)

    grp = group_provider.get_group(NOT_EXISTING_GRP_NAME)
    assert isinstance(grp, SQLGroup)
    assert grp.name == NOT_EXISTING_GRP_NAME


def test_add_group_member(group_provider):
    """
    arrange: given a GroupProvider instance
    act: call add_group_member with a user identifier and a group name
    assert: the user belongs to the group
    """
    group_provider.add_group_member(USER_IDENTIFIER, OTHER_GRP_NAME)
    grp = group_provider.get_group(OTHER_GRP_NAME)
    assert isinstance(grp, SQLGroup)
    assert grp.name == OTHER_GRP_NAME
    members = list(grp.get_members())
    assert len(members) == 1
    assert members[0].identifier == USER_IDENTIFIER


def test_add_group_member_user_non_existing(group_provider):
    """
    arrange: given a GroupProvider instance
    act: call add_group_member with a non existing user identifier and a group name
    assert: the user gets created and belongs to the group
    """
    group_provider.add_group_member(NOT_EXISTING_USER_IDENTIFIER, OTHER_GRP_NAME)
    grp = group_provider.get_group(OTHER_GRP_NAME)
    assert isinstance(grp, SQLGroup)
    assert grp.name == OTHER_GRP_NAME
    members = list(grp.get_members())
    assert len(members) == 1
    assert members[0].identifier == NOT_EXISTING_USER_IDENTIFIER


def test_add_group_member_group_non_existing(group_provider):
    """
    arrange: given a GroupProvider instance
    act: call add_group_member with a user identifier and a non existing group name
    assert: the group gets created and the user belongs to the group
    """
    group_provider.add_group_member(USER_IDENTIFIER, NOT_EXISTING_GRP_NAME)
    grp = group_provider.get_group(NOT_EXISTING_GRP_NAME)
    assert isinstance(grp, SQLGroup)
    assert grp.name == NOT_EXISTING_GRP_NAME
    members = list(grp.get_members())
    assert len(members) == 1
    assert members[0].identifier == USER_IDENTIFIER


def test_add_group_member_pair_already_existing(group_provider):
    """
    arrange: given a GroupProvider instance
    act: call add_group_member twice with a user identifier and a group name
    assert: the user belongs to the group, but is returned only once
    """
    group_provider.add_group_member(USER_IDENTIFIER, OTHER_GRP_NAME)
    group_provider.add_group_member(USER_IDENTIFIER, OTHER_GRP_NAME)

    grp = group_provider.get_group(OTHER_GRP_NAME)
    assert isinstance(grp, SQLGroup)
    assert grp.name == OTHER_GRP_NAME
    members = list(grp.get_members())
    assert len(members) == 1
    assert members[0].identifier == USER_IDENTIFIER


def test_remove_group_member(group_provider):
    """
    arrange: given a GroupProvider instance
    act: call remove_group_member with a user identifier and a group name
    assert: the user does not belong to the group anymore
    """
    group_provider.remove_group_member(USER_IDENTIFIER, GRP_NAME)
    grp = group_provider.get_group(GRP_NAME)
    assert isinstance(grp, SQLGroup)
    assert grp.name == GRP_NAME
    members = list(grp.get_members())
    assert not members


def test_remove_group_member_user_non_existing(group_provider):
    """
    arrange: given a GroupProvider instance
    act: call remove_group_member with a non existing user identifier and a group name
    assert: the member list without the user is returned
    """
    group_provider.remove_group_member(NOT_EXISTING_USER_IDENTIFIER, GRP_NAME)
    grp = group_provider.get_group(GRP_NAME)
    assert isinstance(grp, SQLGroup)
    assert grp.name == GRP_NAME
    members = list(grp.get_members())
    assert len(members) == 1
    assert members[0].identifier == USER_IDENTIFIER


def test_remove_group_member_group_non_existing(group_provider):
    """
    arrange: given a GroupProvider instance
    act: call remove_group_member with a user identifier and a non existing group name
    assert: the group does not exist
    """
    group_provider.remove_group_member(USER_IDENTIFIER, NOT_EXISTING_GRP_NAME)
    grp = group_provider.get_group(NOT_EXISTING_GRP_NAME)
    assert not grp
