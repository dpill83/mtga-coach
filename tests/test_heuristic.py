#!/usr/bin/env python3
"""
Test Suite for Heuristic Evaluation

Comprehensive tests for the heuristic evaluation system.
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from state.game_state import GameState, GameStatus, Phase
from state.player_state import PlayerState, PlayerType, ManaPool
from parser.events import CardInfo, CardType, ZoneType
from rules.action_types import ActionType, ActionTiming, ActionPriority
from engine.board_evaluator import BoardEvaluator, BoardState
from engine.action_evaluator import ActionEvaluator, ActionScore
from engine.threat_assessor import ThreatAssessor, Threat
from engine.heuristic_engine import HeuristicEngine, Recommendation

class TestBoardEvaluator:
    """Test cases for board evaluator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.game_state = GameState()
        self.game_state.initialize_game(1, 2, 20)
        self.board_evaluator = BoardEvaluator(self.game_state)
    
    def test_board_state_creation(self):
        """Test creating a board state."""
        board_state = BoardState(self.game_state)
        
        assert board_state.self_life == 20
        assert board_state.opponent_life == 20
        assert board_state.life_difference == 0
        assert board_state.turn_number == 0
        assert board_state.current_phase == Phase.FIRST_MAIN
    
    def test_board_evaluation(self):
        """Test board state evaluation."""
        board_state = BoardState(self.game_state)
        evaluation = self.board_evaluator.evaluate_board_state(board_state)
        
        assert 'life_score' in evaluation
        assert 'creature_score' in evaluation
        assert 'mana_score' in evaluation
        assert 'hand_score' in evaluation
        assert 'overall_score' in evaluation
        
        # Check that scores are reasonable
        assert evaluation['overall_score'] >= 0.0
    
    def test_life_evaluation(self):
        """Test life evaluation."""
        board_state = BoardState(self.game_state)
        
        # Test with different life totals
        board_state.self_life = 25
        board_state.opponent_life = 15
        board_state.life_difference = 10
        
        evaluation = self.board_evaluator.evaluate_board_state(board_state)
        
        # Should have positive life score
        assert evaluation['life_score'] > 0
    
    def test_creature_evaluation(self):
        """Test creature evaluation."""
        board_state = BoardState(self.game_state)
        
        # Add creatures to self player
        creature = CardInfo(
            instance_id=1,
            grp_id=12345,
            name="Grizzly Bears",
            card_types=[CardType.CREATURE],
            power=2,
            toughness=2,
            controller=1,
            zone_id=1,
            zone_type=ZoneType.BATTLEFIELD
        )
        
        board_state.self_creatures.append(creature)
        
        evaluation = self.board_evaluator.evaluate_board_state(board_state)
        
        # Should have positive creature score
        assert evaluation['creature_score'] > 0
    
    def test_mana_evaluation(self):
        """Test mana evaluation."""
        board_state = BoardState(self.game_state)
        
        # Add mana to self player
        board_state.self_mana = {'total': 5, 'white': 2, 'blue': 1, 'red': 2}
        
        evaluation = self.board_evaluator.evaluate_board_state(board_state)
        
        # Should have positive mana score
        assert evaluation['mana_score'] > 0
    
    def test_threat_evaluation(self):
        """Test threat evaluation."""
        board_state = BoardState(self.game_state)
        
        # Add threatening creature to opponent
        threat_creature = CardInfo(
            instance_id=2,
            grp_id=12346,
            name="Lightning Bolt",
            card_types=[CardType.CREATURE],
            power=3,
            toughness=1,
            controller=2,
            zone_id=1,
            zone_type=ZoneType.BATTLEFIELD
        )
        
        board_state.opponent_creatures.append(threat_creature)
        
        evaluation = self.board_evaluator.evaluate_board_state(board_state)
        
        # Should have negative threat score
        assert evaluation['threat_score'] < 0
    
    def test_lethal_evaluation(self):
        """Test lethal evaluation."""
        board_state = BoardState(self.game_state)
        
        # Set up lethal situation
        board_state.self_life = 5
        board_state.opponent_creatures = [
            CardInfo(
                instance_id=2,
                grp_id=12346,
                name="Lightning Bolt",
                card_types=[CardType.CREATURE],
                power=5,
                toughness=1,
                controller=2,
                zone_id=1,
                zone_type=ZoneType.BATTLEFIELD
            )
        ]
        
        evaluation = self.board_evaluator.evaluate_board_state(board_state)
        
        # Should have negative lethal score
        assert evaluation['lethal_score'] < 0
    
    def test_board_summary(self):
        """Test getting board summary."""
        board_state = BoardState(self.game_state)
        summary = self.board_evaluator.get_board_summary(board_state)
        
        assert 'turn_number' in summary
        assert 'current_phase' in summary
        assert 'self_life' in summary
        assert 'opponent_life' in summary
        assert 'life_difference' in summary

