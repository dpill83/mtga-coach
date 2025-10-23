#!/usr/bin/env python3
"""
State Integration

Integration layer between the parser and state manager.
Handles event processing and state updates.
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from parser.events import GameEvent, EventType
from parser.event_bus import EventBusManager
from state.state_manager import StateManager
from state.game_state import GameState, GameStatus

logger = logging.getLogger(__name__)

class StateIntegration:
    """Integration layer between parser and state manager."""
    
    def __init__(self, websocket_port: int = 8765):
        self.state_manager = StateManager()
        self.event_bus = EventBusManager(port=websocket_port)
        self.is_running = False
        self.state_callbacks: list = []
        
        # Set up state change callback
        self.state_manager.add_state_change_callback(self._on_state_change)
    
    async def start(self) -> bool:
        """Start the state integration."""
        try:
            # Initialize state manager
            if not self.state_manager.initialize():
                logger.error("Failed to initialize state manager")
                return False
            
            # Start event bus
            await self.event_bus.start()
            logger.info("State integration started")
            
            self.is_running = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to start state integration: {e}")
            return False
    
    async def stop(self):
        """Stop the state integration."""
        try:
            self.is_running = False
            
            # Stop event bus
            await self.event_bus.stop()
            
            logger.info("State integration stopped")
            
        except Exception as e:
            logger.error(f"Error stopping state integration: {e}")
    
    async def process_event(self, event: GameEvent) -> bool:
        """Process a game event and update state."""
        if not self.is_running:
            logger.warning("State integration not running")
            return False
        
        try:
            # Process event in state manager
            success = self.state_manager.process_event(event)
            
            if success:
                # Broadcast state update via WebSocket
                await self._broadcast_state_update()
                
                # Log the event
                logger.debug(f"Processed event: {event.event_type}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing event {event.event_type}: {e}")
            return False
    
    def get_current_state(self) -> GameState:
        """Get the current game state."""
        return self.state_manager.get_current_state()
    
    def get_game_summary(self) -> Dict[str, Any]:
        """Get a summary of the current game state."""
        return self.state_manager.get_game_summary()
    
    def is_game_active(self) -> bool:
        """Check if a game is currently active."""
        return self.state_manager.is_game_active()
    
    def add_state_callback(self, callback: Callable) -> bool:
        """Add a callback for state changes."""
        self.state_callbacks.append(callback)
        return True
    
    def remove_state_callback(self, callback: Callable) -> bool:
        """Remove a state callback."""
        if callback in self.state_callbacks:
            self.state_callbacks.remove(callback)
            return True
        return False
    
    def _on_state_change(self, change_type: str, data: Dict[str, Any]) -> None:
        """Handle state changes."""
        try:
            # Log state change
            logger.debug(f"State change: {change_type}")
            
            # Notify callbacks
            for callback in self.state_callbacks:
                try:
                    callback(change_type, data)
                except Exception as e:
                    logger.error(f"Error in state callback: {e}")
            
            # Handle specific state changes
            if change_type == "game_started":
                self._on_game_started(data)
            elif change_type == "game_ended":
                self._on_game_ended(data)
            elif change_type == "card_played":
                self._on_card_played(data)
            elif change_type == "life_changed":
                self._on_life_changed(data)
            elif change_type == "phase_changed":
                self._on_phase_changed(data)
                
        except Exception as e:
            logger.error(f"Error handling state change: {e}")
    
    def _on_game_started(self, data: Dict[str, Any]) -> None:
        """Handle game started event."""
        logger.info(f"Game started: {data.get('game_id', 'unknown')}")
    
    def _on_game_ended(self, data: Dict[str, Any]) -> None:
        """Handle game ended event."""
        winner = data.get('winner')
        reason = data.get('reason', 'unknown')
        logger.info(f"Game ended - Winner: {winner}, Reason: {reason}")
    
    def _on_card_played(self, data: Dict[str, Any]) -> None:
        """Handle card played event."""
        player_id = data.get('player_id')
        card_name = data.get('card_name', 'unknown')
        logger.info(f"Player {player_id} played {card_name}")
    
    def _on_life_changed(self, data: Dict[str, Any]) -> None:
        """Handle life change event."""
        player_id = data.get('player_id')
        old_life = data.get('old_life')
        new_life = data.get('new_life')
        change = data.get('change', 0)
        
        if change > 0:
            logger.info(f"Player {player_id} gained {change} life ({old_life} -> {new_life})")
        elif change < 0:
            logger.info(f"Player {player_id} lost {abs(change)} life ({old_life} -> {new_life})")
    
    def _on_phase_changed(self, data: Dict[str, Any]) -> None:
        """Handle phase change event."""
        old_phase = data.get('old_phase')
        new_phase = data.get('new_phase')
        logger.info(f"Phase changed: {old_phase} -> {new_phase}")
    
    async def _broadcast_state_update(self) -> None:
        """Broadcast current state via WebSocket."""
        try:
            # Get current state summary
            state_summary = self.get_game_summary()
            
            # Create state update event
            state_event = {
                "type": "state_update",
                "timestamp": datetime.now().isoformat(),
                "game_state": state_summary
            }
            
            # Broadcast via event bus
            await self.event_bus.queue_event(state_event)
            
        except Exception as e:
            logger.error(f"Error broadcasting state update: {e}")
    
    def get_state_statistics(self) -> Dict[str, Any]:
        """Get statistics about the current state."""
        return self.state_manager.get_state_statistics()
    
    def validate_state(self) -> list:
        """Validate the current game state."""
        return self.state_manager.validate_state()
    
    def clear_persisted_state(self) -> bool:
        """Clear persisted state."""
        return self.state_manager.clear_persisted_state()

class StateIntegrationManager:
    """Manager for the state integration system."""
    
    def __init__(self, websocket_port: int = 8765):
        self.integration = StateIntegration(websocket_port)
        self.is_running = False
    
    async def start(self) -> bool:
        """Start the state integration manager."""
        try:
            if await self.integration.start():
                self.is_running = True
                logger.info("State integration manager started")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to start state integration manager: {e}")
            return False
    
    async def stop(self):
        """Stop the state integration manager."""
        try:
            await self.integration.stop()
            self.is_running = False
            logger.info("State integration manager stopped")
            
        except Exception as e:
            logger.error(f"Error stopping state integration manager: {e}")
    
    async def process_event(self, event: GameEvent) -> bool:
        """Process a game event."""
        return await self.integration.process_event(event)
    
    def get_current_state(self) -> GameState:
        """Get the current game state."""
        return self.integration.get_current_state()
    
    def get_game_summary(self) -> Dict[str, Any]:
        """Get a summary of the current game state."""
        return self.integration.get_game_summary()
    
    def is_game_active(self) -> bool:
        """Check if a game is currently active."""
        return self.integration.is_game_active()
    
    def add_state_callback(self, callback: Callable) -> bool:
        """Add a state callback."""
        return self.integration.add_state_callback(callback)
    
    def remove_state_callback(self, callback: Callable) -> bool:
        """Remove a state callback."""
        return self.integration.remove_state_callback(callback)
    
    def get_state_statistics(self) -> Dict[str, Any]:
        """Get state statistics."""
        return self.integration.get_state_statistics()
    
    def validate_state(self) -> list:
        """Validate the current state."""
        return self.integration.validate_state()
    
    def clear_persisted_state(self) -> bool:
        """Clear persisted state."""
        return self.integration.clear_persisted_state()
