#!/usr/bin/env python3
"""
Test Suite for Action Legality

Comprehensive tests for the action legality system.
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
from rules.action_types import (
    ActionType, ActionTiming, ActionPriority,
    PlayLandAction, CastSpellAction, ActivateAbilityAction,
    DeclareAttackersAction, DeclareBlockersAction, PassPriorityAction,
    ConcedeAction, MulliganAction, ScryAction, DrawCardAction
)
from rules.legality_engine import LegalityEngine
from rules.timing_rules import TimingRules
from rules.mana_system import ManaSystem, ManaCost
from rules.card_restrictions import CardRestrictionEngine

class TestManaCost:
    """Test cases for mana cost parsing."""
    
    def test_basic_mana_cost(self):
        """Test parsing basic mana costs."""
        cost = ManaCost("{W}")
        assert cost.white == 1
        assert cost.blue == 0
        assert cost.black == 0
        assert cost.red == 0
        assert cost.green == 0
        assert cost.colorless == 0
        assert cost.generic == 0
    
    def test_complex_mana_cost(self):
        """Test parsing complex mana costs."""
        cost = ManaCost("{2}{W}{U}{B}{R}{G}")
        assert cost.white == 1
        assert cost.blue == 1
        assert cost.black == 1
        assert cost.red == 1
        assert cost.green == 1
        assert cost.generic == 2
        assert cost.get_total_cost() == 7
    
    def test_hybrid_mana_cost(self):
        """Test parsing hybrid mana costs."""
        cost = ManaCost("{W/U}{2/U}")
        assert len(cost.hybrid) == 2
        assert "W/U" in cost.hybrid
        assert "2/U" in cost.hybrid
    
    def test_phyrexian_mana_cost(self):
        """Test parsing Phyrexian mana costs."""
        cost = ManaCost("{W/P}{U/P}")
        assert len(cost.phyrexian) == 2
        assert "W/P" in cost.phyrexian
        assert "U/P" in cost.phyrexian
    
    def test_empty_mana_cost(self):
        """Test parsing empty mana cost."""
        cost = ManaCost("")
        assert cost.get_total_cost() == 0
        assert cost.is_colorless()
    
    def test_colorless_mana_cost(self):
        """Test parsing colorless mana cost."""
        cost = ManaCost("{3}")
        assert cost.generic == 3
        assert cost.is_colorless()
        assert not cost.is_mono_colored()
    
    def test_mono_colored_mana_cost(self):
        """Test parsing mono-colored mana cost."""
        cost = ManaCost("{W}{W}{W}")
        assert cost.white == 3
        assert cost.is_mono_colored()
        assert cost.get_primary_color() == 'white'

class TestManaSystem:
    """Test cases for mana system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.game_state = GameState()
        self.game_state.initialize_game(1, 2, 20)
        self.mana_system = ManaSystem(self.game_state)
    
    def test_can_pay_basic_mana_cost(self):
        """Test paying basic mana costs."""
        player = self.game_state.get_self_player()
        
        # Add mana to pool
        player.mana_pool.white = 2
        player.mana_pool.blue = 1
        
        # Test paying cost
        assert self.mana_system.can_pay_cost("{W}", player)
        assert self.mana_system.can_pay_cost("{U}", player)
        assert not self.mana_system.can_pay_cost("{B}", player)
        assert not self.mana_system.can_pay_cost("{W}{W}{W}", player)
    
    def test_pay_basic_mana_cost(self):
        """Test paying basic mana costs."""
        player = self.game_state.get_self_player()
        
        # Add mana to pool
        player.mana_pool.white = 2
        player.mana_pool.blue = 1
        
        # Pay cost
        assert self.mana_system.pay_cost("{W}{U}", player)
        assert player.mana_pool.white == 1
        assert player.mana_pool.blue == 0
    
    def test_cannot_pay_insufficient_mana(self):
        """Test that insufficient mana prevents payment."""
        player = self.game_state.get_self_player()
        
        # Add insufficient mana
        player.mana_pool.white = 1
        
        # Try to pay higher cost
        assert not self.mana_system.can_pay_cost("{W}{W}", player)
        assert not self.mana_system.pay_cost("{W}{W}", player)
    
    def test_generate_mana(self):
        """Test generating mana."""
        player = self.game_state.get_self_player()
        
        # Generate mana
        assert self.mana_system.generate_mana(player, 'white', 2)
        assert player.mana_pool.white == 2
        
        assert self.mana_system.generate_mana(player, 'blue', 1)
        assert player.mana_pool.blue == 1
    
    def test_mana_pool_summary(self):
        """Test getting mana pool summary."""
        player = self.game_state.get_self_player()
        
        # Add mana
        player.mana_pool.white = 2
        player.mana_pool.blue = 1
        
        summary = self.mana_system.get_mana_pool_summary(player)
        
        assert summary['white'] == 2
        assert summary['blue'] == 1
        assert summary['total'] == 3

