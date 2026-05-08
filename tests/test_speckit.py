import os
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from aider.commands import Commands
from aider.speckit import SpecKitDiscovery


class TestSpecKitDiscovery:
    def test_empty_repository(self):
        """Test discovery in an empty repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            
            assert artifacts["spec_files"] == []
            assert artifacts["spec_directories"] == []
            assert artifacts["test_files"] == []
            assert artifacts["summary"]["has_speckit_artifacts"] is False
    
    def test_discover_spec_files(self):
        """Test discovery of .spec files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create some .spec files
            (temp_path / "example.spec").touch()
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / "another.spec").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            
            assert len(artifacts["spec_files"]) == 2
            assert "example.spec" in artifacts["spec_files"]
            assert "subdir/another.spec" in artifacts["spec_files"] or "subdir\\another.spec" in artifacts["spec_files"]
            assert artifacts["summary"]["has_speckit_artifacts"] is True
    
    def test_discover_spec_directories(self):
        """Test discovery of spec/ directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create spec directories
            (temp_path / "spec").mkdir()
            (temp_path / "tests" / "spec").mkdir(parents=True)
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            
            assert len(artifacts["spec_directories"]) == 2
            assert "spec" in artifacts["spec_directories"]
            assert "tests/spec" in artifacts["spec_directories"] or "tests\\spec" in artifacts["spec_directories"]
            assert artifacts["summary"]["has_speckit_artifacts"] is True
    
    def test_discover_test_files(self):
        """Test discovery of test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "test_example.py").touch()
            (temp_path / "example_test.py").touch()
            (temp_path / "test.spec").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            
            assert len(artifacts["test_files"]) >= 2  # At least the .py test files
            assert "test_example.py" in artifacts["test_files"]
            assert "example_test.py" in artifacts["test_files"]
            assert artifacts["summary"]["has_speckit_artifacts"] is True
    
    def test_format_status_report_empty(self):
        """Test status report formatting for empty repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            report = discovery.format_status_report(artifacts)
            
            assert "No SpecKit artifacts found" in report
    
    def test_format_status_report_with_artifacts(self):
        """Test status report formatting with artifacts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create some artifacts
            (temp_path / "example.spec").touch()
            (temp_path / "spec").mkdir()
            (temp_path / "test_example.py").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            report = discovery.format_status_report(artifacts)
            
            assert "SpecKit Status Report" in report
            assert "Spec Files" in report
            assert "Spec Directories" in report
            assert "Test Files" in report
            assert "Summary:" in report


class TestSpecKitCommands:
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_io = Mock()
        self.mock_coder = Mock()
        self.mock_coder.root = None
        
        self.commands = Commands(
            io=self.mock_io,
            coder=self.mock_coder
        )
    
    def test_speckit_command_no_args(self):
        """Test /speckit command with no arguments."""
        self.commands.cmd_speckit("")
        
        self.mock_io.tool_error.assert_called_once()
        assert "Please specify a SpecKit command" in self.mock_io.tool_error.call_args[0][0]
    
    def test_speckit_command_unknown_subcommand(self):
        """Test /speckit command with unknown subcommand."""
        self.commands.cmd_speckit("unknown")
        
        self.mock_io.tool_error.assert_called_once()
        assert "Unknown SpecKit command: unknown" in self.mock_io.tool_error.call_args[0][0]
    
    def test_speckit_status_no_root(self):
        """Test /speckit status with no repository root."""
        self.mock_coder.root = None
        
        self.commands.cmd_speckit("status")
        
        self.mock_io.tool_error.assert_called_once()
        assert "No repository root found" in self.mock_io.tool_error.call_args[0][0]
    
    def test_speckit_status_with_root(self):
        """Test /speckit status with repository root."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_coder.root = temp_dir
            
            # Create a test artifact
            Path(temp_dir) / "example.spec"
            
            self.commands.cmd_speckit("status")
            
            # Should call tool_output with the status report
            self.mock_io.tool_output.assert_called_once()
            output = self.mock_io.tool_output.call_args[0][0]
            assert "SpecKit" in output or "No SpecKit artifacts found" in output
