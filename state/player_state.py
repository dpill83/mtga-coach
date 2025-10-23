#!/usr/bin/env python3
"""
Player State

Represents the state of a single player in the game.
Tracks life, hand, battlefield, mana, and other player-specific data.
"""

from typing import List, Dict, Optional, Set
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from parser.events import CardInfo, ZoneType, CardType

class PlayerType(str, Enum):
    """Player types."""
    SELF = "self"
    OPPONENT = "opponent"

class ManaPool(BaseModel):
    """Player's mana pool."""
    white: int = 0
    blue: int = 0
    black: int = 0
    red: int = 0
    green: int = 0
    colorless: int = 0
    
    def total_mana(self) -> int:
        """Get total mana available."""
        return self.white + self.blue + self.black + self.red + self.green + self.colorless
    
    def can_pay_cost(self, cost: str) -> bool:
        """Check if player can pay a mana cost."""
        # Simplified cost checking - would need proper mana cost parsing
        return self.total_mana() >= len(cost.replace('{', '').replace('}', ''))
    
    def pay_cost(self, cost: str) -> bool:
        """Pay a mana cost (simplified)."""
        if not self.can_pay_cost(cost):
            return False
        
        # Simplified cost payment - would need proper mana cost parsing
        cost_amount = len(cost.replace('{', '').replace('}', ''))
        if self.colorless >= cost_amount:
            self.colorless -= cost_amount
            return True
        return False

class Hand(BaseModel):
    """Player's hand."""
    cards: List[CardInfo] = Field(default_factory=list)
    max_size: int = 7  # Default hand size limit
    
    def add_card(self, card: CardInfo) -> bool:
        """Add a card to hand."""
        if len(self.cards) < self.max_size:
            self.cards.append(card)
            return True
        return False
    
    def remove_card(self, instance_id: int) -> Optional[CardInfo]:
        """Remove a card from hand by instance ID."""
        for i, card in enumerate(self.cards):
            if card.instance_id == instance_id:
                return self.cards.pop(i)
        return None
    
    def get_card(self, instance_id: int) -> Optional[CardInfo]:
        """Get a card from hand by instance ID."""
        for card in self.cards:
            if card.instance_id == instance_id:
                return card
        return None
    
    def size(self) -> int:
        """Get current hand size."""
        return len(self.cards)

class Battlefield(BaseModel):
    """Player's battlefield (cards in play)."""
    creatures: List[CardInfo] = Field(default_factory=list)
    lands: List[CardInfo] = Field(default_factory=list)
    artifacts: List[CardInfo] = Field(default_factory=list)
    enchantments: List[CardInfo] = Field(default_factory=list)
    planeswalkers: List[CardInfo] = Field(default_factory=list)
    other: List[CardInfo] = Field(default_factory=list)
    
    def add_card(self, card: CardInfo) -> bool:
        """Add a card to battlefield."""
        if CardType.CREATURE in card.card_types:
            self.creatures.append(card)
        elif CardType.LAND in card.card_types:
            self.lands.append(card)
        elif CardType.ARTIFACT in card.card_types:
            self.artifacts.append(card)
        elif CardType.ENCHANTMENT in card.card_types:
            self.enchantments.append(card)
        elif CardType.PLANESWALKER in card.card_types:
            self.planeswalkers.append(card)
        else:
            self.other.append(card)
        return True
    
    def remove_card(self, instance_id: int) -> Optional[CardInfo]:
        """Remove a card from battlefield by instance ID."""
        for category in [self.creatures, self.lands, self.artifacts, 
                        self.enchantments, self.planeswalkers, self.other]:
            for i, card in enumerate(category):
                if card.instance_id == instance_id:
                    return category.pop(i)
        return None
    
    def get_card(self, instance_id: int) -> Optional[CardInfo]:
        """Get a card from battlefield by instance ID."""
        for category in [self.creatures, self.lands, self.artifacts, 
                        self.enchantments, self.planeswalkers, self.other]:
            for card in category:
                if card.instance_id == instance_id:
                    return card
        return None
    
    def get_all_cards(self) -> List[CardInfo]:
        """Get all cards on battlefield."""
        return (self.creatures + self.lands + self.artifacts + 
                self.enchantments + self.planeswalkers + self.other)
    
    def get_creatures(self) -> List[CardInfo]:
        """Get all creatures on battlefield."""
        return self.creatures.copy()
    
    def get_lands(self) -> List[CardInfo]:
        """Get all lands on battlefield."""
        return self.lands.copy()

