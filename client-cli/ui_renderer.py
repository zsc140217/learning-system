"""
CLI UI Components
Handles MRTR dialogs, Tasks progress, and UI templates
"""
import asyncio
from typing import Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.prompt import Confirm, Prompt
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

from mcp_client import MCPResponse, MCPClient


console = Console()


class UIRenderer:
    """Renders MCP protocol responses with rich terminal UI"""

    def __init__(self, client: MCPClient):
        self.client = client
        self.session = PromptSession()

    def render_result(self, response: MCPResponse) -> Optional[Dict[str, Any]]:
        """
        Render MCP response based on type

        Returns:
            User input for MRTR, or None
        """
        if not response.is_success():
            self._render_error(response)
            return None

        if response.is_mrtr():
            return self._render_mrtr(response)
        elif response.is_task():
            return self._render_task(response)
        elif response.is_ui_template():
            return self._render_ui_template(response)
        else:
            self._render_standard(response)
            return None

    def _render_error(self, response: MCPResponse):
        """Render error message"""
        error = response.error or {}
        console.print(
            Panel(
                f"[red]Error {error.get('code', 'Unknown')}:[/red] {error.get('message', 'Unknown error')}",
                title="Error",
                border_style="red"
            )
        )

    def _render_standard(self, response: MCPResponse):
        """Render standard result"""
        if isinstance(response.result, dict):
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Key")
            table.add_column("Value")

            for key, value in response.result.items():
                table.add_row(str(key), str(value))

            console.print(table)
        else:
            console.print(Panel(str(response.result), title="Result", border_style="green"))

    def _render_mrtr(self, response: MCPResponse) -> Dict[str, Any]:
        """
        Render MRTR confirmation dialog

        Returns:
            User input values
        """
        mrtr_data = response.get_mrtr_data()
        message = mrtr_data.get("message", "Confirmation required")
        fields = mrtr_data.get("fields", [])
        request_state = mrtr_data.get("requestState")

        # Show warning panel
        console.print(
            Panel(
                message,
                title="[yellow]Confirmation Required[/yellow]",
                border_style="yellow"
            )
        )

        # Collect user input
        user_input = {}

        for field in fields:
            field_name = field.get("name")
            field_type = field.get("type", "string")
            field_label = field.get("label", field_name)
            field_default = field.get("default")

            if field_type == "boolean":
                value = Confirm.ask(field_label, default=field_default if field_default is not None else False)
                user_input[field_name] = value
            else:
                value = Prompt.ask(field_label, default=str(field_default) if field_default else "")
                user_input[field_name] = value

        return {
            "user_input": user_input,
            "request_state": request_state
        }

    def _render_task(self, response: MCPResponse) -> None:
        """
        Render task with progress tracking

        Polls task status until completion
        """
        task_data = response.get_task_data()
        task_id = task_data.get("taskId")
        initial_message = task_data.get("message", "Processing...")

        console.print(f"\n[cyan]Task started:[/cyan] {task_id}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:

            task = progress.add_task(initial_message, total=100)

            # Poll task status
            while True:
                status_response = asyncio.run(self.client.get_task_status(task_id))

                if not status_response.is_success():
                    console.print("[red]Failed to get task status[/red]")
                    break

                task_status = status_response.get_task_data()
                status = task_status.get("status")
                task_progress = task_status.get("progress", 0) * 100
                message = task_status.get("message", initial_message)

                progress.update(task, completed=task_progress, description=message)

                if status in ["completed", "failed"]:
                    break

                asyncio.run(asyncio.sleep(1))

            # Show final result
            if status == "completed":
                console.print("[green]Task completed successfully![/green]")
                result = task_status.get("result")
                if result:
                    console.print(Panel(str(result), title="Result", border_style="green"))
            else:
                error_msg = task_status.get("error", "Unknown error")
                console.print(f"[red]Task failed:[/red] {error_msg}")

    def _render_ui_template(self, response: MCPResponse) -> None:
        """
        Render MCP Apps UI template (simplified for CLI)

        In CLI mode, we show the data in a formatted way
        In Web mode, this would render the HTML template
        """
        ui_data = response.get_ui_template_data()
        template_id = ui_data.get("templateId")
        template_data = ui_data.get("data", {})

        console.print(
            Panel(
                f"[cyan]Template ID:[/cyan] {template_id}",
                title="MCP App",
                border_style="cyan"
            )
        )

        # Render data as table
        if isinstance(template_data, dict):
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Key")
            table.add_column("Value")

            for key, value in template_data.items():
                if isinstance(value, (list, dict)):
                    value_str = f"{len(value)} items" if isinstance(value, list) else "Object"
                else:
                    value_str = str(value)
                table.add_row(str(key), value_str)

            console.print(table)
        else:
            console.print(str(template_data))

        console.print("\n[dim]Note: Full UI rendering available in Web client[/dim]")
