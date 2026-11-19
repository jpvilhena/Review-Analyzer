"""The command dispatcher forwards arguments without executing unrelated commands."""
import unittest
from unittest.mock import patch
from review_analyzer.__main__ import main


class CommandTests(unittest.TestCase):
    @patch("review_analyzer.__main__.import_module")
    def test_subcommand_arguments_and_help_are_forwarded(self, load):
        for command in ("collect", "pilot", "review"):
            main([command, "--help"])
            load.assert_called_with(f"review_analyzer.cli.{command}")
            load.return_value.main.assert_called_with(["--help"])

    @patch("review_analyzer.__main__.import_module")
    @patch("argparse.ArgumentParser.print_help")
    def test_empty_command_shows_help_without_loading_a_service(self, help_text, load):
        main([])
        help_text.assert_called_once()
        load.assert_not_called()
