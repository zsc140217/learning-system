"""
Base agent class for all learning system agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ..bus.agent_bus import AgentBus


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the learning system.

    Each agent:
    - Has a unique ID
    - Connects to the event bus
    - Can subscribe to and emit events
    - Manages its own lifecycle (start/stop)
    """

    def __init__(self, agent_id: str, bus: AgentBus):
        """
        Initialize the agent

        Args:
            agent_id: Unique identifier for this agent
            bus: Event bus for inter-agent communication
        """
        self.agent_id = agent_id
        self.bus = bus
        self.is_running = False
        self._subscriptions: List[str] = []

    async def start(self) -> None:
        """Start the agent and mark it as running"""
        self.is_running = True

    async def stop(self) -> None:
        """Stop the agent and clean up subscriptions"""
        # Unsubscribe from all events
        for event_type in self._subscriptions:
            self.bus.unsubscribe(event_type, self._handle_event)
        self._subscriptions.clear()
        self.is_running = False

    async def subscribe(self, event_type: str) -> None:
        """
        Subscribe to a specific event type

        Args:
            event_type: The type of event to listen for
        """
        if event_type not in self._subscriptions:
            self.bus.subscribe(event_type, self._handle_event)
            self._subscriptions.append(event_type)

    async def emit(self, event: Dict[str, Any]) -> None:
        """
        Emit an event to the bus

        Args:
            event: Event dictionary with 'type' and other data
        """
        await self.bus.publish(event)

    async def _handle_event(self, event: Dict[str, Any]) -> None:
        """
        Internal event handler that delegates to process_event

        Args:
            event: Event dictionary from the bus
        """
        if self.is_running:
            await self.process_event(event)

    @abstractmethod
    async def process_event(self, event: Dict[str, Any]) -> None:
        """
        Process an incoming event (must be implemented by subclasses)

        Args:
            event: Event dictionary to process
        """
        pass
