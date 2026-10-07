import unittest

from cyberscope.integrity.comparison import diff_values


class ComparisonTests(unittest.TestCase):
    def test_nested_diff_reports_changed_added_and_removed_paths(self) -> None:
        differences = diff_values(
            {"network": {"hostname": "pi", "dns": ["1.1.1.1"]}, "old": 1},
            {"network": {"hostname": "lab", "dns": ["1.1.1.1"]}, "new": 2},
        )
        self.assertEqual(
            [(item.path, item.kind) for item in differences],
            [("network.hostname", "changed"), ("new", "added"), ("old", "removed")],
        )

    def test_list_is_reported_as_one_changed_parameter(self) -> None:
        differences = diff_values({"usb": ["trusted"]}, {"usb": ["trusted", "new"]})
        self.assertEqual(len(differences), 1)
        self.assertEqual(differences[0].path, "usb")
        self.assertEqual(differences[0].before, ["trusted"])

    def test_equal_values_have_no_differences(self) -> None:
        self.assertEqual(diff_values({"same": {"value": 1}}, {"same": {"value": 1}}), [])


if __name__ == "__main__":
    unittest.main()
