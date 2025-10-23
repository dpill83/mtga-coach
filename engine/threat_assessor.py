#!/usr/bin/env python3
"""
Threat Assessor

Identifies and prioritizes threats on the board.
Provides threat detection and response recommendations.
"""

from typing import List, Dict, Optional, Set, Any, Tuple
from datetime import datetime
import logging

from state.game_state import GameState, GameStatus
from state.player_state import PlayerState, PlayerType
from parser.events import CardInfo, CardType, ZoneType
from rules.action_types import Action, ActionType

logger = logging.getLogger(__name__)

class Threat:
    """Represents a threat on the board."""
    
    def __init__(self, source: CardInfo, threat_level: float, threat_type: str, 
                 description: str, priority: int, response_actions: List[Action] = None):
        self.source = source
        self.threat_level = threat_level
        self.threat_type = threat_type
        self.description = description
        self.priority = priority
        self.response_actions = response_actions or []
        self.timestamp = datetime.now()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the threat."""
        return {
            'source_name': self.source.name,
            'threat_level': self.threat_level,
            'threat_type': self.threat_type,
            'description': self.description,
            'priority': self.priority,
            'response_count': len(self.response_actions)
        }

class ThreatAssessor:
    """Assesses threats on the board and recommends responses."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.threat_weights = self._get_default_weights()
        self.threat_history: List[Threat] = []
        
    def _get_default_weights(self) -> Dict[str, float]:
        """Get default threat assessment weights."""
        return {
            'lethal_damage': 10.0,
            'immediate_lethal': 15.0,
            'high_power_creature': 5.0,
            'flying_creature': 3.0,
            'ability_creature': 4.0,
            'planeswalker': 6.0,
            'enchantment': 3.0,
            'artifact': 2.0,
            'hand_advantage': 2.0,
            'mana_advantage': 1.5
        }
    
    def assess_threats(self, player_id: int) -> List[Threat]:
        """Assess all threats for a player."""
        try:
            threats = []
            
            # Get player state
            player = self.game_state.get_player(player_id)
            if not player:
                return threats
            
            # Assess opponent creatures
            threats.extend(self._assess_opponent_creatures(player))
            
            # Assess opponent planeswalkers
            threats.extend(self._assess_opponent_planeswalkers(player))
            
            # Assess opponent enchantments
            threats.extend(self._assess_opponent_enchantments(player))
            
            # Assess opponent artifacts
            threats.extend(self._assess_opponent_artifacts(player))
            
            # Assess opponent hand advantage
            threats.extend(self._assess_hand_advantage(player))
            
            # Assess opponent mana advantage
            threats.extend(self._assess_mana_advantage(player))
            
            # Sort by priority
            threats.sort(key=lambda x: x.priority, reverse=True)
            
            # Store in history
            self.threat_history.extend(threats)
            
            return threats
            
        except Exception as e:
            logger.error(f"Error assessing threats for player {player_id}: {e}")
            return []
    
    def _assess_opponent_creatures(self, player: PlayerState) -> List[Threat]:
        """Assess threats from opponent creatures."""
        threats = []
        
        # Get opponent
        opponent = self.game_state.get_opponent_player()
        if not opponent:
            return threats
        
        for creature in opponent.battlefield.get_creatures():
            threat_level = 0.0
            threat_type = "creature"
            description = f"Opponent creature: {creature.name}"
            priority = 1
            
            # Power and toughness
            power = creature.power or 0
            toughness = creature.toughness or 0
            
            if power > 0:
                threat_level += power * 0.5
                description += f" ({power}/{toughness})"
            
            # Check for lethal
            if power >= player.life_total:
                threat_level += 10.0
                threat_type = "lethal_creature"
                priority = 10
                description += " - LETHAL THREAT"
            
            # Check for flying
            if 'flying' in creature.keywords:
                threat_level += 2.0
                description += " (flying)"
                priority += 1
            
            # Check for abilities
            if creature.abilities:
                threat_level += 1.0
                description += " (has abilities)"
                priority += 1
            
            # Check for high power
            if power >= 4:
                threat_level += 2.0
                description += " (high power)"
                priority += 2
            
            # Check for toughness
            if toughness >= 4:
                threat_level += 1.0
                description += " (high toughness)"
                priority += 1
            
            if threat_level > 0:
                threat = Threat(
                    source=creature,
                    threat_level=threat_level,
                    threat_type=threat_type,
                    description=description,
                    priority=priority
                )
                threats.append(threat)
        
        return threats
    
    def _assess_opponent_planeswalkers(self, player: PlayerState) -> List[Threat]:
        """Assess threats from opponent planeswalkers."""
        threats = []
        
        # Get opponent
        opponent = self.game_state.get_opponent_player()
        if not opponent:
            return threats
        
        for planeswalker in opponent.battlefield.planeswalkers:
            threat_level = 3.0
            threat_type = "planeswalker"
            description = f"Opponent planeswalker: {planeswalker.name}"
            priority = 5
            
            # Planeswalkers are always threats
            if planeswalker.abilities:
                threat_level += len(planeswalker.abilities) * 0.5
                description += " (has abilities)"
                priority += 1
            
            threat = Threat(
                source=planeswalker,
                threat_level=threat_level,
                threat_type=threat_type,
                description=description,
                priority=priority
            )
            threats.append(threat)
        
        return threats
    
    def _assess_opponent_enchantments(self, player: PlayerState) -> List[Threat]:
        """Assess threats from opponent enchantments."""
        threats = []
        
        # Get opponent
        opponent = self.game_state.get_opponent_player()
        if not opponent:
            return threats
        
        for enchantment in opponent.battlefield.enchantments:
            threat_level = 1.0
            threat_type = "enchantment"
            description = f"Opponent enchantment: {enchantment.name}"
            priority = 2
            
            # Check for specific threatening enchantments
            if self._is_threatening_enchantment(enchantment):
                threat_level += 2.0
                description += " (threatening effect)"
                priority += 2
            
            if enchantment.abilities:
                threat_level += 1.0
                description += " (has abilities)"
                priority += 1
            
            threat = Threat(
                source=enchantment,
                threat_level=threat_level,
                threat_type=threat_type,
                description=description,
                priority=priority
            )
            threats.append(threat)
        
        return threats
    
    def _assess_opponent_artifacts(self, player: PlayerState) -> List[Threat]:
        """Assess threats from opponent artifacts."""
        threats = []
        
        # Get opponent
        opponent = self.game_state.get_opponent_player()
        if not opponent:
            return threats
        
        for artifact in opponent.battlefield.artifacts:
            threat_level = 0.5
            threat_type = "artifact"
            description = f"Opponent artifact: {artifact.name}"
            priority = 1
            
            # Check for specific threatening artifacts
            if self._is_threatening_artifact(artifact):
                threat_level += 1.5
                description += " (threatening effect)"
                priority += 2
            
            if artifact.abilities:
                threat_level += 1.0
                description += " (has abilities)"
                priority += 1
            
            threat = Threat(
                source=artifact,
                threat_level=threat_level,
                threat_type=threat_type,
                description=description,
                priority=priority
            )
            threats.append(threat)
        
        return threats
    
    def _assess_hand_advantage(self, player: PlayerState) -> List[Threat]:
        """Assess threats from opponent hand advantage."""
        threats = []
        
        # Get opponent
        opponent = self.game_state.get_opponent_player()
        if not opponent:
            return threats
        
        # Check hand size difference
        hand_difference = opponent.hand.size() - player.hand.size()
        
        if hand_difference > 2:
            threat_level = hand_difference * 0.5
            threat_type = "hand_advantage"
            description = f"Opponent has {hand_difference} more cards in hand"
            priority = 3
            
            threat = Threat(
                source=CardInfo(
                    instance_id=0,
                    grp_id=0,
                    name="Hand Advantage",
                    controller=opponent.player_id,
                    zone_id=2,
                    zone_type=ZoneType.HAND
                ),
                threat_level=threat_level,
                threat_type=threat_type,
                description=description,
                priority=priority
            )
            threats.append(threat)
        
        return threats
    
    def _assess_mana_advantage(self, player: PlayerState) -> List[Threat]:
        """Assess threats from opponent mana advantage."""
        threats = []
        
        # Get opponent
        opponent = self.game_state.get_opponent_player()
        if not opponent:
            return threats
        
        # Check mana difference
        self_mana = player.get_mana_summary()
        opponent_mana = opponent.get_mana_summary()
        
        mana_difference = opponent_mana.get('total', 0) - self_mana.get('total', 0)
        
        if mana_difference > 3:
            threat_level = mana_difference * 0.3
            threat_type = "mana_advantage"
            description = f"Opponent has {mana_difference} more mana"
            priority = 2
            
            threat = Threat(
                source=CardInfo(
                    instance_id=0,
                    grp_id=0,
                    name="Mana Advantage",
                    controller=opponent.player_id,
                    zone_id=1,
                    zone_type=ZoneType.BATTLEFIELD
                ),
                threat_level=threat_level,
                threat_type=threat_type,
                description=description,
                priority=priority
            )
            threats.append(threat)
        
        return threats
    
    def _is_threatening_enchantment(self, enchantment: CardInfo) -> bool:
        """Check if an enchantment is threatening."""
        # Simplified threat detection
        threatening_keywords = ['destroy', 'damage', 'counter', 'discard', 'exile']
        for keyword in threatening_keywords:
            if keyword in enchantment.name.lower() or keyword in enchantment.oracle_text.lower():
                return True
        return False
    
    def _is_threatening_artifact(self, artifact: CardInfo) -> bool:
        """Check if an artifact is threatening."""
        # Simplified threat detection
        threatening_keywords = ['destroy', 'damage', 'counter', 'discard', 'exile']
        for keyword in threatening_keywords:
            if keyword in artifact.name.lower() or keyword in artifact.oracle_text.lower():
                return True
        return False
    
    def get_immediate_threats(self, player_id: int) -> List[Threat]:
        """Get immediate threats that need immediate response."""
        all_threats = self.assess_threats(player_id)
        return [threat for threat in all_threats if threat.priority >= 8]
    
    def get_high_priority_threats(self, player_id: int) -> List[Threat]:
        """Get high priority threats."""
        all_threats = self.assess_threats(player_id)
        return [threat for threat in all_threats if threat.priority >= 5]
    
    def get_threat_summary(self, player_id: int) -> Dict[str, Any]:
        """Get a summary of all threats."""
        threats = self.assess_threats(player_id)
        
        summary = {
            'total_threats': len(threats),
            'immediate_threats': len([t for t in threats if t.priority >= 8]),
            'high_priority_threats': len([t for t in threats if t.priority >= 5]),
            'threat_types': list(set(t.threat_type for t in threats)),
            'highest_priority': max([t.priority for t in threats]) if threats else 0,
            'threats': [t.get_summary() for t in threats[:5]]  # Top 5 threats
        }
        
        return summary
    
    def get_threat_history(self) -> List[Dict[str, Any]]:
        """Get threat assessment history."""
        return [threat.get_summary() for threat in self.threat_history]
    
    def clear_threat_history(self) -> None:
        """Clear threat assessment history."""
        self.threat_history.clear()
    
    def set_threat_weights(self, weights: Dict[str, float]) -> None:
        """Set custom threat assessment weights."""
        self.threat_weights.update(weights)
    
    def get_threat_weights(self) -> Dict[str, float]:
        """Get current threat assessment weights."""
        return self.threat_weights.copy()