class Graveyard(BaseModel):
    """Player's graveyard."""
    cards: List[CardInfo] = Field(default_factory=list)
    
    def add_card(self, card: CardInfo) -> bool:
        """Add a card to graveyard."""
        self.cards.append(card)
        return True
    
    def remove_card(self, instance_id: int) -> Optional[CardInfo]:
        """Remove a card from graveyard by instance ID."""
        for i, card in enumerate(self.cards):
            if card.instance_id == instance_id:
                return self.cards.pop(i)
        return None
    
    def get_card(self, instance_id: int) -> Optional[CardInfo]:
        """Get a card from graveyard by instance ID."""
        for card in self.cards:
            if card.instance_id == instance_id:
                return card
        return None

class PlayerState(BaseModel):
    """Complete state of a single player."""
    player_id: int
    player_type: PlayerType
    life_total: int = 20
    max_hand_size: int = 7
    hand: Hand = Field(default_factory=Hand)
    battlefield: Battlefield = Field(default_factory=Battlefield)
    graveyard: Graveyard = Field(default_factory=Graveyard)
    mana_pool: ManaPool = Field(default_factory=ManaPool)
    
    # Game state tracking
    has_played_land_this_turn: bool = False
    has_attacked_this_turn: bool = False
    has_used_ability_this_turn: Set[str] = Field(default_factory=set)
    
    # Counters and effects
    poison_counters: int = 0
    energy_counters: int = 0
    experience_counters: int = 0
    
    # Commander-specific (for Commander format)
    commander_damage: int = 0
    commander_tax: int = 0
    
    def can_play_land(self) -> bool:
        """Check if player can play a land this turn."""
        return not self.has_played_land_this_turn
    
    def can_attack(self) -> bool:
        """Check if player can attack this turn."""
        return not self.has_attacked_this_turn
    
    def can_use_ability(self, ability_name: str) -> bool:
        """Check if player can use a specific ability this turn."""
        return ability_name not in self.has_used_ability_this_turn
    
    def use_ability(self, ability_name: str) -> bool:
        """Mark an ability as used this turn."""
        self.has_used_ability_this_turn.add(ability_name)
        return True
    
    def reset_turn_flags(self):
        """Reset turn-specific flags."""
        self.has_played_land_this_turn = False
        self.has_attacked_this_turn = False
        self.has_used_ability_this_turn.clear()
    
    def get_total_power(self) -> int:
        """Get total power of all creatures on battlefield."""
        total = 0
        for creature in self.battlefield.creatures:
            if creature.power is not None:
                total += creature.power
        return total
    
    def get_total_toughness(self) -> int:
        """Get total toughness of all creatures on battlefield."""
        total = 0
        for creature in self.battlefield.creatures:
            if creature.toughness is not None:
                total += creature.toughness
        return total
    
    def get_creature_count(self) -> int:
        """Get number of creatures on battlefield."""
        return len(self.battlefield.creatures)
    
    def get_land_count(self) -> int:
        """Get number of lands on battlefield."""
        return len(self.battlefield.lands)
    
    def is_alive(self) -> bool:
        """Check if player is still alive."""
        return self.life_total > 0
    
    def take_damage(self, amount: int) -> int:
        """Take damage and return actual damage taken."""
        if amount <= 0:
            return 0
        
        actual_damage = min(amount, self.life_total)
        self.life_total = max(0, self.life_total - amount)
        return actual_damage
    
    def gain_life(self, amount: int) -> int:
        """Gain life and return actual life gained."""
        if amount <= 0:
            return 0
        
        self.life_total += amount
        return amount
    
    def add_mana(self, color: str, amount: int = 1) -> bool:
        """Add mana to mana pool."""
        if color.lower() == 'w':
            self.mana_pool.white += amount
        elif color.lower() == 'u':
            self.mana_pool.blue += amount
        elif color.lower() == 'b':
            self.mana_pool.black += amount
        elif color.lower() == 'r':
            self.mana_pool.red += amount
        elif color.lower() == 'g':
            self.mana_pool.green += amount
        elif color.lower() == 'c':
            self.mana_pool.colorless += amount
        else:
            return False
        return True
    
    def get_mana_summary(self) -> Dict[str, int]:
        """Get summary of mana pool."""
        return {
            'white': self.mana_pool.white,
            'blue': self.mana_pool.blue,
            'black': self.mana_pool.black,
            'red': self.mana_pool.red,
            'green': self.mana_pool.green,
            'colorless': self.mana_pool.colorless,
            'total': self.mana_pool.total_mana()
        }
