#!/usr/bin/env python3
"""
Card Restrictions

Handles card-specific restrictions and requirements.
Implements Magic: The Gathering card rules and limitations.
"""

from typing import List, Dict, Optional, Set, Any, Tuple
from datetime import datetime
import logging

from state.game_state import GameState
from state.player_state import PlayerState
from parser.events import CardInfo, CardType, ZoneType
from rules.action_types import Action, ActionType

logger = logging.getLogger(__name__)

class CardRestriction:
    """Represents a restriction on a card."""
    
    def __init__(self, restriction_type: str, condition: str, value: Any = None):
        self.restriction_type = restriction_type
        self.condition = condition
        self.value = value
        self.applies_to = []  # Card types this applies to
        self.exceptions = []  # Exceptions to this restriction
    
    def applies_to_card(self, card: CardInfo) -> bool:
        """Check if this restriction applies to a card."""
        if not self.applies_to:
            return True
        
        for card_type in self.applies_to:
            if card_type in card.card_types:
                return True
        
        return False
    
    def is_exception(self, card: CardInfo) -> bool:
        """Check if a card is an exception to this restriction."""
        for exception in self.exceptions:
            if exception in card.name.lower():
                return True
        
        return False

class CardRestrictionEngine:
    """Engine for handling card restrictions and requirements."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.restrictions: List[CardRestriction] = []
        self.card_specific_rules: Dict[str, List[str]] = {}
        
        # Initialize default restrictions
        self._initialize_default_restrictions()
    
    def _initialize_default_restrictions(self) -> None:
        """Initialize default Magic: The Gathering restrictions."""
        # Land restrictions
        land_restriction = CardRestriction(
            "play_land",
            "once_per_turn",
            "A player can only play one land per turn"
        )
        land_restriction.applies_to = [CardType.LAND]
        self.restrictions.append(land_restriction)
        
        # Hand size restrictions
        hand_size_restriction = CardRestriction(
            "hand_size",
            "max_seven",
            "A player's maximum hand size is seven"
        )
        self.restrictions.append(hand_size_restriction)
        
        # Legendary restrictions
        legendary_restriction = CardRestriction(
            "legendary",
            "one_per_player",
            "A player can only control one legendary permanent with the same name"
        )
        legendary_restriction.applies_to = [CardType.CREATURE, CardType.PLANESWALKER]
        self.restrictions.append(legendary_restriction)
        
        # Planeswalker restrictions
        planeswalker_restriction = CardRestriction(
            "planeswalker",
            "one_per_player",
            "A player can only control one planeswalker with the same name"
        )
        planeswalker_restriction.applies_to = [CardType.PLANESWALKER]
        self.restrictions.append(planeswalker_restriction)
        
        # Commander restrictions (for Commander format)
        commander_restriction = CardRestriction(
            "commander",
            "one_per_deck",
            "A player can only have one commander"
        )
        commander_restriction.applies_to = [CardType.CREATURE, CardType.PLANESWALKER]
        self.restrictions.append(commander_restriction)
    
    def can_play_card(self, card: CardInfo, player: PlayerState) -> bool:
        """Check if a player can play a card."""
        try:
            # Check basic restrictions
            if not self._check_basic_restrictions(card, player):
                return False
            
            # Check card-specific restrictions
            if not self._check_card_specific_restrictions(card, player):
                return False
            
            # Check zone restrictions
            if not self._check_zone_restrictions(card, player):
                return False
            
            # Check timing restrictions
            if not self._check_timing_restrictions(card, player):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if card can be played: {e}")
            return False
    
    def can_activate_ability(self, card: CardInfo, ability: str, player: PlayerState) -> bool:
        """Check if a player can activate an ability."""
        try:
            # Check if card is on battlefield
            if not self._is_card_on_battlefield(card, player):
                return False
            
            # Check if ability can be activated
            if not self._can_activate_ability_type(ability, card, player):
                return False
            
            # Check if player has priority
            if not self._player_has_priority(player):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if ability can be activated: {e}")
            return False
    
    def can_attack_with(self, creature: CardInfo, player: PlayerState) -> bool:
        """Check if a player can attack with a creature."""
        try:
            # Check if creature is on battlefield
            if not self._is_card_on_battlefield(creature, player):
                return False
            
            # Check if creature can attack
            if not self._creature_can_attack(creature, player):
                return False
            
            # Check if it's the player's turn
            if self.game_state.active_player != player.player_id:
                return False
            
            # Check if player can attack
            if not player.can_attack():
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if creature can attack: {e}")
            return False
    
    def can_block_with(self, creature: CardInfo, attacker: CardInfo, player: PlayerState) -> bool:
        """Check if a player can block with a creature."""
        try:
            # Check if creature is on battlefield
            if not self._is_card_on_battlefield(creature, player):
                return False
            
            # Check if creature can block
            if not self._creature_can_block(creature, attacker, player):
                return False
            
            # Check if it's not the player's turn
            if self.game_state.active_player == player.player_id:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if creature can block: {e}")
            return False
    
    def _check_basic_restrictions(self, card: CardInfo, player: PlayerState) -> bool:
        """Check basic restrictions for playing a card."""
        # Check hand size
        if player.hand.size() >= player.max_hand_size:
            return False
        
        # Check if card is in hand
        if not player.hand.get_card(card.instance_id):
            return False
        
        return True
    
    def _check_card_specific_restrictions(self, card: CardInfo, player: PlayerState) -> bool:
        """Check card-specific restrictions."""
        # Check legendary restrictions
        if self._is_legendary(card):
            if not self._can_play_legendary(card, player):
                return False
        
        # Check planeswalker restrictions
        if CardType.PLANESWALKER in card.card_types:
            if not self._can_play_planeswalker(card, player):
                return False
        
        # Check land restrictions
        if CardType.LAND in card.card_types:
            if not self._can_play_land(card, player):
                return False
        
        return True
    
    def _check_zone_restrictions(self, card: CardInfo, player: PlayerState) -> bool:
        """Check zone restrictions for playing a card."""
        # Check if card is in the correct zone
        if card.zone_type != ZoneType.HAND:
            return False
        
        # Check if card is in the player's hand
        if not player.hand.get_card(card.instance_id):
            return False
        
        return True
    
    def _check_timing_restrictions(self, card: CardInfo, player: PlayerState) -> bool:
        """Check timing restrictions for playing a card."""
        # Check if it's the player's turn (for most cards)
        if self.game_state.active_player != player.player_id:
            return False
        
        # Check if player has priority
        if not self._player_has_priority(player):
            return False
        
        return True
    
    def _is_card_on_battlefield(self, card: CardInfo, player: PlayerState) -> bool:
        """Check if a card is on the battlefield."""
        return player.battlefield.get_card(card.instance_id) is not None
    
    def _can_activate_ability_type(self, ability: str, card: CardInfo, player: PlayerState) -> bool:
        """Check if an ability type can be activated."""
        # Check if ability is in the card's abilities
        if ability not in card.abilities:
            return False
        
        # Check if player can use this ability
        if not player.can_use_ability(ability):
            return False
        
        return True
    
    def _player_has_priority(self, player: PlayerState) -> bool:
        """Check if a player has priority."""
        # Simplified priority check
        return self.game_state.active_player == player.player_id
    
    def _creature_can_attack(self, creature: CardInfo, player: PlayerState) -> bool:
        """Check if a creature can attack."""
        # Check if creature has summoning sickness
        if self._has_summoning_sickness(creature, player):
            return False
        
        # Check if creature is tapped
        if self._is_creature_tapped(creature):
            return False
        
        # Check if creature has attack restrictions
        if self._has_attack_restrictions(creature):
            return False
        
        return True
    
    def _creature_can_block(self, creature: CardInfo, attacker: CardInfo, player: PlayerState) -> bool:
        """Check if a creature can block."""
        # Check if creature is tapped
        if self._is_creature_tapped(creature):
            return False
        
        # Check if creature has block restrictions
        if self._has_block_restrictions(creature):
            return False
        
        # Check if creature can block the attacker
        if not self._can_block_attacker(creature, attacker):
            return False
        
        return True
    
    def _is_legendary(self, card: CardInfo) -> bool:
        """Check if a card is legendary."""
        return 'legendary' in card.type_line.lower()
    
    def _can_play_legendary(self, card: CardInfo, player: PlayerState) -> bool:
        """Check if a player can play a legendary card."""
        # Check if player already controls a legendary with the same name
        for battlefield_card in player.battlefield.get_all_cards():
            if (battlefield_card.name == card.name and 
                self._is_legendary(battlefield_card)):
                return False
        
        return True
    
    def _can_play_planeswalker(self, card: CardInfo, player: PlayerState) -> bool:
        """Check if a player can play a planeswalker."""
        # Check if player already controls a planeswalker with the same name
        for battlefield_card in player.battlefield.get_all_cards():
            if (battlefield_card.name == card.name and 
                CardType.PLANESWALKER in battlefield_card.card_types):
                return False
        
        return True
    
    def _can_play_land(self, card: CardInfo, player: PlayerState) -> bool:
        """Check if a player can play a land."""
        # Check if player has already played a land this turn
        if not player.can_play_land():
            return False
        
        return True
    
    def _has_summoning_sickness(self, creature: CardInfo, player: PlayerState) -> bool:
        """Check if a creature has summoning sickness."""
        # Simplified summoning sickness check
        # In a real implementation, this would track when the creature entered the battlefield
        return False
    
    def _is_creature_tapped(self, creature: CardInfo) -> bool:
        """Check if a creature is tapped."""
        # Simplified tapped check
        # In a real implementation, this would check the creature's tapped state
        return False
    
    def _has_attack_restrictions(self, creature: CardInfo) -> bool:
        """Check if a creature has attack restrictions."""
        # Check for specific keywords that prevent attacking
        for keyword in creature.keywords:
            if keyword.lower() in ['defender', 'can\'t attack']:
                return True
        
        return False
    
    def _has_block_restrictions(self, creature: CardInfo) -> bool:
        """Check if a creature has block restrictions."""
        # Check for specific keywords that prevent blocking
        for keyword in creature.keywords:
            if keyword.lower() in ['can\'t block']:
                return True
        
        return False
    
    def _can_block_attacker(self, creature: CardInfo, attacker: CardInfo) -> bool:
        """Check if a creature can block a specific attacker."""
        # Check for specific blocking restrictions
        for keyword in creature.keywords:
            if keyword.lower() in ['can only block']:
                # Would need to check specific restrictions
                pass
        
        return True
    
    def get_card_restrictions(self, card: CardInfo) -> List[str]:
        """Get all restrictions that apply to a card."""
        restrictions = []
        
        for restriction in self.restrictions:
            if restriction.applies_to_card(card) and not restriction.is_exception(card):
                restrictions.append(restriction.condition)
        
        return restrictions
    
    def add_restriction(self, restriction: CardRestriction) -> None:
        """Add a new restriction."""
        self.restrictions.append(restriction)
    
    def remove_restriction(self, restriction_type: str) -> bool:
        """Remove a restriction by type."""
        for i, restriction in enumerate(self.restrictions):
            if restriction.restriction_type == restriction_type:
                self.restrictions.pop(i)
                return True
        
        return False
    
    def get_restriction_summary(self) -> Dict[str, Any]:
        """Get a summary of all restrictions."""
        return {
            'total_restrictions': len(self.restrictions),
            'restriction_types': [r.restriction_type for r in self.restrictions],
            'applies_to': [r.applies_to for r in self.restrictions],
            'conditions': [r.condition for r in self.restrictions]
        }
