instructions_addendum = """
####

TASK REQUIREMENTS:
Use the above instructions to modify the supplied files: {file_list}

CONSTRAINTS:
- Preserve existing function/class names (referenced by tests)
- Use only standard libraries (no external package installations)
- Maintain backward compatibility with existing interfaces
- Follow the existing code style and conventions
- Respect language-specific best practices and idioms

SUCCESS CRITERIA:
- All unit tests must pass
- Code must be syntactically correct and follow language conventions
- Implementation must handle edge cases mentioned in instructions
- Error handling must be robust and informative
- Performance should be reasonable for the given constraints

IMPLEMENTATION APPROACH:
1. Read and understand the full requirements carefully
2. Identify the specific changes needed in each file
3. Implement changes incrementally and systematically
4. Validate each change against requirements
5. Ensure proper error handling and edge cases are covered
6. Test the implementation logic before finalizing

If requirements are unclear or ambiguous, ask specific clarifying questions before implementing.
Focus on correctness first, then optimize for clarity and maintainability.
"""  # noqa: E501


test_failures = """
####

TESTING ERRORS DETECTED:
See the testing errors above. The tests are correct - do not modify them.

ERROR ANALYSIS APPROACH:
1. Categorize the error type (syntax, logic, runtime, timeout)
2. Identify the root cause in {file_list}
3. Determine the minimal fix required
4. Implement the fix while preserving existing functionality

ERROR TYPES TO HANDLE:
- Syntax Errors: Check indentation, brackets, quotes, semicolons
- Logic Errors: Verify algorithm correctness and edge cases
- Runtime Errors: Handle exceptions, null/undefined values, type mismatches
- Test Timeouts: Optimize performance and avoid infinite loops
- Import/Module Errors: Verify module availability and correct paths
- Type Errors: Ensure proper type handling and conversions

DEBUGGING STRATEGY:
- Focus on the specific failing test case first
- Trace through the code execution path systematically
- Identify where actual behavior differs from expected behavior
- Check for off-by-one errors, boundary conditions, and edge cases
- Verify input validation and error handling paths
- Make targeted fixes without over-engineering the solution

COMMON PITFALLS TO AVOID:
- Don't change test files or test expectations
- Don't introduce unnecessary complexity
- Don't break existing functionality while fixing errors
- Don't ignore error messages - they contain valuable debugging information

Fix the code in {file_list} to resolve ALL errors while maintaining code quality and readability.
"""


# Discord Bot-Specific Test Scenarios and Prompts

discord_bot_context = """
DISCORD BOT CONTEXT:
You are working on a Discord bot that handles mention-based commands, URL scraping,
message summarization, and database operations. The bot must respect Discord's API
constraints and provide reliable, user-friendly functionality.

KEY DISCORD CONSTRAINTS:
- Message length limit: 2000 characters
- Rate limiting: Respect Discord API rate limits
- Thread management: Create threads for responses when appropriate
- Mention parsing: Handle @bot mentions correctly
- Error recovery: Gracefully handle API failures and network issues
"""

discord_command_parsing = """
DISCORD COMMAND PARSING REQUIREMENTS:
The bot must correctly parse and handle mention-based commands:

COMMAND FORMATS TO SUPPORT:
- @bot <command> [arguments]
- Direct mentions with natural language requests
- Commands in threads vs main channels
- Commands with URLs for scraping

PARSING CONSTRAINTS:
- Extract command from mention text accurately
- Handle malformed or incomplete commands gracefully
- Validate command permissions and context
- Provide helpful error messages for invalid commands

IMPLEMENTATION REQUIREMENTS:
- Use regex or string parsing for mention extraction
- Implement command validation and sanitization
- Handle Unicode characters and special symbols
- Support case-insensitive command matching
"""

