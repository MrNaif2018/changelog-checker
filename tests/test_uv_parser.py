from changelog_checker.models import ChangeType
from changelog_checker.parsers.uv_parser import UVParser


class TestUVParser:
    def setup_method(self):
        self.parser = UVParser()

    def test_get_package_manager_name(self):
        assert self.parser.get_package_manager_name() == "uv"

    def test_validate_output_valid(self):
        valid_outputs = [
            "Resolved 10 packages in 1.2s",
            "Prepared 5 packages",
            "Installed 3 packages",
            "Uninstalled 2 packages",
            "Some other text\nResolved packages in 0.5s\nMore text",
        ]
        for output in valid_outputs:
            assert self.parser.validate_output(output), f"Should validate: {output}"

    def test_validate_output_invalid(self):
        invalid_outputs = ["", "pip install requests", "npm install express", "Random text without UV indicators"]
        for output in invalid_outputs:
            assert not self.parser.validate_output(output), f"Should not validate: {output}"

    def test_parse_package_update(self):
        output = """
        - requests==2.28.0
        + requests==2.29.0
        """
        changes = self.parser.parse(output)
        assert len(changes) == 1
        change = changes[0]
        assert change.name == "requests"
        assert change.change_type == ChangeType.UPDATED
        assert change.old_version == "2.28.0"
        assert change.new_version == "2.29.0"

    def test_parse_package_addition(self):
        output = """
        + new-package==1.0.0
        """
        changes = self.parser.parse(output)
        assert len(changes) == 1
        change = changes[0]
        assert change.name == "new-package"
        assert change.change_type == ChangeType.ADDED
        assert change.old_version is None
        assert change.new_version == "1.0.0"

    def test_parse_package_removal(self):
        output = """
        - old-package==0.5.0
        """
        changes = self.parser.parse(output)
        assert len(changes) == 1
        change = changes[0]
        assert change.name == "old-package"
        assert change.change_type == ChangeType.REMOVED
        assert change.old_version == "0.5.0"
        assert change.new_version is None

    def test_parse_multiple_changes(self):
        output = """
        - requests==2.28.0
        + requests==2.29.0
        + new-package==1.0.0
        - old-package==0.5.0
        - beautifulsoup4==4.11.0
        + beautifulsoup4==4.12.0
        """
        changes = self.parser.parse(output)
        assert len(changes) == 4
        assert changes[0].name == "requests"
        assert changes[0].change_type == ChangeType.UPDATED
        assert changes[0].old_version == "2.28.0"
        assert changes[0].new_version == "2.29.0"
        assert changes[1].name == "new-package"
        assert changes[1].change_type == ChangeType.ADDED
        assert changes[1].new_version == "1.0.0"
        assert changes[2].name == "old-package"
        assert changes[2].change_type == ChangeType.REMOVED
        assert changes[2].old_version == "0.5.0"
        assert changes[3].name == "beautifulsoup4"
        assert changes[3].change_type == ChangeType.UPDATED
        assert changes[3].old_version == "4.11.0"
        assert changes[3].new_version == "4.12.0"

    def test_parse_empty_output(self):
        changes = self.parser.parse("")
        assert changes == []

    def test_parse_no_changes(self):
        output = """
        Resolved 10 packages in 1.2s
        No changes to dependencies
        """
        changes = self.parser.parse(output)
        assert changes == []

    def test_parse_complex_package_names(self):
        output = """
        - package-with-dashes==1.0.0
        + package-with-dashes==1.1.0
        + package_with_underscores==2.0.0
        - CamelCasePackage==0.5.0
        """
        changes = self.parser.parse(output)
        assert len(changes) == 3
        assert changes[0].name == "package-with-dashes"
        assert changes[0].change_type == ChangeType.UPDATED
        assert changes[1].name == "package_with_underscores"
        assert changes[1].change_type == ChangeType.ADDED
        assert changes[2].name == "CamelCasePackage"
        assert changes[2].change_type == ChangeType.REMOVED

    def test_parse_version_formats(self):
        output = """
        - package1==1.0.0
        + package1==1.0.1
        - package2==2.0.0a1
        + package2==2.0.0b1
        - package3==3.0.0.dev1
        + package3==3.0.0
        """
        changes = self.parser.parse(output)
        assert len(changes) == 3
        assert changes[0].old_version == "1.0.0"
        assert changes[0].new_version == "1.0.1"
        assert changes[1].old_version == "2.0.0a1"
        assert changes[1].new_version == "2.0.0b1"
        assert changes[2].old_version == "3.0.0.dev1"
        assert changes[2].new_version == "3.0.0"

    def test_parse_with_extra_whitespace(self):
        output = """

        - requests==2.28.0
        + requests==2.29.0

        + new-package==1.0.0

        """
        changes = self.parser.parse(output)
        assert len(changes) == 2
        assert changes[0].name == "requests"
        assert changes[0].change_type == ChangeType.UPDATED
        assert changes[1].name == "new-package"
        assert changes[1].change_type == ChangeType.ADDED
