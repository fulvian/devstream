#!/usr/bin/env python3
"""
Template Variables Processor for DevStream CLAUDE.md Inheritance
Context7-compliant template system inspired by projen and chezmoi patterns.

This module provides template variable processing and substitution for
project-specific CLAUDE.md generation.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class TemplateVariables:
    """
    Context7-compliant template variables processor.

    Inspired by projen's project options and chezmoi's template system,
    provides intelligent variable detection and substitution for project-specific
    configuration files.
    """

    def __init__(self, project_root: str, framework_root: str):
        """
        Initialize template variables processor.

        Args:
            project_root: Path to project directory
            framework_root: Path to DevStream framework directory
        """
        self.project_root = Path(project_root)
        self.framework_root = Path(framework_root)

    def detect_project_type(self) -> str:
        """
        Detect project type based on file indicators.

        Context7 pattern: Multi-language project detection with priority ordering.

        Returns:
            Project type string (python, typescript, generic, etc.)
        """
        indicators = {
            'python': [
                'pyproject.toml',
                'requirements.txt',
                'setup.py',
                'Pipfile',
                'poetry.lock',
                'setup.cfg'
            ],
            'typescript': [
                'package.json',
                'tsconfig.json',
                'tsconfig.build.json',
                'next.config.js',
                'vite.config.ts'
            ],
            'rust': [
                'Cargo.toml',
                'Cargo.lock'
            ],
            'go': [
                'go.mod',
                'go.sum',
                'main.go'
            ],
            'javascript': [
                'package.json',
                'webpack.config.js',
                'rollup.config.js'
            ]
        }

        # Check indicators in priority order
        for project_type, files in indicators.items():
            for file_name in files:
                if (self.project_root / file_name).exists():
                    return project_type

        return 'generic'

    def get_python_info(self) -> Dict[str, Any]:
        """
        Get Python-specific project information.

        Context7 pattern: Safe detection with fallbacks for missing components.

        Returns:
            Dictionary with Python project information
        """
        python_info = {
            'version': 'unknown',
            'has_requirements': False,
            'has_pyproject': False,
            'has_setup_py': False,
            'venv_path': str(self.project_root / '.venv'),
            'python_executable': str(self.project_root / '.venv' / 'bin' / 'python'),
            'pip_executable': str(self.project_root / '.venv' / 'bin' / 'pip')
        }

        # Detect Python files
        if (self.project_root / 'requirements.txt').exists():
            python_info['has_requirements'] = True

        if (self.project_root / 'pyproject.toml').exists():
            python_info['has_pyproject'] = True

        if (self.project_root / 'setup.py').exists():
            python_info['has_setup_py'] = True

        # Try to get Python version from project venv
        venv_python = self.project_root / '.venv' / 'bin' / 'python'
        if venv_python.exists():
            try:
                import subprocess
                result = subprocess.run(
                    [str(venv_python), '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    python_info['version'] = result.stdout.strip().split()[-1]
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                pass

        return python_info

    def get_typescript_info(self) -> Dict[str, Any]:
        """
        Get TypeScript-specific project information.

        Returns:
            Dictionary with TypeScript project information
        """
        typescript_info = {
            'has_package_json': False,
            'has_tsconfig': False,
            'has_nextjs': False,
            'has_vite': False,
            'package_manager': 'npm'
        }

        if (self.project_root / 'package.json').exists():
            typescript_info['has_package_json'] = True

        if (self.project_root / 'tsconfig.json').exists():
            typescript_info['has_tsconfig'] = True

        if (self.project_root / 'next.config.js').exists():
            typescript_info['has_nextjs'] = True

        if (self.project_root / 'vite.config.ts').exists():
            typescript_info['has_vite'] = True

        # Detect package manager (yarn, pnpm, npm)
        if (self.project_root / 'yarn.lock').exists():
            typescript_info['package_manager'] = 'yarn'
        elif (self.project_root / 'pnpm-lock.yaml').exists():
            typescript_info['package_manager'] = 'pnpm'

        return typescript_info

    def generate_variables(self) -> Dict[str, Any]:
        """
        Generate complete template variables dictionary.

        Context7 pattern: Hierarchical variable organization with
        project-specific and framework-specific contexts.

        Returns:
            Complete template variables dictionary
        """
        project_type = self.detect_project_type()

        variables = {
            'project': {
                'name': self.project_root.name,
                'root': str(self.project_root),
                'type': project_type,
                'venv_path': str(self.project_root / '.venv'),
                'env_file': str(self.project_root / '.env.project'),
                'created_at': datetime.now().isoformat(),
                'created_date': datetime.now().strftime('%Y-%m-%d')
            },
            'framework': {
                'root': str(self.framework_root),
                'venv_path': str(self.framework_root / '.devstream'),
                'version': '2.2.0',
                'claude_md': str(self.framework_root / 'CLAUDE.md')
            },
            'devstream': {
                'version': '2.2.0',
                'mode': 'multi-project',
                'architecture': 'Direct DB Architecture',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
            }
        }

        # Add type-specific information
        if project_type == 'python':
            variables['project'].update(self.get_python_info())
        elif project_type == 'typescript':
            variables['project'].update(self.get_typescript_info())

        return variables

    def substitute_template_variables(self, template_content: str, variables: Dict[str, Any]) -> str:
        """
        Substitute template variables in content.

        Context7 pattern: Safe variable substitution with error handling.
        Inspired by chezmoi's Go template system.

        Args:
            template_content: Template content with variable placeholders
            variables: Variables dictionary for substitution

        Returns:
            Content with substituted variables
        """
        try:
            # Simple template substitution (can be enhanced with jinja2)
            result = template_content

            # Replace {{ variable.path }} with actual values
            def replace_var(match):
                var_path = match.group(1).strip()
                value = self._get_nested_value(variables, var_path)
                return str(value) if value is not None else match.group(0)

            import re
            # Pattern to match {{ variable.path }}
            pattern = r'\{\{\s*([^}]+)\s*\}\}'

            result = re.sub(pattern, replace_var, result)

            return result

        except Exception as e:
            print(f"Error substituting template variables: {e}", file=sys.stderr)
            return template_content

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        Get nested value from dictionary using dot notation.

        Args:
            data: Dictionary to search
            path: Dot-separated path (e.g., "project.name")

        Returns:
            Value at path or None if not found
        """
        keys = path.split('.')
        current = data

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return None


def main():
    """
    Command line interface for template variables processing.

    Usage:
        python template_variables.py <project_root> <framework_root> [output_file]
    """
    if len(sys.argv) < 3:
        print("Usage: python template_variables.py <project_root> <framework_root> [output_file]")
        sys.exit(1)

    project_root = sys.argv[1]
    framework_root = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None

    processor = TemplateVariables(project_root, framework_root)
    variables = processor.generate_variables()

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(variables, f, indent=2)
        print(f"Template variables written to: {output_file}")
    else:
        print(json.dumps(variables, indent=2))


if __name__ == '__main__':
    main()