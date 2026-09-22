import sys
import unittest

from cyberscope.utils.commands import CommandRunner


class CommandRunnerTests(unittest.TestCase):
    def test_runner_rejects_string_command(self) -> None:
        with self.assertRaises(TypeError):
            CommandRunner().run("hostname")  # type: ignore[arg-type]

    def test_runner_captures_real_argument_array_output(self) -> None:
        result = CommandRunner().run([sys.executable, "-c", "print('safe')"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "safe")
        self.assertFalse(result.timed_out)

    def test_runner_structures_missing_command(self) -> None:
        result = CommandRunner().run(["cyberscope-command-that-does-not-exist"])
        self.assertIsNone(result.returncode)
        self.assertIn("not found", result.error.lower())


if __name__ == "__main__":
    unittest.main()
