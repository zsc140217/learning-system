"""
MCP 2026 CLI Client - Main Entry Point
Interactive terminal client for Learning System
"""
import asyncio
import sys
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from loguru import logger

from mcp_client import MCPClient
from ui_renderer import UIRenderer


console = Console()


class LearningSystemCLI:
    """Main CLI application"""

    def __init__(self, server_url: str, debug: bool = False):
        self.server_url = server_url
        self.client = MCPClient(server_url)
        self.renderer = UIRenderer(self.client)
        self.session = PromptSession()

        # Configure logging
        logger.remove()
        if debug:
            logger.add(sys.stderr, level="DEBUG")
        else:
            logger.add(sys.stderr, level="INFO")

    async def start(self):
        """Start interactive CLI session"""
        # Health check
        console.print("[cyan]Connecting to MCP server...[/cyan]")
        is_healthy = await self.client.health_check()

        if not is_healthy:
            console.print(f"[red]Failed to connect to server at {self.server_url}[/red]")
            console.print("[yellow]Make sure the server is running:[/yellow]")
            console.print("  cd mcp-server")
            console.print("  python server.py")
            return

        console.print("[green]Connected successfully![/green]\n")

        # Show welcome banner
        self._show_banner()

        # Main loop
        while True:
            try:
                user_input = await self.session.prompt_async("You> ")

                if not user_input.strip():
                    continue

                # Handle special commands
                if user_input.lower() in ["/exit", "/quit", "exit", "quit"]:
                    console.print("[yellow]Goodbye![/yellow]")
                    break
                elif user_input.lower() == "/help":
                    self._show_help()
                    continue
                elif user_input.lower() == "/tools":
                    await self._list_tools()
                    continue

                # Parse command
                await self._handle_command(user_input)

            except KeyboardInterrupt:
                console.print("\n[yellow]Use /exit to quit[/yellow]")
            except EOFError:
                break
            except Exception as e:
                logger.exception("Unexpected error")
                console.print(f"[red]Error: {e}[/red]")

        await self.client.close()

    def _show_banner(self):
        """Show welcome banner"""
        banner = """
[bold cyan]Learning System CLI[/bold cyan]
MCP 2026 Protocol Client

Features:
  - MRTR (Multi-Round Trip Request) confirmation dialogs
  - Tasks with real-time progress tracking
  - MCP Apps UI templates

Type /help for available commands
        """
        console.print(Panel(banner, border_style="cyan"))

    def _show_help(self):
        """Show help information"""
        help_text = """
[bold]Available Commands:[/bold]

[cyan]/help[/cyan]       - Show this help message
[cyan]/tools[/cyan]      - List all available tools
[cyan]/exit[/cyan]       - Exit the CLI

[bold]Tool Commands:[/bold]

[cyan]analyze <text>[/cyan]           - Analyze session content
[cyan]search <query>[/cyan]           - Search knowledge graph
[cyan]create_project <name>[/cyan]    - Create new project
[cyan]get_review_plan[/cyan]          - Get review recommendations

[bold]Examples:[/bold]

analyze "Today I learned about MCP protocol"
search "FastAPI"
create_project "my-travel-system"
        """
        console.print(Panel(help_text, title="Help", border_style="cyan"))

    async def _list_tools(self):
        """List all available tools"""
        console.print("[cyan]Fetching available tools...[/cyan]")

        response = await self.client.list_tools()

        if response.is_success():
            tools = response.result.get("tools", [])

            if tools:
                console.print(f"\n[bold]Available Tools ({len(tools)}):[/bold]\n")
                for tool in tools:
                    name = tool.get("name", "unknown")
                    description = tool.get("description", "No description")
                    console.print(f"  [cyan]{name}[/cyan] - {description}")
            else:
                console.print("[yellow]No tools available[/yellow]")
        else:
            self.renderer.render_result(response)

    async def _handle_command(self, user_input: str):
        """
        Handle user command

        Supports:
        - analyze <text>
        - search <query>
        - create_project <name>
        - get_review_plan
        """
        parts = user_input.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Map commands to tools
        if command == "analyze":
            await self._call_tool("analyze_session", {"session_data": args})
        elif command == "search":
            await self._call_tool("search_knowledge", {"query": args})
        elif command == "create_project":
            await self._call_tool("create_project", {"project_name": args})
        elif command == "get_review_plan":
            await self._call_tool("get_review_plan", {})
        else:
            console.print(f"[yellow]Unknown command: {command}[/yellow]")
            console.print("Type /help for available commands")

    async def _call_tool(self, tool_name: str, params: dict):
        """Call a tool and handle the response"""
        console.print(f"[dim]Calling {tool_name}...[/dim]\n")

        response = await self.client.call_tool(tool_name, params)

        # Render result
        mrtr_data = self.renderer.render_result(response)

        # Handle MRTR confirmation
        if mrtr_data:
            user_input = mrtr_data["user_input"]
            request_state = mrtr_data["request_state"]

            console.print("\n[cyan]Sending confirmation...[/cyan]")

            confirm_response = await self.client.confirm_mrtr(
                tool_name,
                request_state,
                user_input
            )

            self.renderer.render_result(confirm_response)


@click.command()
@click.option(
    "--server",
    default="http://localhost:8080",
    help="MCP server URL"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging"
)
def main(server: str, debug: bool):
    """
    MCP 2026 CLI Client for Learning System

    Interactive terminal client supporting MRTR, Tasks, and MCP Apps.
    """
    cli = LearningSystemCLI(server, debug)
    asyncio.run(cli.start())


if __name__ == "__main__":
    main()
