from changelog_checker.models import ChangeType
from changelog_checker.parsers.pip_parser import PipParser


class TestPipParser:
    def setup_method(self):
        self.parser = PipParser()

    def test_get_package_manager_name(self):
        assert self.parser.get_package_manager_name() == "pip"

    def test_validate_output_valid(self):
        valid_outputs = ["", "Package            Version         Latest          Type"]
        for valid_output in valid_outputs:
            assert self.parser.validate_output(valid_output), f"Should validate: {valid_output}"

    def test_validate_output_invalid(self):
        invalid_outputs = ["Random text without pip header"]
        for invalid_output in invalid_outputs:
            assert not self.parser.validate_output(invalid_output), f"Should not validate: {invalid_output}"

    def test_parse_package_update(self):
        output = """
Package            Version         Latest          Type
------------------ --------------- --------------- -----
requests           2.32.4          2.32.5          wheel
"""
        changes = self.parser.parse(output)
        assert len(changes) == 1
        change = changes[0]
        assert change.name == "requests"
        assert change.change_type == ChangeType.UPDATED
        assert change.old_version == "2.32.4"
        assert change.new_version == "2.32.5"

    def test_parse_multiple_changes(self):
        output = """
Package            Version         Latest          Type
------------------ --------------- --------------- -----
certifi            2025.7.9        2025.8.3        wheel
charset-normalizer 3.4.2           3.4.3           wheel
coverage           7.9.2           7.10.4          wheel
distlib            0.3.9           0.4.0           wheel
"""
        changes = self.parser.parse(output)
        assert len(changes) == 4
        assert changes[0].name == "certifi"
        assert changes[0].change_type == ChangeType.UPDATED
        assert changes[0].old_version == "2025.7.9"
        assert changes[0].new_version == "2025.8.3"
        assert changes[1].name == "charset-normalizer"
        assert changes[1].change_type == ChangeType.UPDATED
        assert changes[1].old_version == "3.4.2"
        assert changes[1].new_version == "3.4.3"
        assert changes[2].name == "coverage"
        assert changes[2].change_type == ChangeType.UPDATED
        assert changes[2].old_version == "7.9.2"
        assert changes[2].new_version == "7.10.4"
        assert changes[3].name == "distlib"
        assert changes[3].change_type == ChangeType.UPDATED
        assert changes[3].old_version == "0.3.9"
        assert changes[3].new_version == "0.4.0"

    def test_parse_empty_output(self):
        changes = self.parser.parse("")
        assert changes == []

    def test_parse_no_changes(self):
        output = ""
        changes = self.parser.parse(output)
        assert changes == []
