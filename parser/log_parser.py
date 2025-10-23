#!/usr/bin/env python3
"""
MTGA Log Parser

Parses MTGA log files and extracts structured game events.
Handles Unity log format and GRE (Game Rules Engine) messages.
"""

import re
import json
import logging
from typing import List, Optional, Dict, Any, Iterator
from datetime import datetime

from .events import (
    GameEvent, EventType, Phase, ZoneType, CardType,
    GameStartEvent, DrawCardEvent, PlayCardEvent, LifeChangeEvent,
    PhaseChangeEvent, CardInfo, UnknownEvent
)

logger = logging.getLogger(__name__)

class MTGALogParser:
    def __init__(self, card_cache=None):
        self.card_cache = card_cache
        self.current_game_state = {}
        self.current_turn = 0
        self.current_phase = None
        
        # Regex patterns for log parsing
        self.unity_log_pattern = re.compile(
            r'\[UnityCrossThreadLogger\]\s*(.+)$'
        )
        
        self.gre_message_pattern = re.compile(
            r'greToClientEvent.*?(\{.*\})'
        )
        
        self.client_message_pattern = re.compile(
            r'ClientToMatchServiceMessageType_ClientToGREMessage.*?(\{.*\})'
        )
    
    def parse_log_line(self, line: str) -> Optional[GameEvent]:
        """
        Parse a single log line and return a game event if found.
        
        Args:
            line: Raw log line
            
        Returns:
            GameEvent if parseable, None otherwise
        """
        try:
            # Check if this is a Unity log line
            unity_match = self.unity_log_pattern.match(line.strip())
            if not unity_match:
                return None
            
            # Extract JSON payload
            json_str = unity_match.group(1)
            
            # Try to parse JSON
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse JSON: {e}")
                return None
            
            # Parse based on message type
            if 'greToClientEvent' in data:
                return self._parse_gre_message(data['greToClientEvent'])
            elif 'ClientToMatchServiceMessageType_ClientToGREMessage' in data:
                return self._parse_client_message(data['ClientToMatchServiceMessageType_ClientToGREMessage'])
            else:
                logger.debug(f"Unknown message type: {list(data.keys())}")
                return None
                
        except Exception as e:
            logger.error(f"Error parsing log line: {e}")
            return UnknownEvent(
                raw_message=line,
                parse_error=str(e)
            )
    
    def _parse_gre_message(self, data: Dict[str, Any]) -> Optional[GameEvent]:
        """Parse GRE (Game Rules Engine) message."""
        try:
            gre_event = data.get('greToClientEvent', {})
            message_type = gre_event.get('type', '')
            
            if message_type == 'GREMessageType_GameStateMessage':
                return self._parse_game_state_message(gre_event)
            elif message_type == 'GREMessageType_GameStateMessage_GameState':
                return self._parse_detailed_game_state(gre_event)
            elif message_type == 'GREMessageType_GameStateMessage_GameState_Zone':
                return self._parse_zone_message(gre_event)
            else:
                logger.debug(f"Unknown GRE message type: {message_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error parsing GRE message: {e}")
            return None
    
    def _parse_client_message(self, data: Dict[str, Any]) -> Optional[GameEvent]:
        """Parse client-to-server message."""
        try:
            # These are usually player actions
            message_type = data.get('type', '')
            
            if 'SelectCard' in message_type:
                return self._parse_card_selection(data)
            elif 'SelectTargets' in message_type:
                return self._parse_target_selection(data)
            elif 'DeclareAttackers' in message_type:
                return self._parse_attack_declaration(data)
            else:
                logger.debug(f"Unknown client message type: {message_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error parsing client message: {e}")
            return None
    
    def _parse_game_state_message(self, data: Dict[str, Any]) -> Optional[GameEvent]:
        """Parse game state message."""
        try:
            game_state = data.get('gameStateMessage', {})
            
            # Update current game state
            self.current_game_state.update(game_state)
            
            # Check for turn/phase changes
            turn_info = game_state.get('turnInfo', {})
            if turn_info:
                turn_number = turn_info.get('turnNumber', 0)
                phase = turn_info.get('phase', '')
                step = turn_info.get('step', '')
                
                # Detect phase changes
                if phase != self.current_phase:
                    old_phase = self.current_phase
                    self.current_phase = phase
                    
                    return PhaseChangeEvent(
                        old_phase=old_phase,
                        new_phase=phase,
                        turn_number=turn_number,
                        phase=phase,
                        step=step,
                        active_player=turn_info.get('activePlayer'),
                        priority_player=turn_info.get('priorityPlayer'),
                        raw_data=data
                    )
            
            # Parse zones and objects for card events
            zones = game_state.get('zones', [])
            objects = game_state.get('objects', [])
            
            # Create card info objects
            cards = self._parse_cards(objects)
            
            # Check for new cards in hand (draw events)
            hand_zone = next((z for z in zones if z.get('type') == 'ZoneType_Hand'), None)
            if hand_zone:
                hand_cards = hand_zone.get('objectInstanceIds', [])
                # This is simplified - in reality we'd track previous state
                for card in cards:
                    if card.instance_id in hand_cards and card.zone_type == ZoneType.HAND:
                        return DrawCardEvent(
                            player=card.controller,
                            card=card,
                            raw_data=data
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing game state: {e}")
            return None
    
    def _parse_detailed_game_state(self, data: Dict[str, Any]) -> Optional[GameEvent]:
        """Parse detailed game state message."""
        # This would handle more complex game state updates
        return None
    
    def _parse_zone_message(self, data: Dict[str, Any]) -> Optional[GameEvent]:
        """Parse zone-specific message."""
        # This would handle zone changes, card movements, etc.
        return None
    
    def _parse_card_selection(self, data: Dict[str, Any]) -> Optional[GameEvent]:
        """Parse card selection message."""
        # This would handle player selecting cards
        return None
    
    def _parse_target_selection(self, data: Dict[str, Any]) -> Optional[GameEvent]:
        """Parse target selection message."""
        # This would handle player selecting targets
        return None
    
    def _parse_attack_declaration(self, data: Dict[str, Any]) -> Optional[GameEvent]:
        """Parse attack declaration message."""
        # This would handle declaring attackers
        return None
    
    def _parse_cards(self, objects: List[Dict[str, Any]]) -> List[CardInfo]:
        """Parse card objects from game state."""
        cards = []
        
        for obj in objects:
            try:
                # Map Arena card ID to Scryfall data if available
                grp_id = obj.get('grpId', 0)
                card_name = obj.get('name', 'Unknown')
                
                # Get card data from cache if available
                card_data = None
                if self.card_cache and grp_id:
                    card_data = self.card_cache.get_card_by_arena_id(str(grp_id))
                
                # Determine zone type
                zone_id = obj.get('zoneId', 0)
                zone_type = self._map_zone_type(zone_id)
                
                # Parse card types
                card_types = []
                for card_type in obj.get('cardTypes', []):
                    if 'Creature' in card_type:
                        card_types.append(CardType.CREATURE)
                    elif 'Instant' in card_type:
                        card_types.append(CardType.INSTANT)
                    elif 'Sorcery' in card_type:
                        card_types.append(CardType.SORCERY)
                    elif 'Enchantment' in card_type:
                        card_types.append(CardType.ENCHANTMENT)
                    elif 'Artifact' in card_type:
                        card_types.append(CardType.ARTIFACT)
                    elif 'Planeswalker' in card_type:
                        card_types.append(CardType.PLANESWALKER)
                    elif 'Land' in card_type:
                        card_types.append(CardType.LAND)
                
                card = CardInfo(
                    instance_id=obj.get('instanceId', 0),
                    grp_id=grp_id,
                    name=card_name,
                    mana_cost=obj.get('manaCost', ''),
                    cmc=obj.get('cmc', 0),
                    power=obj.get('power'),
                    toughness=obj.get('toughness'),
                    card_types=card_types,
                    colors=obj.get('colors', []),
                    abilities=obj.get('abilities', []),
                    keywords=obj.get('keywords', []),
                    controller=obj.get('controller', 0),
                    zone_id=zone_id,
                    zone_type=zone_type,
                    visibility=obj.get('visibility', 'visible'),
                    counters=obj.get('counters', {})
                )
                
                cards.append(card)
                
            except Exception as e:
                logger.error(f"Error parsing card object: {e}")
                continue
        
        return cards
    
    def _map_zone_type(self, zone_id: int) -> Optional[ZoneType]:
        """Map zone ID to zone type."""
        # This is simplified - in reality we'd need to track zone mappings
        zone_mapping = {
            1: ZoneType.BATTLEFIELD,
            2: ZoneType.HAND,
            3: ZoneType.GRAVEYARD,
            4: ZoneType.LIBRARY,
            5: ZoneType.EXILE,
            6: ZoneType.STACK
        }
        return zone_mapping.get(zone_id)
    
    def parse_log_file(self, file_path: str) -> Iterator[GameEvent]:
        """
        Parse an entire log file and yield events.
        
        Args:
            file_path: Path to log file
            
        Yields:
            GameEvent objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    event = self.parse_log_line(line)
                    if event:
                        yield event
                        
        except Exception as e:
            logger.error(f"Error reading log file {file_path}: {e}")
    
    def parse_log_lines(self, lines: List[str]) -> List[GameEvent]:
        """
        Parse a list of log lines.
        
        Args:
            lines: List of log lines
            
        Returns:
            List of parsed events
        """
        events = []
        for line in lines:
            event = self.parse_log_line(line)
            if event:
                events.append(event)
        return events
