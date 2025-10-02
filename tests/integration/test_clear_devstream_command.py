"""
Integration tests for /clear-devstream slash command file validation.

Tests validate the command file structure, frontmatter, MCP tool references,
and workflow instructions WITHOUT executing the command.

FASE 5.3 (Recovery) - Command Tests Only
"""

import pytest
from pathlib import Path
import re

# Path to command file
COMMAND_FILE = Path(__file__).parent.parent.parent / '.claude/commands/clear-devstream.md'


def test_command_file_exists_and_is_markdown():
    """
    Verify /clear-devstream command file exists and is valid Markdown.

    Validates:
    - File exists at correct location
    - File is readable
    - File has .md extension
    - File contains markdown content
    """
    # Assert file exists
    assert COMMAND_FILE.exists(), f"Command file not found: {COMMAND_FILE}"

    # Assert file is readable
    assert COMMAND_FILE.is_file(), f"Path is not a file: {COMMAND_FILE}"

    # Read content
    content = COMMAND_FILE.read_text()

    # Assert non-empty
    assert len(content) > 0, "Command file is empty"

    # Assert markdown extension
    assert COMMAND_FILE.suffix == '.md', f"Expected .md extension, got {COMMAND_FILE.suffix}"

    # Assert contains markdown elements (headers or lists)
    assert '#' in content or '-' in content or '*' in content, \
        "File does not appear to be Markdown (no headers or lists found)"


def test_command_frontmatter_valid_and_complete():
    """
    Verify YAML frontmatter is valid and contains required fields.

    Validates:
    - Frontmatter exists (--- delimiters)
    - description field present
    - description is non-empty
    - description matches expected content
    """
    content = COMMAND_FILE.read_text()

    # Extract frontmatter (between first two --- delimiters)
    frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    assert frontmatter_match, "No YAML frontmatter found (missing --- delimiters)"

    frontmatter = frontmatter_match.group(1)

    # Check for description field
    assert 'description:' in frontmatter, "Missing 'description' field in frontmatter"

    # Extract description value
    desc_match = re.search(r'description:\s*(.+)', frontmatter)
    assert desc_match, "description field has no value"

    description = desc_match.group(1).strip()

    # Assert non-empty
    assert len(description) > 0, "description field is empty"

    # Assert contains expected keywords
    assert 'clear' in description.lower() or 'devstream' in description.lower(), \
        f"description does not mention expected keywords: {description}"


def test_mcp_tool_references_correct():
    """
    Verify MCP tool references are correct and not deprecated.

    Validates:
    - Contains mcp__devstream__devstream_store_memory
    - Contains mcp__devstream__devstream_search_memory
    - No typos in tool name
    - No deprecated tool references
    """
    content = COMMAND_FILE.read_text()

    # Expected tool names
    expected_tools = [
        'mcp__devstream__devstream_store_memory',
        'mcp__devstream__devstream_search_memory'
    ]

    # Assert both expected tools reference exist
    for expected_tool in expected_tools:
        assert expected_tool in content, \
            f"Expected MCP tool '{expected_tool}' not found in command file"

    # Find all MCP tool references
    mcp_tools = re.findall(r'mcp__[a-z_]+__[a-z_]+', content)

    # Assert at least two tool references
    assert len(mcp_tools) >= 2, f"Expected at least 2 MCP tool references, found {len(mcp_tools)}"

    # Assert all tool references are valid (no typos)
    valid_tools = [
        'mcp__devstream__devstream_store_memory',
        'mcp__devstream__devstream_search_memory'
    ]
    for tool in mcp_tools:
        assert tool in valid_tools, f"Unknown or misspelled MCP tool: {tool}"

    # Assert no deprecated tools
    deprecated_tools = ['mcp__devstream__store_memory', 'mcp__devstream__search_memory']
    for deprecated in deprecated_tools:
        assert deprecated not in content, \
            f"Deprecated tool '{deprecated}' found - use 'mcp__devstream__devstream_*' instead"


def test_workflow_instructions_complete():
    """
    Verify workflow instructions are complete with all required steps.

    Validates:
    - Contains 5 sequential steps (### 1., ### 2., etc.)
    - Marker file path mentioned
    - Summary preview step present
    - All required actions documented
    """
    content = COMMAND_FILE.read_text()

    # Remove frontmatter to get body
    body = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)

    # Count numbered steps (### 1., ### 2., ### 3., etc.)
    numbered_steps = re.findall(r'^### \d+\.', body, re.MULTILINE)
    assert len(numbered_steps) >= 5, \
        f"Expected at least 5 numbered steps (### N.), found {len(numbered_steps)}"

    # Assert marker file path mentioned
    marker_path = '~/.claude/state/devstream_last_session.txt'
    assert marker_path in content, \
        f"Marker file path '{marker_path}' not mentioned in workflow"

    # Assert summary preview mentioned
    preview_keywords = ['500', 'preview', 'first 500', 'summary preview']
    has_preview = any(keyword in content.lower() for keyword in preview_keywords)
    assert has_preview, "Summary preview step (500 chars) not mentioned"

    # Assert required actions documented
    required_actions = [
        'generate',  # Generate summary
        'store',     # Store in memory
        'write',     # Write marker file
        'display',   # Display preview
        'clear'      # Clear conversation
    ]

    for action in required_actions:
        assert action.lower() in body.lower(), \
            f"Required action '{action}' not documented in workflow"

    # Assert MCP tool mentioned in workflow
    assert 'mcp__devstream' in body, \
        "MCP tool not referenced in workflow instructions"
