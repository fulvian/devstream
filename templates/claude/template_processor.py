#!/usr/bin/env python3
"""
Template Processor for DevStream CLAUDE.md Inheritance
Context7-compliant template processing system.

This module provides template processing and generation capabilities
for project-specific configuration files, inspired by projen and chezmoi.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from template_variables import TemplateVariables


class TemplateProcessor:
    """
    Context7-compliant template processor.

    Inspired by projen's file generation and chezmoi's template system,
    provides intelligent template processing for project-specific files.
    """

    def __init__(self, project_root: str, framework_root: str):
        """
        Initialize template processor.

        Args:
            project_root: Path to project directory
            framework_root: Path to DevStream framework directory
        """
        self.project_root = Path(project_root)
        self.framework_root = Path(framework_root)
        self.template_dir = self.framework_root / 'templates' / 'claude'
        self.variables_processor = TemplateVariables(project_root, framework_root)

    def needs_update(self, source_file: Path, target_file: Path, version_file: Path) -> bool:
        """
        Check if template needs update based on modification times.

        Context7 pattern: Smart update detection to avoid unnecessary processing.

        Args:
            source_file: Source template file
            target_file: Target file to check
            version_file: Version tracking file

        Returns:
            True if update is needed
        """
        # Force update if target doesn't exist
        if not target_file.exists():
            return True

        # Update if source template is newer
        if source_file.exists() and source_file.stat().st_mtime > target_file.stat().st_mtime:
            return True

        # Update if framework CLAUDE.md is newer (base template changed)
        framework_claude = self.framework_root / 'CLAUDE.md'
        if framework_claude.exists() and framework_claude.stat().st_mtime > target_file.stat().st_mtime:
            return True

        return False

    def select_template(self, project_type: str, project_info: Dict[str, Any]) -> Optional[Path]:
        """
        Select appropriate template based on project type and characteristics.

        Context7 pattern: Intelligent template selection with fallbacks.

        Args:
            project_type: Detected project type
            project_info: Project-specific information

        Returns:
            Path to selected template file or None
        """
        template_preferences = []

        # Build template preferences based on project type and characteristics
        if project_type == 'python':
            if project_info.get('has_pyproject'):
                template_preferences.extend([
                    'claude-python-pyproject.md.tmpl',
                    'claude-python-project.md.tmpl',
                    'claude-python.md.tmpl'
                ])
            elif project_info.get('has_requirements'):
                template_preferences.extend([
                    'claude-python-requirements.md.tmpl',
                    'claude-python-project.md.tmpl',
                    'claude-python.md.tmpl'
                ])
            else:
                template_preferences.append('claude-python.md.tmpl')

        elif project_type == 'typescript':
            if project_info.get('has_nextjs'):
                template_preferences.extend([
                    'claude-typescript-nextjs.md.tmpl',
                    'claude-typescript-project.md.tmpl',
                    'claude-typescript.md.tmpl'
                ])
            else:
                template_preferences.extend([
                    'claude-typescript-project.md.tmpl',
                    'claude-typescript.md.tmpl'
                ])

        # Generic template as fallback
        template_preferences.extend([
            'claude-generic-project.md.tmpl',
            'claude-project.md.tmpl'
        ])

        # Find first existing template
        for template_name in template_preferences:
            template_path = self.template_dir / template_name
            if template_path.exists():
                return template_path

        return None

    def process_template_file(self, template_path: Path, variables: Dict[str, Any]) -> str:
        """
        Process a single template file with variable substitution.

        Context7 pattern: Safe template processing with error handling.

        Args:
            template_path: Path to template file
            variables: Template variables dictionary

        Returns:
            Processed template content
        """
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

            processed_content = self.variables_processor.substitute_template_variables(
                template_content, variables
            )

            return processed_content

        except Exception as e:
            print(f"Error processing template {template_path}: {e}", file=sys.stderr)
            raise

    def adapt_framework_claude_md(self, framework_claude: Path, variables: Dict[str, Any]) -> str:
        """
        Adapt framework CLAUDE.md for project use.

        Context7 pattern: Intelligent adaptation of framework configurations
        for project-specific contexts.

        Args:
            framework_claude: Path to framework CLAUDE.md
            variables: Template variables dictionary

        Returns:
            Adapted CLAUDE.md content
        """
        try:
            with open(framework_claude, 'r', encoding='utf-8') as f:
                content = f.read()

            # Add project-specific header
            project_header = f"""# CLAUDE.md - {{{{ project.name }}}} Project Rules