class TestActionEvaluator:
    """Test cases for action evaluator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.game_state = GameState()
        self.game_state.initialize_game(1, 2, 20)
        self.action_evaluator = ActionEvaluator(self.game_state)
    
    def test_action_evaluation(self):
        """Test action evaluation."""
        from rules.action_types import PassPriorityAction
        
        action = PassPriorityAction(player_id=1)
        score, reasoning = self.action_evaluator._evaluate_single_action(action, 1)
        
        assert score >= 0.0
        assert len(reasoning) > 0
    
    def test_play_land_evaluation(self):
        """Test playing a land evaluation."""
        from rules.action_types import PlayLandAction
        
        land = CardInfo(
            instance_id=1,
            grp_id=12345,
            name="Plains",
            card_types=[CardType.LAND],
            controller=1,
            zone_id=2,
            zone_type=ZoneType.HAND
        )
        
        action = PlayLandAction(player_id=1, card=land)
        score, reasoning = self.action_evaluator._evaluate_single_action(action, 1)
        
        assert score >= 0.0
        assert len(reasoning) > 0
    
    def test_cast_spell_evaluation(self):
        """Test casting a spell evaluation."""
        from rules.action_types import CastSpellAction
        
        spell = CardInfo(
            instance_id=1,
            grp_id=12345,
            name="Lightning Bolt",
            card_types=[CardType.INSTANT],
            mana_cost="{R}",
            controller=1,
            zone_id=2,
            zone_type=ZoneType.HAND
        )
        
        action = CastSpellAction(player_id=1, spell=spell, mana_cost="{R}")
        score, reasoning = self.action_evaluator._evaluate_single_action(action, 1)
        
        assert score >= 0.0
        assert len(reasoning) > 0
    
    def test_activate_ability_evaluation(self):
        """Test activating an ability evaluation."""
        from rules.action_types import ActivateAbilityAction
        
        creature = CardInfo(
            instance_id=1,
            grp_id=12345,
            name="Rhys the Redeemed",
            card_types=[CardType.CREATURE],
            abilities=["{G}{G}: Create a 1/1 green Elf Warrior creature token"],
            controller=1,
            zone_id=1,
            zone_type=ZoneType.BATTLEFIELD
        )
        
        action = ActivateAbilityAction(
            player_id=1,
            source=creature,
            ability="{G}{G}: Create a 1/1 green Elf Warrior creature token"
        )
        score, reasoning = self.action_evaluator._evaluate_single_action(action, 1)
        
        assert score >= 0.0
        assert len(reasoning) > 0
    
    def test_declare_attackers_evaluation(self):
        """Test declaring attackers evaluation."""
        from rules.action_types import DeclareAttackersAction
        
        creature = CardInfo(
            instance_id=1,
            grp_id=12345,
            name="Grizzly Bears",
            card_types=[CardType.CREATURE],
            power=2,
            toughness=2,
            controller=1,
            zone_id=1,
            zone_type=ZoneType.BATTLEFIELD
        )
        
        action = DeclareAttackersAction(player_id=1, attackers=[creature])
        score, reasoning = self.action_evaluator._evaluate_single_action(action, 1)
        
        assert score >= 0.0
        assert len(reasoning) > 0
    
    def test_action_scoring_weights(self):
        """Test action scoring weights."""
        weights = self.action_evaluator.get_scoring_weights()
        
        assert 'lethal_damage' in weights
        assert 'prevent_lethal' in weights
        assert 'card_advantage' in weights
        assert 'mana_efficiency' in weights
    
    def test_set_scoring_weights(self):
        """Test setting scoring weights."""
        new_weights = {'lethal_damage': 15.0, 'card_advantage': 5.0}
        self.action_evaluator.set_scoring_weights(new_weights)
        
        weights = self.action_evaluator.get_scoring_weights()
        assert weights['lethal_damage'] == 15.0
        assert weights['card_advantage'] == 5.0

class TestThreatAssessor:
    """Test cases for threat assessor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.game_state = GameState()
        self.game_state.initialize_game(1, 2, 20)
        self.threat_assessor = ThreatAssessor(self.game_state)
    
    def test_threat_assessment(self):
        """Test threat assessment."""
        threats = self.threat_assessor.assess_threats(1)
        
        # Should return a list of threats
        assert isinstance(threats, list)
    
    def test_opponent_creature_threats(self):
        """Test assessing opponent creature threats."""
        # Add threatening creature to opponent
        opponent = self.game_state.get_opponent_player()
        if opponent:
            threat_creature = CardInfo(
                instance_id=2,
                grp_id=12346,
                name="Lightning Bolt",
                card_types=[CardType.CREATURE],
                power=3,
                toughness=1,
                controller=2,
                zone_id=1,
                zone_type=ZoneType.BATTLEFIELD
            )
            
            opponent.battlefield.add_card(threat_creature)
            
            threats = self.threat_assessor.assess_threats(1)
            
            # Should have threats
            assert len(threats) > 0
    
    def test_lethal_threats(self):
        """Test lethal threat detection."""
        # Set up lethal situation
        self_player = self.game_state.get_self_player()
        if self_player:
            self_player.life_total = 5
            
            opponent = self.game_state.get_opponent_player()
            if opponent:
                lethal_creature = CardInfo(
                    instance_id=2,
                    grp_id=12346,
                    name="Lightning Bolt",
                    card_types=[CardType.CREATURE],
                    power=5,
                    toughness=1,
                    controller=2,
                    zone_id=1,
                    zone_type=ZoneType.BATTLEFIELD
                )
                
                opponent.battlefield.add_card(lethal_creature)
                
                threats = self.threat_assessor.assess_threats(1)
                
                # Should have lethal threats
                lethal_threats = [t for t in threats if t.priority >= 8]
                assert len(lethal_threats) > 0
    
    def test_immediate_threats(self):
        """Test getting immediate threats."""
        immediate_threats = self.threat_assessor.get_immediate_threats(1)
        
        # Should return a list
        assert isinstance(immediate_threats, list)
    
    def test_high_priority_threats(self):
        """Test getting high priority threats."""
        high_priority_threats = self.threat_assessor.get_high_priority_threats(1)
        
        # Should return a list
        assert isinstance(high_priority_threats, list)
    
    def test_threat_summary(self):
        """Test getting threat summary."""
        summary = self.threat_assessor.get_threat_summary(1)
        
        assert 'total_threats' in summary
        assert 'immediate_threats' in summary
        assert 'high_priority_threats' in summary
        assert 'threat_types' in summary
        assert 'highest_priority' in summary
        assert 'threats' in summary
    
    def test_threat_weights(self):
        """Test threat assessment weights."""
        weights = self.threat_assessor.get_threat_weights()
        
        assert 'lethal_damage' in weights
        assert 'immediate_lethal' in weights
        assert 'high_power_creature' in weights
        assert 'flying_creature' in weights
    
    def test_set_threat_weights(self):
        """Test setting threat weights."""
        new_weights = {'lethal_damage': 20.0, 'high_power_creature': 10.0}
        self.threat_assessor.set_threat_weights(new_weights)
        
        weights = self.threat_assessor.get_threat_weights()
        assert weights['lethal_damage'] == 20.0
        assert weights['high_power_creature'] == 10.0

