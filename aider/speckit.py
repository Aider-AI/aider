"""
SpecKit integration for aider.

Provides discovery and status reporting for SpecKit-style artifacts.
"""

import os
from pathlib import Path
from typing import List, Dict, Any


class SpecKitDiscovery:
    """Discovers and reports on SpecKit artifacts in a repository."""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
    
    def discover_artifacts(self) -> Dict[str, Any]:
        """
        Discover SpecKit artifacts in the repository.
        
        Returns:
            Dict containing discovered artifacts and their status
        """
        artifacts = {
            "spec_files": [],
            "spec_directories": [],
            "test_files": [],
            "summary": {}
        }
        
        # Look for .spec files
        spec_files = list(self.root_path.rglob("*.spec"))
        artifacts["spec_files"] = [str(f.relative_to(self.root_path)) for f in spec_files]
        
        # Look for spec/ directories
        spec_dirs = []
        for item in self.root_path.rglob("spec"):
            if item.is_dir():
                spec_dirs.append(str(item.relative_to(self.root_path)))
        artifacts["spec_directories"] = spec_dirs
        
        # Look for test files that might be SpecKit related
        test_patterns = ["*test*.spec", "*_test.py", "test_*.py"]
        test_files = []
        for pattern in test_patterns:
            test_files.extend(self.root_path.rglob(pattern))
        
        # Filter out duplicates and convert to relative paths
        unique_tests = set()
        for f in test_files:
            if f.is_file():
                unique_tests.add(str(f.relative_to(self.root_path)))
        artifacts["test_files"] = sorted(list(unique_tests))
        
        # Generate summary
        artifacts["summary"] = {
            "total_spec_files": len(artifacts["spec_files"]),
            "total_spec_directories": len(artifacts["spec_directories"]),
            "total_test_files": len(artifacts["test_files"]),
            "has_speckit_artifacts": bool(
                artifacts["spec_files"] or 
                artifacts["spec_directories"] or 
                artifacts["test_files"]
            )
        }
        
        return artifacts
    
    def format_status_report(self, artifacts: Dict[str, Any]) -> str:
        """Format the artifacts into a human-readable status report."""
        summary = artifacts["summary"]
        
        if not summary["has_speckit_artifacts"]:
            return "No SpecKit artifacts found in the repository."
        
        report = ["SpecKit Status Report", "=" * 20, ""]
        
        if artifacts["spec_files"]:
            report.append(f"Spec Files ({len(artifacts['spec_files'])}):")
            for spec_file in artifacts["spec_files"]:
                report.append(f"  - {spec_file}")
            report.append("")
        
        if artifacts["spec_directories"]:
            report.append(f"Spec Directories ({len(artifacts['spec_directories'])}):")
            for spec_dir in artifacts["spec_directories"]:
                report.append(f"  - {spec_dir}/")
            report.append("")
        
        if artifacts["test_files"]:
            report.append(f"Test Files ({len(artifacts['test_files'])}):")
            for test_file in artifacts["test_files"]:
                report.append(f"  - {test_file}")
            report.append("")
        
        report.append("Summary:")
        report.append(f"  Total spec files: {summary['total_spec_files']}")
        report.append(f"  Total spec directories: {summary['total_spec_directories']}")
        report.append(f"  Total test files: {summary['total_test_files']}")
        
        return "\n".join(report)
