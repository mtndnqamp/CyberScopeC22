import unittest

from cyberscope.utils.environment import detect_environment


class EnvironmentTests(unittest.TestCase):
    def test_pi_model_has_precedence_over_virtualisation(self) -> None:
        info = detect_environment(
            model_text="Raspberry Pi 4 Model B",
            cpuinfo_text="",
            system="Linux",
            machine="aarch64",
            virtualisation="kvm",
        )
        self.assertEqual(info.kind, "RASPBERRY_PI")

    def test_virtualised_linux_is_vm(self) -> None:
        info = detect_environment("", "", "Linux", "x86_64", "oracle")
        self.assertEqual(info.kind, "LINUX_VM")

    def test_plain_linux_is_generic(self) -> None:
        info = detect_environment("", "processor: 0", "Linux", "x86_64", "none")
        self.assertEqual(info.kind, "GENERIC_LINUX")

    def test_hostname_is_not_an_input_to_detection(self) -> None:
        info = detect_environment("", "", "Plan9", "mips", "none")
        self.assertEqual(info.kind, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
