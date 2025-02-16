from datetime import datetime

from .base_coder_auto_approve import AutoApproveCoder
from .base_coder import Coder
from .news_prompts import NewsPrompts
from bs4 import BeautifulSoup  # noqa: E402


class NewsCoder(AutoApproveCoder):
    """A coder that retrieves and summarizes latest game reviews from Metacritic."""

    edit_format = "news"
    gpt_prompts = NewsPrompts()

    # def get_edits(self, mode="update"):
    #     """Process and format the game review into markdown."""
    #     content = self.get_multi_response_content_in_progress()
    #     edits = self._process_reviews(content)
    #     return edits
        

    def _process_reviews(self, html_content):
        """Helper function to process HTML content and extract game reviews."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            game_entries = soup.find_all("h3")  # Find all h3 elements which contain game titles

            if not game_entries:
                self.io.tool_warning("No game reviews found on Metacritic.")
                return ["No game reviews found on Metacritic."]

            edits = []
            for game_entry in game_entries:
                try:
                    review = self._extract_review_data(game_entry)
                    if review:
                        markdown_content = self._format_review_markdown(review)
                        filename = f"game_reviews/{review['title'].replace(' ', '_')}_review.md"
                        edits.append((filename, "", markdown_content))
                    else:
                        continue

                except Exception as e:
                    self.io.tool_error(f"Error processing review: {str(e)}")
                    continue  # Continue to the next review

            return edits

        except Exception as e:
            self.io.tool_error(f"Error during review processing: {str(e)}")
            return [f"Error during review processing: {str(e)}"]

    def _extract_review_data(self, game_entry):
        """Extracts review data from a game entry."""
        try:
            title = game_entry.text.strip()
            url = game_entry.find_parent("a")["href"] if game_entry.find_parent("a") else ""
            # Assuming the Metascore is in the next sibling div with class "metascore_w"
            metascore_element = game_entry.find_parent("div", class_="clamp-summary-wrap").find_previous_sibling("div", class_="metascore_w") if game_entry.find_parent("div", class_="clamp-summary-wrap") else None
            score = metascore_element.text.strip() if metascore_element else "N/A"

            # Extract the summary from the next sibling div with class "summary"
            summary_element = game_entry.find_parent("div", class_="clamp-summary-wrap").find("div", class_="summary") if game_entry.find_parent("div", class_="clamp-summary-wrap") else None
            summary = summary_element.text.strip() if summary_element else "N/A"

            # Extract the platform and release date from the parent div with class "clamp-details"
            details_element = game_entry.find_parent("div", class_="clamp-summary-wrap").find("div", class_="clamp-details") if game_entry.find_parent("div", class_="clamp-summary-wrap") else None
            platform = details_element.find("span", class_="platform").text.strip() if details_element and details_element.find("span", class_="platform") else "N/A"
            release_date = details_element.find("span", class_="data").text.strip() if details_element and details_element.find("span", class_="data") else "N/A"

            return {
                "title": title,
                "score": score,
                "summary": summary,
                "release_date": release_date,
                "platform": platform,
                "url": url
            }
        except Exception as e:
            self.io.tool_error(f"Error extracting review  {str(e)}")
            return None

    def _format_review_markdown(self, review):
        """Formats the review data into markdown."""
        return f"""# {review['title']} Review Summary
**Platform:** {review['platform']}
**Release Date:** {review['release_date']}
**Metascore:** {review['score']}
**Summary:** {review['summary']}

## Key Details
- [View on Metacritic](https://www.metacritic.com{review['url']})
- Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

    # def apply_edits(self, edits):
    #     """Write the formatted review to a markdown file."""
    #     for path, _, content in edits:
    #         full_path = self.abs_root_path(path)
    #         self.io.write_text(full_path, content)
