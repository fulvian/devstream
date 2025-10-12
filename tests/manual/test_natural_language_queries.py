#!/usr/bin/env python3
"""
Real-world Natural Language Query Testing for DevStream Memory System

Tests the vector search and memory retrieval with realistic user queries
to validate the system works as expected in production scenarios.

Usage:
    python test_natural_language_queries.py
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from devstream.database.connection import ConnectionPool
from devstream.memory.storage import MemoryStorage
from devstream.memory.search import HybridSearchEngine
from devstream.memory.models import SearchQuery
from devstream.memory.processing import TextProcessor
from devstream.memory.embedding_generator import EmbeddingGenerator
from devstream.ollama.client import OllamaClient

console = Console()


class NaturalLanguageQueryTester:
    """
    Test DevStream memory system with natural language queries.

    Simulates real-world usage patterns to validate:
    - Vector search quality
    - Hybrid search (semantic + keyword) effectiveness
    - Response relevance
    - Performance under realistic conditions
    """

    def __init__(self, db_path: str = "data/devstream.db"):
        self.db_path = db_path
        self.pool = None
        self.storage = None
        self.search_engine = None
        self.embedding_generator = None

    async def initialize(self):
        """Initialize all components."""
        console.print("\n[bold cyan]🚀 Initializing DevStream Memory System...[/bold cyan]")

        self.pool = ConnectionPool(self.db_path)
        await self.pool.initialize()

        self.storage = MemoryStorage(self.pool)
        await self.storage.create_virtual_tables()

        self.ollama_client = OllamaClient(base_url="http://localhost:11434")
        self.processor = TextProcessor(self.ollama_client)
        self.embedding_generator = self.storage.embedding_generator
        self.search_engine = HybridSearchEngine(self.storage, self.processor)

        console.print("[green]✅ System initialized[/green]\n")

    async def close(self):
        """Clean up resources."""
        if self.pool:
            await self.pool.close()

    async def query_natural_language(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Execute a natural language query against the memory system.

        Args:
            query: Natural language query (e.g., "How do I fix vector search issues?")
            top_k: Number of results to return

        Returns:
            List of search results with relevance scores
        """
        console.print(f"\n[bold yellow]🔍 Query:[/bold yellow] {query}")
        console.print(f"[dim]Searching top {top_k} results...[/dim]")

        # Use hybrid search for best results
        search_query = SearchQuery(
            query_text=query,
            max_results=top_k,
            semantic_weight=0.6,
            keyword_weight=0.4
        )
        results = await self.search_engine.search(search_query)

        return results

    def display_results(self, results: List[Any], query: str):
        """Display search results in a formatted table."""
        if not results:
            console.print("[red]❌ No results found[/red]\n")
            return

        # Create results table
        table = Table(title=f"Search Results for: '{query}'", show_lines=True)
        table.add_column("Rank", justify="center", style="cyan", width=5)
        table.add_column("Relevance", justify="center", style="magenta", width=10)
        table.add_column("Content Type", justify="center", style="blue", width=15)
        table.add_column("Preview", style="white", width=60)
        table.add_column("Keywords", style="yellow", width=30)

        for i, result in enumerate(results, 1):
            memory = result.memory_entry
            score = result.combined_score

            # Format content preview (first 200 chars)
            content_preview = memory.content[:200] + "..." if len(memory.content) > 200 else memory.content

            # Format keywords
            keywords = ", ".join(memory.keywords[:5]) if memory.keywords else "N/A"

            # Color code relevance score
            if score > 0.7:
                score_style = "[green bold]"
            elif score > 0.5:
                score_style = "[yellow]"
            else:
                score_style = "[red]"

            table.add_row(
                str(i),
                f"{score_style}{score:.3f}[/]",
                memory.content_type.value,
                content_preview,
                keywords
            )

        console.print(table)
        console.print()

    async def run_test_scenarios(self):
        """
        Run predefined test scenarios with realistic queries.
        """
        console.print("\n[bold magenta]📋 Running Natural Language Test Scenarios[/bold magenta]\n")

        # Define realistic test queries
        test_scenarios = [
            {
                "category": "Technical Troubleshooting",
                "queries": [
                    "How do I fix vector search dimension mismatch errors?",
                    "What causes FTS table schema problems?",
                    "Why is my embedding generation failing?",
                ]
            },
            {
                "category": "Implementation Guidance",
                "queries": [
                    "How do I implement async database operations?",
                    "Best practices for sqlite-vec integration",
                    "How to optimize vector search performance?",
                ]
            },
            {
                "category": "Architecture & Design",
                "queries": [
                    "What is the DevStream memory architecture?",
                    "How does hybrid search combine semantic and keyword search?",
                    "Explain the Context7 integration pattern",
                ]
            },
            {
                "category": "Performance & Optimization",
                "queries": [
                    "How fast is vector search in DevStream?",
                    "Performance benchmarks for embedding generation",
                    "Optimize database query performance",
                ]
            },
            {
                "category": "General Knowledge",
                "queries": [
                    "What is DevStream?",
                    "How does semantic memory work?",
                    "Explain vector embeddings",
                ]
            }
        ]

        results_summary = []

        for scenario in test_scenarios:
            console.print(Panel(
                f"[bold cyan]Testing: {scenario['category']}[/bold cyan]",
                expand=False
            ))

            for query in scenario['queries']:
                results = await self.query_natural_language(query, top_k=3)
                self.display_results(results, query)

                # Track results for summary
                results_summary.append({
                    'category': scenario['category'],
                    'query': query,
                    'results_count': len(results),
                    'top_score': results[0].combined_score if results else 0.0
                })

                # Small delay between queries
                await asyncio.sleep(0.5)

        return results_summary

    async def interactive_mode(self):
        """
        Interactive mode for manual testing with custom queries.
        """
        console.print("\n[bold green]🎮 Interactive Query Mode[/bold green]")
        console.print("[dim]Enter natural language queries. Type 'exit' to quit.[/dim]\n")

        while True:
            try:
                # Get user input
                query = console.input("[bold cyan]Query:[/bold cyan] ").strip()

                if query.lower() in ['exit', 'quit', 'q']:
                    console.print("[yellow]👋 Exiting interactive mode[/yellow]")
                    break

                if not query:
                    continue

                # Execute query
                results = await self.query_natural_language(query, top_k=5)
                self.display_results(results, query)

                # Ask for feedback
                feedback = console.input("\n[dim]Relevant results? (y/n/skip):[/dim] ").strip().lower()
                if feedback == 'y':
                    console.print("[green]✅ Great![/green]")
                elif feedback == 'n':
                    console.print("[yellow]⚠️  Noted. This helps improve the system.[/yellow]")

                console.print()

            except KeyboardInterrupt:
                console.print("\n[yellow]👋 Exiting interactive mode[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]❌ Error: {e}[/red]")

    def display_summary(self, results_summary: List[Dict[str, Any]]):
        """Display test summary statistics."""
        console.print("\n[bold magenta]📊 Test Summary[/bold magenta]\n")

        # Calculate statistics
        total_queries = len(results_summary)
        queries_with_results = sum(1 for r in results_summary if r['results_count'] > 0)
        avg_top_score = sum(r['top_score'] for r in results_summary) / total_queries if total_queries > 0 else 0

        # High relevance queries (score > 0.7)
        high_relevance = sum(1 for r in results_summary if r['top_score'] > 0.7)

        # Create summary table
        table = Table(title="Test Results Summary", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white", justify="right")
        table.add_column("Status", style="magenta", justify="center")

        table.add_row(
            "Total Queries",
            str(total_queries),
            "✅"
        )
        table.add_row(
            "Queries with Results",
            f"{queries_with_results}/{total_queries}",
            "✅" if queries_with_results == total_queries else "⚠️"
        )
        table.add_row(
            "Average Top Score",
            f"{avg_top_score:.3f}",
            "✅" if avg_top_score > 0.6 else "⚠️"
        )
        table.add_row(
            "High Relevance Results (>0.7)",
            f"{high_relevance}/{total_queries}",
            "✅" if high_relevance > total_queries * 0.7 else "⚠️"
        )

        console.print(table)
        console.print()

        # Category breakdown
        console.print("[bold cyan]📋 Results by Category[/bold cyan]\n")

        categories = {}
        for result in results_summary:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'queries': 0, 'total_score': 0.0, 'with_results': 0}

            categories[cat]['queries'] += 1
            categories[cat]['total_score'] += result['top_score']
            if result['results_count'] > 0:
                categories[cat]['with_results'] += 1

        cat_table = Table(show_header=True)
        cat_table.add_column("Category", style="cyan")
        cat_table.add_column("Queries", justify="right", style="white")
        cat_table.add_column("Avg Score", justify="right", style="yellow")
        cat_table.add_column("Coverage", justify="right", style="green")

        for cat, stats in categories.items():
            avg_score = stats['total_score'] / stats['queries']
            coverage = f"{stats['with_results']}/{stats['queries']}"

            cat_table.add_row(
                cat,
                str(stats['queries']),
                f"{avg_score:.3f}",
                coverage
            )

        console.print(cat_table)
        console.print()


async def main():
    """Main test execution."""
    tester = NaturalLanguageQueryTester()

    try:
        # Initialize system
        await tester.initialize()

        # Show menu
        console.print(Panel(
            "[bold]DevStream Natural Language Query Tester[/bold]\n\n"
            "Choose test mode:\n"
            "  [cyan]1[/cyan] - Run predefined test scenarios (recommended)\n"
            "  [cyan]2[/cyan] - Interactive mode (custom queries)\n"
            "  [cyan]3[/cyan] - Both\n",
            title="🧪 Test Menu",
            expand=False
        ))

        choice = console.input("[bold]Select mode (1/2/3):[/bold] ").strip()

        if choice == '1':
            results_summary = await tester.run_test_scenarios()
            tester.display_summary(results_summary)

        elif choice == '2':
            await tester.interactive_mode()

        elif choice == '3':
            results_summary = await tester.run_test_scenarios()
            tester.display_summary(results_summary)
            console.print("\n" + "="*80 + "\n")
            await tester.interactive_mode()

        else:
            console.print("[red]Invalid choice. Exiting.[/red]")

        console.print("\n[bold green]✅ Testing completed![/bold green]\n")

    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        import traceback
        traceback.print_exc()

    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
