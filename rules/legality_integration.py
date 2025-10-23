#!/usr/bin/env python3
"""
Legality Integration

Integration layer that combines all legality components.
Provides a unified interface for determining legal actions.
"""

from typing import List, Dict, Optional, Set, Any
from datetime import datetime
import logging

from state.game_state import GameState, GameStatus
from state.player_state import PlayerState
from parser.events import CardInfo, CardType, ZoneType
from rules.action_types import Action, ActionType, ActionTiming, ActionPriority
from rules.legality_engine import LegalityEngine
from rules.timing_rules import TimingRules
from rules.mana_system import ManaSystem
from rules.card_restrictions import CardRestrictionEngine

logger = logging.getLogger(__name__)

class LegalityIntegration:
    """Integration layer for all legality components."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.legality_engine = LegalityEngine(game_state)
        self.timing_rules = TimingRules(game_state)
        self.mana_system = ManaSystem(game_state)
        self.card_restrictions = CardRestrictionEngine(game_state)
        
        # Cache for legal actions
        self.legal_actions_cache: Dict[int, List[Action]] = {}
        self.cache_timestamp: Optional[datetime] = None
        self.cache_duration = 1.0  # seconds
    
    def get_legal_actions(self, player_id: int, force_refresh: bool = False) -> List[Action]:
        """Get all legal actions for a player."""
        # Check cache
        if not force_refresh and self._is_cache_valid():
            cached_actions = self.legal_actions_cache.get(player_id, [])
            if cached_actions:
                return cached_actions
        
        # Generate legal actions
        legal_actions = self._generate_legal_actions(player_id)
        
        # Cache results
        self.legal_actions_cache[player_id] = legal_actions
        self.cache_timestamp = datetime.now()
        
        return legal_actions
    
    def is_action_legal(self, action: Action) -> bool:
        """Check if a specific action is legal."""
        try:
            # Check basic legality
            if not self.legality_engine.is_action_legal(action):
                return False
            
            # Check timing
            if not self.timing_rules.can_perform_action(action, action.player_id):
                return False
            
            # Check card restrictions
            if not self._check_card_restrictions(action):
                return False
            
            # Check mana requirements
            if not self._check_mana_requirements(action):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking action legality: {e}")
            return False
    
    def can_play_card(self, card: CardInfo, player: PlayerState) -> bool:
        """Check if a player can play a card."""
        try:
            # Check card restrictions
            if not self.card_restrictions.can_play_card(card, player):
                return False
            
            # Check mana cost
            if not self.mana_system.can_pay_cost(card.mana_cost, player):
                return False
            
            # Check timing
            if not self._check_card_timing(card, player):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if card can be played: {e}")
            return False
    
    def can_activate_ability(self, card: CardInfo, ability: str, player: PlayerState) -> bool:
        """Check if a player can activate an ability."""
        try:
            # Check card restrictions
            if not self.card_restrictions.can_activate_ability(card, ability, player):
                return False
            
            # Check timing
            if not self.timing_rules.can_perform_action(None, player.player_id):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if ability can be activated: {e}")
            return False
    
    def can_attack_with(self, creature: CardInfo, player: PlayerState) -> bool:
        """Check if a player can attack with a creature."""
        try:
            # Check card restrictions
            if not self.card_restrictions.can_attack_with(creature, player):
                return False
            
            # Check timing
            if not self._check_attack_timing(player):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if creature can attack: {e}")
            return False
    
    def can_block_with(self, creature: CardInfo, attacker: CardInfo, player: PlayerState) -> bool:
        """Check if a player can block with a creature."""
        try:
            # Check card restrictions
            if not self.card_restrictions.can_block_with(creature, attacker, player):
                return False
            
            # Check timing
            if not self._check_block_timing(player):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if creature can block: {e}")
            return False
    
    def pay_mana_cost(self, cost: str, player: PlayerState) -> bool:
        """Pay a mana cost."""
        return self.mana_system.pay_cost(cost, player)
    
    def generate_mana(self, player: PlayerState, color: str, amount: int = 1) -> bool:
        """Generate mana for a player."""
        return self.mana_system.generate_mana(player, color, amount)
    
    def get_mana_pool_summary(self, player: PlayerState) -> Dict[str, Any]:
        """Get a summary of a player's mana pool."""
        return self.mana_system.get_mana_pool_summary(player)
    
    def get_priority_info(self) -> Dict[str, Any]:
        """Get information about current priority state."""
        return self.timing_rules.get_priority_info()
    
    def pass_priority(self, player_id: int) -> bool:
        """Pass priority for a player."""
        return self.timing_rules.pass_priority(player_id)
    
    def get_card_restrictions(self, card: CardInfo) -> List[str]:
        """Get all restrictions that apply to a card."""
        return self.card_restrictions.get_card_restrictions(card)
    
    def _generate_legal_actions(self, player_id: int) -> List[Action]:
        """Generate all legal actions for a player."""
        legal_actions = []
        
        try:
            # Get player
            player = self.game_state.get_player(player_id)
            if not player:
                return legal_actions
            
            # Generate actions based on current state
            if self.game_state.current_phase in [Phase.FIRST_MAIN, Phase.SECOND_MAIN]:
                legal_actions.extend(self._generate_main_phase_actions(player))
            
            elif self.game_state.current_phase == Phase.COMBAT_BEGIN:
                legal_actions.extend(self._generate_combat_phase_actions(player))
            
            elif self.game_state.current_phase == Phase.DECLARE_ATTACKERS:
                legal_actions.extend(self._generate_attack_actions(player))
            
            elif self.game_state.current_phase == Phase.DECLARE_BLOCKERS:
                legal_actions.extend(self._generate_block_actions(player))
            
            # Always available actions
            legal_actions.extend(self._generate_always_available_actions(player))
            
            # Validate all actions
            validated_actions = []
            for action in legal_actions:
                if self.is_action_legal(action):
                    validated_actions.append(action)
            
            return validated_actions
            
        except Exception as e:
            logger.error(f"Error generating legal actions for player {player_id}: {e}")
            return []
    
    def _generate_main_phase_actions(self, player: PlayerState) -> List[Action]:
        """Generate actions available during main phases."""
        actions = []
        
        # Play land (once per turn)
        if player.can_play_land():
            for land in player.hand.cards:
                if CardType.LAND in land.card_types:
                    if self.can_play_card(land, player):
                        from rules.action_types import PlayLandAction
                        action = PlayLandAction(
                            player_id=player.player_id,
                            card=land,
                            land_type=self._get_land_type(land)
                        )
                        actions.append(action)
        
        # Cast spells
        for spell in player.hand.cards:
            if self.can_play_card(spell, player):
                from rules.action_types import CastSpellAction
                action = CastSpellAction(
                    player_id=player.player_id,
                    spell=spell,
                    mana_cost=spell.mana_cost
                )
                actions.append(action)
        
        # Activate abilities
        for card in player.battlefield.get_all_cards():
            for ability in card.abilities:
                if self.can_activate_ability(card, ability, player):
                    from rules.action_types import ActivateAbilityAction
                    action = ActivateAbilityAction(
                        player_id=player.player_id,
                        source=card,
                        ability=ability
                    )
                    actions.append(action)
        
        return actions
    
    def _generate_combat_phase_actions(self, player: PlayerState) -> List[Action]:
        """Generate actions available during combat phase."""
        actions = []
        
        # Declare attackers
        if player.can_attack():
            creatures = player.battlefield.get_creatures()
            if creatures:
                from rules.action_types import DeclareAttackersAction
                action = DeclareAttackersAction(
                    player_id=player.player_id,
                    attackers=creatures
                )
                actions.append(action)
        
        return actions
    
    def _generate_attack_actions(self, player: PlayerState) -> List[Action]:
        """Generate actions available during declare attackers step."""
        actions = []
        
        # Declare attackers
        if player.can_attack():
            creatures = player.battlefield.get_creatures()
            if creatures:
                from rules.action_types import DeclareAttackersAction
                action = DeclareAttackersAction(
                    player_id=player.player_id,
                    attackers=creatures
                )
                actions.append(action)
        
        return actions
    
    def _generate_block_actions(self, player: PlayerState) -> List[Action]:
        """Generate actions available during declare blockers step."""
        actions = []
        
        # Declare blockers
        creatures = player.battlefield.get_creatures()
        if creatures:
            from rules.action_types import DeclareBlockersAction
            action = DeclareBlockersAction(
                player_id=player.player_id,
                blocks={}  # Would be populated based on attackers
            )
            actions.append(action)
        
        return actions
    
    def _generate_always_available_actions(self, player: PlayerState) -> List[Action]:
        """Generate actions that are always available."""
        actions = []
        
        # Pass priority
        from rules.action_types import PassPriorityAction
        actions.append(PassPriorityAction(player_id=player.player_id))
        
        # Concede
        from rules.action_types import ConcedeAction
        actions.append(ConcedeAction(player_id=player.player_id))
        
        return actions
    
    def _check_card_restrictions(self, action: Action) -> bool:
        """Check card-specific restrictions."""
        if hasattr(action, 'card'):
            return self.card_restrictions.can_play_card(action.card, self.game_state.get_player(action.player_id))
        elif hasattr(action, 'source'):
            return self.card_restrictions.can_activate_ability(action.source, action.ability, self.game_state.get_player(action.player_id))
        elif hasattr(action, 'attackers'):
            for attacker in action.attackers:
                if not self.card_restrictions.can_attack_with(attacker, self.game_state.get_player(action.player_id)):
                    return False
        elif hasattr(action, 'blocks'):
            for attacker_id, blocker_ids in action.blocks.items():
                for blocker_id in blocker_ids:
                    blocker = self.game_state.get_player(action.player_id).battlefield.get_card(blocker_id)
                    if blocker:
                        attacker = self.game_state.get_active_player().battlefield.get_card(attacker_id)
                        if attacker:
                            if not self.card_restrictions.can_block_with(blocker, attacker, self.game_state.get_player(action.player_id)):
                                return False
        
        return True
    
    def _check_mana_requirements(self, action: Action) -> bool:
        """Check mana requirements."""
        if hasattr(action, 'mana_cost') and action.mana_cost:
            player = self.game_state.get_player(action.player_id)
            if player:
                return self.mana_system.can_pay_cost(action.mana_cost, player)
        
        return True
    
    def _check_card_timing(self, card: CardInfo, player: PlayerState) -> bool:
        """Check timing requirements for playing a card."""
        # Check if it's the player's turn
        if self.game_state.active_player != player.player_id:
            return False
        
        # Check if player has priority
        if not self.timing_rules._player_has_priority(player.player_id):
            return False
        
        return True
    
    def _check_attack_timing(self, player: PlayerState) -> bool:
        """Check timing requirements for attacking."""
        # Check if it's the player's turn
        if self.game_state.active_player != player.player_id:
            return False
        
        # Check if player can attack
        if not player.can_attack():
            return False
        
        return True
    
    def _check_block_timing(self, player: PlayerState) -> bool:
        """Check timing requirements for blocking."""
        # Check if it's not the player's turn
        if self.game_state.active_player == player.player_id:
            return False
        
        return True
    
    def _get_land_type(self, land: CardInfo) -> str:
        """Get the type of land."""
        if "Basic" in land.type_line:
            return "basic"
        else:
            return "non-basic"
    
    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        if self.cache_timestamp is None:
            return False
        
        elapsed = (datetime.now() - self.cache_timestamp).total_seconds()
        return elapsed < self.cache_duration
    
    def clear_cache(self) -> None:
        """Clear the legal actions cache."""
        self.legal_actions_cache.clear()
        self.cache_timestamp = None
    
    def get_legality_summary(self, player_id: int) -> Dict[str, Any]:
        """Get a summary of legal actions for a player."""
        legal_actions = self.get_legal_actions(player_id)
        
        summary = {
            "player_id": player_id,
            "total_legal_actions": len(legal_actions),
            "action_types": list(set(action.action_type for action in legal_actions)),
            "can_play_land": any(action.action_type == ActionType.PLAY_LAND for action in legal_actions),
            "can_cast_spell": any(action.action_type == ActionType.CAST_SPELL for action in legal_actions),
            "can_activate_ability": any(action.action_type == ActionType.ACTIVATE_ABILITY for action in legal_actions),
            "can_attack": any(action.action_type == ActionType.DECLARE_ATTACKERS for action in legal_actions),
            "can_block": any(action.action_type == ActionType.DECLARE_BLOCKERS for action in legal_actions),
            "priority_info": self.get_priority_info(),
            "mana_pool": self.get_mana_pool_summary(self.game_state.get_player(player_id)) if self.game_state.get_player(player_id) else None
        }
        
        return summary
