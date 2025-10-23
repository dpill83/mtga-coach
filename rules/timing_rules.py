#!/usr/bin/env python3
"""
Magic Timing Rules

Implements Magic: The Gathering timing rules and priority system.
Handles when actions can be performed and priority passing.
"""

from typing import List, Dict, Optional, Set, Any
from datetime import datetime
from enum import Enum
import logging

from state.game_state import GameState, GameStatus
from state.player_state import PlayerState
from parser.events import Phase, ZoneType, CardType, CardInfo
from rules.action_types import Action, ActionType, ActionTiming, ActionPriority

logger = logging.getLogger(__name__)

class PriorityState(str, Enum):
    """Priority states in Magic."""
    ACTIVE_PLAYER = "active_player"
    NON_ACTIVE_PLAYER = "non_active_player"
    STACK_RESOLVING = "stack_resolving"
    COMBAT_DAMAGE = "combat_damage"
    TRIGGERED_ABILITY = "triggered_ability"

class TimingRules:
    """Magic timing rules engine."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.priority_passed: Set[int] = set()
        self.priority_sequence: List[int] = []
        self.current_priority_player: Optional[int] = None
        self.priority_start_time: Optional[datetime] = None
        
    def can_perform_action(self, action: Action, player_id: int) -> bool:
        """Check if an action can be performed at the current time."""
        try:
            # Check basic timing
            if not self._check_basic_timing(action, player_id):
                return False
            
            # Check priority
            if not self._check_priority(action, player_id):
                return False
            
            # Check phase-specific timing
            if not self._check_phase_timing(action, player_id):
                return False
            
            # Check step-specific timing
            if not self._check_step_timing(action, player_id):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking timing for action {action.action_type}: {e}")
            return False
    
    def _check_basic_timing(self, action: Action, player_id: int) -> bool:
        """Check basic timing requirements."""
        # Check if game is active
        if not self.game_state.is_game_active():
            return False
        
        # Check if player exists and is alive
        player = self.game_state.get_player(player_id)
        if not player or not player.is_alive():
            return False
        
        # Check if it's the player's turn (for most actions)
        if action.action_type in [ActionType.PLAY_LAND, ActionType.DECLARE_ATTACKERS]:
            if self.game_state.active_player != player_id:
                return False
        
        return True
    
    def _check_priority(self, action: Action, player_id: int) -> bool:
        """Check priority requirements."""
        # Some actions don't require priority
        if action.action_type in [ActionType.CONCEDE, ActionType.MULLIGAN]:
            return True
        
        # Check if player has priority
        if not self._player_has_priority(player_id):
            return False
        
        return True
    
    def _check_phase_timing(self, action: Action, player_id: int) -> bool:
        """Check phase-specific timing requirements."""
        current_phase = self.game_state.current_phase
        
        # Main phase actions
        if action.timing == ActionTiming.MAIN_PHASE:
            if current_phase not in [Phase.FIRST_MAIN, Phase.SECOND_MAIN]:
                return False
        
        # Combat phase actions
        elif action.timing == ActionTiming.COMBAT_PHASE:
            if current_phase not in [Phase.COMBAT_BEGIN, Phase.DECLARE_ATTACKERS, 
                                       Phase.DECLARE_BLOCKERS, Phase.COMBAT_DAMAGE, Phase.END_COMBAT]:
                return False
        
        # Specific step actions
        elif action.timing == ActionTiming.DECLARE_ATTACKERS:
            if current_phase != Phase.DECLARE_ATTACKERS:
                return False
        
        elif action.timing == ActionTiming.DECLARE_BLOCKERS:
            if current_phase != Phase.DECLARE_BLOCKERS:
                return False
        
        elif action.timing == ActionTiming.COMBAT_DAMAGE:
            if current_phase != Phase.COMBAT_DAMAGE:
                return False
        
        return True
    
    def _check_step_timing(self, action: Action, player_id: int) -> bool:
        """Check step-specific timing requirements."""
        current_step = self.game_state.current_step
        
        # Upkeep step
        if current_step == "Upkeep":
            if action.action_type not in [ActionType.CAST_SPELL, ActionType.ACTIVATE_ABILITY, 
                                       ActionType.PASS_PRIORITY, ActionType.CONCEDE]:
                return False
        
        # Draw step
        elif current_step == "Draw":
            if action.action_type not in [ActionType.CAST_SPELL, ActionType.ACTIVATE_ABILITY, 
                                        ActionType.PASS_PRIORITY, ActionType.CONCEDE]:
                return False
        
        # End step
        elif current_step == "End":
            if action.action_type not in [ActionType.CAST_SPELL, ActionType.ACTIVATE_ABILITY, 
                                        ActionType.PASS_PRIORITY, ActionType.CONCEDE]:
                return False
        
        return True
    
    def _player_has_priority(self, player_id: int) -> bool:
        """Check if a player has priority."""
        # Check if it's the player's turn
        if self.game_state.active_player == player_id:
            return True
        
        # Check if it's the non-active player's turn to respond
        if self.game_state.priority_player == player_id:
            return True
        
        # Check if player has passed priority
        if player_id in self.priority_passed:
            return False
        
        return True
    
    def pass_priority(self, player_id: int) -> bool:
        """Pass priority for a player."""
        try:
            # Mark player as having passed priority
            self.priority_passed.add(player_id)
            
            # Check if all players have passed priority
            if self._all_players_passed_priority():
                self._resolve_priority()
                return True
            
            # Move to next player
            self._move_to_next_player()
            return True
            
        except Exception as e:
            logger.error(f"Error passing priority for player {player_id}: {e}")
            return False
    
    def _all_players_passed_priority(self) -> bool:
        """Check if all players have passed priority."""
        # Get all players
        players = []
        if self.game_state.self_player:
            players.append(self.game_state.self_player.player_id)
        if self.game_state.opponent_player:
            players.append(self.game_state.opponent_player.player_id)
        
        # Check if all players have passed
        return all(player_id in self.priority_passed for player_id in players)
    
    def _resolve_priority(self) -> None:
        """Resolve priority and move to next phase/step."""
        try:
            # Clear priority passed flags
            self.priority_passed.clear()
            
            # Move to next phase/step
            self._advance_phase()
            
        except Exception as e:
            logger.error(f"Error resolving priority: {e}")
    
    def _move_to_next_player(self) -> None:
        """Move priority to the next player."""
        try:
            # Get all players
            players = []
            if self.game_state.self_player:
                players.append(self.game_state.self_player.player_id)
            if self.game_state.opponent_player:
                players.append(self.game_state.opponent_player.player_id)
            
            # Find current priority player
            current_player = self.game_state.priority_player
            if current_player is None:
                current_player = self.game_state.active_player
            
            # Move to next player
            current_index = players.index(current_player) if current_player in players else 0
            next_index = (current_index + 1) % len(players)
            next_player = players[next_index]
            
            # Set priority player
            self.game_state.priority_player = next_player
            self.current_priority_player = next_player
            
        except Exception as e:
            logger.error(f"Error moving to next player: {e}")
    
    def _advance_phase(self) -> None:
        """Advance to the next phase."""
        try:
            current_phase = self.game_state.current_phase
            
            # Phase progression
            if current_phase == Phase.UNTAP:
                self.game_state.set_phase(Phase.UPKEEP)
            elif current_phase == Phase.UPKEEP:
                self.game_state.set_phase(Phase.DRAW)
            elif current_phase == Phase.DRAW:
                self.game_state.set_phase(Phase.FIRST_MAIN)
            elif current_phase == Phase.FIRST_MAIN:
                self.game_state.set_phase(Phase.COMBAT_BEGIN)
            elif current_phase == Phase.COMBAT_BEGIN:
                self.game_state.set_phase(Phase.DECLARE_ATTACKERS)
            elif current_phase == Phase.DECLARE_ATTACKERS:
                self.game_state.set_phase(Phase.DECLARE_BLOCKERS)
            elif current_phase == Phase.DECLARE_BLOCKERS:
                self.game_state.set_phase(Phase.COMBAT_DAMAGE)
            elif current_phase == Phase.COMBAT_DAMAGE:
                self.game_state.set_phase(Phase.END_COMBAT)
            elif current_phase == Phase.END_COMBAT:
                self.game_state.set_phase(Phase.SECOND_MAIN)
            elif current_phase == Phase.SECOND_MAIN:
                self.game_state.set_phase(Phase.END_STEP)
            elif current_phase == Phase.END_STEP:
                self.game_state.set_phase(Phase.CLEANUP)
            elif current_phase == Phase.CLEANUP:
                # End of turn
                self._end_turn()
            
        except Exception as e:
            logger.error(f"Error advancing phase: {e}")
    
    def _end_turn(self) -> None:
        """End the current turn."""
        try:
            # Reset turn flags for all players
            if self.game_state.self_player:
                self.game_state.self_player.reset_turn_flags()
            if self.game_state.opponent_player:
                self.game_state.opponent_player.reset_turn_flags()
            
            # Advance turn
            self.game_state.next_turn()
            
            # Start new turn
            self.game_state.set_phase(Phase.UNTAP)
            
        except Exception as e:
            logger.error(f"Error ending turn: {e}")
    
    def get_priority_info(self) -> Dict[str, Any]:
        """Get information about current priority state."""
        return {
            "active_player": self.game_state.active_player,
            "priority_player": self.game_state.priority_player,
            "priority_passed": list(self.priority_passed),
            "current_phase": self.game_state.current_phase,
            "current_step": self.game_state.current_step,
            "turn_number": self.game_state.turn_number
        }
    
    def reset_priority(self) -> None:
        """Reset priority state."""
        self.priority_passed.clear()
        self.priority_sequence.clear()
        self.current_priority_player = None
        self.priority_start_time = None
    
    def can_respond_to(self, action: Action, responding_player_id: int) -> bool:
        """Check if a player can respond to an action."""
        try:
            # Check if player has priority
            if not self._player_has_priority(responding_player_id):
                return False
            
            # Check if action is on the stack
            if not self._is_action_on_stack(action):
                return False
            
            # Check if player can respond
            if not self._can_player_respond(responding_player_id):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if player can respond: {e}")
            return False
    
    def _is_action_on_stack(self, action: Action) -> bool:
        """Check if an action is on the stack."""
        # Simplified check - in a real implementation, this would check the actual stack
        return action.action_type in [ActionType.CAST_SPELL, ActionType.ACTIVATE_ABILITY]
    
    def _can_player_respond(self, player_id: int) -> bool:
        """Check if a player can respond to something."""
        # Check if player has priority
        if not self._player_has_priority(player_id):
            return False
        
        # Check if player has passed priority
        if player_id in self.priority_passed:
            return False
        
        return True
    
    def get_legal_responses(self, action: Action, responding_player_id: int) -> List[Action]:
        """Get legal responses to an action."""
        legal_responses = []
        
        try:
            # Check if player can respond
            if not self.can_respond_to(action, responding_player_id):
                return legal_responses
            
            # Get player
            player = self.game_state.get_player(responding_player_id)
            if not player:
                return legal_responses
            
            # Generate possible responses
            # Counter spells
            for spell in player.hand.cards:
                if self._can_counter_spell(spell, action):
                    response = Action(
                        action_type=ActionType.COUNTER_SPELL,
                        player_id=responding_player_id,
                        target_spell=action.spell if hasattr(action, 'spell') else None,
                        counter_spell=spell
                    )
                    legal_responses.append(response)
            
            # Pass priority
            pass_action = Action(
                action_type=ActionType.PASS_PRIORITY,
                player_id=responding_player_id
            )
            legal_responses.append(pass_action)
            
            return legal_responses
            
        except Exception as e:
            logger.error(f"Error getting legal responses: {e}")
            return []
    
    def _can_counter_spell(self, spell: CardInfo, target_action: Action) -> bool:
        """Check if a spell can counter another spell."""
        # Simplified counter spell logic
        if not spell.abilities:
            return False
        
        # Check if spell has counter ability
        for ability in spell.abilities:
            if "counter" in ability.lower():
                return True
        
        return False
