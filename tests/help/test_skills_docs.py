import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml


class TestSkillsDocumentation(unittest.TestCase):
    """Coverage for systems/specs/04-architect-handoff-and-docs.md."""

    def test_skills_page_has_usage_navigation_metadata_and_required_guidance(self):
        path = Path(__file__).parents[2] / "aider/website/docs/usage/skills.md"
        content = path.read_text(encoding="utf-8")
        _, frontmatter, body = content.split("---", 2)
        metadata = yaml.safe_load(frontmatter)

        self.assertEqual(metadata["parent"], "Usage")
        self.assertEqual(metadata["nav_order"], 65)
        for required in (
            ".agents/skills/<directory>/SKILL.md",
            "name",
            "description",
            "code",
            "ask",
            "architect",
            "automatically",
            "temporary",
            "latency",
            "cost",
            "token",
            "usage",
            "warning",
            "fallback",
        ):
            with self.subTest(required=required):
                self.assertIn(required.lower(), body.lower())
        normalized = " ".join(body.lower().split())
        self.assertRegex(
            normalized,
            r"(directory name.{0,80}identifier|identifier.{0,80}directory name)",
        )

    def test_internal_markdown_links_resolve(self):
        path = Path(__file__).parents[2] / "aider/website/docs/usage/skills.md"
        site_root = Path(__file__).parents[2] / "aider/website"
        content = path.read_text(encoding="utf-8")
        body = content.split("---", 2)[2]
        body = re.sub(r"```.*?```|~~~.*?~~~", "", body, flags=re.DOTALL)
        inline_targets = re.findall(r"(?<!!)\[[^\]]+\]\(([^)\s]+)", body)
        reference_targets = re.findall(r"^\s*\[[^\]]+\]:\s*(\S+)", body, re.MULTILINE)

        for target in inline_targets + reference_targets:
            with self.subTest(target=target):
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc:
                    continue

                relative_path = unquote(parsed.path)
                if not relative_path:
                    destination = path
                elif relative_path.startswith("/"):
                    destination = site_root / relative_path.lstrip("/")
                    post = re.fullmatch(
                        r"/(\d{4})/(\d{2})/(\d{2})/(.+)\.html", relative_path
                    )
                    if post:
                        destination = site_root / "_posts" / (
                            f"{post[1]}-{post[2]}-{post[3]}-{post[4]}.md"
                        )
                else:
                    destination = path.parent / relative_path

                candidates = [destination]
                if destination.suffix == ".html":
                    candidates.append(destination.with_suffix(".md"))
                elif not destination.suffix:
                    candidates.append(destination.with_suffix(".md"))

                self.assertTrue(
                    any(candidate.resolve().exists() for candidate in candidates),
                    f"Missing link target: {target}",
                )
                markdown_target = next(
                    (
                        candidate
                        for candidate in candidates
                        if candidate.suffix == ".md" and candidate.resolve().exists()
                    ),
                    None,
                )
                if parsed.fragment and markdown_target:
                    self.assertIn(
                        unquote(parsed.fragment),
                        self.markdown_heading_ids(markdown_target),
                        f"Missing heading anchor in link target: {target}",
                    )

    def markdown_heading_ids(self, path):
        content = path.read_text(encoding="utf-8")
        heading_ids = set(re.findall(r"\{#([^}]+)\}", content))
        heading_counts = {}
        for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", content, re.MULTILINE):
            heading = re.sub(r"\{#[^}]+\}", "", heading)
            heading = re.sub(r"`([^`]*)`", r"\1", heading)
            heading = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading)
            slug = re.sub(r"[^\w -]", "", heading.lower(), flags=re.UNICODE)
            slug = re.sub(r"\s+", "-", slug.strip())
            count = heading_counts.get(slug, 0)
            heading_counts[slug] = count + 1
            heading_ids.add(slug if count == 0 else f"{slug}-{count}")
        return heading_ids


if __name__ == "__main__":
    unittest.main()