class TestCardRestrictions:
    """Test cases for card restrictions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.game_state = GameState()
        self.game_state.initialize_game(1, 2, 20)
        self.restriction_engine = CardRestrictionEngine(self.game_state)
    
    def test_can_play_land(self):
        """Test playing a land."""
        player = self.game_state.get_self_player()
        
        # Create land card
        land = CardInfo(
            instance_id=1,
            grp_id=12345,
            name="Plains",
            card_types=[CardType.LAND],
            controller=1,
            zone_id=2,
            zone_type=ZoneType.HAND
        )
        
        # Add to hand
        player.hand.add_card(land)
        
        # Test playing land
        assert self.restriction_engine.can_play_card(land, player)
        
        # Play the land
        player.battlefield.add_card(land)
        player.hand.remove_card(land.instance_id)
        player.has_played_land_this_turn = True
        
        # Test playing another land
        land2 = CardInfo(
            instance_id=2,
            grp_id=12346,
            name="Island",
            card_types=[CardType.LAND],
            controller=1,
            zone_id=2,
            zone_type=ZoneType.HAND
        )
        
        player.hand.add_card(land2)
        assert not self.restriction_engine.can_play_card(land2, player)
    
    def test_can_play_legendary(self):
        """Test playing legendary cards."""
        player = self.game_state.get_self_player()
        
        # Create legendary creature
        legendary = CardInfo(
            instance_id=1,
            grp_id=12345,
            name="Gideon, Champion of Justice",
            card_types=[CardType.PLANESWALKER],
            type_line="Legendary Planeswalker — Gideon",
            controller=1,
            zone_id=2,
            zone_type=ZoneType.HAND
        )
        
        # Add to hand
        player.hand.add_card(legendary)
        
        # Test playing legendary
        assert self.restriction_engine.can_play_card(legendary, player)
        
        # Play the legendary
        player.battlefield.add_card(legendary)
        player.hand.remove_card(legendary.instance_id)
        
        # Test playing another legendary with same name
        legendary2 = CardInfo(
            instance_id=2,
            grp_id=12346,
            name="Gideon, Champion of Justice",
            card_types=[CardType.PLANESWALKER],
            type_line="Legendary Planeswalker — Gideon",
            controller=1,
            zone_id=2,
            zone_type=ZoneType.HAND
        )
        
        player.hand.add_card(legendary2)
        assert not self.restriction_engine.can_play_card(legendary2, player)
    
    def test_can_activate_ability(self):
        """Test activating abilities."""
        player = self.game_state.get_self_player()
        
        # Create creature with ability
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
        
        # Add to battlefield
        player.battlefield.add_card(creature)
        
        # Test activating ability
        assert self.restriction_engine.can_activate_ability(
            creature, 
            "{G}{G}: Create a 1/1 green Elf Warrior creature token", 
            player
        )
    
    def test_can_attack_with_creature(self):
        """Test attacking with creatures."""
        player = self.game_state.get_self_player()
        
        # Create creature
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
        
        # Add to battlefield
        player.battlefield.add_card(creature)
        
        # Test attacking
        assert self.restriction_engine.can_attack_with(creature, player)
    
    def test_can_block_with_creature(self):
        """Test blocking with creatures."""
        player = self.game_state.get_self_player()
        
        # Create creature
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
        
        # Add to battlefield
        player.battlefield.add_card(creature)
        
        # Create attacker
        attacker = CardInfo(
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
        
        # Test blocking
        assert self.restriction_engine.can_block_with(creature, attacker, player)

class TestTimingRules:
    """Test cases for timing rules."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.game_state = GameState()
        self.game_state.initialize_game(1, 2, 20)
        self.timing_rules = TimingRules(self.game_state)
    
    def test_can_perform_action_during_main_phase(self):
        """Test performing actions during main phase."""
        # Set to main phase
        self.game_state.set_phase(Phase.FIRST_MAIN)
        
        # Create action
        from rules.action_types import PlayLandAction, CardInfo, CardType, ZoneType
        
        land = CardInfo(
            instance_id=1,
            grp_id=12345,
            name="Plains",
            card_types=[CardType.LAND],
            controller=1,
            zone_id=2,
            zone_type=ZoneType.HAND
        )
        
        action = PlayLandAction(
            player_id=1,
            card=land
        )
        
        # Test action
        assert self.timing_rules.can_perform_action(action, 1)
    
    def test_cannot_perform_action_during_wrong_phase(self):
        """Test that actions cannot be performed during wrong phase."""
        # Set to combat phase
        self.game_state.set_phase(Phase.COMBAT_BEGIN)
        
        # Create action
        from rules.action_types import PlayLandAction, CardInfo, CardType, ZoneType
        
        land = CardInfo(
            instance_id=1,
            grp_id=12345,
            name="Plains",
            card_types=[CardType.LAND],
            controller=1,
            zone_id=2,
            zone_type=ZoneType.HAND
        )
        
        action = PlayLandAction(
            player_id=1,
            card=land
        )
        
        # Test action
        assert not self.timing_rules.can_perform_action(action, 1)
    
    def test_priority_system(self):
        """Test priority system."""
        # Set active player
        self.game_state.set_active_player(1)
        
        # Test priority
        assert self.timing_rules._player_has_priority(1)
        assert not self.timing_rules._player_has_priority(2)
        
        # Pass priority
        assert self.timing_rules.pass_priority(1)
        
        # Test priority after passing
        assert not self.timing_rules._player_has_priority(1)
        assert self.timing_rules._player_has_priority(2)
    
    def test_priority_info(self):
        """Test getting priority information."""
        # Set active player
        self.game_state.set_active_player(1)
        
        # Get priority info
        info = self.timing_rules.get_priority_info()
        
        assert info['active_player'] == 1
        assert info['current_phase'] == Phase.FIRST_MAIN
        assert info['turn_number'] == 0

