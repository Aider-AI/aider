import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Mock pyperclip before importing Commands to avoid dependency issues
with patch.dict('sys.modules', {'pyperclip': Mock()}):
    from aider.commands import Commands
from aider.speckit import SpecKitDiscovery


class TestSpecKitDiscovery:
    def test_empty_repository(self):
        """Test discovery in an empty repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            
            assert artifacts["constitution"] is None
            assert artifacts["spec_files"] == []
            assert artifacts["spec_directories"] == []
            assert artifacts["test_files"] == []
            assert artifacts["summary"]["has_speckit_artifacts"] is False
            assert artifacts["summary"]["mtarp_ready"] is False
    
    def test_discover_constitution(self):
        """Test discovery of constitution.md."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create constitution
            constitution_dir = temp_path / ".specify" / "memory"
            constitution_dir.mkdir(parents=True)
            (constitution_dir / "constitution.md").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            
            assert artifacts["constitution"] == ".specify/memory/constitution.md"
            assert artifacts["summary"]["has_constitution"] is True
            assert artifacts["summary"]["has_speckit_artifacts"] is True
    
    def test_discover_complete_spec_directory(self):
        """Test discovery of complete spec directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create complete spec directory
            spec_dir = temp_path / "specs" / "001-feature"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").touch()
            (spec_dir / "plan.md").touch()
            (spec_dir / "tasks.md").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            
            assert "specs/001-feature" in artifacts["spec_directories"]
            assert "specs/001-feature/spec.md" in artifacts["spec_files"]
            assert "specs/001-feature/plan.md" in artifacts["spec_files"]
            assert "specs/001-feature/tasks.md" in artifacts["spec_files"]
            assert artifacts["summary"]["complete_spec_directories"] == 1
            assert artifacts["summary"]["has_speckit_artifacts"] is True
    
    def test_discover_incomplete_spec_directory(self):
        """Test discovery of incomplete spec directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create incomplete spec directory (missing plan.md and tasks.md)
            spec_dir = temp_path / "specs" / "001-feature"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            
            assert "specs/001-feature" in artifacts["spec_directories"]
            assert "specs/001-feature/spec.md" in artifacts["spec_files"]
            assert "specs/001-feature/plan.md" not in artifacts["spec_files"]
            assert "specs/001-feature/tasks.md" not in artifacts["spec_files"]
            assert artifacts["summary"]["complete_spec_directories"] == 0
            assert artifacts["summary"]["has_speckit_artifacts"] is True
    
    def test_discover_multiple_spec_directories(self):
        """Test discovery of multiple spec directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create multiple spec directories
            spec_dir1 = temp_path / "specs" / "001-feature"
            spec_dir1.mkdir(parents=True)
            (spec_dir1 / "spec.md").touch()
            (spec_dir1 / "plan.md").touch()
            (spec_dir1 / "tasks.md").touch()
            
            spec_dir2 = temp_path / "specs" / "002-feature"
            spec_dir2.mkdir(parents=True)
            (spec_dir2 / "spec.md").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            
            assert len(artifacts["spec_directories"]) == 2
            assert "specs/001-feature" in artifacts["spec_directories"]
            assert "specs/002-feature" in artifacts["spec_directories"]
            assert artifacts["summary"]["complete_spec_directories"] == 1
            assert artifacts["summary"]["has_speckit_artifacts"] is True
    
    def test_discover_test_files(self):
        """Test discovery of test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "test_example.py").touch()
            (temp_path / "example_test.py").touch()
            (temp_path / "tests").mkdir()
            (temp_path / "tests" / "test_integration.py").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            
            assert len(artifacts["test_files"]) == 3
            assert "test_example.py" in artifacts["test_files"]
            assert "example_test.py" in artifacts["test_files"]
            assert "tests/test_integration.py" in artifacts["test_files"] or "tests\\test_integration.py" in artifacts["test_files"]
            assert artifacts["summary"]["has_speckit_artifacts"] is True
    
    def test_mtarp_readiness_calculation(self):
        """Test MTARP readiness calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create constitution
            constitution_dir = temp_path / ".specify" / "memory"
            constitution_dir.mkdir(parents=True)
            (constitution_dir / "constitution.md").touch()
            
            # Create complete spec directory
            spec_dir = temp_path / "specs" / "001-feature"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").touch()
            (spec_dir / "plan.md").touch()
            (spec_dir / "tasks.md").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            
            assert artifacts["summary"]["mtarp_ready"] is True
            assert artifacts["summary"]["has_constitution"] is True
            assert artifacts["summary"]["complete_spec_directories"] == 1
    
    def test_mtarp_readiness_missing_constitution(self):
        """Test MTARP readiness when constitution is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create complete spec directory but no constitution
            spec_dir = temp_path / "specs" / "001-feature"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").touch()
            (spec_dir / "plan.md").touch()
            (spec_dir / "tasks.md").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            
            assert artifacts["summary"]["mtarp_ready"] is False
            assert artifacts["summary"]["has_constitution"] is False
            assert artifacts["summary"]["complete_spec_directories"] == 1
    
    def test_mtarp_readiness_no_complete_specs(self):
        """Test MTARP readiness when no complete specs exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create constitution
            constitution_dir = temp_path / ".specify" / "memory"
            constitution_dir.mkdir(parents=True)
            (constitution_dir / "constitution.md").touch()
            
            # Create incomplete spec directory
            spec_dir = temp_path / "specs" / "001-feature"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            
            assert artifacts["summary"]["mtarp_ready"] is False
            assert artifacts["summary"]["has_constitution"] is True
            assert artifacts["summary"]["complete_spec_directories"] == 0
    
    def test_format_status_report_empty(self):
        """Test status report formatting for empty repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            report = discovery.format_status_report(artifacts)
            
            assert "No SpecKit artifacts found" in report
    
    def test_format_status_report_with_constitution(self):
        """Test status report formatting with constitution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create constitution
            constitution_dir = temp_path / ".specify" / "memory"
            constitution_dir.mkdir(parents=True)
            (constitution_dir / "constitution.md").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            report = discovery.format_status_report(artifacts)
            
            assert "SpecKit Status Report" in report
            assert "Constitution: ✓ Found" in report
            assert "MTARP Ready: ✗ No" in report
    
    def test_format_status_report_complete_spec(self):
        """Test status report formatting with complete spec."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create complete spec directory
            spec_dir = temp_path / "specs" / "001-feature"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").touch()
            (spec_dir / "plan.md").touch()
            (spec_dir / "tasks.md").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            report = discovery.format_status_report(artifacts)
            
            assert "SpecKit Status Report" in report
            assert "✓ Complete (spec.md, plan.md, tasks.md)" in report
            assert "Complete spec directories: 1" in report
    
    def test_format_status_report_incomplete_spec(self):
        """Test status report formatting with incomplete spec."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create incomplete spec directory
            spec_dir = temp_path / "specs" / "001-feature"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            report = discovery.format_status_report(artifacts)
            
            assert "SpecKit Status Report" in report
            assert "⚠ Incomplete (missing plan.md, tasks.md)" in report
            assert "Complete spec directories: 0" in report
    
    def test_format_status_report_mtarp_ready(self):
        """Test status report formatting when MTARP ready."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create constitution
            constitution_dir = temp_path / ".specify" / "memory"
            constitution_dir.mkdir(parents=True)
            (constitution_dir / "constitution.md").touch()
            
            # Create complete spec directory
            spec_dir = temp_path / "specs" / "001-feature"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").touch()
            (spec_dir / "plan.md").touch()
            (spec_dir / "tasks.md").touch()
            
            discovery = SpecKitDiscovery(temp_dir)
            artifacts = discovery.discover_artifacts()
            report = discovery.format_status_report(artifacts)
            
            assert "MTARP Ready: ✓ Yes (constitution + 1 complete spec)" in report


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
            
            self.commands.cmd_speckit("status")
            
            # Should call tool_output with the status report
            self.mock_io.tool_output.assert_called_once()
            output = self.mock_io.tool_output.call_args[0][0]
            assert "SpecKit" in output or "No SpecKit artifacts found" in output
    
    def test_speckit_status_with_constitution_and_complete_spec(self):
        """Test /speckit status with constitution and complete spec."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.mock_coder.root = temp_dir
            
            # Create constitution
            constitution_dir = temp_path / ".specify" / "memory"
            constitution_dir.mkdir(parents=True)
            (constitution_dir / "constitution.md").touch()
            
            # Create complete spec directory
            spec_dir = temp_path / "specs" / "001-feature"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").touch()
            (spec_dir / "plan.md").touch()
            (spec_dir / "tasks.md").touch()
            
            self.commands.cmd_speckit("status")
            
            # Should call tool_output with the status report
            self.mock_io.tool_output.assert_called_once()
            output = self.mock_io.tool_output.call_args[0][0]
            assert "Constitution: ✓ Found" in output
            assert "✓ Complete" in output
            assert "MTARP Ready: ✓ Yes" in output
