#!/usr/bin/env python3
"""
Heuristic Engine

Main heuristic engine that combines all evaluation components.
Provides the primary interface for AI decision-making.
"""

from typing import List, Dict, Optional, Set, Any, Tuple
from datetime import datetime
import logging

from state.game_state import GameState, GameStatus
from state.player_state import PlayerState, PlayerType
from parser.events import CardInfo, CardType, ZoneType
from rules.action_types import Action, ActionType, ActionTiming, ActionPriority
from rules.legality_integration import LegalityIntegration
from engine.board_evaluator import BoardEvaluator, BoardState
from engine.action_evaluator import ActionEvaluator, ActionScore
from engine.threat_assessor import ThreatAssessor, Threat

logger = logging.getLogger(__name__)

class Recommendation:
    """Represents a recommended action with reasoning."""
    
    def __init__(self, action: Action, score: float, reasoning: List[str], 
                 priority: str, confidence: float):
        self.action = action
        self.score = score
        self.reasoning = reasoning
        self.priority = priority
        self.confidence = confidence
        self.timestamp = datetime.now()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the recommendation."""
        return {
            'action_type': self.action.action_type,
            'score': self.score,
            'priority': self.priority,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'timestamp': self.timestamp.isoformat()
        }

class HeuristicEngine:
    """Main heuristic engine for AI decision-making."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.legality_integration = LegalityIntegration(game_state)
        self.board_evaluator = BoardEvaluator(game_state)
        self.action_evaluator = ActionEvaluator(game_state)
        self.threat_assessor = ThreatAssessor(game_state)
        
        # Engine settings
        self.max_recommendations = 5
        self.min_confidence_threshold = 0.3
        self.lethal_priority_boost = 5.0
        
    def get_recommendations(self, player_id: int, max_recommendations: Optional[int] = None) -> List[Recommendation]:
        """Get action recommendations for a player."""
        try:
            # Get legal actions
            legal_actions = self.legality_integration.get_legal_actions(player_id)
            
            if not legal_actions:
                return []
            
            # Evaluate actions
            scored_actions = self.action_evaluator.evaluate_actions(legal_actions, player_id)
            
            # Assess threats
            threats = self.threat_assessor.assess_threats(player_id)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(scored_actions, threats, player_id)
            
            # Limit recommendations
            max_recs = max_recommendations or self.max_recommendations
            return recommendations[:max_recs]
            
        except Exception as e:
            logger.error(f"Error getting recommendations for player {player_id}: {e}")
            return []
    
    def get_best_action(self, player_id: int) -> Optional[Recommendation]:
        """Get the single best action recommendation."""
        recommendations = self.get_recommendations(player_id, 1)
        return recommendations[0] if recommendations else None
    
    def get_emergency_actions(self, player_id: int) -> List[Recommendation]:
        """Get emergency actions for critical situations."""
        try:
            # Get immediate threats
            immediate_threats = self.threat_assessor.get_immediate_threats(player_id)
            
            if not immediate_threats:
                return []
            
            # Get legal actions
            legal_actions = self.legality_integration.get_legal_actions(player_id)
            
            # Filter for emergency actions
            emergency_actions = self._filter_emergency_actions(legal_actions, immediate_threats)
            
            # Evaluate emergency actions
            scored_actions = self.action_evaluator.evaluate_actions(emergency_actions, player_id)
            
            # Generate emergency recommendations
            recommendations = self._generate_emergency_recommendations(scored_actions, immediate_threats)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting emergency actions for player {player_id}: {e}")
            return []
    
    def get_board_analysis(self, player_id: int) -> Dict[str, Any]:
        """Get a comprehensive board analysis."""
        try:
            # Get board state
            board_state = BoardState(self.game_state)
            
            # Evaluate board
            board_evaluation = self.board_evaluator.evaluate_board_state(board_state)
            
            # Assess threats
            threats = self.threat_assessor.assess_threats(player_id)
            
            # Get legal actions
            legal_actions = self.legality_integration.get_legal_actions(player_id)
            
            # Get recommendations
            recommendations = self.get_recommendations(player_id, 3)
            
            analysis = {
                'board_state': self.board_evaluator.get_board_summary(board_state),
                'board_evaluation': board_evaluation,
                'threats': self.threat_assessor.get_threat_summary(player_id),
                'legal_actions': len(legal_actions),
                'recommendations': [rec.get_summary() for rec in recommendations],
                'game_status': self.game_state.status,
                'turn_number': self.game_state.turn_number,
                'current_phase': self.game_state.current_phase,
                'active_player': self.game_state.active_player
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error getting board analysis for player {player_id}: {e}")
            return {}
    
    def _generate_recommendations(self, scored_actions: List[ActionScore], 
                                threats: List[Threat], player_id: int) -> List[Recommendation]:
        """Generate recommendations from scored actions."""
        recommendations = []
        
        for scored_action in scored_actions:
            # Calculate confidence
            confidence = self._calculate_confidence(scored_action, threats)
            
            # Skip low confidence actions
            if confidence < self.min_confidence_threshold:
                continue
            
            # Create recommendation
            recommendation = Recommendation(
                action=scored_action.action,
                score=scored_action.score,
                reasoning=scored_action.reasoning,
                priority=scored_action.priority,
                confidence=confidence
            )
            
            recommendations.append(recommendation)
        
        # Sort by score and confidence
        recommendations.sort(key=lambda x: (x.score, x.confidence), reverse=True)
        
        return recommendations
    
    def _generate_emergency_recommendations(self, scored_actions: List[ActionScore], 
                                         immediate_threats: List[Threat]) -> List[Recommendation]:
        """Generate emergency recommendations."""
        recommendations = []
        
        for scored_action in scored_actions:
            # Boost score for emergency situations
            emergency_score = scored_action.score + self.lethal_priority_boost
            
            # Calculate confidence
            confidence = self._calculate_emergency_confidence(scored_action, immediate_threats)
            
            # Create emergency recommendation
            recommendation = Recommendation(
                action=scored_action.action,
                score=emergency_score,
                reasoning=scored_action.reasoning + ["Emergency response to immediate threat"],
                priority="critical",
                confidence=confidence
            )
            
            recommendations.append(recommendation)
        
        # Sort by emergency score
        recommendations.sort(key=lambda x: x.score, reverse=True)
        
        return recommendations
    
    def _filter_emergency_actions(self, actions: List[Action], threats: List[Threat]) -> List[Action]:
        """Filter actions for emergency situations."""
        emergency_actions = []
        
        for action in actions:
            # Include removal actions
            if action.action_type == ActionType.CAST_SPELL:
                if self._is_removal_action(action):
                    emergency_actions.append(action)
            
            # Include blocking actions
            elif action.action_type == ActionType.DECLARE_BLOCKERS:
                emergency_actions.append(action)
            
            # Include defensive actions
            elif action.action_type == ActionType.ACTIVATE_ABILITY:
                if self._is_defensive_ability(action):
                    emergency_actions.append(action)
        
        return emergency_actions
    
    def _is_removal_action(self, action: Action) -> bool:
        """Check if an action is removal."""
        if hasattr(action, 'spell'):
            spell = action.spell
            if spell:
                # Check for removal keywords
                removal_keywords = ['destroy', 'exile', 'damage', 'counter']
                for keyword in removal_keywords:
                    if keyword in spell.name.lower() or keyword in spell.oracle_text.lower():
                        return True
        return False
    
    def _is_defensive_ability(self, action: Action) -> bool:
        """Check if an ability is defensive."""
        if hasattr(action, 'ability'):
            ability = action.ability
            if ability:
                # Check for defensive keywords
                defensive_keywords = ['block', 'prevent', 'gain life', 'counter']
                for keyword in defensive_keywords:
                    if keyword in ability.lower():
                        return True
        return False
    
    def _calculate_confidence(self, scored_action: ActionScore, threats: List[Threat]) -> float:
        """Calculate confidence in a recommendation."""
        confidence = 0.5  # Base confidence
        
        # Boost confidence for high-scoring actions
        if scored_action.score >= 6.0:
            confidence += 0.3
        elif scored_action.score >= 4.0:
            confidence += 0.2
        elif scored_action.score >= 2.0:
            confidence += 0.1
        
        # Boost confidence for actions that address threats
        if self._action_addresses_threats(scored_action, threats):
            confidence += 0.2
        
        # Boost confidence for lethal actions
        if self._action_provides_lethal(scored_action):
            confidence += 0.3
        
        # Cap confidence at 1.0
        return min(confidence, 1.0)
    
    def _calculate_emergency_confidence(self, scored_action: ActionScore, 
                                      immediate_threats: List[Threat]) -> float:
        """Calculate confidence for emergency actions."""
        confidence = 0.7  # Higher base confidence for emergency
        
        # Boost confidence for actions that address immediate threats
        if self._action_addresses_immediate_threats(scored_action, immediate_threats):
            confidence += 0.2
        
        # Boost confidence for defensive actions
        if self._is_defensive_action(scored_action):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _action_addresses_threats(self, scored_action: ActionScore, threats: List[Threat]) -> bool:
        """Check if an action addresses threats."""
        if not threats:
            return False
        
        # Simplified threat addressing check
        if scored_action.action.action_type == ActionType.CAST_SPELL:
            if hasattr(scored_action.action, 'spell'):
                spell = scored_action.action.spell
                if spell:
                    # Check if spell can remove threats
                    if self._is_removal_action(scored_action.action):
                        return True
        
        return False
    
    def _action_provides_lethal(self, scored_action: ActionScore) -> bool:
        """Check if an action provides lethal damage."""
        if scored_action.action.action_type == ActionType.DECLARE_ATTACKERS:
            if hasattr(scored_action.action, 'attackers'):
                attackers = scored_action.action.attackers
                if attackers:
                    total_power = sum(attacker.power or 0 for attacker in attackers)
                    opponent = self.game_state.get_opponent_player()
                    if opponent and total_power >= opponent.life_total:
                        return True
        
        return False
    
    def _action_addresses_immediate_threats(self, scored_action: ActionScore, 
                                          immediate_threats: List[Threat]) -> bool:
        """Check if an action addresses immediate threats."""
        if not immediate_threats:
            return False
        
        # Check if action can remove immediate threats
        if scored_action.action.action_type == ActionType.CAST_SPELL:
            if self._is_removal_action(scored_action.action):
                return True
        
        return False
    
    def _is_defensive_action(self, scored_action: ActionScore) -> bool:
        """Check if an action is defensive."""
        if scored_action.action.action_type == ActionType.DECLARE_BLOCKERS:
            return True
        elif scored_action.action.action_type == ActionType.ACTIVATE_ABILITY:
            return self._is_defensive_ability(scored_action.action)
        
        return False
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get the status of the heuristic engine."""
        return {
            'max_recommendations': self.max_recommendations,
            'min_confidence_threshold': self.min_confidence_threshold,
            'lethal_priority_boost': self.lethal_priority_boost,
            'board_evaluator_weights': self.board_evaluator.get_evaluation_weights(),
            'action_evaluator_weights': self.action_evaluator.get_scoring_weights(),
            'threat_assessor_weights': self.threat_assessor.get_threat_weights()
        }
    
    def set_engine_settings(self, settings: Dict[str, Any]) -> None:
        """Set engine settings."""
        if 'max_recommendations' in settings:
            self.max_recommendations = settings['max_recommendations']
        if 'min_confidence_threshold' in settings:
            self.min_confidence_threshold = settings['min_confidence_threshold']
        if 'lethal_priority_boost' in settings:
            self.lethal_priority_boost = settings['lethal_priority_boost']
    
    def set_evaluation_weights(self, weights: Dict[str, float]) -> None:
        """Set evaluation weights for all components."""
        if 'board' in weights:
            self.board_evaluator.set_evaluation_weights(weights['board'])
        if 'action' in weights:
            self.action_evaluator.set_scoring_weights(weights['action'])
        if 'threat' in weights:
            self.threat_assessor.set_threat_weights(weights['threat'])
