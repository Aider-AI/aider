import unittest
from unittest.mock import patch
import os
from aider.args import get_parser


class TestArgsBosEos(unittest.TestCase):
    def setUp(self):
        self.parser = get_parser([], None)

    def test_bos_eos_args(self):
        args = self.parser.parse_args(["--bos-token", "<BOS>", "--eos-token", "<EOS>"])
        self.assertEqual(args.bos_token, "<BOS>")
        self.assertEqual(args.eos_token, "<EOS>")

    def test_bos_eos_args_default(self):
        args = self.parser.parse_args([])
        self.assertIsNone(args.bos_token)
        self.assertIsNone(args.eos_token)

    @patch.dict(os.environ, {"AIDER_BOS_TOKEN": "<ENV_BOS>", "AIDER_EOS_TOKEN": "<ENV_EOS>"})
    def test_bos_eos_env_vars(self):
        args = self.parser.parse_args([])
        self.assertEqual(args.bos_token, "<ENV_BOS>")
        self.assertEqual(args.eos_token, "<ENV_EOS>")

    @patch.dict(os.environ, {"AIDER_BOS_TOKEN": "<ENV_BOS>", "AIDER_EOS_TOKEN": "<ENV_EOS>"})
    def test_bos_eos_args_override_env(self):
        args = self.parser.parse_args(["--bos-token", "<ARG_BOS>", "--eos-token", "<ARG_EOS>"])
        self.assertEqual(args.bos_token, "<ARG_BOS>")
        self.assertEqual(args.eos_token, "<ARG_EOS>")


if __name__ == "__main__":
    unittest.main()
