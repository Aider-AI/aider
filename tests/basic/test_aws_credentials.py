import os
from unittest.mock import patch

from aider.models import Model


class TestAWSCredentials:
    """Test AWS credential handling, especially AWS_PROFILE."""

    def test_bedrock_model_with_aws_profile(self):
        """Test that Bedrock models accept AWS_PROFILE as valid authentication."""
        # Save original environment
        original_env = os.environ.copy()

        try:
            # Set up test environment
            os.environ.clear()
            os.environ["AWS_PROFILE"] = "test-profile"

            # Create a model instance
            with patch("aider.llm.litellm.validate_environment") as mock_validate:
                # Mock the litellm validate_environment to return missing AWS keys
                mock_validate.return_value = {
                    "missing_keys": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
                    "keys_in_environment": False,
                }

                # Test with a bedrock model
                model = Model("bedrock/anthropic.claude-v2")

                # Check that the AWS keys were removed from missing_keys
                assert "AWS_ACCESS_KEY_ID" not in model.missing_keys
                assert "AWS_SECRET_ACCESS_KEY" not in model.missing_keys
                # With no missing keys, validation should pass
                assert model.keys_in_environment

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

    def test_us_anthropic_model_with_aws_profile(self):
        """Test that us.anthropic models accept AWS_PROFILE as valid authentication."""
        # Save original environment
        original_env = os.environ.copy()

        try:
            # Set up test environment
            os.environ.clear()
            os.environ["AWS_PROFILE"] = "test-profile"

            # Create a model instance
            with patch("aider.llm.litellm.validate_environment") as mock_validate:
                # Mock the litellm validate_environment to return missing AWS keys
                mock_validate.return_value = {
                    "missing_keys": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
                    "keys_in_environment": False,
                }

                # Test with a us.anthropic model
                model = Model("us.anthropic.claude-3-7-sonnet-20250219-v1:0")

                # Check that the AWS keys were removed from missing_keys
                assert "AWS_ACCESS_KEY_ID" not in model.missing_keys
                assert "AWS_SECRET_ACCESS_KEY" not in model.missing_keys
                # With no missing keys, validation should pass
                assert model.keys_in_environment

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

    def test_non_bedrock_model_with_aws_profile(self):
        """Test that non-Bedrock models do not accept AWS_PROFILE for AWS credentials."""
        # Save original environment
        original_env = os.environ.copy()

        try:
            # Set up test environment
            os.environ.clear()
            os.environ["AWS_PROFILE"] = "test-profile"

            # Create a model instance
            with patch("aider.llm.litellm.validate_environment") as mock_validate:
                # Mock the litellm validate_environment to return missing AWS keys
                mock_validate.return_value = {
                    "missing_keys": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
                    "keys_in_environment": False,
                }

                # Test with a non-Bedrock model
                model = Model("gpt-4")

                # For non-Bedrock models, AWS credential keys should remain in missing_keys
                assert "AWS_ACCESS_KEY_ID" in model.missing_keys
                assert "AWS_SECRET_ACCESS_KEY" in model.missing_keys
                # With missing keys, validation should fail
                assert not model.keys_in_environment

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

    def test_bedrock_model_without_aws_profile(self):
        """Test that Bedrock models require credentials when AWS_PROFILE is not set."""
        # Save original environment
        original_env = os.environ.copy()

        try:
            # Set up test environment
            os.environ.clear()

            # Create a model instance
            with patch("aider.llm.litellm.validate_environment") as mock_validate:
                # Mock the litellm validate_environment to return missing AWS keys
                mock_validate.return_value = {
                    "missing_keys": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
                    "keys_in_environment": False,
                }

                # Test with a bedrock model without AWS_PROFILE
                model = Model("bedrock/anthropic.claude-v2")

                # Without AWS_PROFILE, AWS credential keys should remain in missing_keys
                assert "AWS_ACCESS_KEY_ID" in model.missing_keys
                assert "AWS_SECRET_ACCESS_KEY" in model.missing_keys
                # With missing keys, validation should fail
                assert not model.keys_in_environment

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

    def test_mixed_missing_keys_with_aws_profile(self):
        """Test that only AWS credential keys are affected by AWS_PROFILE."""
        # Save original environment
        original_env = os.environ.copy()

        try:
            # Set up test environment
            os.environ.clear()
            os.environ["AWS_PROFILE"] = "test-profile"

            # Create a model instance
            with patch("aider.llm.litellm.validate_environment") as mock_validate:
                # Mock the litellm validate_environment to return missing AWS keys and another key
                mock_validate.return_value = {
                    "missing_keys": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "ANOTHER_KEY"],
                    "keys_in_environment": False,
                }

                # Test with a bedrock model
                model = Model("bedrock/anthropic.claude-v2")

                # AWS credential keys should be removed from missing_keys
                assert "AWS_ACCESS_KEY_ID" not in model.missing_keys
                assert "AWS_SECRET_ACCESS_KEY" not in model.missing_keys
                # But other keys should remain
                assert "ANOTHER_KEY" in model.missing_keys
                # With other missing keys, validation should still fail
                assert not model.keys_in_environment

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