**Version**: {{{{ devstream.version }}}} | **Date**: {{{{ devstream.date }}}} | **Status**: Project-Specific Configuration

---

"""

            # Process the content through template substitution
            processed_content = self.variables_processor.substitute_template_variables(
                project_header + content, variables
            )

            return processed_content

        except Exception as e:
            print(f"Error adapting framework CLAUDE.md: {e}", file=sys.stderr)
            raise

    def generate_project_claude_md(self) -> str:
        """
        Generate project-specific CLAUDE.md content.

        Context7 pattern: Multi-layer template generation with intelligent selection.

        Returns:
            Generated CLAUDE.md content
        """
        variables = self.variables_processor.generate_variables()
        project_type = variables['project']['type']
        project_info = {k: v for k, v in variables['project'].items() if isinstance(v, (bool, str))}

        # Try to find and use a specific template
        template_path = self.select_template(project_type, project_info)

        if template_path:
            print(f"Using template: {template_path.name}")
            return self.process_template_file(template_path, variables)
        else:
            print("No specific template found, adapting framework CLAUDE.md")
            framework_claude = self.framework_root / 'CLAUDE.md'
            return self.adapt_framework_claude_md(framework_claude, variables)

    def update_project_claude_md(self) -> bool:
        """
        Update project CLAUDE.md if needed.

        Context7 pattern: Conditional updates with version tracking.

        Returns:
            True if CLAUDE.md was updated
        """
        project_claude = self.project_root / 'CLAUDE.md'
        version_file = self.project_root / '.claude_version'
        framework_claude = self.framework_root / 'CLAUDE.md'

        # Check if update is needed
        if not self.needs_update(framework_claude, project_claude, version_file):
            print("Project CLAUDE.md is up to date")
            return False

        try:
            # Generate new content and variables
            content = self.generate_project_claude_md()
            variables = self.variables_processor.generate_variables()

            # Write to project
            with open(project_claude, 'w', encoding='utf-8') as f:
                f.write(content)

            # Update version tracking
            with open(version_file, 'w') as f:
                f.write(f"{variables['devstream']['timestamp']}\n")

            print(f"✅ Updated project CLAUDE.md: {project_claude}")
            return True

        except Exception as e:
            print(f"Error updating project CLAUDE.md: {e}", file=sys.stderr)
            return False


def main():
    """
    Command line interface for template processing.

    Usage:
        python template_processor.py <project_root> <framework_root> [--force]
    """
    if len(sys.argv) < 3:
        print("Usage: python template_processor.py <project_root> <framework_root> [--force]")
        sys.exit(1)

    project_root = sys.argv[1]
    framework_root = sys.argv[2]
    force_update = '--force' in sys.argv

    processor = TemplateProcessor(project_root, framework_root)

    if force_update:
        # Force update regardless of modification times
        try:
            content = processor.generate_project_claude_md()
            project_claude = Path(project_root) / 'CLAUDE.md'
            with open(project_claude, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Force updated project CLAUDE.md: {project_claude}")
        except Exception as e:
            print(f"Error force updating project CLAUDE.md: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Conditional update
        updated = processor.update_project_claude_md()
        if updated:
            print("Project CLAUDE.md updated successfully")
        else:
            print("No update needed")


if __name__ == '__main__':
    main()