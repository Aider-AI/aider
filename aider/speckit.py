"""
SpecKit integration for aider.

Provides discovery and status reporting for SpecKit-style artifacts.
"""

from pathlib import Path
from typing import Any


class SpecKitDiscovery:
    """Discovers and reports on SpecKit artifacts in a repository."""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)

    def discover_artifacts(self) -> dict[str, Any]:
        """
        Discover SpecKit artifacts in the repository.

        Returns:
            Dict containing discovered artifacts and their status
        """
        artifacts = {
            "constitution": None,
            "spec_files": [],
            "spec_directories": [],
            "test_files": [],
            "summary": {},
        }

        # Look for constitution.md
        constitution_path = self.root_path / ".specify" / "memory" / "constitution.md"
        if constitution_path.exists() and constitution_path.is_file():
            artifacts["constitution"] = str(constitution_path.relative_to(self.root_path))

        # Look for specs/ directories and their contents
        specs_dir = self.root_path / "specs"
        spec_dirs = []
        spec_files = []

        if specs_dir.exists() and specs_dir.is_dir():
            for item in specs_dir.iterdir():
                if item.is_dir():
                    spec_dir_name = f"specs/{item.name}"
                    spec_dirs.append(spec_dir_name)

                    # Check for spec artifacts in this directory
                    for artifact in ["spec.md", "plan.md", "tasks.md"]:
                        artifact_path = item / artifact
                        if artifact_path.exists() and artifact_path.is_file():
                            spec_files.append(f"{spec_dir_name}/{artifact}")

        artifacts["spec_directories"] = sorted(spec_dirs)
        artifacts["spec_files"] = sorted(spec_files)

        # Look for test files that might be SpecKit related
        test_patterns = ["*test*.py", "test_*.py"]
        test_files = []
        for pattern in test_patterns:
            test_files.extend(self.root_path.rglob(pattern))

        # Filter out duplicates and convert to relative paths
        unique_tests = set()
        for f in test_files:
            if f.is_file():
                unique_tests.add(str(f.relative_to(self.root_path)))
        artifacts["test_files"] = sorted(list(unique_tests))

        # Calculate MTARP readiness
        mtarp_readiness = self._calculate_mtarp_readiness(artifacts)

        # Generate summary
        artifacts["summary"] = {
            "total_spec_files": len(artifacts["spec_files"]),
            "total_spec_directories": len(artifacts["spec_directories"]),
            "total_test_files": len(artifacts["test_files"]),
            "has_constitution": bool(artifacts["constitution"]),
            "complete_spec_directories": len(mtarp_readiness["complete_specs"]),
            "mtarp_ready": mtarp_readiness["ready"],
            "has_speckit_artifacts": bool(
                artifacts["constitution"]
                or artifacts["spec_files"]
                or artifacts["spec_directories"]
                or artifacts["test_files"]
            ),
        }

        return artifacts

    def _calculate_mtarp_readiness(self, artifacts: dict[str, Any]) -> dict[str, Any]:
        """Calculate MTARP readiness based on discovered artifacts."""
        has_constitution = bool(artifacts.get("constitution"))

        complete_specs = []
        for spec_dir in artifacts.get("spec_directories", []):
            has_spec = f"{spec_dir}/spec.md" in artifacts.get("spec_files", [])
            has_plan = f"{spec_dir}/plan.md" in artifacts.get("spec_files", [])
            has_tasks = f"{spec_dir}/tasks.md" in artifacts.get("spec_files", [])

            if has_spec and has_plan and has_tasks:
                complete_specs.append(spec_dir)

        return {
            "ready": has_constitution and len(complete_specs) >= 1,
            "constitution": has_constitution,
            "complete_specs": complete_specs,
            "total_specs": len(artifacts.get("spec_directories", [])),
        }

    def format_status_report(self, artifacts: dict[str, Any]) -> str:
        """Format the artifacts into a human-readable status report."""
        summary = artifacts["summary"]

        if not summary["has_speckit_artifacts"]:
            return "No SpecKit artifacts found in the repository."

        report = ["SpecKit Status Report", "=" * 20, ""]

        # Constitution status
        if artifacts["constitution"]:
            report.append(f"Constitution: ✓ Found ({artifacts['constitution']})")
        else:
            report.append("Constitution: ✗ Not found (.specify/memory/constitution.md)")
        report.append("")

        # Spec directories with completeness status
        if artifacts["spec_directories"]:
            report.append(f"Spec Directories ({len(artifacts['spec_directories'])}):")
            for spec_dir in artifacts["spec_directories"]:
                has_spec = f"{spec_dir}/spec.md" in artifacts["spec_files"]
                has_plan = f"{spec_dir}/plan.md" in artifacts["spec_files"]
                has_tasks = f"{spec_dir}/tasks.md" in artifacts["spec_files"]

                if has_spec and has_plan and has_tasks:
                    report.append(f"  - {spec_dir}/ ✓ Complete (spec.md, plan.md, tasks.md)")
                else:
                    missing = []
                    if not has_spec:
                        missing.append("spec.md")
                    if not has_plan:
                        missing.append("plan.md")
                    if not has_tasks:
                        missing.append("tasks.md")
                    report.append(f"  - {spec_dir}/ ⚠ Incomplete (missing {', '.join(missing)})")
            report.append("")

        # Test files
        if artifacts["test_files"]:
            report.append(f"Test Files ({len(artifacts['test_files'])}):")
            for test_file in artifacts["test_files"]:
                report.append(f"  - {test_file}")
            report.append("")

        # Summary with MTARP readiness
        report.append("Summary:")
        report.append(f"  Total spec files: {summary['total_spec_files']}")
        report.append(f"  Total spec directories: {summary['total_spec_directories']}")
        report.append(f"  Complete spec directories: {summary['complete_spec_directories']}")
        report.append(f"  Total test files: {summary['total_test_files']}")

        # MTARP readiness indicator
        if summary["mtarp_ready"]:
            report.append("  MTARP Ready: ✓ Yes (constitution + 1 complete spec)")
        else:
            reasons = []
            if not summary["has_constitution"]:
                reasons.append("missing constitution")
            if summary["complete_spec_directories"] == 0:
                reasons.append("no complete specs")
            report.append(f"  MTARP Ready: ✗ No ({', '.join(reasons)})")

        return "\n".join(report)
