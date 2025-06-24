#!/usr/bin/env python3
"""
Test suite for Discord bot benchmark improvements

This module tests the enhanced prompt templates, Discord bot-specific scenarios,
and improved error handling in the benchmarking system.
"""

import unittest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the modules we're testing
import prompts
from discord_bot_scenarios import DiscordBotTestScenarios, DiscordBotEdgeCases, DiscordBotMetrics
from discord_bot_benchmark import DiscordBotBenchmark


class TestEnhancedPrompts(unittest.TestCase):
    """Test the enhanced prompt templates and structure."""

    def test_instructions_addendum_structure(self):
        """Test that the enhanced instructions addendum has proper structure."""
        prompt = prompts.instructions_addendum
        
        # Check for key sections
        self.assertIn("TASK REQUIREMENTS:", prompt)
        self.assertIn("CONSTRAINTS:", prompt)
        self.assertIn("SUCCESS CRITERIA:", prompt)
        self.assertIn("IMPLEMENTATION APPROACH:", prompt)
        
        # Check for specific improvements
        self.assertIn("Preserve existing function/class names", prompt)
        self.assertIn("Use only standard libraries", prompt)
        self.assertIn("All unit tests must pass", prompt)
        self.assertIn("Error handling must be robust", prompt)

    def test_test_failures_structure(self):
        """Test that the enhanced test failures prompt has proper structure."""
        prompt = prompts.test_failures
        
        # Check for key sections
        self.assertIn("TESTING ERRORS DETECTED:", prompt)
        self.assertIn("ERROR ANALYSIS APPROACH:", prompt)
        self.assertIn("ERROR TYPES TO HANDLE:", prompt)
        self.assertIn("DEBUGGING STRATEGY:", prompt)
        self.assertIn("COMMON PITFALLS TO AVOID:", prompt)
        
        # Check for specific error types
        self.assertIn("Syntax Errors:", prompt)
        self.assertIn("Logic Errors:", prompt)
        self.assertIn("Runtime Errors:", prompt)
        self.assertIn("Test Timeouts:", prompt)

    def test_discord_bot_prompts_exist(self):
        """Test that Discord bot-specific prompts are defined."""
        self.assertTrue(hasattr(prompts, 'discord_bot_context'))
        self.assertTrue(hasattr(prompts, 'discord_command_parsing'))
        self.assertTrue(hasattr(prompts, 'discord_url_scraping'))
        self.assertTrue(hasattr(prompts, 'discord_message_handling'))
        self.assertTrue(hasattr(prompts, 'discord_summarization'))
        self.assertTrue(hasattr(prompts, 'discord_database_operations'))

    def test_discord_prompt_template_class(self):
        """Test the DiscordBotPromptTemplate class functionality."""
        template = prompts.DiscordBotPromptTemplate()
        
        # Test format_prompt method
        formatted = template.format_prompt(
            context="Test context",
            task="Test task",
            files="test.py",
            requirements="Test requirements",
            constraints="Test constraints",
            success_criteria="Test success criteria"
        )
        
        self.assertIn("CONTEXT: Test context", formatted)
        self.assertIn("TASK: Test task", formatted)
        self.assertIn("FILES TO MODIFY: test.py", formatted)
        self.assertIn("REQUIREMENTS:", formatted)
        self.assertIn("CONSTRAINTS:", formatted)
        self.assertIn("SUCCESS CRITERIA:", formatted)


