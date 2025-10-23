#!/usr/bin/env python3
"""
State Manager

Main state manager that coordinates between the parser and game state.
Handles state persistence, validation, and recovery.
"""

import json
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from pathlib import Path

from parser.events import GameEvent, EventType
from state.game_state import GameState, GameStatus
from state.player_state import PlayerState, PlayerType

logger = logging.getLogger(__name__)

class StateManager:
    """Main state manager for the MTGA Coach."""
    
    def __init__(self, persistence_file: Optional[str] = None):
        self.game_state = GameState()
        self.persistence_file = persistence_file or "data/game_state.json"
        self.state_change_callbacks: List[Callable] = []
        self.is_initialized = False
        
        # Set up state change callback
        self.game_state.add_state_change_callback(self._handle_state_change)
    
    def initialize(self) -> bool:
        """Initialize the state manager."""
        try:
            # Load persisted state if available
            if self._load_persisted_state():
                logger.info("Loaded persisted game state")
            else:
                logger.info("Starting with fresh game state")
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize state manager: {e}")
            return False
    
    def process_event(self, event: GameEvent) -> bool:
        """Process a game event and update state."""
        if not self.is_initialized:
            logger.warning("State manager not initialized")
            return False
        
        try:
            # Process the event
            success = self.game_state.process_event(event)
            
            if success:
                # Persist state if needed
                self._persist_state()
                
                # Log state change
                logger.debug(f"Processed event: {event.event_type}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing event {event.event_type}: {e}")
            return False
    
    def get_current_state(self) -> GameState:
        """Get the current game state."""
        return self.game_state
    
    def get_game_summary(self) -> Dict[str, Any]:
        """Get a summary of the current game state."""
        return self.game_state.get_game_summary()
    
    def is_game_active(self) -> bool:
        """Check if a game is currently active."""
        return self.game_state.is_game_active()
    
    def get_self_player(self) -> Optional[PlayerState]:
        """Get the self player state."""
        return self.game_state.get_self_player()
    
    def get_opponent_player(self) -> Optional[PlayerState]:
        """Get the opponent player state."""
        return self.game_state.get_opponent_player()
    
    def get_active_player(self) -> Optional[PlayerState]:
        """Get the currently active player."""
        return self.game_state.get_active_player()
    
    def add_state_change_callback(self, callback: Callable) -> bool:
        """Add a callback for state changes."""
        self.state_change_callbacks.append(callback)
        return True
    
    def remove_state_change_callback(self, callback: Callable) -> bool:
        """Remove a state change callback."""
        if callback in self.state_change_callbacks:
            self.state_change_callbacks.remove(callback)
            return True
        return False
    
    def _handle_state_change(self, change_type: str, data: Dict[str, Any]) -> None:
        """Handle state changes from the game state."""
        try:
            # Log state change
            logger.debug(f"State change: {change_type} - {data}")
            
            # Notify callbacks
            for callback in self.state_change_callbacks:
                try:
                    callback(change_type, data)
                except Exception as e:
                    logger.error(f"Error in state change callback: {e}")
            
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
    
    def _persist_state(self) -> bool:
        """Persist the current game state to file."""
        try:
            # Ensure directory exists
            Path(self.persistence_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Create persistence data
            persistence_data = {
                "timestamp": datetime.now().isoformat(),
                "game_state": self.game_state.dict(),
                "version": "1.0.0"
            }
            
            # Write to file
            with open(self.persistence_file, 'w', encoding='utf-8') as f:
                json.dump(persistence_data, f, indent=2, default=str)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to persist state: {e}")
            return False
    
    def _load_persisted_state(self) -> bool:
        """Load persisted game state from file."""
        try:
            if not Path(self.persistence_file).exists():
                return False
            
            with open(self.persistence_file, 'r', encoding='utf-8') as f:
                persistence_data = json.load(f)
            
            # Validate version
            if persistence_data.get("version") != "1.0.0":
                logger.warning("Persisted state version mismatch")
                return False
            
            # Load game state
            game_state_data = persistence_data.get("game_state", {})
            if game_state_data:
                self.game_state = GameState(**game_state_data)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to load persisted state: {e}")
            return False
    
    def clear_persisted_state(self) -> bool:
        """Clear persisted state file."""
        try:
            if Path(self.persistence_file).exists():
                Path(self.persistence_file).unlink()
                logger.info("Cleared persisted state")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear persisted state: {e}")
            return False
    
    def validate_state(self) -> List[str]:
        """Validate the current game state for consistency."""
        errors = []
        
        try:
            # Check basic game state
            if not self.game_state.game_id:
                errors.append("Game ID not set")
            
            if self.game_state.status not in [GameStatus.WAITING, GameStatus.STARTING, 
                                            GameStatus.ACTIVE, GameStatus.ENDED, GameStatus.PAUSED]:
                errors.append(f"Invalid game status: {self.game_state.status}")
            
            # Check players
            if not self.game_state.self_player:
                errors.append("Self player not initialized")
            elif self.game_state.self_player.life_total < 0:
                errors.append("Self player has negative life total")
            
            if not self.game_state.opponent_player:
                errors.append("Opponent player not initialized")
            elif self.game_state.opponent_player.life_total < 0:
                errors.append("Opponent player has negative life total")
            
            # Check hand sizes
            if self.game_state.self_player:
                hand_size = self.game_state.self_player.hand.size()
                if hand_size > self.game_state.self_player.max_hand_size:
                    errors.append(f"Self player hand size exceeds maximum: {hand_size}")
            
            if self.game_state.opponent_player:
                hand_size = self.game_state.opponent_player.hand.size()
                if hand_size > self.game_state.opponent_player.max_hand_size:
                    errors.append(f"Opponent player hand size exceeds maximum: {hand_size}")
            
            # Check for duplicate cards
            if self.game_state.self_player:
                self._check_duplicate_cards(self.game_state.self_player, "self", errors)
            
            if self.game_state.opponent_player:
                self._check_duplicate_cards(self.game_state.opponent_player, "opponent", errors)
            
        except Exception as e:
            errors.append(f"Error during state validation: {e}")
        
        return errors
    
    def _check_duplicate_cards(self, player: PlayerState, player_name: str, errors: List[str]) -> None:
        """Check for duplicate cards in a player's state."""
        # Check hand
        hand_instance_ids = [card.instance_id for card in player.hand.cards]
        if len(hand_instance_ids) != len(set(hand_instance_ids)):
            errors.append(f"{player_name} player has duplicate cards in hand")
        
        # Check battlefield
        battlefield_instance_ids = [card.instance_id for card in player.battlefield.get_all_cards()]
        if len(battlefield_instance_ids) != len(set(battlefield_instance_ids)):
            errors.append(f"{player_name} player has duplicate cards on battlefield")
        
        # Check graveyard
        graveyard_instance_ids = [card.instance_id for card in player.graveyard.cards]
        if len(graveyard_instance_ids) != len(set(graveyard_instance_ids)):
            errors.append(f"{player_name} player has duplicate cards in graveyard")
    
    def get_state_statistics(self) -> Dict[str, Any]:
        """Get statistics about the current state."""
        stats = {
            "game_id": self.game_state.game_id,
            "status": self.game_state.status,
            "turn_number": self.game_state.turn_number,
            "current_phase": self.game_state.current_phase,
            "active_player": self.game_state.active_player,
            "event_count": len(self.game_state.event_history),
            "state_change_count": len(self.game_state.state_changes),
            "validation_errors": len(self.validate_state())
        }
        
        if self.game_state.self_player:
            stats["self_player"] = {
                "life_total": self.game_state.self_player.life_total,
                "hand_size": self.game_state.self_player.hand.size(),
                "creature_count": self.game_state.self_player.get_creature_count(),
                "land_count": self.game_state.self_player.get_land_count(),
                "mana_pool": self.game_state.self_player.get_mana_summary()
            }
        
        if self.game_state.opponent_player:
            stats["opponent_player"] = {
                "life_total": self.game_state.opponent_player.life_total,
                "hand_size": self.game_state.opponent_player.hand.size(),
                "creature_count": self.game_state.opponent_player.get_creature_count(),
                "land_count": self.game_state.opponent_player.get_land_count(),
                "mana_pool": self.game_state.opponent_player.get_mana_summary()
            }
        
        return stats
