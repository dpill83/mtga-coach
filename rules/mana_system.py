#!/usr/bin/env python3
"""
Mana System

Handles mana cost validation, payment, and mana pool management.
Implements Magic: The Gathering mana rules and restrictions.
"""

from typing import List, Dict, Optional, Set, Any, Tuple
from datetime import datetime
import re
import logging

from state.player_state import PlayerState, ManaPool
from parser.events import CardInfo, CardType
from rules.action_types import Action, ActionType

logger = logging.getLogger(__name__)

class ManaCost:
    """Represents a mana cost."""
    
    def __init__(self, cost_string: str):
        self.cost_string = cost_string
        self.white = 0
        self.blue = 0
        self.black = 0
        self.red = 0
        self.green = 0
        self.colorless = 0
        self.generic = 0
        self.hybrid = []
        self.phyrexian = []
        self.snow = 0
        self.energy = 0
        self.life = 0
        
        self._parse_cost()
    
    def _parse_cost(self) -> None:
        """Parse the mana cost string."""
        if not self.cost_string:
            return
        
        # Remove spaces and convert to uppercase
        cost = self.cost_string.replace(' ', '').upper()
        
        # Parse individual mana symbols
        symbols = re.findall(r'\{[^}]+\}', cost)
        
        for symbol in symbols:
            symbol = symbol[1:-1]  # Remove { and }
            
            if symbol == 'W':
                self.white += 1
            elif symbol == 'U':
                self.blue += 1
            elif symbol == 'B':
                self.black += 1
            elif symbol == 'R':
                self.red += 1
            elif symbol == 'G':
                self.green += 1
            elif symbol == 'C':
                self.colorless += 1
            elif symbol.isdigit():
                self.generic += int(symbol)
            elif '/' in symbol:
                # Hybrid mana
                self.hybrid.append(symbol)
            elif 'P' in symbol:
                # Phyrexian mana
                self.phyrexian.append(symbol)
            elif 'S' in symbol:
                # Snow mana
                self.snow += 1
            elif 'E' in symbol:
                # Energy
                self.energy += 1
            elif 'L' in symbol:
                # Life
                self.life += 1
    
    def get_total_cost(self) -> int:
        """Get total mana cost."""
        return (self.white + self.blue + self.black + self.red + 
                self.green + self.colorless + self.generic + 
                len(self.hybrid) + len(self.phyrexian) + self.snow)
    
    def get_colored_cost(self) -> Dict[str, int]:
        """Get colored mana cost."""
        return {
            'white': self.white,
            'blue': self.blue,
            'black': self.black,
            'red': self.red,
            'green': self.green,
            'colorless': self.colorless
        }
    
    def get_hybrid_cost(self) -> List[str]:
        """Get hybrid mana cost."""
        return self.hybrid.copy()
    
    def get_phyrexian_cost(self) -> List[str]:
        """Get Phyrexian mana cost."""
        return self.phyrexian.copy()
    
    def is_colorless(self) -> bool:
        """Check if cost is colorless."""
        return (self.white == 0 and self.blue == 0 and self.black == 0 and 
                self.red == 0 and self.green == 0 and len(self.hybrid) == 0)
    
    def is_mono_colored(self) -> bool:
        """Check if cost is mono-colored."""
        colored_count = sum([
            self.white, self.blue, self.black, self.red, self.green
        ])
        return colored_count == 1 and len(self.hybrid) == 0
    
    def get_primary_color(self) -> Optional[str]:
        """Get the primary color of the cost."""
        if self.white > 0:
            return 'white'
        elif self.blue > 0:
            return 'blue'
        elif self.black > 0:
            return 'black'
        elif self.red > 0:
            return 'red'
        elif self.green > 0:
            return 'green'
        return None