discord_url_scraping = """
DISCORD URL SCRAPING REQUIREMENTS:
The bot must handle URL scraping with proper routing and fallback mechanisms:

URL ROUTING LOGIC:
- Detect X.com and Twitter.com URLs in messages
- Route Twitter/X URLs to Apify scraping service
- Handle other URLs with appropriate scraping methods
- Implement fallback mechanisms when scraping fails

SCRAPING CONSTRAINTS:
- Respect rate limits of scraping services
- Handle network timeouts and API failures gracefully
- Validate scraped content quality and relevance
- Format scraped content for Discord message limits

ERROR HANDLING:
- Provide meaningful error messages when scraping fails
- Implement retry logic with exponential backoff
- Log scraping failures for debugging
- Fallback to alternative scraping methods when possible
"""

discord_message_handling = """
DISCORD MESSAGE HANDLING REQUIREMENTS:
The bot must handle Discord's message constraints and threading:

MESSAGE LENGTH MANAGEMENT:
- Split messages longer than 2000 characters intelligently
- Preserve formatting and readability when splitting
- Use code blocks and proper markdown formatting
- Handle Unicode characters and emojis correctly

THREAD MANAGEMENT:
- Create threads for bot responses when appropriate
- Post summaries and long content in threads
- Handle thread creation failures gracefully
- Manage thread permissions and visibility

RESPONSE FORMATTING:
- Use Discord markdown for better readability
- Include proper error formatting and user feedback
- Handle special characters and escape sequences
- Maintain consistent formatting across responses
"""

discord_summarization = """
DISCORD SUMMARIZATION REQUIREMENTS:
The bot must provide intelligent message summarization features:

SUMMARIZATION COMMANDS:
- /sum-day: Summarize messages from the last 24 hours
- /psalm-day: Load and summarize psalm-related messages
- Custom time range summarization
- Thread-specific summarization

SUMMARIZATION LOGIC:
- Filter relevant messages based on content quality
- Exclude bot messages and system notifications
- Prioritize messages with engagement (reactions, replies)
- Handle different message types (text, embeds, attachments)

CONTENT PROCESSING:
- Extract key topics and themes from messages
- Identify important decisions or announcements
- Preserve context and conversation flow
- Generate concise but comprehensive summaries

OUTPUT REQUIREMENTS:
- Format summaries for Discord readability
- Include message timestamps and authors when relevant
- Organize content by topics or chronological order
- Respect Discord's message length limits
"""

discord_database_operations = """
DISCORD DATABASE OPERATIONS REQUIREMENTS:
The bot must handle SQLite database operations for message and summary storage:

DATABASE SCHEMA REQUIREMENTS:
- Messages table: id, content, author, timestamp, channel_id, thread_id
- Summaries table: id, summary_text, date_range, channel_id, created_at
- Proper indexing for query performance
- Foreign key relationships where appropriate

CRUD OPERATIONS:
- Insert new messages with proper validation
- Update message metadata when needed
- Query messages by date range, channel, author
- Delete old messages based on retention policies

PERFORMANCE CONSIDERATIONS:
- Use prepared statements to prevent SQL injection
- Implement connection pooling for concurrent access
- Optimize queries with proper indexing
- Handle database locks and transaction management

ERROR HANDLING:
- Handle database connection failures gracefully
- Implement retry logic for transient failures
- Validate data before database operations
- Log database errors for debugging and monitoring
"""

# Standardized Prompt Templates

class DiscordBotPromptTemplate:
    """Standardized prompt template for Discord bot testing scenarios."""

    @staticmethod
    def format_prompt(context, task, files, requirements, constraints, success_criteria, error_handling="", implementation_notes=""):
        return f"""
CONTEXT: {context}

TASK: {task}

FILES TO MODIFY: {files}

REQUIREMENTS:
{requirements}

CONSTRAINTS:
{constraints}

SUCCESS CRITERIA:
{success_criteria}

{error_handling}

{implementation_notes}

Remember to follow Discord bot best practices and handle all edge cases appropriately.
"""
