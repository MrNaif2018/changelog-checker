from changelog_checker.research.changelog_finder import ChangelogFinder


class TestParseChangelogEnhanced:
    def setup_method(self):
        self.finder = ChangelogFinder()

    def test_parse_rst_style_with_dates(self):
        content = """
Release Notes
=============

eth-utils v5.3.0 (2025-04-14)
-----------------------------

Bugfixes
~~~~~~~~

- Replace ``arg["name"]`` with ``arg.get("name")`` to correctly handle optional names.

Features
~~~~~~~~

- Add new methods: ``to_wei_decimals``, and ``from_wei_decimals``

eth-utils v5.2.0 (2025-01-21)
-----------------------------

Bugfixes
~~~~~~~~

- Update types in `is_same_address` to accept `AnyAddress`, `str`, or `bytes`.

eth-utils v5.1.0 (2024-10-21)
-----------------------------

Features
~~~~~~~~

- Some feature for v5.1.0
"""
        entries = self.finder.parse_changelog(content, "5.0.0", "5.3.0")
        assert len(entries) == 3
        assert entries[0].version == "5.3.0"
        assert entries[1].version == "5.2.0"
        assert entries[2].version == "5.1.0"
        assert "to_wei_decimals" in entries[0].content
        assert "is_same_address" in entries[1].content

    def test_parse_v_prefix_versions(self):
        content = """
# Changelog

## v1.2.3
- Changes for v1.2.3

## v1.2.2
- Changes for v1.2.2

v1.2.1
------
- Changes for v1.2.1

v1.2.0 (2024-01-15)
- Changes with date

**v1.1.9**
- Bold v prefix
"""
        entries = self.finder.parse_changelog(content, "1.1.8", "1.2.3")
        assert len(entries) == 5
        versions = [entry.version for entry in entries]
        assert versions == ["1.2.3", "1.2.2", "1.2.1", "1.2.0", "1.1.9"]

    def test_parse_package_name_with_version(self):
        content = """
package-name v1.2.3 (2024-01-15)
================================

- Feature A
- Feature B

another-package v1.2.2 (2024-01-10)
===================================

- Bug fix
"""
        entries = self.finder.parse_changelog(content, "1.2.1", "1.2.3")
        assert len(entries) == 2
        assert entries[0].version == "1.2.3"
        assert entries[1].version == "1.2.2"
        assert "Feature A" in entries[0].content

    def test_parse_mixed_formats(self):
        content = """
# Changelog

## Version 2.0.0
- Major release

**v1.9.0**
- Bold version

[1.8.0]
- Bracketed version

1.7.0 - 2024-01-01
- Version with dash and date

package v1.6.0 (2024-01-01)
---------------------------
- Package name format

v1.5.0
======
- Simple v prefix with equals underline
"""
        entries = self.finder.parse_changelog(content, "1.4.0", "2.0.0")
        assert len(entries) == 6
        versions = [entry.version for entry in entries]
        expected = ["2.0.0", "1.9.0", "1.8.0", "1.7.0", "1.6.0", "1.5.0"]
        assert versions == expected

    def test_parse_rst_underlines_filtered(self):
        content = """
package v1.2.0 (2024-01-01)
---------------------------

Features
~~~~~~~~

- New feature
- Another feature

Bugfixes
~~~~~~~~

- Bug fix
"""
        entries = self.finder.parse_changelog(content, "1.1.0", "1.2.0")
        assert len(entries) == 1
        assert entries[0].version == "1.2.0"
        content_lines = entries[0].content.split("\n")
        for line in content_lines:
            if line.strip():
                assert not (len(set(line.strip())) == 1 and line.strip()[0] in "-~=^")

    def test_parse_version_range_boundary(self):
        content = """
## v1.3.0
- Version 1.3.0

## v1.2.0
- Version 1.2.0

## v1.1.0
- Version 1.1.0
"""
        entries = self.finder.parse_changelog(content, "1.1.0", "1.3.0")
        assert len(entries) == 2
        versions = [entry.version for entry in entries]
        assert versions == ["1.3.0", "1.2.0"]

    def test_parse_no_matching_versions(self):
        content = """
## v2.0.0
- Version 2.0.0

## v1.0.0
- Version 1.0.0
"""
        entries = self.finder.parse_changelog(content, "1.5.0", "1.9.0")
        assert len(entries) == 0

    def test_parse_empty_content(self):
        entries = self.finder.parse_changelog("", "1.0.0", "2.0.0")
        assert len(entries) == 0
        entries = self.finder.parse_changelog("   \n\n   ", "1.0.0", "2.0.0")
        assert len(entries) == 0

    def test_parse_version_with_four_parts(self):
        content = """
## v1.2.3.4
- Version with four parts

## v1.2.3.3
- Another four-part version
"""
        entries = self.finder.parse_changelog(content, "1.2.3.2", "1.2.3.4")
        assert len(entries) == 2
        assert entries[0].version == "1.2.3.4"
        assert entries[1].version == "1.2.3.3"

    def test_parse_bullet_point_release_format(self):
        content = """
* Release 0.19.1 (13 Mar 2025)

New API:
* ``der.remove_implitic`` and ``der.encode_implicit`` for decoding and
  encoding DER IMPLICIT values with custom tag values and arbitrary
  classes

Bug fixes:
* Minor fixes around arithmetic with curves that have non-prime order
  (useful for experimentation, not practical deployments)
* Fix arithmetic to work with curves that have (0, 0) on the curve
* Fix canonicalization of signatures when ``s`` is just slightly
  above half of curve order

Maintenance:
* Dropped official support for Python 3.5 (again, issues with CI, support
  for Python 2.6 and Python 2.7 is unchanged)
* Officialy support Python 3.12 and 3.13 (add them to CI)
* Removal of few more unnecessary `six.b` literals (Alexandre Detiste)
* Fix typos in warning messages


* Release 0.19.0 (08 Apr 2024)

Features:
* Some new features for 0.19.0

Bug fixes:
* Some bug fixes for 0.19.0
"""
        entries = self.finder.parse_changelog(content, "0.18.0", "0.19.1")
        assert len(entries) == 2
        assert entries[0].version == "0.19.1"
        assert entries[1].version == "0.19.0"
        assert "der.remove_implitic" in entries[0].content
        assert "der.encode_implicit" in entries[0].content
        assert "Minor fixes around arithmetic" in entries[0].content
        assert "Dropped official support for Python 3.5" in entries[0].content
        assert "Some new features for 0.19.0" in entries[1].content

    def test_parse_package_name_with_dots(self):
        content = """
web3.py v7.12.1 (2025-07-14)
----------------------------

Bugfixes
~~~~~~~~

- Fix ``AutoProvider`` batching setup by adding a proxy batch request.

web3.py v7.12.0 (2025-05-22)
----------------------------

Features
~~~~~~~~

- Introduce ``ens.utils.dns_encode_name`` as a rename of the current ``ens_encode_name``.
"""
        entries = self.finder.parse_changelog(content, "7.11.0", "7.12.1")
        assert len(entries) == 2
        assert entries[0].version == "7.12.1"
        assert entries[1].version == "7.12.0"
        assert "AutoProvider" in entries[0].content
        assert "dns_encode_name" in entries[1].content

    def test_parse_package_version_rst_format(self):
        content = """
Release Notes
=============

.. towncrier release notes start

pyrlp v4.1.0 (2025-02-04)
-------------------------

Features
~~~~~~~~

- Merge template, adding ``py313`` support and replacing ``bumpversion`` with ``bump-my-version``.
  ``rust-backend`` still only supported up to ``py312``. (`#156`__)


pyrlp v4.0.1 (2024-04-24)
-------------------------

Internal Changes - for pyrlp Contributors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Add python 3.12 support, ``rust-backend`` now works with python 3.11 and 3.12 (`#150`__)


Miscellaneous Changes
~~~~~~~~~~~~~~~~~~~~~

- `#151`__


pyrlp v4.0.0 (2023-11-29)
-------------------------

Features
~~~~~~~~

- ``repr()`` now returns an evaluatable string, like ``MyRLPObj(my_int_field=1, my_str_field="a_str")`` (`#117 `__)
"""
        entries = self.finder.parse_changelog(content, "3.9.0", "4.1.0")
        assert len(entries) == 3
        assert entries[0].version == "4.1.0"
        assert entries[1].version == "4.0.1"
        assert entries[2].version == "4.0.0"
        assert "py313" in entries[0].content
        assert "bump-my-version" in entries[0].content
        assert "rust-backend" in entries[0].content
        assert "python 3.12 support" in entries[1].content
        assert "repr()" in entries[2].content
        assert "MyRLPObj" in entries[2].content

    def test_parse_sphinx_release_format(self):
        content = """
- :release:`3.4.1 <2024-08-11>`
- :release:`3.3.2 <2024-08-11>`
- :bug:`2419` (fixed in :issue:`2421`) Massage our import of the TripleDES
  cipher to support Cryptography >=43; this should prevent
  ``CryptographyDeprecationWarning`` from appearing upon import. Thanks to
  Erick Alejo for the report and Bryan Banda for the patch.
- :bug:`2420` Modify a test-harness skiptest check to work with newer versions
  of Cryptography. Props to Paul Howarth for the patch.
- :bug:`2353` Fix a 64-bit-ism in the test suite so the tests don't encounter a
  false negative on 32-bit systems. Reported by Stanislav Levin.
- :release:`3.4.0 <2023-12-18>`
- :feature:`-` `Transport` grew a new ``packetizer_class`` kwarg for overriding
  the packet-handler class used internally. Mostly for testing, but advanced
  users may find this useful when doing deep hacks.
- :bug:`- major` Address `CVE 2023-48795 <https://terrapin-attack.com/>`_ (aka
  the "Terrapin Attack", a vulnerability found in the SSH protocol re:
  extension negotiation) by implementing support for the ``strict kex``
  countermeasure for both client and server modes. Thanks to Fabian Bäumer for
  its discovery and for notifying us.
"""
        entries = self.finder.parse_changelog(content, "3.3.0", "3.4.1")
        assert len(entries) == 3
        assert entries[0].version == "3.4.1"
        assert entries[1].version == "3.4.0"
        assert entries[2].version == "3.3.2"
        assert "TripleDES" in entries[0].content
        assert "CryptographyDeprecationWarning" in entries[0].content
        assert "test-harness skiptest" in entries[0].content
        assert "64-bit-ism" in entries[0].content
        assert "packetizer_class" not in entries[0].content
        assert "CVE 2023-48795" not in entries[0].content
        assert "Terrapin Attack" not in entries[0].content
        assert "packetizer_class" in entries[1].content
        assert "CVE 2023-48795" in entries[1].content
        assert "Terrapin Attack" in entries[1].content
        assert "TripleDES" not in entries[1].content
        assert "CryptographyDeprecationWarning" not in entries[1].content
        assert "test-harness skiptest" not in entries[1].content
        assert "64-bit-ism" not in entries[1].content
        assert "TripleDES" in entries[2].content
        assert "CryptographyDeprecationWarning" in entries[2].content
        assert "test-harness skiptest" in entries[2].content
        assert "64-bit-ism" in entries[2].content
        assert "packetizer_class" not in entries[2].content
        assert "CVE 2023-48795" not in entries[2].content
        assert "Terrapin Attack" not in entries[2].content

    def test_parse_two_part_version(self):
        content = """
==========
Change log
==========

8.2 (01 May 2025)
=================

- Optimize QRColorMask apply_mask method for enhanced performance
- Fix typos on StyledPilImage embeded_* parameters.
  The old parameters with the typos are still accepted
  for backward compatibility.


8.1 (02 April 2025)
====================

- Added support for Python 3.13.

8.0 (27 September 2024)
========================

- Added support for Python 3.11 and 3.12.

- Drop support for Python <=3.8.
"""
        entries = self.finder.parse_changelog(content, "7.9.0", "8.2")
        assert len(entries) == 3
        assert entries[0].version == "8.2"
        assert entries[1].version == "8.1"
        assert entries[2].version == "8.0"
        assert "QRColorMask apply_mask method" in entries[0].content
        assert "StyledPilImage embeded_* parameters" in entries[0].content
        assert "backward compatibility" in entries[0].content
        assert "Added support for Python 3.13" in entries[1].content
        assert "Added support for Python 3.11 and 3.12" in entries[2].content
        assert "Drop support for Python <=3.8" in entries[2].content
        for entry in entries:
            content_lines = entry.content.split("\n")
            for line in content_lines:
                if line.strip():
                    assert not (len(set(line.strip())) == 1 and line.strip()[0] == "=")
