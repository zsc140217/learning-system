"""
Test MCP Server Connection
Quick script to verify server is running
"""
import asyncio
import sys

try:
    from mcp_client import MCPClient
    from rich.console import Console
except ImportError:
    print("Error: Dependencies not installed")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

console = Console()


async def test_connection():
    """Test connection to MCP server"""
    client = MCPClient("http://localhost:8080")
    
    console.print("\n[cyan]Testing MCP Server Connection...[/cyan]\n")
    
    # Health check
    console.print("1. Health check... ", end="")
    is_healthy = await client.health_check()
    
    if is_healthy:
        console.print("[green]OK[/green]")
    else:
        console.print("[red]FAILED[/red]")
        console.print("\n[yellow]Server is not running. Please start it:[/yellow]")
        console.print("  cd ../mcp-server")
        console.print("  python server.py")
        await client.close()
        return
    
    # List tools
    console.print("2. List tools... ", end="")
    response = await client.list_tools()
    
    if response.is_success():
        console.print("[green]OK[/green]")
        tools = response.result.get("tools", [])
        console.print(f"\n[cyan]Found {len(tools)} tools:[/cyan]")
        for tool in tools[:5]:  # Show first 5
            name = tool.get("name", "unknown")
            console.print(f"  - {name}")
        if len(tools) > 5:
            console.print(f"  ... and {len(tools) - 5} more")
    else:
        console.print("[red]FAILED[/red]")
        console.print(f"Error: {response.error}")
    
    console.print("\n[green]Connection test completed![/green]\n")
    await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(test_connection())
    except KeyboardInterrupt:
        console.print("\n[yellow]Test cancelled[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
