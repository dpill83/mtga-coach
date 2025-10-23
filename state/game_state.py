#!/usr/bin/env python3
"""
Game State Manager

Main game state manager that tracks the overall game state,
including both players, current phase, and game rules.
"""

from typing import Dict, List, Optional, Set, Callable
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from parser.events import GameEvent, EventType, Phase, ZoneType, CardInfo
from state.player_state import PlayerState, PlayerType, ManaPool

class GameStatus(str, Enum):
    """Game status."""
    WAITING = "waiting"
    STARTING = "starting"
    ACTIVE = "active"
    ENDED = "ended"
    PAUSED = "paused"

class GameState(BaseModel):
    """Complete game state."""
    game_id: Optional[str] = None
    status: GameStatus = GameStatus.WAITING
    turn_number: int = 0
    current_phase: Optional[Phase] = None
    current_step: Optional[str] = None
    active_player: Optional[int] = None
    priority_player: Optional[int] = None
    
    # Players
    self_player: Optional[PlayerState] = None
    opponent_player: Optional[PlayerState] = None
    
    # Game rules and state
    starting_life: int = 20
    max_hand_size: int = 7
    mulligan_count: int = 0
    
    # Stack and priority
    stack: List[CardInfo] = Field(default_factory=list)
    priority_passed: bool = False
    
    # Game history
    event_history: List[GameEvent] = Field(default_factory=list)
    state_changes: List[Dict] = Field(default_factory=list)
    
    # Callbacks for state changes
    state_change_callbacks: List[Callable] = Field(default_factory=list)
    
    def initialize_game(self, self_player_id: int, opponent_player_id: int, 
                      starting_life: int = 20) -> bool:
        """Initialize a new game."""
        try:
            self.game_id = f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.status = GameStatus.STARTING
            self.turn_number = 0
            self.starting_life = starting_life
            
            # Create player states
            self.self_player = PlayerState(
                player_id=self_player_id,
                player_type=PlayerType.SELF,
                life_total=starting_life
            )
            
            self.opponent_player = PlayerState(
                player_id=opponent_player_id,
                player_type=PlayerType.OPPONENT,
                life_total=starting_life
            )
            
            self.status = GameStatus.ACTIVE
            self._notify_state_change("game_initialized", {
                "game_id": self.game_id,
                "starting_life": starting_life
            })
            
            return True
            
        except Exception as e:
            print(f"Error initializing game: {e}")
            return False
    
    def get_player(self, player_id: int) -> Optional[PlayerState]:
        """Get player state by ID."""
        if self.self_player and self.self_player.player_id == player_id:
            return self.self_player
        elif self.opponent_player and self.opponent_player.player_id == player_id:
            return self.opponent_player
        return None
    
    def get_self_player(self) -> Optional[PlayerState]:
        """Get self player state."""
        return self.self_player
    
    def get_opponent_player(self) -> Optional[PlayerState]:
        """Get opponent player state."""
        return self.opponent_player
    
    def get_active_player(self) -> Optional[PlayerState]:
        """Get currently active player."""
        if self.active_player is not None:
            return self.get_player(self.active_player)
        return None
    
    def set_active_player(self, player_id: int) -> bool:
        """Set the active player."""
        player = self.get_player(player_id)
        if player:
            self.active_player = player_id
            self._notify_state_change("active_player_changed", {
                "player_id": player_id,
                "turn_number": self.turn_number
            })
            return True
        return False
    
    def set_phase(self, phase: Phase, step: Optional[str] = None) -> bool:
        """Set the current phase and step."""
        old_phase = self.current_phase
        old_step = self.current_step
        
        self.current_phase = phase
        self.current_step = step
        
        self._notify_state_change("phase_changed", {
            "old_phase": old_phase,
            "new_phase": phase,
            "old_step": old_step,
            "new_step": step,
            "turn_number": self.turn_number
        })
        
        return True
    
    def next_turn(self) -> bool:
        """Advance to next turn."""
        self.turn_number += 1
        
        # Reset turn flags for both players
        if self.self_player:
            self.self_player.reset_turn_flags()
        if self.opponent_player:
            self.opponent_player.reset_turn_flags()
        
        self._notify_state_change("turn_advanced", {
            "turn_number": self.turn_number,
            "active_player": self.active_player
        })
        
        return True
    
    def process_event(self, event: GameEvent) -> bool:
        """Process a game event and update state."""
        try:
            # Add to event history
            self.event_history.append(event)
            
            # Process based on event type
            if event.event_type == EventType.GAME_START:
                return self._process_game_start(event)
            elif event.event_type == EventType.GAME_END:
                return self._process_game_end(event)
            elif event.event_type == EventType.DRAW_CARD:
                return self._process_draw_card(event)
            elif event.event_type == EventType.PLAY_CARD:
                return self._process_play_card(event)
            elif event.event_type == EventType.LIFE_CHANGE:
                return self._process_life_change(event)
            elif event.event_type == EventType.PHASE_CHANGE:
                return self._process_phase_change(event)
            elif event.event_type == EventType.TURN_CHANGE:
                return self._process_turn_change(event)
            else:
                # Handle other event types
                self._notify_state_change("event_processed", {
                    "event_type": event.event_type,
                    "timestamp": event.timestamp
                })
                return True
                
        except Exception as e:
            print(f"Error processing event {event.event_type}: {e}")
            return False
    
    def _process_game_start(self, event: GameEvent) -> bool:
        """Process game start event."""
        if hasattr(event, 'player_life') and hasattr(event, 'opponent_life'):
            if self.self_player:
                self.self_player.life_total = event.player_life
            if self.opponent_player:
                self.opponent_player.life_total = event.opponent_life
        
        self.status = GameStatus.ACTIVE
        self._notify_state_change("game_started", {
            "game_id": self.game_id,
            "starting_life": self.starting_life
        })
        return True
    
    def _process_game_end(self, event: GameEvent) -> bool:
        """Process game end event."""
        self.status = GameStatus.ENDED
        self._notify_state_change("game_ended", {
            "game_id": self.game_id,
            "winner": getattr(event, 'winner', None),
            "reason": getattr(event, 'reason', None)
        })
        return True
    
    def _process_draw_card(self, event: GameEvent) -> bool:
        """Process draw card event."""
        if hasattr(event, 'player') and hasattr(event, 'card'):
            player = self.get_player(event.player)
            if player:
                player.hand.add_card(event.card)
                self._notify_state_change("card_drawn", {
                    "player_id": event.player,
                    "card_name": event.card.name,
                    "hand_size": player.hand.size()
                })
        return True
    
    def _process_play_card(self, event: GameEvent) -> bool:
        """Process play card event."""
        if hasattr(event, 'player') and hasattr(event, 'card'):
            player = self.get_player(event.player)
            if player:
                # Remove from hand
                removed_card = player.hand.remove_card(event.card.instance_id)
                if removed_card:
                    # Add to battlefield
                    player.battlefield.add_card(event.card)
                    
                    # Handle land play
                    if CardType.LAND in event.card.card_types:
                        player.has_played_land_this_turn = True
                    
                    self._notify_state_change("card_played", {
                        "player_id": event.player,
                        "card_name": event.card.name,
                        "card_types": event.card.card_types,
                        "hand_size": player.hand.size()
                    })
        return True
    
    def _process_life_change(self, event: GameEvent) -> bool:
        """Process life change event."""
        if hasattr(event, 'player') and hasattr(event, 'new_life'):
            player = self.get_player(event.player)
            if player:
                old_life = player.life_total
                player.life_total = event.new_life
                
                self._notify_state_change("life_changed", {
                    "player_id": event.player,
                    "old_life": old_life,
                    "new_life": event.new_life,
                    "change": event.new_life - old_life
                })
        return True
    
    def _process_phase_change(self, event: GameEvent) -> bool:
        """Process phase change event."""
        if hasattr(event, 'new_phase'):
            self.set_phase(event.new_phase, getattr(event, 'new_step', None))
        return True
    
    def _process_turn_change(self, event: GameEvent) -> bool:
        """Process turn change event."""
        if hasattr(event, 'new_turn'):
            self.turn_number = event.new_turn
            if hasattr(event, 'active_player'):
                self.set_active_player(event.active_player)
        return True
    
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
    
    def _notify_state_change(self, change_type: str, data: Dict) -> None:
        """Notify all callbacks of a state change."""
        for callback in self.state_change_callbacks:
            try:
                callback(change_type, data)
            except Exception as e:
                print(f"Error in state change callback: {e}")
    
    def get_game_summary(self) -> Dict:
        """Get a summary of the current game state."""
        summary = {
            "game_id": self.game_id,
            "status": self.status,
            "turn_number": self.turn_number,
            "current_phase": self.current_phase,
            "current_step": self.current_step,
            "active_player": self.active_player,
            "self_player": None,
            "opponent_player": None
        }
        
        if self.self_player:
            summary["self_player"] = {
                "life_total": self.self_player.life_total,
                "hand_size": self.self_player.hand.size(),
                "creature_count": self.self_player.get_creature_count(),
                "land_count": self.self_player.get_land_count(),
                "mana_pool": self.self_player.get_mana_summary()
            }
        
        if self.opponent_player:
            summary["opponent_player"] = {
                "life_total": self.opponent_player.life_total,
                "hand_size": self.opponent_player.hand.size(),
                "creature_count": self.opponent_player.get_creature_count(),
                "land_count": self.opponent_player.get_land_count(),
                "mana_pool": self.opponent_player.get_mana_summary()
            }
        
        return summary
    
    def is_game_active(self) -> bool:
        """Check if game is currently active."""
        return self.status == GameStatus.ACTIVE
    
    def is_game_ended(self) -> bool:
        """Check if game has ended."""
        return self.status == GameStatus.ENDED
    
    def get_winner(self) -> Optional[int]:
        """Get the winner player ID if game has ended."""
        if not self.is_game_ended():
            return None
        
        # Check for life total 0 or less
        if self.self_player and self.self_player.life_total <= 0:
            return self.opponent_player.player_id if self.opponent_player else None
        elif self.opponent_player and self.opponent_player.life_total <= 0:
            return self.self_player.player_id if self.self_player else None
        
        return None
