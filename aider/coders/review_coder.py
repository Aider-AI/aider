from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path
import git
from github import Github
import os

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
        self.main_branch = None

    def get_pr_changes(self) -> List[FileChange]:
        """Get all file changes in the PR or between branches"""
        if not self.repo:
            self.io.tool_error("No git repository found")
            return []

        changes = []
        repo = git.Repo(self.repo.root)

        if self.pr_number:
            # Get GitHub token from environment
            github_token = os.getenv('GITHUB_TOKEN')

            try:
                # Get the GitHub repository
                g = Github(github_token) if github_token else Github()
                remote_url = repo.remotes.origin.url
                repo_name = remote_url.split('github.com/')[-1].replace('.git', '')

                self.io.tool_output(f"Fetching PR information for {repo_name} from {remote_url}")
                self.io.tool_output(f"PR number: {self.pr_number}")

                gh_repo = g.get_repo(repo_name)
                
                # Get the PR
                pr = gh_repo.get_pull(int(self.pr_number))
                
                # Update base and head branches from PR if not explicitly set
                if not self.base_branch:
                    self.base_branch = pr.base.ref
                if not self.main_branch:
                    self.main_branch = pr.head.ref

            except Exception as e:
                self.io.tool_error(f"Error fetching PR information: {str(e)}")
                return []

        self.io.tool_output(f"Reviewing {self.pr_number}, {self.base_branch} against {self.main_branch}")
        # Get the diff between branches
        diff = repo.git.diff(f"{self.base_branch}...{self.main_branch}", "--name-status")

        self.io.tool_output(f"Diff:\n{diff}")

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

    def review_pr(self, pr_number_or_branch: str, base_branch: str = None):
        """Main method to review a PR or branch changes"""
        if pr_number_or_branch.isdigit():
            # PR number provided
            self.pr_number = pr_number_or_branch
            self.base_branch = None
            self.main_branch = None
        else:
            # Branch comparison
            self.pr_number = None
            self.base_branch = base_branch
            self.main_branch = pr_number_or_branch

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