class TestDiscordBotScenarios(unittest.TestCase):
    """Test the Discord bot-specific test scenarios."""

    def setUp(self):
        self.scenarios = DiscordBotTestScenarios()
        self.edge_cases = DiscordBotEdgeCases()
        self.metrics = DiscordBotMetrics()

    def test_message_handling_scenarios(self):
        """Test message handling test scenarios."""
        scenarios = self.scenarios.MESSAGE_HANDLING_SCENARIOS
        
        # Check that key scenarios exist
        self.assertIn("mention_parsing", scenarios)
        self.assertIn("message_length_handling", scenarios)
        self.assertIn("thread_management", scenarios)
        
        # Check mention parsing scenario structure
        mention_scenario = scenarios["mention_parsing"]
        self.assertIn("description", mention_scenario)
        self.assertIn("test_cases", mention_scenario)
        
        # Check test cases have proper structure
        test_cases = mention_scenario["test_cases"]
        self.assertTrue(len(test_cases) > 0)
        
        for test_case in test_cases:
            self.assertIn("input", test_case)
            self.assertIn("expected", test_case)

    def test_url_scraping_scenarios(self):
        """Test URL scraping test scenarios."""
        scenarios = self.scenarios.URL_SCRAPING_SCENARIOS
        
        self.assertIn("twitter_x_routing", scenarios)
        self.assertIn("scraping_error_handling", scenarios)
        
        # Check Twitter/X routing scenario
        twitter_scenario = scenarios["twitter_x_routing"]
        self.assertIn("description", twitter_scenario)
        self.assertIn("test_cases", twitter_scenario)

    def test_summarization_scenarios(self):
        """Test summarization test scenarios."""
        scenarios = self.scenarios.SUMMARIZATION_SCENARIOS
        
        self.assertIn("daily_summary", scenarios)
        self.assertIn("psalm_day_summary", scenarios)

    def test_database_scenarios(self):
        """Test database operation scenarios."""
        scenarios = self.scenarios.DATABASE_SCENARIOS
        
        self.assertIn("message_storage", scenarios)
        self.assertIn("data_cleanup", scenarios)

    def test_edge_cases_coverage(self):
        """Test that edge cases cover important scenarios."""
        # Check Discord limits
        self.assertTrue(len(self.edge_cases.DISCORD_LIMITS) > 0)
        self.assertIn("Messages exactly at 2000 character limit", self.edge_cases.DISCORD_LIMITS)
        
        # Check error conditions
        self.assertTrue(len(self.edge_cases.ERROR_CONDITIONS) > 0)
        self.assertIn("Network timeouts during Discord API calls", self.edge_cases.ERROR_CONDITIONS)
        
        # Check performance tests
        self.assertTrue(len(self.edge_cases.PERFORMANCE_TESTS) > 0)
        
        # Check security tests
        self.assertTrue(len(self.edge_cases.SECURITY_TESTS) > 0)
        self.assertIn("SQL injection prevention in database queries", self.edge_cases.SECURITY_TESTS)

    def test_metrics_categories(self):
        """Test that metrics cover all important categories."""
        # Check functional correctness metrics
        functional = self.metrics.FUNCTIONAL_CORRECTNESS
        self.assertIn("command_parsing_accuracy", functional)
        self.assertIn("response_relevance", functional)
        self.assertIn("thread_creation_success", functional)
        
        # Check performance metrics
        performance = self.metrics.PERFORMANCE_METRICS
        self.assertIn("response_time", performance)
        self.assertIn("memory_efficiency", performance)
        
        # Check reliability metrics
        reliability = self.metrics.RELIABILITY_METRICS
        self.assertIn("error_recovery_rate", reliability)
        self.assertIn("uptime_percentage", reliability)


