#!/usr/bin/env python3
"""
Action Evaluator

Evaluates and scores individual actions based on their potential impact.
Provides the foundation for action recommendation.
"""

from typing import List, Dict, Optional, Set, Any, Tuple
from datetime import datetime
import logging

from state.game_state import GameState, GameStatus
from state.player_state import PlayerState, PlayerType
from parser.events import CardInfo, CardType, ZoneType
from rules.action_types import Action, ActionType, ActionTiming, ActionPriority
from engine.board_evaluator import BoardEvaluator, BoardState

logger = logging.getLogger(__name__)

class ActionScore:
    """Represents a scored action with reasoning."""
    
    def __init__(self, action: Action, score: float, reasoning: List[str]):
        self.action = action
        self.score = score
        self.reasoning = reasoning
        self.priority = self._calculate_priority()
    
    def _calculate_priority(self) -> str:
        """Calculate priority level based on score."""
        if self.score >= 8.0:
            return "critical"
        elif self.score >= 6.0:
            return "high"
        elif self.score >= 4.0:
            return "medium"
        elif self.score >= 2.0:
            return "low"
        else:
            return "very_low"
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the scored action."""
        return {
            'action_type': self.action.action_type,
            'score': self.score,
            'priority': self.priority,
            'reasoning': self.reasoning,
            'player_id': self.action.player_id
        }

class ActionEvaluator:
    """Evaluates and scores actions based on their potential impact."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.board_evaluator = BoardEvaluator(game_state)
        self.scoring_weights = self._get_default_weights()
        
    def _get_default_weights(self) -> Dict[str, float]:
        """Get default scoring weights for different action types."""
        return {
            'lethal_damage': 10.0,
            'prevent_lethal': 9.0,
            'card_advantage': 3.0,
            'mana_efficiency': 2.0,
            'board_presence': 2.5,
            'threat_removal': 4.0,
            'tempo_advantage': 2.0,
            'value_generation': 2.5,
            'combo_potential': 3.5,
            'defensive_play': 1.5,
            'aggressive_play': 2.0,
            'utility_play': 1.0
        }
    
    def evaluate_actions(self, actions: List[Action], player_id: int) -> List[ActionScore]:
        """Evaluate and score a list of actions."""
        scored_actions = []
        
        for action in actions:
            try:
                score, reasoning = self._evaluate_single_action(action, player_id)
                scored_action = ActionScore(action, score, reasoning)
                scored_actions.append(scored_action)
                
            except Exception as e:
                logger.error(f"Error evaluating action {action.action_type}: {e}")
                # Add with low score
                scored_action = ActionScore(action, 0.0, [f"Error evaluating action: {str(e)}"])
                scored_actions.append(scored_action)
        
        # Sort by score (highest first)
        scored_actions.sort(key=lambda x: x.score, reverse=True)
        
        return scored_actions
    
    def _evaluate_single_action(self, action: Action, player_id: int) -> Tuple[float, List[str]]:
        """Evaluate a single action and return score with reasoning."""
        score = 0.0
        reasoning = []
        
        # Get current board state
        board_state = BoardState(self.game_state)
        
        # Evaluate based on action type
        if action.action_type == ActionType.PLAY_LAND:
            score, reasoning = self._evaluate_play_land(action, board_state)
        elif action.action_type == ActionType.CAST_SPELL:
            score, reasoning = self._evaluate_cast_spell(action, board_state)
        elif action.action_type == ActionType.ACTIVATE_ABILITY:
            score, reasoning = self._evaluate_activate_ability(action, board_state)
        elif action.action_type == ActionType.DECLARE_ATTACKERS:
            score, reasoning = self._evaluate_declare_attackers(action, board_state)
        elif action.action_type == ActionType.DECLARE_BLOCKERS:
            score, reasoning = self._evaluate_declare_blockers(action, board_state)
        elif action.action_type == ActionType.PASS_PRIORITY:
            score, reasoning = self._evaluate_pass_priority(action, board_state)
        elif action.action_type == ActionType.CONCEDE:
            score, reasoning = self._evaluate_concede(action, board_state)
        else:
            score, reasoning = self._evaluate_generic_action(action, board_state)
        
        return score, reasoning
    
    def _evaluate_play_land(self, action: Action, board_state: BoardState) -> Tuple[float, List[str]]:
        """Evaluate playing a land."""
        score = 0.0
        reasoning = []
        
        # Basic land play value
        score += 2.0
        reasoning.append("Playing a land increases mana production")
        
        # Check if it's the first land of the turn
        if not board_state.self_player.has_played_land_this_turn:
            score += 1.0
            reasoning.append("First land of the turn")
        
        # Check if we're behind on lands
        if board_state.self_lands < board_state.turn_number:
            score += 1.5
            reasoning.append("Catching up on land drops")
        
        # Check if we have mana to spend
        if board_state.self_mana.get('total', 0) > 0:
            score += 0.5
            reasoning.append("Have mana to spend")
        
        return score, reasoning
    
    def _evaluate_cast_spell(self, action: Action, board_state: BoardState) -> Tuple[float, List[str]]:
        """Evaluate casting a spell."""
        score = 0.0
        reasoning = []
        
        # Get spell info
        spell = getattr(action, 'spell', None)
        if not spell:
            return 0.0, ["No spell information available"]
        
        # Basic spell value
        score += 1.0
        reasoning.append("Casting a spell")
        
        # Evaluate based on spell type
        if CardType.CREATURE in spell.card_types:
            score, reasoning = self._evaluate_creature_spell(action, board_state, score, reasoning)
        elif CardType.INSTANT in spell.card_types or CardType.SORCERY in spell.card_types:
            score, reasoning = self._evaluate_instant_sorcery_spell(action, board_state, score, reasoning)
        elif CardType.ENCHANTMENT in spell.card_types:
            score, reasoning = self._evaluate_enchantment_spell(action, board_state, score, reasoning)
        elif CardType.ARTIFACT in spell.card_types:
            score, reasoning = self._evaluate_artifact_spell(action, board_state, score, reasoning)
        elif CardType.PLANESWALKER in spell.card_types:
            score, reasoning = self._evaluate_planeswalker_spell(action, board_state, score, reasoning)
        
        # Check mana efficiency
        mana_cost = getattr(action, 'mana_cost', '')
        if mana_cost:
            score, reasoning = self._evaluate_mana_efficiency(action, board_state, score, reasoning)
        
        return score, reasoning
    
    def _evaluate_creature_spell(self, action: Action, board_state: BoardState, score: float, reasoning: List[str]) -> Tuple[float, List[str]]:
        """Evaluate casting a creature spell."""
        spell = getattr(action, 'spell', None)
        if not spell:
            return score, reasoning
        
        # Creature power and toughness
        power = spell.power or 0
        toughness = spell.toughness or 0
        
        # Basic creature value
        score += (power + toughness) * 0.5
        reasoning.append(f"Creature with {power}/{toughness}")
        
        # Check for lethal
        if power >= board_state.opponent_life:
            score += 8.0
            reasoning.append("Creature provides lethal damage")
        
        # Check for board presence
        if power > 0:
            score += 1.0
            reasoning.append("Creature provides board presence")
        
        # Check for flying
        if 'flying' in spell.keywords:
            score += 0.5
            reasoning.append("Flying creature")
        
        # Check for abilities
        if spell.abilities:
            score += 0.5
            reasoning.append("Creature has abilities")
        
        return score, reasoning
    
    def _evaluate_instant_sorcery_spell(self, action: Action, board_state: BoardState, score: float, reasoning: List[str]) -> Tuple[float, List[str]]:
        """Evaluate casting an instant or sorcery spell."""
        spell = getattr(action, 'spell', None)
        if not spell:
            return score, reasoning
        
        # Check for removal spells
        if self._is_removal_spell(spell):
            score += 3.0
            reasoning.append("Removal spell")
            
            # Check if there are targets
            if board_state.opponent_creatures:
                score += 1.0
                reasoning.append("Has targets to remove")
        
        # Check for card draw
        if self._is_card_draw_spell(spell):
            score += 2.0
            reasoning.append("Card draw spell")
            
            # Check if we need cards
            if board_state.self_hand_size < 4:
                score += 1.0
                reasoning.append("Need more cards in hand")
        
        # Check for damage spells
        if self._is_damage_spell(spell):
            score += 2.0
            reasoning.append("Damage spell")
            
            # Check for lethal
            if self._can_deal_lethal_damage(spell, board_state):
                score += 5.0
                reasoning.append("Can deal lethal damage")
        
        return score, reasoning
    
    def _evaluate_enchantment_spell(self, action: Action, board_state: BoardState, score: float, reasoning: List[str]) -> Tuple[float, List[str]]:
        """Evaluate casting an enchantment spell."""
        spell = getattr(action, 'spell', None)
        if not spell:
            return score, reasoning
        
        # Basic enchantment value
        score += 1.5
        reasoning.append("Enchantment provides ongoing value")
        
        # Check for specific enchantment types
        if self._is_aura_enchantment(spell):
            score += 1.0
            reasoning.append("Aura enchantment")
        elif self._is_global_enchantment(spell):
            score += 2.0
            reasoning.append("Global enchantment")
        
        return score, reasoning
    
    def _evaluate_artifact_spell(self, action: Action, board_state: BoardState, score: float, reasoning: List[str]) -> Tuple[float, List[str]]:
        """Evaluate casting an artifact spell."""
        spell = getattr(action, 'spell', None)
        if not spell:
            return score, reasoning
        
        # Basic artifact value
        score += 1.0
        reasoning.append("Artifact provides utility")
        
        # Check for mana artifacts
        if self._is_mana_artifact(spell):
            score += 1.5
            reasoning.append("Mana artifact")
        
        return score, reasoning
    
    def _evaluate_planeswalker_spell(self, action: Action, board_state: BoardState, score: float, reasoning: List[str]) -> Tuple[float, List[str]]:
        """Evaluate casting a planeswalker spell."""
        spell = getattr(action, 'spell', None)
        if not spell:
            return score, reasoning
        
        # Basic planeswalker value
        score += 3.0
        reasoning.append("Planeswalker provides ongoing value")
        
        # Check for loyalty abilities
        if spell.abilities:
            score += 1.0
            reasoning.append("Planeswalker has abilities")
        
        return score, reasoning
    
    def _evaluate_mana_efficiency(self, action: Action, board_state: BoardState, score: float, reasoning: List[str]) -> Tuple[float, List[str]]:
        """Evaluate mana efficiency of an action."""
        mana_cost = getattr(action, 'mana_cost', '')
        if not mana_cost:
            return score, reasoning
        
        # Parse mana cost
        cost_amount = len(mana_cost.replace('{', '').replace('}', ''))
        available_mana = board_state.self_mana.get('total', 0)
        
        # Check if we can afford it
        if available_mana >= cost_amount:
            score += 1.0
            reasoning.append("Can afford the mana cost")
        else:
            score -= 2.0
            reasoning.append("Cannot afford the mana cost")
        
        # Check mana efficiency
        if cost_amount <= 3:
            score += 0.5
            reasoning.append("Efficient mana cost")
        elif cost_amount >= 6:
            score -= 0.5
            reasoning.append("Expensive mana cost")
        
        return score, reasoning
    
    def _evaluate_activate_ability(self, action: Action, board_state: BoardState) -> Tuple[float, List[str]]:
        """Evaluate activating an ability."""
        score = 0.0
        reasoning = []
        
        # Basic ability value
        score += 1.0
        reasoning.append("Activating an ability")
        
        # Check ability type
        ability = getattr(action, 'ability', '')
        if ability:
            if 'create' in ability.lower():
                score += 1.0
                reasoning.append("Creature generation ability")
            elif 'draw' in ability.lower():
                score += 1.5
                reasoning.append("Card draw ability")
            elif 'damage' in ability.lower():
                score += 1.0
                reasoning.append("Damage ability")
        
        return score, reasoning
    
    def _evaluate_declare_attackers(self, action: Action, board_state: BoardState) -> Tuple[float, List[str]]:
        """Evaluate declaring attackers."""
        score = 0.0
        reasoning = []
        
        # Get attackers
        attackers = getattr(action, 'attackers', [])
        if not attackers:
            return 0.0, ["No attackers to declare"]
        
        # Calculate total power
        total_power = sum(attacker.power or 0 for attacker in attackers)
        
        # Check for lethal
        if total_power >= board_state.opponent_life:
            score += 8.0
            reasoning.append("Attackers can deal lethal damage")
        else:
            # Regular attack value
            score += total_power * 0.3
            reasoning.append(f"Attackers deal {total_power} damage")
        
        # Check for flying attackers
        flying_attackers = [a for a in attackers if 'flying' in a.keywords]
        if flying_attackers:
            score += len(flying_attackers) * 0.5
            reasoning.append("Flying attackers")
        
        return score, reasoning
    
    def _evaluate_declare_blockers(self, action: Action, board_state: BoardState) -> Tuple[float, List[str]]:
        """Evaluate declaring blockers."""
        score = 0.0
        reasoning = []
        
        # Basic blocking value
        score += 1.0
        reasoning.append("Declaring blockers")
        
        # Check if we're preventing damage
        if board_state.self_life <= 5:
            score += 3.0
            reasoning.append("Blocking to prevent lethal damage")
        elif board_state.self_life <= 10:
            score += 1.5
            reasoning.append("Blocking to preserve life total")
        
        return score, reasoning
    
    def _evaluate_pass_priority(self, action: Action, board_state: BoardState) -> Tuple[float, List[str]]:
        """Evaluate passing priority."""
        score = 0.0
        reasoning = []
        
        # Basic pass value
        score += 0.5
        reasoning.append("Passing priority")
        
        # Check if we have better options
        if board_state.self_hand_size > 0:
            score -= 0.5
            reasoning.append("Have cards in hand")
        
        return score, reasoning
    
    def _evaluate_concede(self, action: Action, board_state: BoardState) -> Tuple[float, List[str]]:
        """Evaluate conceding."""
        score = 0.0
        reasoning = []
        
        # Concede is usually not recommended
        score -= 5.0
        reasoning.append("Conceding the game")
        
        return score, reasoning
    
    def _evaluate_generic_action(self, action: Action, board_state: BoardState) -> Tuple[float, List[str]]:
        """Evaluate a generic action."""
        score = 0.0
        reasoning = []
        
        # Basic action value
        score += 0.5
        reasoning.append(f"Performing {action.action_type}")
        
        return score, reasoning
    
    def _is_removal_spell(self, spell: CardInfo) -> bool:
        """Check if a spell is removal."""
        # Simplified removal detection
        removal_keywords = ['destroy', 'exile', 'damage', 'counter']
        for keyword in removal_keywords:
            if keyword in spell.name.lower() or keyword in spell.oracle_text.lower():
                return True
        return False
    
    def _is_card_draw_spell(self, spell: CardInfo) -> bool:
        """Check if a spell draws cards."""
        draw_keywords = ['draw', 'card']
        for keyword in draw_keywords:
            if keyword in spell.name.lower() or keyword in spell.oracle_text.lower():
                return True
        return False
    
    def _is_damage_spell(self, spell: CardInfo) -> bool:
        """Check if a spell deals damage."""
        damage_keywords = ['damage', 'bolt', 'shock', 'fire']
        for keyword in damage_keywords:
            if keyword in spell.name.lower() or keyword in spell.oracle_text.lower():
                return True
        return False
    
    def _can_deal_lethal_damage(self, spell: CardInfo, board_state: BoardState) -> bool:
        """Check if a spell can deal lethal damage."""
        # Simplified lethal damage detection
        if spell.power and spell.power >= board_state.opponent_life:
            return True
        return False
    
    def _is_aura_enchantment(self, spell: CardInfo) -> bool:
        """Check if an enchantment is an aura."""
        return 'aura' in spell.type_line.lower()
    
    def _is_global_enchantment(self, spell: CardInfo) -> bool:
        """Check if an enchantment is global."""
        return 'enchantment' in spell.type_line.lower() and 'aura' not in spell.type_line.lower()
    
    def _is_mana_artifact(self, spell: CardInfo) -> bool:
        """Check if an artifact produces mana."""
        mana_keywords = ['mana', 'tapping', 'add']
        for keyword in mana_keywords:
            if keyword in spell.name.lower() or keyword in spell.oracle_text.lower():
                return True
        return False
    
    def set_scoring_weights(self, weights: Dict[str, float]) -> None:
        """Set custom scoring weights."""
        self.scoring_weights.update(weights)
    
    def get_scoring_weights(self) -> Dict[str, float]:
        """Get current scoring weights."""
        return self.scoring_weights.copy()
