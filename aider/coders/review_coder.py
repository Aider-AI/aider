from typing import List, Optional, NamedTuple
from dataclasses import dataclass
from pathlib import Path
import git
from github import Github
import os
import re
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, ProgressColumn

from .review_prompts import ReviewPrompts
from .base_coder import Coder
from aider.sendchat import send_completion


@dataclass
class FileChange:
    filename: str
    old_content: Optional[str]
    new_content: str
    change_type: str  # 'added', 'modified', 'deleted'

class ReviewComment(NamedTuple):
    file: str
    line: int
    type: str
    content: str


class ReviewCoder(Coder):
    edit_format = "review"  # Unique identifier for this coder
    gpt_prompts = ReviewPrompts()

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
                # Handle both HTTPS and SSH URLs
                if 'git@github.com:' in remote_url:
                    repo_name = remote_url.split('git@github.com:')[-1].replace('.git', '')
                else:
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

        self.io.tool_output(
            f"Reviewing {self.pr_number}, {self.base_branch} against {self.main_branch}")
        if self.pr_number:
            # Get changes from GitHub PR
            pr = gh_repo.get_pull(int(self.pr_number))
            files = pr.get_files()

            for file in files:
                if file.status == 'added':
                    changes.append(FileChange(
                        filename=file.filename,
                        old_content=None,
                        new_content=file.patch,
                        change_type='added'
                    ))
                elif file.status == 'modified':
                    changes.append(FileChange(
                        filename=file.filename,
                        old_content=file.raw_url,  # GitHub raw URL for the original content
                        new_content=file.patch,
                        change_type='modified'
                    ))
                elif file.status == 'removed':
                    changes.append(FileChange(
                        filename=file.filename,
                        old_content=file.raw_url,  # GitHub raw URL for the deleted content
                        new_content=None,
                        change_type='deleted'
                    ))
        else:
            # Get changes from local branches
            current_branch = repo.active_branch.name
            if self.base_branch != current_branch:
                self.io.tool_error(
                    f"Must be on base branch ({self.base_branch}) to review local changes")
                return []

            diff = repo.git.diff(f"{self.base_branch}...{self.main_branch}", "--name-status")
            self.io.tool_output(f"Diff:\n{diff}")

            for line in diff.splitlines():
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

    def parse_review(self, review_text: str) -> tuple[str, List[ReviewComment], str]:
        """Parse the complete review including summary, comments and assessment"""
        # Parse summary
        summary_match = re.search(r'<summary>(.*?)</summary>', review_text, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else ""

        # Parse comments
        pattern = r'<comment file="([^"]+)" line="(\d+)" type="([^"]+)">\s*(.*?)\s*</comment>'
        comments = []
        for match in re.finditer(pattern, review_text, re.DOTALL):
            file, line, type_, content = match.groups()
            comments.append(ReviewComment(
                file=file,
                line=int(line),
                type=type_,
                content=content.strip()
            ))

        # Parse assessment
        assessment_match = re.search(r'<assessment>(.*?)</assessment>', review_text, re.DOTALL)
        assessment = assessment_match.group(1).strip() if assessment_match else ""
        
        return summary, comments, assessment


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

        self.io.tool_output(f"Reviewing changes:")

        messages = [
            {"role": "system", "content": self.gpt_prompts.main_system},
            {"role": "user", "content": prompt}
        ]
        
        hash_obj, response = send_completion(
            self.main_model.name,
            messages,
            None,
            stream=True,
            temperature=0,  # Use 0 for more consistent reviews
            extra_params=self.main_model.extra_params,
        )

        # Collect the full response with progress indicator
        full_response = ""
        with self.io.create_progress_context("Analyzing changes...") as progress:
            review_task = progress.add_task("Analyzing changes...", total=None)
            
            for chunk in response:
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        full_response += content
                        
                        # Update progress description based on content
                        if "<summary>" in content:
                            progress.update(review_task, description="Generating summary...")
                        elif "<comment" in content:
                            progress.update(review_task, description="Adding review comments...")
                        elif "<assessment>" in content:
                            progress.update(review_task, description="Making final assessment...")
        
        # Parse and display complete review
        summary, comments, assessment = self.parse_review(full_response)
        self.io.display_review(summary, comments, assessment)

    def get_edits(self):
        """ReviewCoder doesn't make edits"""
        return []

    def apply_edits(self, edits):
        """ReviewCoder doesn't apply edits"""
        pass