class TestDiscordBotBenchmark(unittest.TestCase):
    """Test the Discord bot benchmark integration."""

    def setUp(self):
        self.test_output_dir = Path("test_output")
        self.benchmark = DiscordBotBenchmark(self.test_output_dir)

    def test_benchmark_initialization(self):
        """Test that the benchmark initializes correctly."""
        self.assertEqual(self.benchmark.output_dir, self.test_output_dir)
        self.assertIsInstance(self.benchmark.scenarios, DiscordBotTestScenarios)
        self.assertIsInstance(self.benchmark.edge_cases, DiscordBotEdgeCases)
        self.assertIsInstance(self.benchmark.metrics, DiscordBotMetrics)

    def test_generate_discord_bot_tests(self):
        """Test that Discord bot tests are generated correctly."""
        test_cases = self.benchmark.generate_discord_bot_tests()
        
        # Check that we have test cases
        self.assertTrue(len(test_cases) > 0)
        
        # Check test case structure
        for test_case in test_cases:
            self.assertIn("test_id", test_case)
            self.assertIn("category", test_case)
            self.assertIn("description", test_case)
            self.assertIn("expected_functionality", test_case)

    def test_message_handling_test_generation(self):
        """Test generation of message handling tests."""
        tests = self.benchmark._generate_message_handling_tests()
        
        self.assertTrue(len(tests) > 0)
        
        # Check for mention parsing test
        mention_test = next((t for t in tests if t["test_id"] == "discord_mention_parsing"), None)
        self.assertIsNotNone(mention_test)
        self.assertEqual(mention_test["category"], "message_handling")
        self.assertIn("expected_functionality", mention_test)

    def test_url_scraping_test_generation(self):
        """Test generation of URL scraping tests."""
        tests = self.benchmark._generate_url_scraping_tests()
        
        self.assertTrue(len(tests) > 0)
        
        # Check for URL scraping test
        scraping_test = next((t for t in tests if t["test_id"] == "discord_url_scraping"), None)
        self.assertIsNotNone(scraping_test)
        self.assertEqual(scraping_test["category"], "url_scraping")

    def test_edge_case_test_generation(self):
        """Test generation of edge case tests."""
        tests = self.benchmark._generate_edge_case_tests()
        
        self.assertTrue(len(tests) > 0)
        
        # Check that edge case tests are properly categorized
        categories = {test["test_id"] for test in tests}
        expected_categories = {
            "discord_edge_discord_limits",
            "discord_edge_error_conditions", 
            "discord_edge_performance_tests",
            "discord_edge_security_tests"
        }
        
        for expected in expected_categories:
            self.assertIn(expected, categories)


class TestPromptQualityImprovements(unittest.TestCase):
    """Test the overall quality improvements in prompts."""

    def test_prompt_clarity_and_structure(self):
        """Test that prompts have clear structure and specific guidance."""
        # Test instructions addendum
        instructions = prompts.instructions_addendum
        
        # Should have clear sections
        sections = ["TASK REQUIREMENTS:", "CONSTRAINTS:", "SUCCESS CRITERIA:", "IMPLEMENTATION APPROACH:"]
        for section in sections:
            self.assertIn(section, instructions)
        
        # Should provide specific guidance
        self.assertIn("Preserve existing function/class names", instructions)
        self.assertIn("All unit tests must pass", instructions)
        self.assertIn("Error handling must be robust", instructions)

    def test_error_handling_comprehensiveness(self):
        """Test that error handling prompts are comprehensive."""
        test_failures = prompts.test_failures
        
        # Should categorize error types
        error_types = ["Syntax Errors:", "Logic Errors:", "Runtime Errors:", "Test Timeouts:"]
        for error_type in error_types:
            self.assertIn(error_type, test_failures)
        
        # Should provide debugging strategy
        self.assertIn("DEBUGGING STRATEGY:", test_failures)
        self.assertIn("Focus on the specific failing test case", test_failures)
        
        # Should warn about common pitfalls
        self.assertIn("COMMON PITFALLS TO AVOID:", test_failures)
        self.assertIn("Don't change test files", test_failures)

    def test_discord_specific_guidance(self):
        """Test that Discord-specific prompts provide appropriate guidance."""
        # Test Discord bot context
        context = prompts.discord_bot_context
        self.assertIn("2000 characters", context)
        self.assertIn("Rate limiting", context)
        self.assertIn("@bot mentions", context)
        
        # Test command parsing requirements
        parsing = prompts.discord_command_parsing
        self.assertIn("@bot <command>", parsing)
        self.assertIn("mention extraction", parsing)
        
        # Test URL scraping requirements
        scraping = prompts.discord_url_scraping
        self.assertIn("X.com and Twitter.com", scraping)
        self.assertIn("Apify", scraping)
        self.assertIn("fallback mechanisms", scraping)


if __name__ == "__main__":
    unittest.main()
