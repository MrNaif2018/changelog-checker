from changelog_checker.models import (
    ChangelogEntry,
    ChangeType,
    DependencyChange,
    PackageInfo,
    PackageReport,
)


class TestChangeType:
    def test_change_type_values(self):
        assert ChangeType.UPDATED.value == "updated"
        assert ChangeType.ADDED.value == "added"
        assert ChangeType.REMOVED.value == "removed"


class TestDependencyChange:
    def test_dependency_change_creation(self):
        change = DependencyChange(name="requests", change_type=ChangeType.UPDATED, old_version="2.28.0", new_version="2.29.0")
        assert change.name == "requests"
        assert change.change_type == ChangeType.UPDATED
        assert change.old_version == "2.28.0"
        assert change.new_version == "2.29.0"

    def test_dependency_change_str_updated(self):
        change = DependencyChange(name="requests", change_type=ChangeType.UPDATED, old_version="2.28.0", new_version="2.29.0")
        assert str(change) == "requests: 2.28.0 -> 2.29.0"

    def test_dependency_change_str_added(self):
        change = DependencyChange(name="new-package", change_type=ChangeType.ADDED, new_version="1.0.0")
        assert str(change) == "new-package: added 1.0.0"

    def test_dependency_change_str_removed(self):
        change = DependencyChange(name="old-package", change_type=ChangeType.REMOVED, old_version="0.5.0")
        assert str(change) == "old-package: removed 0.5.0"

    def test_dependency_change_defaults(self):
        change = DependencyChange(name="test-package", change_type=ChangeType.ADDED)
        assert change.name == "test-package"
        assert change.change_type == ChangeType.ADDED
        assert change.old_version is None
        assert change.new_version is None


class TestPackageInfo:
    def test_package_info_creation(self):
        info = PackageInfo(
            name="requests",
            github_url="https://github.com/user/requests",
            pypi_url="https://pypi.org/project/requests/",
            changelog_url="https://github.com/user/requests/blob/main/CHANGELOG.md",
            changelog_found=True,
        )
        assert info.name == "requests"
        assert info.github_url == "https://github.com/user/requests"
        assert info.pypi_url == "https://pypi.org/project/requests/"
        assert info.changelog_url == "https://github.com/user/requests/blob/main/CHANGELOG.md"
        assert info.changelog_found is True

    def test_package_info_defaults(self):
        info = PackageInfo(name="test-package")
        assert info.name == "test-package"
        assert info.github_url is None
        assert info.pypi_url is None
        assert info.changelog_url is None
        assert info.changelog_found is False


class TestChangelogEntry:
    def test_changelog_entry_creation(self):
        entry = ChangelogEntry(
            version="1.2.3", content="- Fixed bug in authentication\n- Added new feature", date="2023-12-01"
        )
        assert entry.version == "1.2.3"
        assert entry.content == "- Fixed bug in authentication\n- Added new feature"
        assert entry.date == "2023-12-01"

    def test_changelog_entry_defaults(self):
        entry = ChangelogEntry(version="1.0.0", content="Initial release")
        assert entry.version == "1.0.0"
        assert entry.content == "Initial release"
        assert entry.date is None


class TestPackageReport:
    def test_package_report_creation(self):
        dependency_change = DependencyChange(
            name="requests", change_type=ChangeType.UPDATED, old_version="2.28.0", new_version="2.29.0"
        )
        package_info = PackageInfo(name="requests", github_url="https://github.com/user/requests")
        changelog_entries = [
            ChangelogEntry(version="2.29.0", content="Bug fixes"),
            ChangelogEntry(version="2.28.1", content="Security update"),
        ]
        report = PackageReport(
            dependency_change=dependency_change, package_info=package_info, changelog_entries=changelog_entries
        )
        assert report.dependency_change == dependency_change
        assert report.package_info == package_info
        assert report.changelog_entries == changelog_entries
        assert report.error_message is None

    def test_package_report_with_error(self):
        dependency_change = DependencyChange(name="unknown-package", change_type=ChangeType.ADDED, new_version="1.0.0")
        package_info = PackageInfo(name="unknown-package")
        report = PackageReport(
            dependency_change=dependency_change,
            package_info=package_info,
            changelog_entries=[],
            error_message="Package not found on PyPI",
        )
        assert report.dependency_change == dependency_change
        assert report.package_info == package_info
        assert report.changelog_entries == []
        assert report.error_message == "Package not found on PyPI"
