#!/usr/bin/env python3
"""
Board Evaluator

Evaluates the current board state and assigns scores to different aspects.
Provides the foundation for heuristic decision-making.
"""

from typing import List, Dict, Optional, Set, Any, Tuple
from datetime import datetime
import logging

from state.game_state import GameState, GameStatus
from state.player_state import PlayerState, PlayerType
from parser.events import CardInfo, CardType, ZoneType
from rules.action_types import Action, ActionType

logger = logging.getLogger(__name__)

class BoardState:
    """Represents the current board state for evaluation."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.self_player = game_state.get_self_player()
        self.opponent_player = game_state.get_opponent_player()
        self.turn_number = game_state.turn_number
        self.current_phase = game_state.current_phase
        self.active_player = game_state.active_player
        
        # Board metrics
        self.self_life = self.self_player.life_total if self.self_player else 20
        self.opponent_life = self.opponent_player.life_total if self.opponent_player else 20
        self.life_difference = self.self_life - self.opponent_life
        
        # Creature metrics
        self.self_creatures = self.self_player.battlefield.get_creatures() if self.self_player else []
        self.opponent_creatures = self.opponent_player.battlefield.get_creatures() if self.opponent_player else []
        
        # Mana metrics
        self.self_mana = self.self_player.get_mana_summary() if self.self_player else {}
        self.opponent_mana = self.opponent_player.get_mana_summary() if self.opponent_player else {}
        
        # Hand metrics
        self.self_hand_size = self.self_player.hand.size() if self.self_player else 0
        self.opponent_hand_size = self.opponent_player.hand.size() if self.opponent_player else 0
        
        # Land metrics
        self.self_lands = self.self_player.get_land_count() if self.self_player else 0
        self.opponent_lands = self.opponent_player.get_land_count() if self.opponent_player else 0

class BoardEvaluator:
    """Evaluates board states and assigns scores."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.evaluation_weights = self._get_default_weights()
        
    def _get_default_weights(self) -> Dict[str, float]:
        """Get default evaluation weights."""
        return {
            'life_total': 1.0,
            'life_difference': 2.0,
            'creature_power': 1.5,
            'creature_toughness': 1.0,
            'creature_count': 1.0,
            'mana_advantage': 1.2,
            'hand_advantage': 0.8,
            'land_advantage': 1.1,
            'threat_level': 2.5,
            'lethal_potential': 3.0,
            'board_control': 1.8,
            'tempo_advantage': 1.3
        }
    
    def evaluate_board_state(self, board_state: BoardState) -> Dict[str, float]:
        """Evaluate the current board state and return scores."""
        try:
            evaluation = {}
            
            # Life evaluation
            evaluation['life_score'] = self._evaluate_life(board_state)
            
            # Creature evaluation
            evaluation['creature_score'] = self._evaluate_creatures(board_state)
            
            # Mana evaluation
            evaluation['mana_score'] = self._evaluate_mana(board_state)
            
            # Hand evaluation
            evaluation['hand_score'] = self._evaluate_hands(board_state)
            
            # Land evaluation
            evaluation['land_score'] = self._evaluate_lands(board_state)
            
            # Threat evaluation
            evaluation['threat_score'] = self._evaluate_threats(board_state)
            
            # Lethal evaluation
            evaluation['lethal_score'] = self._evaluate_lethal(board_state)
            
            # Board control evaluation
            evaluation['control_score'] = self._evaluate_board_control(board_state)
            
            # Tempo evaluation
            evaluation['tempo_score'] = self._evaluate_tempo(board_state)
            
            # Overall score
            evaluation['overall_score'] = self._calculate_overall_score(evaluation)
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating board state: {e}")
            return {'overall_score': 0.0}
    
    def _evaluate_life(self, board_state: BoardState) -> float:
        """Evaluate life totals and differences."""
        score = 0.0
        
        # Self life score (diminishing returns)
        if board_state.self_life > 0:
            score += min(board_state.self_life * 0.1, 2.0)  # Cap at 2.0 for 20+ life
        
        # Life difference score
        if board_state.life_difference > 0:
            score += board_state.life_difference * 0.2
        elif board_state.life_difference < 0:
            score += board_state.life_difference * 0.3  # Penalty for being behind
        
        return score
    
    def _evaluate_creatures(self, board_state: BoardState) -> float:
        """Evaluate creature presence and power."""
        score = 0.0
        
        # Self creatures
        self_power = sum(creature.power or 0 for creature in board_state.self_creatures)
        self_toughness = sum(creature.toughness or 0 for creature in board_state.self_creatures)
        self_count = len(board_state.self_creatures)
        
        score += self_power * 0.3
        score += self_toughness * 0.2
        score += self_count * 0.1
        
        # Opponent creatures (negative score)
        opponent_power = sum(creature.power or 0 for creature in board_state.opponent_creatures)
        opponent_toughness = sum(creature.toughness or 0 for creature in board_state.opponent_creatures)
        opponent_count = len(board_state.opponent_creatures)
        
        score -= opponent_power * 0.3
        score -= opponent_toughness * 0.2
        score -= opponent_count * 0.1
        
        return score
    
    def _evaluate_mana(self, board_state: BoardState) -> float:
        """Evaluate mana advantage."""
        score = 0.0
        
        # Self mana
        self_total = board_state.self_mana.get('total', 0)
        score += self_total * 0.1
        
        # Mana difference
        opponent_total = board_state.opponent_mana.get('total', 0)
        mana_difference = self_total - opponent_total
        score += mana_difference * 0.15
        
        return score
    
    def _evaluate_hands(self, board_state: BoardState) -> float:
        """Evaluate hand advantage."""
        score = 0.0
        
        # Hand size difference
        hand_difference = board_state.self_hand_size - board_state.opponent_hand_size
        score += hand_difference * 0.2
        
        # Optimal hand size (4-7 cards)
        if 4 <= board_state.self_hand_size <= 7:
            score += 0.5
        elif board_state.self_hand_size > 7:
            score -= 0.3  # Penalty for too many cards
        
        return score
    
    def _evaluate_lands(self, board_state: BoardState) -> float:
        """Evaluate land advantage."""
        score = 0.0
        
        # Land count difference
        land_difference = board_state.self_lands - board_state.opponent_lands
        score += land_difference * 0.3
        
        # Optimal land count (based on turn)
        optimal_lands = min(board_state.turn_number, 6)  # 6 lands is usually enough
        if board_state.self_lands >= optimal_lands:
            score += 0.5
        elif board_state.self_lands < optimal_lands:
            score -= 0.2  # Penalty for being behind on lands
        
        return score
    
    def _evaluate_threats(self, board_state: BoardState) -> float:
        """Evaluate threat level from opponent."""
        score = 0.0
        
        # Opponent creature threats
        for creature in board_state.opponent_creatures:
            if creature.power and creature.power > 0:
                # High power creatures are more threatening
                threat_level = creature.power * 0.5
                
                # Flying creatures are more threatening
                if 'flying' in creature.keywords:
                    threat_level *= 1.5
                
                # Creatures with abilities are more threatening
                if creature.abilities:
                    threat_level *= 1.2
                
                score -= threat_level
        
        return score
    
    def _evaluate_lethal(self, board_state: BoardState) -> float:
        """Evaluate lethal potential."""
        score = 0.0
        
        # Self lethal potential
        self_power = sum(creature.power or 0 for creature in board_state.self_creatures)
        if self_power >= board_state.opponent_life:
            score += 5.0  # High score for lethal
        
        # Opponent lethal potential
        opponent_power = sum(creature.power or 0 for creature in board_state.opponent_creatures)
        if opponent_power >= board_state.self_life:
            score -= 5.0  # High penalty for opponent lethal
        
        return score
    
    def _evaluate_board_control(self, board_state: BoardState) -> float:
        """Evaluate board control."""
        score = 0.0
        
        # Creature count advantage
        creature_difference = len(board_state.self_creatures) - len(board_state.opponent_creatures)
        score += creature_difference * 0.4
        
        # Power advantage
        self_power = sum(creature.power or 0 for creature in board_state.self_creatures)
        opponent_power = sum(creature.power or 0 for creature in board_state.opponent_creatures)
        power_difference = self_power - opponent_power
        score += power_difference * 0.3
        
        return score
    
    def _evaluate_tempo(self, board_state: BoardState) -> float:
        """Evaluate tempo advantage."""
        score = 0.0
        
        # Turn advantage (being ahead on curve)
        if board_state.turn_number <= 6:
            # Early game: land count matters more
            if board_state.self_lands >= board_state.turn_number:
                score += 0.5
            else:
                score -= 0.3
        else:
            # Late game: creature count and power matter more
            creature_difference = len(board_state.self_creatures) - len(board_state.opponent_creatures)
            score += creature_difference * 0.2
        
        return score
    
    def _calculate_overall_score(self, evaluation: Dict[str, float]) -> float:
        """Calculate overall board score."""
        overall_score = 0.0
        
        for metric, score in evaluation.items():
            if metric != 'overall_score':
                weight = self.evaluation_weights.get(metric.replace('_score', ''), 1.0)
                overall_score += score * weight
        
        return overall_score
    
    def get_board_summary(self, board_state: BoardState) -> Dict[str, Any]:
        """Get a summary of the board state."""
        return {
            'turn_number': board_state.turn_number,
            'current_phase': board_state.current_phase,
            'active_player': board_state.active_player,
            'self_life': board_state.self_life,
            'opponent_life': board_state.opponent_life,
            'life_difference': board_state.life_difference,
            'self_creatures': len(board_state.self_creatures),
            'opponent_creatures': len(board_state.opponent_creatures),
            'self_power': sum(creature.power or 0 for creature in board_state.self_creatures),
            'opponent_power': sum(creature.power or 0 for creature in board_state.opponent_creatures),
            'self_mana': board_state.self_mana.get('total', 0),
            'opponent_mana': board_state.opponent_mana.get('total', 0),
            'self_hand_size': board_state.self_hand_size,
            'opponent_hand_size': board_state.opponent_hand_size,
            'self_lands': board_state.self_lands,
            'opponent_lands': board_state.opponent_lands
        }
    
    def set_evaluation_weights(self, weights: Dict[str, float]) -> None:
        """Set custom evaluation weights."""
        self.evaluation_weights.update(weights)
    
    def get_evaluation_weights(self) -> Dict[str, float]:
        """Get current evaluation weights."""
        return self.evaluation_weights.copy()