class TestLegalityEngine:
    """Test cases for legality engine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.game_state = GameState()
        self.game_state.initialize_game(1, 2, 20)
        self.legality_engine = LegalityEngine(self.game_state)
    
    def test_get_legal_actions(self):
        """Test getting legal actions."""
        # Get legal actions for player 1
        actions = self.legality_engine.get_legal_actions(1)
        
        # Should have some legal actions
        assert len(actions) > 0
        
        # Check action types
        action_types = [action.action_type for action in actions]
        assert ActionType.PASS_PRIORITY in action_types
        assert ActionType.CONCEDE in action_types
    
    def test_is_action_legal(self):
        """Test checking if an action is legal."""
        # Create action
        from rules.action_types import PassPriorityAction
        
        action = PassPriorityAction(player_id=1)
        
        # Test legality
        assert self.legality_engine.is_action_legal(action)
    
    def test_illegal_action(self):
        """Test illegal action."""
        # Create illegal action
        from rules.action_types import PlayLandAction, CardInfo, CardType, ZoneType
        
        land = CardInfo(
            instance_id=1,
            grp_id=12345,
            name="Plains",
            card_types=[CardType.LAND],
            controller=1,
            zone_id=2,
            zone_type=ZoneType.HAND
        )
        
        action = PlayLandAction(
            player_id=1,
            card=land
        )
        
        # Test legality (should be illegal because card not in hand)
        assert not self.legality_engine.is_action_legal(action)
    
    def test_legal_actions_caching(self):
        """Test legal actions caching."""
        # Get legal actions first time
        actions1 = self.legality_engine.get_legal_actions(1)
        
        # Get legal actions second time (should use cache)
        actions2 = self.legality_engine.get_legal_actions(1)
        
        # Should be the same
        assert len(actions1) == len(actions2)
        assert all(action1.action_type == action2.action_type 
                  for action1, action2 in zip(actions1, actions2))

def run_manual_tests():
    """Run manual tests for action legality."""
    print("MTGA Coach - Action Legality Manual Tests")
    print("=" * 50)
    
    # Test 1: Mana Cost Parsing
    print("1. Testing mana cost parsing...")
    from rules.mana_system import ManaCost
    
    cost = ManaCost("{2}{W}{U}")
    print(f"   Parsed cost: {cost.cost_string}")
    print(f"   White: {cost.white}, Blue: {cost.blue}, Generic: {cost.generic}")
    print(f"   Total cost: {cost.get_total_cost()}")
    
    # Test 2: Mana System
    print("2. Testing mana system...")
    from state.game_state import GameState
    from rules.mana_system import ManaSystem
    
    game_state = GameState()
    game_state.initialize_game(1, 2, 20)
    mana_system = ManaSystem(game_state)
    
    player = game_state.get_self_player()
    player.mana_pool.white = 2
    player.mana_pool.blue = 1
    
    print(f"   Can pay {{W}}: {mana_system.can_pay_cost('{W}', player)}")
    print(f"   Can pay {{W}}{{U}}: {mana_system.can_pay_cost('{W}{U}', player)}")
    print(f"   Can pay {{B}}: {mana_system.can_pay_cost('{B}', player)}")
    
    # Test 3: Card Restrictions
    print("3. Testing card restrictions...")
    from rules.card_restrictions import CardRestrictionEngine
    
    restriction_engine = CardRestrictionEngine(game_state)
    
    # Create test card
    from parser.events import CardInfo, CardType, ZoneType
    
    land = CardInfo(
        instance_id=1,
        grp_id=12345,
        name="Plains",
        card_types=[CardType.LAND],
        controller=1,
        zone_id=2,
        zone_type=ZoneType.HAND
    )
    
    player.hand.add_card(land)
    
    print(f"   Can play land: {restriction_engine.can_play_card(land, player)}")
    
    # Test 4: Timing Rules
    print("4. Testing timing rules...")
    from rules.timing_rules import TimingRules
    
    timing_rules = TimingRules(game_state)
    
    # Set to main phase
    game_state.set_phase(Phase.FIRST_MAIN)
    
    from rules.action_types import PlayLandAction
    
    action = PlayLandAction(
        player_id=1,
        card=land
    )
    
    print(f"   Can perform action: {timing_rules.can_perform_action(action, 1)}")
    
    # Test 5: Legality Engine
    print("5. Testing legality engine...")
    from rules.legality_engine import LegalityEngine
    
    legality_engine = LegalityEngine(game_state)
    
    legal_actions = legality_engine.get_legal_actions(1)
    print(f"   Legal actions: {len(legal_actions)}")
    
    for action in legal_actions[:3]:  # Show first 3 actions
        print(f"     - {action.action_type}")
    
    print("Manual tests completed!")

if __name__ == "__main__":
    run_manual_tests()