class ManaSystem:
    """Mana system for Magic: The Gathering."""
    
    def __init__(self, game_state):
        self.game_state = game_state
        self.mana_pool_history: Dict[int, List[ManaPool]] = {}
        self.mana_spent_history: Dict[int, List[Dict[str, int]]] = {}
    
    def can_pay_cost(self, cost_string: str, player: PlayerState) -> bool:
        """Check if a player can pay a mana cost."""
        try:
            if not cost_string:
                return True
            
            cost = ManaCost(cost_string)
            return self._can_pay_mana_cost(cost, player)
            
        except Exception as e:
            logger.error(f"Error checking mana cost: {e}")
            return False
    
    def pay_cost(self, cost_string: str, player: PlayerState) -> bool:
        """Pay a mana cost."""
        try:
            if not cost_string:
                return True
            
            cost = ManaCost(cost_string)
            if not self._can_pay_mana_cost(cost, player):
                return False
            
            # Pay the cost
            return self._pay_mana_cost(cost, player)
            
        except Exception as e:
            logger.error(f"Error paying mana cost: {e}")
            return False
    
    def _can_pay_mana_cost(self, cost: ManaCost, player: PlayerState) -> bool:
        """Check if player can pay a mana cost."""
        # Check basic mana
        if not self._can_pay_basic_mana(cost, player):
            return False
        
        # Check hybrid mana
        if not self._can_pay_hybrid_mana(cost, player):
            return False
        
        # Check Phyrexian mana
        if not self._can_pay_phyrexian_mana(cost, player):
            return False
        
        # Check snow mana
        if not self._can_pay_snow_mana(cost, player):
            return False
        
        # Check energy
        if not self._can_pay_energy(cost, player):
            return False
        
        # Check life
        if not self._can_pay_life(cost, player):
            return False
        
        return True
    
    def _can_pay_basic_mana(self, cost: ManaCost, player: PlayerState) -> bool:
        """Check if player can pay basic mana costs."""
        mana_pool = player.mana_pool
        
        # Check colored mana
        if mana_pool.white < cost.white:
            return False
        if mana_pool.blue < cost.blue:
            return False
        if mana_pool.black < cost.black:
            return False
        if mana_pool.red < cost.red:
            return False
        if mana_pool.green < cost.green:
            return False
        if mana_pool.colorless < cost.colorless:
            return False
        
        # Check generic mana
        available_generic = mana_pool.total_mana() - (
            cost.white + cost.blue + cost.black + cost.red + cost.green + cost.colorless
        )
        if available_generic < cost.generic:
            return False
        
        return True
    
    def _can_pay_hybrid_mana(self, cost: ManaCost, player: PlayerState) -> bool:
        """Check if player can pay hybrid mana costs."""
        mana_pool = player.mana_pool
        
        for hybrid in cost.hybrid:
            if not self._can_pay_hybrid_symbol(hybrid, mana_pool):
                return False
        
        return True
    
    def _can_pay_hybrid_symbol(self, symbol: str, mana_pool: ManaPool) -> bool:
        """Check if player can pay a hybrid mana symbol."""
        # Parse hybrid symbol (e.g., "W/U", "2/U", "W/P")
        if '/' not in symbol:
            return False
        
        options = symbol.split('/')
        
        # Check if player can pay any of the options
        for option in options:
            if self._can_pay_mana_symbol(option, mana_pool):
                return True
        
        return False
    
    def _can_pay_mana_symbol(self, symbol: str, mana_pool: ManaPool) -> bool:
        """Check if player can pay a single mana symbol."""
        if symbol == 'W':
            return mana_pool.white > 0
        elif symbol == 'U':
            return mana_pool.blue > 0
        elif symbol == 'B':
            return mana_pool.black > 0
        elif symbol == 'R':
            return mana_pool.red > 0
        elif symbol == 'G':
            return mana_pool.green > 0
        elif symbol == 'C':
            return mana_pool.colorless > 0
        elif symbol.isdigit():
            return mana_pool.total_mana() >= int(symbol)
        else:
            return False
    
    def _can_pay_phyrexian_mana(self, cost: ManaCost, player: PlayerState) -> bool:
        """Check if player can pay Phyrexian mana costs."""
        for phyrexian in cost.phyrexian:
            if not self._can_pay_phyrexian_symbol(phyrexian, player):
                return False
        
        return True
    
    def _can_pay_phyrexian_symbol(self, symbol: str, player: PlayerState) -> bool:
        """Check if player can pay a Phyrexian mana symbol."""
        # Phyrexian mana can be paid with 2 life or the appropriate mana
        if 'P' in symbol:
            # Check if player has enough life
            if player.life_total >= 2:
                return True
            
            # Check if player has the appropriate mana
            color = symbol.replace('P', '')
            if color == 'W':
                return player.mana_pool.white > 0
            elif color == 'U':
                return player.mana_pool.blue > 0
            elif color == 'B':
                return player.mana_pool.black > 0
            elif color == 'R':
                return player.mana_pool.red > 0
            elif color == 'G':
                return player.mana_pool.green > 0
            elif color == 'C':
                return player.mana_pool.colorless > 0
        
        return False
    
    def _can_pay_snow_mana(self, cost: ManaCost, player: PlayerState) -> bool:
        """Check if player can pay snow mana costs."""
        # Simplified snow mana check - would need to track snow permanents
        return cost.snow == 0  # For now, assume no snow mana required
    
    def _can_pay_energy(self, cost: ManaCost, player: PlayerState) -> bool:
        """Check if player can pay energy costs."""
        return player.energy_counters >= cost.energy
    
    def _can_pay_life(self, cost: ManaCost, player: PlayerState) -> bool:
        """Check if player can pay life costs."""
        return player.life_total >= cost.life
    
    def _pay_mana_cost(self, cost: ManaCost, player: PlayerState) -> bool:
        """Pay a mana cost."""
        try:
            # Pay basic mana
            if not self._pay_basic_mana(cost, player):
                return False
            
            # Pay hybrid mana
            if not self._pay_hybrid_mana(cost, player):
                return False
            
            # Pay Phyrexian mana
            if not self._pay_phyrexian_mana(cost, player):
                return False
            
            # Pay snow mana
            if not self._pay_snow_mana(cost, player):
                return False
            
            # Pay energy
            if not self._pay_energy(cost, player):
                return False
            
            # Pay life
            if not self._pay_life(cost, player):
                return False
            
            # Record mana spent
            self._record_mana_spent(cost, player)
            
            return True
            
        except Exception as e:
            logger.error(f"Error paying mana cost: {e}")
            return False
    
    def _pay_basic_mana(self, cost: ManaCost, player: PlayerState) -> bool:
        """Pay basic mana costs."""
        mana_pool = player.mana_pool
        
        # Pay colored mana
        mana_pool.white -= cost.white
        mana_pool.blue -= cost.blue
        mana_pool.black -= cost.black
        mana_pool.red -= cost.red
        mana_pool.green -= cost.green
        mana_pool.colorless -= cost.colorless
        
        # Pay generic mana
        generic_paid = 0
        while generic_paid < cost.generic:
            if mana_pool.white > 0:
                mana_pool.white -= 1
            elif mana_pool.blue > 0:
                mana_pool.blue -= 1
            elif mana_pool.black > 0:
                mana_pool.black -= 1
            elif mana_pool.red > 0:
                mana_pool.red -= 1
            elif mana_pool.green > 0:
                mana_pool.green -= 1
            elif mana_pool.colorless > 0:
                mana_pool.colorless -= 1
            else:
                return False
            generic_paid += 1
        
        return True
    
    def _pay_hybrid_mana(self, cost: ManaCost, player: PlayerState) -> bool:
        """Pay hybrid mana costs."""
        for hybrid in cost.hybrid:
            if not self._pay_hybrid_symbol(hybrid, player):
                return False
        
        return True
    
    def _pay_hybrid_symbol(self, symbol: str, player: PlayerState) -> bool:
        """Pay a hybrid mana symbol."""
        options = symbol.split('/')
        
        # Try to pay with the first available option
        for option in options:
            if self._can_pay_mana_symbol(option, player.mana_pool):
                return self._pay_mana_symbol(option, player.mana_pool)
        
        return False
    
    def _pay_mana_symbol(self, symbol: str, mana_pool: ManaPool) -> bool:
        """Pay a single mana symbol."""
        if symbol == 'W':
            mana_pool.white -= 1
        elif symbol == 'U':
            mana_pool.blue -= 1
        elif symbol == 'B':
            mana_pool.black -= 1
        elif symbol == 'R':
            mana_pool.red -= 1
        elif symbol == 'G':
            mana_pool.green -= 1
        elif symbol == 'C':
            mana_pool.colorless -= 1
        elif symbol.isdigit():
            amount = int(symbol)
            for _ in range(amount):
                if mana_pool.white > 0:
                    mana_pool.white -= 1
                elif mana_pool.blue > 0:
                    mana_pool.blue -= 1
                elif mana_pool.black > 0:
                    mana_pool.black -= 1
                elif mana_pool.red > 0:
                    mana_pool.red -= 1
                elif mana_pool.green > 0:
                    mana_pool.green -= 1
                elif mana_pool.colorless > 0:
                    mana_pool.colorless -= 1
                else:
                    return False
        else:
            return False
        
        return True
    
    def _pay_phyrexian_mana(self, cost: ManaCost, player: PlayerState) -> bool:
        """Pay Phyrexian mana costs."""
        for phyrexian in cost.phyrexian:
            if not self._pay_phyrexian_symbol(phyrexian, player):
                return False
        
        return True
    
    def _pay_phyrexian_symbol(self, symbol: str, player: PlayerState) -> bool:
        """Pay a Phyrexian mana symbol."""
        if 'P' in symbol:
            # Try to pay with mana first
            color = symbol.replace('P', '')
            if self._can_pay_mana_symbol(color, player.mana_pool):
                return self._pay_mana_symbol(color, player.mana_pool)
            
            # Otherwise pay with life
            if player.life_total >= 2:
                player.take_damage(2)
                return True
        
        return False
    
    def _pay_snow_mana(self, cost: ManaCost, player: PlayerState) -> bool:
        """Pay snow mana costs."""
        # Simplified snow mana payment
        return cost.snow == 0
    
    def _pay_energy(self, cost: ManaCost, player: PlayerState) -> bool:
        """Pay energy costs."""
        if player.energy_counters >= cost.energy:
            player.energy_counters -= cost.energy
            return True
        return False
    
    def _pay_life(self, cost: ManaCost, player: PlayerState) -> bool:
        """Pay life costs."""
        if player.life_total >= cost.life:
            player.take_damage(cost.life)
            return True
        return False
    
    def _record_mana_spent(self, cost: ManaCost, player: PlayerState) -> None:
        """Record mana spent for history."""
        if player.player_id not in self.mana_spent_history:
            self.mana_spent_history[player.player_id] = []
        
        spent = {
            'white': cost.white,
            'blue': cost.blue,
            'black': cost.black,
            'red': cost.red,
            'green': cost.green,
            'colorless': cost.colorless,
            'generic': cost.generic,
            'hybrid': cost.hybrid.copy(),
            'phyrexian': cost.phyrexian.copy(),
            'snow': cost.snow,
            'energy': cost.energy,
            'life': cost.life
        }
        
        self.mana_spent_history[player.player_id].append(spent)
    
    def get_mana_history(self, player_id: int) -> List[Dict[str, int]]:
        """Get mana spending history for a player."""
        return self.mana_spent_history.get(player_id, [])
    
    def can_generate_mana(self, player: PlayerState, color: str, amount: int = 1) -> bool:
        """Check if a player can generate mana of a specific color."""
        # Check if player has lands that can produce that color
        for land in player.battlefield.lands:
            if self._land_can_produce_mana(land, color):
                return True
        
        # Check if player has artifacts that can produce mana
        for artifact in player.battlefield.artifacts:
            if self._artifact_can_produce_mana(artifact, color):
                return True
        
        return False
    
    def _land_can_produce_mana(self, land: CardInfo, color: str) -> bool:
        """Check if a land can produce mana of a specific color."""
        # Simplified land mana production
        if color == 'white':
            return 'plains' in land.name.lower() or 'white' in land.name.lower()
        elif color == 'blue':
            return 'island' in land.name.lower() or 'blue' in land.name.lower()
        elif color == 'black':
            return 'swamp' in land.name.lower() or 'black' in land.name.lower()
        elif color == 'red':
            return 'mountain' in land.name.lower() or 'red' in land.name.lower()
        elif color == 'green':
            return 'forest' in land.name.lower() or 'green' in land.name.lower()
        elif color == 'colorless':
            return True  # All lands can produce colorless mana
        
        return False
    
    def _artifact_can_produce_mana(self, artifact: CardInfo, color: str) -> bool:
        """Check if an artifact can produce mana of a specific color."""
        # Simplified artifact mana production
        if 'mana' in artifact.name.lower():
            return True
        
        return False
    
    def generate_mana(self, player: PlayerState, color: str, amount: int = 1) -> bool:
        """Generate mana for a player."""
        try:
            if not self.can_generate_mana(player, color, amount):
                return False
            
            # Add mana to pool
            for _ in range(amount):
                if color == 'white':
                    player.mana_pool.white += 1
                elif color == 'blue':
                    player.mana_pool.blue += 1
                elif color == 'black':
                    player.mana_pool.black += 1
                elif color == 'red':
                    player.mana_pool.red += 1
                elif color == 'green':
                    player.mana_pool.green += 1
                elif color == 'colorless':
                    player.mana_pool.colorless += 1
                else:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating mana: {e}")
            return False
    
    def get_mana_pool_summary(self, player: PlayerState) -> Dict[str, Any]:
        """Get a summary of a player's mana pool."""
        return {
            'white': player.mana_pool.white,
            'blue': player.mana_pool.blue,
            'black': player.mana_pool.black,
            'red': player.mana_pool.red,
            'green': player.mana_pool.green,
            'colorless': player.mana_pool.colorless,
            'total': player.mana_pool.total_mana(),
            'can_generate': {
                'white': self.can_generate_mana(player, 'white'),
                'blue': self.can_generate_mana(player, 'blue'),
                'black': self.can_generate_mana(player, 'black'),
                'red': self.can_generate_mana(player, 'red'),
                'green': self.can_generate_mana(player, 'green'),
                'colorless': self.can_generate_mana(player, 'colorless')
            }
        }