class TestHeuristicEngine:
    """Test cases for heuristic engine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.game_state = GameState()
        self.game_state.initialize_game(1, 2, 20)
        self.heuristic_engine = HeuristicEngine(self.game_state)
    
    def test_get_recommendations(self):
        """Test getting action recommendations."""
        recommendations = self.heuristic_engine.get_recommendations(1)
        
        # Should return a list of recommendations
        assert isinstance(recommendations, list)
        
        # Each recommendation should have required fields
        for rec in recommendations:
            assert hasattr(rec, 'action')
            assert hasattr(rec, 'score')
            assert hasattr(rec, 'reasoning')
            assert hasattr(rec, 'priority')
            assert hasattr(rec, 'confidence')
    
    def test_get_best_action(self):
        """Test getting the best action."""
        best_action = self.heuristic_engine.get_best_action(1)
        
        # Should return a recommendation or None
        if best_action:
            assert isinstance(best_action, Recommendation)
    
    def test_get_emergency_actions(self):
        """Test getting emergency actions."""
        emergency_actions = self.heuristic_engine.get_emergency_actions(1)
        
        # Should return a list
        assert isinstance(emergency_actions, list)
    
    def test_get_board_analysis(self):
        """Test getting board analysis."""
        analysis = self.heuristic_engine.get_board_analysis(1)
        
        assert 'board_state' in analysis
        assert 'board_evaluation' in analysis
        assert 'threats' in analysis
        assert 'legal_actions' in analysis
        assert 'recommendations' in analysis
        assert 'game_status' in analysis
        assert 'turn_number' in analysis
        assert 'current_phase' in analysis
        assert 'active_player' in analysis
    
    def test_engine_status(self):
        """Test getting engine status."""
        status = self.heuristic_engine.get_engine_status()
        
        assert 'max_recommendations' in status
        assert 'min_confidence_threshold' in status
        assert 'lethal_priority_boost' in status
        assert 'board_evaluator_weights' in status
        assert 'action_evaluator_weights' in status
        assert 'threat_assessor_weights' in status
    
    def test_set_engine_settings(self):
        """Test setting engine settings."""
        settings = {
            'max_recommendations': 10,
            'min_confidence_threshold': 0.5,
            'lethal_priority_boost': 10.0
        }
        
        self.heuristic_engine.set_engine_settings(settings)
        
        status = self.heuristic_engine.get_engine_status()
        assert status['max_recommendations'] == 10
        assert status['min_confidence_threshold'] == 0.5
        assert status['lethal_priority_boost'] == 10.0
    
    def test_set_evaluation_weights(self):
        """Test setting evaluation weights."""
        weights = {
            'board': {'life_total': 2.0, 'creature_power': 3.0},
            'action': {'lethal_damage': 15.0, 'card_advantage': 5.0},
            'threat': {'lethal_damage': 20.0, 'high_power_creature': 10.0}
        }
        
        self.heuristic_engine.set_evaluation_weights(weights)
        
        # Check that weights were set
        status = self.heuristic_engine.get_engine_status()
        assert status['board_evaluator_weights']['life_total'] == 2.0
        assert status['action_evaluator_weights']['lethal_damage'] == 15.0
        assert status['threat_assessor_weights']['lethal_damage'] == 20.0

def run_manual_tests():
    """Run manual tests for heuristic evaluation."""
    print("MTGA Coach - Heuristic Evaluation Manual Tests")
    print("=" * 60)
    
    # Test 1: Board Evaluator
    print("1. Testing board evaluator...")
    from state.game_state import GameState
    from engine.board_evaluator import BoardEvaluator, BoardState
    
    game_state = GameState()
    game_state.initialize_game(1, 2, 20)
    board_evaluator = BoardEvaluator(game_state)
    
    board_state = BoardState(game_state)
    evaluation = board_evaluator.evaluate_board_state(board_state)
    
    print(f"   Board evaluation: {evaluation['overall_score']:.2f}")
    print(f"   Life score: {evaluation['life_score']:.2f}")
    print(f"   Creature score: {evaluation['creature_score']:.2f}")
    print(f"   Mana score: {evaluation['mana_score']:.2f}")
    
    # Test 2: Action Evaluator
    print("2. Testing action evaluator...")
    from engine.action_evaluator import ActionEvaluator
    from rules.action_types import PassPriorityAction
    
    action_evaluator = ActionEvaluator(game_state)
    
    action = PassPriorityAction(player_id=1)
    score, reasoning = action_evaluator._evaluate_single_action(action, 1)
    
    print(f"   Action score: {score:.2f}")
    print(f"   Reasoning: {reasoning}")
    
    # Test 3: Threat Assessor
    print("3. Testing threat assessor...")
    from engine.threat_assessor import ThreatAssessor
    
    threat_assessor = ThreatAssessor(game_state)
    threats = threat_assessor.assess_threats(1)
    
    print(f"   Threats detected: {len(threats)}")
    for threat in threats[:3]:  # Show first 3 threats
        print(f"     - {threat.description} (Priority: {threat.priority})")
    
    # Test 4: Heuristic Engine
    print("4. Testing heuristic engine...")
    from engine.heuristic_engine import HeuristicEngine
    
    heuristic_engine = HeuristicEngine(game_state)
    recommendations = heuristic_engine.get_recommendations(1)
    
    print(f"   Recommendations: {len(recommendations)}")
    for rec in recommendations[:3]:  # Show first 3 recommendations
        print(f"     - {rec.action.action_type} (Score: {rec.score:.2f}, Priority: {rec.priority})")
    
    # Test 5: Board Analysis
    print("5. Testing board analysis...")
    analysis = heuristic_engine.get_board_analysis(1)
    
    print(f"   Board state: {analysis['board_state']['self_life']} vs {analysis['board_state']['opponent_life']}")
    print(f"   Legal actions: {analysis['legal_actions']}")
    print(f"   Recommendations: {len(analysis['recommendations'])}")
    
    print("Manual tests completed!")

if __name__ == "__main__":
    run_manual_tests()
