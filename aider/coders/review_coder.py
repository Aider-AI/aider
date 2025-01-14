from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path
import git

from .base_coder import Coder


@dataclass
class FileChange:
    filename: str
    old_content: Optional[str]
    new_content: str
    change_type: str  # 'added', 'modified', 'deleted'


class ReviewCoder(Coder):
    edit_format = "review"  # Unique identifier for this coder

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pr_number = None
        self.base_branch = None
        self.head_branch = None

    def get_pr_changes(self) -> List[FileChange]:
        """Get all file changes in the PR"""
        if not self.repo:
            self.io.tool_error("No git repository found")
            return []

        changes = []
        repo = git.Repo(self.repo.root)

        # Get the diff between branches
        diff = repo.git.diff(f"{self.base_branch}...{self.head_branch}", "--name-status")

        for line in diff.splitlines():
            self.io.debug(line)
            status, filename = line.split('\t')

            if status.startswith('A'):  # Added
                new_content = self.io.read_text(filename)
                changes.append(FileChange(
                    filename=filename,
                    old_content=None,
                    new_content=new_content,
                    change_type='added'
                ))
            elif status.startswith('M'):  # Modified
                old_content = repo.git.show(f"{self.base_branch}:{filename}")
                new_content = self.io.read_text(filename)
                changes.append(FileChange(
                    filename=filename,
                    old_content=old_content,
                    new_content=new_content,
                    change_type='modified'
                ))
            elif status.startswith('D'):  # Deleted
                old_content = repo.git.show(f"{self.base_branch}:{filename}")
                changes.append(FileChange(
                    filename=filename,
                    old_content=old_content,
                    new_content=None,
                    change_type='deleted'
                ))

        return changes

    def format_review_prompt(self, changes: List[FileChange]) -> str:
        """Format the changes into a prompt for the LLM"""
        prompt = "Please review the following changes and provide:\n"
        prompt += "1. A summary of each file's changes\n"
        prompt += "2. Potential issues or improvements\n"
        prompt += "3. Overall assessment of the changes\n\n"

        for change in changes:
            prompt += f"\nFile: {change.filename}\n"
            prompt += f"Change type: {change.change_type}\n"

            if change.change_type == 'modified':
                prompt += f"Previous content:\n{self.fence[0]}\n{change.old_content}\n{self.fence[1]}\n"
                prompt += f"New content:\n{self.fence[0]}\n{change.new_content}\n{self.fence[1]}\n"
            elif change.change_type == 'added':
                prompt += f"New content:\n{self.fence[0]}\n{change.new_content}\n{self.fence[1]}\n"
            elif change.change_type == 'deleted':
                prompt += f"Deleted content:\n{self.fence[0]}\n{change.old_content}\n{self.fence[1]}\n"

        return prompt

    def review_pr(self, pr_number: str, base: str, head: str):
        """Main method to review a PR"""
        self.pr_number = pr_number
        self.base_branch = base
        self.head_branch = head

        changes = self.get_pr_changes()
        if not changes:
            self.io.tool_error("No changes found in PR")
            return

        prompt = self.format_review_prompt(changes)

        # Send to LLM for review
        messages = self.format_messages()
        messages.append({"role": "user", "content": prompt})

        # Stream the review response
        for chunk in self.send_message(prompt):
            yield chunk

    def get_edits(self):
        """ReviewCoder doesn't make edits"""
        return []

    def apply_edits(self, edits):
        """ReviewCoder doesn't apply edits"""
        pass
