#!/usr/bin/env python3
"""
Test Suite for Game State Management

Comprehensive tests for the game state system.
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
from state.player_state import PlayerState, PlayerType, ManaPool, Hand, Battlefield, Graveyard
from state.state_manager import StateManager
from state.state_integration import StateIntegration, StateIntegrationManager
from parser.events import GameEvent, EventType, CardInfo, CardType, ZoneType

class TestPlayerState:
    """Test cases for player state."""
    
    def test_player_creation(self):
        """Test creating a player state."""
        player = PlayerState(
            player_id=1,
            player_type=PlayerType.SELF,
            life_total=20
        )
        
        assert player.player_id == 1
        assert player.player_type == PlayerType.SELF
        assert player.life_total == 20
        assert player.hand.size() == 0
        assert player.get_creature_count() == 0
        assert player.get_land_count() == 0
    
    def test_mana_pool(self):
        """Test mana pool functionality."""
        player = PlayerState(player_id=1, player_type=PlayerType.SELF)
        
        # Test adding mana
        assert player.add_mana('r', 2)
        assert player.mana_pool.red == 2
        
        assert player.add_mana('u', 1)
        assert player.mana_pool.blue == 1
        
        # Test total mana
        assert player.mana_pool.total_mana() == 3
        
        # Test mana summary
        summary = player.get_mana_summary()
        assert summary['red'] == 2
        assert summary['blue'] == 1
        assert summary['total'] == 3
    
    def test_hand_management(self):
        """Test hand management."""
        player = PlayerState(player_id=1, player_type=PlayerType.SELF)
        
        # Create test card
        card = CardInfo(
            instance_id=1,
            grp_id=12345,
            name="Lightning Bolt",
            controller=1,
            zone_id=2,
            zone_type=ZoneType.HAND
        )
        
        # Test adding card to hand
        assert player.hand.add_card(card)
        assert player.hand.size() == 1
        
        # Test getting card
        retrieved_card = player.hand.get_card(1)
        assert retrieved_card is not None
        assert retrieved_card.name == "Lightning Bolt"
        
        # Test removing card
        removed_card = player.hand.remove_card(1)
        assert removed_card is not None
        assert removed_card.name == "Lightning Bolt"
        assert player.hand.size() == 0
    
    def test_battlefield_management(self):
        """Test battlefield management."""
        player = PlayerState(player_id=1, player_type=PlayerType.SELF)
        
        # Create test creature
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
        
        # Test adding creature to battlefield
        assert player.battlefield.add_card(creature)
        assert player.get_creature_count() == 1
        assert player.get_total_power() == 2
        assert player.get_total_toughness() == 2
        
        # Test getting creature
        retrieved_creature = player.battlefield.get_card(1)
        assert retrieved_creature is not None
        assert retrieved_creature.name == "Grizzly Bears"
        
        # Test removing creature
        removed_creature = player.battlefield.remove_card(1)
        assert removed_creature is not None
        assert removed_creature.name == "Grizzly Bears"
        assert player.get_creature_count() == 0
    
    def test_life_management(self):
        """Test life total management."""
        player = PlayerState(player_id=1, player_type=PlayerType.SELF, life_total=20)
        
        # Test taking damage
        damage_taken = player.take_damage(5)
        assert damage_taken == 5
        assert player.life_total == 15
        
        # Test gaining life
        life_gained = player.gain_life(3)
        assert life_gained == 3
        assert player.life_total == 18
        
        # Test taking more damage than life
        damage_taken = player.take_damage(25)
        assert damage_taken == 18  # Can only take as much as life total
        assert player.life_total == 0
        assert not player.is_alive()
    
    def test_turn_flags(self):
        """Test turn-specific flags."""
        player = PlayerState(player_id=1, player_type=PlayerType.SELF)
        
        # Test initial state
        assert player.can_play_land()
        assert player.can_attack()
        assert player.can_use_ability("test_ability")
        
        # Test using abilities
        assert player.use_ability("test_ability")
        assert not player.can_use_ability("test_ability")
        
        # Test resetting flags
        player.reset_turn_flags()
        assert player.can_use_ability("test_ability")

class TestGameState:
    """Test cases for game state."""
    
    def test_game_initialization(self):
        """Test game initialization."""
        game_state = GameState()
        
        # Test initial state
        assert game_state.status == GameStatus.WAITING
        assert game_state.turn_number == 0
        assert game_state.self_player is None
        assert game_state.opponent_player is None
        
        # Test initialization
        assert game_state.initialize_game(1, 2, 20)
        assert game_state.status == GameStatus.ACTIVE
        assert game_state.self_player is not None
        assert game_state.opponent_player is not None
        assert game_state.self_player.player_id == 1
        assert game_state.opponent_player.player_id == 2
    
    def test_player_management(self):
        """Test player management."""
        game_state = GameState()
        game_state.initialize_game(1, 2, 20)
        
        # Test getting players
        self_player = game_state.get_self_player()
        opponent_player = game_state.get_opponent_player()
        
        assert self_player is not None
        assert opponent_player is not None
        assert self_player.player_id == 1
        assert opponent_player.player_id == 2
        
        # Test getting player by ID
        player_1 = game_state.get_player(1)
        player_2 = game_state.get_player(2)
        player_3 = game_state.get_player(3)
        
        assert player_1 is not None
        assert player_2 is not None
        assert player_3 is None
        assert player_1.player_id == 1
        assert player_2.player_id == 2
    
    def test_phase_management(self):
        """Test phase management."""
        game_state = GameState()
        game_state.initialize_game(1, 2, 20)
        
        # Test setting phase
        assert game_state.set_phase(Phase.FIRST_MAIN, "PreCombat")
        assert game_state.current_phase == Phase.FIRST_MAIN
        assert game_state.current_step == "PreCombat"
        
        # Test phase change
        assert game_state.set_phase(Phase.COMBAT_BEGIN)
        assert game_state.current_phase == Phase.COMBAT_BEGIN
        assert game_state.current_step is None
    
    def test_turn_management(self):
        """Test turn management."""
        game_state = GameState()
        game_state.initialize_game(1, 2, 20)
        
        # Test initial turn
        assert game_state.turn_number == 0
        
        # Test advancing turn
        assert game_state.next_turn()
        assert game_state.turn_number == 1
        
        # Test setting active player
        assert game_state.set_active_player(1)
        assert game_state.active_player == 1
        assert game_state.get_active_player().player_id == 1
    
    def test_game_summary(self):
        """Test game summary generation."""
        game_state = GameState()
        game_state.initialize_game(1, 2, 20)
        
        summary = game_state.get_game_summary()
        
        assert "game_id" in summary
        assert "status" in summary
        assert "turn_number" in summary
        assert "self_player" in summary
        assert "opponent_player" in summary
        
        assert summary["status"] == GameStatus.ACTIVE
        assert summary["turn_number"] == 0
        assert summary["self_player"]["life_total"] == 20
        assert summary["opponent_player"]["life_total"] == 20
    
    def test_game_status(self):
        """Test game status management."""
        game_state = GameState()
        
        # Test initial status
        assert not game_state.is_game_active()
        assert not game_state.is_game_ended()
        
        # Test after initialization
        game_state.initialize_game(1, 2, 20)
        assert game_state.is_game_active()
        assert not game_state.is_game_ended()
        
        # Test after game end
        game_state.status = GameStatus.ENDED
        assert not game_state.is_game_active()
        assert game_state.is_game_ended()

class TestStateManager:
    """Test cases for state manager."""
    
    def test_state_manager_creation(self):
        """Test creating state manager."""
        state_manager = StateManager()
        
        assert state_manager.game_state is not None
        assert not state_manager.is_initialized
        
        # Test initialization
        assert state_manager.initialize()
        assert state_manager.is_initialized
    
    def test_event_processing(self):
        """Test event processing."""
        state_manager = StateManager()
        state_manager.initialize()
        
        # Create test event
        from parser.events import GameStartEvent, EventType
        
        event = GameStartEvent(
            event_type=EventType.GAME_START,
            player_life=20,
            opponent_life=20
        )
        
        # Test processing event
        assert state_manager.process_event(event)
        
        # Check state was updated
        game_state = state_manager.get_current_state()
        assert game_state.status == GameStatus.ACTIVE
    
    def test_state_validation(self):
        """Test state validation."""
        state_manager = StateManager()
        state_manager.initialize()
        
        # Test validation of empty state
        errors = state_manager.validate_state()
        assert isinstance(errors, list)
        
        # Test validation after game start
        from parser.events import GameStartEvent, EventType
        
        event = GameStartEvent(
            event_type=EventType.GAME_START,
            player_life=20,
            opponent_life=20
        )
        
        state_manager.process_event(event)
        errors = state_manager.validate_state()
        assert isinstance(errors, list)
    
    def test_state_statistics(self):
        """Test state statistics."""
        state_manager = StateManager()
        state_manager.initialize()
        
        stats = state_manager.get_state_statistics()
        
        assert "game_id" in stats
        assert "status" in stats
        assert "turn_number" in stats
        assert "event_count" in stats
        assert "validation_errors" in stats

class TestStateIntegration:
    """Test cases for state integration."""
    
    @pytest.mark.asyncio
    async def test_state_integration_creation(self):
        """Test creating state integration."""
        integration = StateIntegration(port=8766)  # Use different port for testing
        
        assert integration.state_manager is not None
        assert integration.event_bus is not None
        assert not integration.is_running
    
    @pytest.mark.asyncio
    async def test_state_integration_lifecycle(self):
        """Test state integration lifecycle."""
        integration = StateIntegration(port=8767)  # Use different port for testing
        
        try:
            # Test starting
            assert await integration.start()
            assert integration.is_running
            
            # Test stopping
            await integration.stop()
            assert not integration.is_running
            
        except Exception as e:
            # Clean up on error
            await integration.stop()
            raise e
    
    @pytest.mark.asyncio
    async def test_event_processing(self):
        """Test event processing in integration."""
        integration = StateIntegration(port=8768)  # Use different port for testing
        
        try:
            await integration.start()
            
            # Create test event
            from parser.events import GameStartEvent, EventType
            
            event = GameStartEvent(
                event_type=EventType.GAME_START,
                player_life=20,
                opponent_life=20
            )
            
            # Test processing event
            assert await integration.process_event(event)
            
            # Check state was updated
            assert integration.is_game_active()
            
        finally:
            await integration.stop()
    
    @pytest.mark.asyncio
    async def test_state_callbacks(self):
        """Test state change callbacks."""
        integration = StateIntegration(port=8769)  # Use different port for testing
        
        callback_events = []
        
        def test_callback(change_type: str, data: Dict[str, Any]):
            callback_events.append((change_type, data))
        
        try:
            await integration.start()
            integration.add_state_callback(test_callback)
            
            # Create test event
            from parser.events import GameStartEvent, EventType
            
            event = GameStartEvent(
                event_type=EventType.GAME_START,
                player_life=20,
                opponent_life=20
            )
            
            # Process event
            await integration.process_event(event)
            
            # Check callback was called
            assert len(callback_events) > 0
            
        finally:
            await integration.stop()

def run_manual_tests():
    """Run manual tests for state management."""
    print("MTGA Coach - State Management Manual Tests")
    print("=" * 50)
    
    # Test 1: Player State
    print("1. Testing player state...")
    player = PlayerState(player_id=1, player_type=PlayerType.SELF, life_total=20)
    print(f"   Created player with {player.life_total} life")
    
    # Test mana
    player.add_mana('r', 2)
    player.add_mana('u', 1)
    print(f"   Mana pool: {player.get_mana_summary()}")
    
    # Test hand
    card = CardInfo(
        instance_id=1,
        grp_id=12345,
        name="Lightning Bolt",
        controller=1,
        zone_id=2,
        zone_type=ZoneType.HAND
    )
    player.hand.add_card(card)
    print(f"   Hand size: {player.hand.size()}")
    
    # Test 2: Game State
    print("2. Testing game state...")
    game_state = GameState()
    game_state.initialize_game(1, 2, 20)
    print(f"   Game initialized with status: {game_state.status}")
    
    # Test 3: State Manager
    print("3. Testing state manager...")
    state_manager = StateManager()
    state_manager.initialize()
    print(f"   State manager initialized: {state_manager.is_initialized}")
    
    # Test 4: State Integration
    print("4. Testing state integration...")
    integration = StateIntegration(port=8770)
    
    async def test_integration():
        try:
            await integration.start()
            print("   State integration started")
            
            # Test event processing
            from parser.events import GameStartEvent, EventType
            
            event = GameStartEvent(
                event_type=EventType.GAME_START,
                player_life=20,
                opponent_life=20
            )
            
            success = await integration.process_event(event)
            print(f"   Event processed: {success}")
            
            # Test state summary
            summary = integration.get_game_summary()
            print(f"   Game summary: {summary['status']}")
            
        finally:
            await integration.stop()
            print("   State integration stopped")
    
    # Run async test
    asyncio.run(test_integration())
    
    print("Manual tests completed!")

if __name__ == "__main__":
    run_manual_tests()
