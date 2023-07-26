#  Copyright 2023 Canonical Ltd.
#  See LICENSE file for licensing details.
"""Marks this package in order to be used by the Indico plugin system."""

from indico.core.plugins import IndicoPlugin


class SAMLGroupsPlugin(IndicoPlugin):  # pylint: disable=too-few-public-methods
    """SAML Groups Plugin."""
