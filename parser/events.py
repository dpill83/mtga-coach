#!/usr/bin/env python3
"""
Event Schema Definitions

Pydantic models for MTGA game events parsed from log files.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum

class EventType(str, Enum):
    """Types of game events."""
    GAME_START = "game_start"
    GAME_END = "game_end"
    DRAW_CARD = "draw_card"
    PLAY_CARD = "play_card"
    CAST_SPELL = "cast_spell"
    ACTIVATE_ABILITY = "activate_ability"
    DECLARE_ATTACKERS = "declare_attackers"
    DECLARE_BLOCKERS = "declare_blockers"
    COMBAT_DAMAGE = "combat_damage"
    LIFE_CHANGE = "life_change"
    PHASE_CHANGE = "phase_change"
    STEP_CHANGE = "step_change"
    TURN_CHANGE = "turn_change"
    ZONE_CHANGE = "zone_change"
    COUNTER_CHANGE = "counter_change"
    TRIGGERED_ABILITY = "triggered_ability"
    UNKNOWN = "unknown"

class Phase(str, Enum):
    """Game phases."""
    UNTAP = "untap"
    UPKEEP = "upkeep"
    DRAW = "draw"
    FIRST_MAIN = "first_main"
    COMBAT_BEGIN = "combat_begin"
    DECLARE_ATTACKERS = "declare_attackers"
    DECLARE_BLOCKERS = "declare_blockers"
    COMBAT_DAMAGE = "combat_damage"
    COMBAT_END = "combat_end"
    SECOND_MAIN = "second_main"
    END_STEP = "end_step"
    CLEANUP = "cleanup"

class ZoneType(str, Enum):
    """Zone types."""
    BATTLEFIELD = "battlefield"
    HAND = "hand"
    GRAVEYARD = "graveyard"
    LIBRARY = "library"
    EXILE = "exile"
    STACK = "stack"
    COMMAND = "command"

class CardType(str, Enum):
    """Card types."""
    CREATURE = "creature"
    INSTANT = "instant"
    SORCERY = "sorcery"
    ENCHANTMENT = "enchantment"
    ARTIFACT = "artifact"
    PLANESWALKER = "planeswalker"
    LAND = "land"

class BaseEvent(BaseModel):
    """Base event with common fields."""
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.now)
    game_id: Optional[str] = None
    turn_number: Optional[int] = None
    phase: Optional[Phase] = None
    step: Optional[str] = None
    active_player: Optional[int] = None
    priority_player: Optional[int] = None
    raw_data: Optional[Dict[str, Any]] = None

class CardInfo(BaseModel):
    """Card information."""
    instance_id: int
    grp_id: int  # Arena card ID
    name: str
    mana_cost: str = ""
    cmc: int = 0
    power: Optional[int] = None
    toughness: Optional[int] = None
    card_types: List[CardType] = []
    colors: List[str] = []
    abilities: List[str] = []
    keywords: List[str] = []
    controller: int
    zone_id: int
    zone_type: Optional[ZoneType] = None
    visibility: str = "visible"
    counters: Dict[str, int] = {}

class GameStartEvent(BaseEvent):
    """Game start event."""
    event_type: EventType = EventType.GAME_START
    player_life: int = 20
    opponent_life: int = 20
    player_hand: List[CardInfo] = []
    opponent_hand: List[CardInfo] = []
    battlefield: List[CardInfo] = []

class GameEndEvent(BaseEvent):
    """Game end event."""
    event_type: EventType = EventType.GAME_END
    winner: Optional[int] = None
    reason: Optional[str] = None

class DrawCardEvent(BaseEvent):
    """Card drawn event."""
    event_type: EventType = EventType.DRAW_CARD
    player: int
    card: CardInfo
    from_zone: ZoneType = ZoneType.LIBRARY
    to_zone: ZoneType = ZoneType.HAND

class PlayCardEvent(BaseEvent):
    """Card played event."""
    event_type: EventType = EventType.PLAY_CARD
    player: int
    card: CardInfo
    from_zone: ZoneType
    to_zone: ZoneType
    mana_paid: Dict[str, int] = {}  # Color -> amount
    targets: List[int] = []  # Instance IDs of targets

class CastSpellEvent(BaseEvent):
    """Spell cast event."""
    event_type: EventType = EventType.CAST_SPELL
    player: int
    spell: CardInfo
    mana_cost: str
    mana_paid: Dict[str, int] = {}
    targets: List[int] = []

class ActivateAbilityEvent(BaseEvent):
    """Activated ability event."""
    event_type: EventType = EventType.ACTIVATE_ABILITY
    player: int
    source: CardInfo
    ability: str
    cost: str
    targets: List[int] = []

class DeclareAttackersEvent(BaseEvent):
    """Attackers declared event."""
    event_type: EventType = EventType.DECLARE_ATTACKERS
    player: int
    attackers: List[CardInfo]
    targets: List[int] = []  # Planeswalkers or players

class DeclareBlockersEvent(BaseEvent):
    """Blockers declared event."""
    event_type: EventType = EventType.DECLARE_BLOCKERS
    player: int
    blocks: List[Dict[str, Any]]  # {attacker_id: [blocker_ids]}

class CombatDamageEvent(BaseEvent):
    """Combat damage event."""
    event_type: EventType = EventType.COMBAT_DAMAGE
    damage_sources: List[Dict[str, Any]]  # {source_id: {target_id: amount}}

class LifeChangeEvent(BaseEvent):
    """Life total change event."""
    event_type: EventType = EventType.LIFE_CHANGE
    player: int
    old_life: int
    new_life: int
    change: int
    source: Optional[str] = None

class PhaseChangeEvent(BaseEvent):
    """Phase change event."""
    event_type: EventType = EventType.PHASE_CHANGE
    old_phase: Optional[Phase] = None
    new_phase: Phase
    old_step: Optional[str] = None
    new_step: Optional[str] = None

class TurnChangeEvent(BaseEvent):
    """Turn change event."""
    event_type: EventType = EventType.TURN_CHANGE
    old_turn: int
    new_turn: int
    active_player: int

class ZoneChangeEvent(BaseEvent):
    """Zone change event."""
    event_type: EventType = EventType.ZONE_CHANGE
    card: CardInfo
    from_zone: ZoneType
    to_zone: ZoneType
    reason: Optional[str] = None

class CounterChangeEvent(BaseEvent):
    """Counter change event."""
    event_type: EventType = EventType.COUNTER_CHANGE
    card: CardInfo
    counter_type: str
    old_count: int
    new_count: int
    change: int

class TriggeredAbilityEvent(BaseEvent):
    """Triggered ability event."""
    event_type: EventType = EventType.TRIGGERED_ABILITY
    source: CardInfo
    ability: str
    trigger: str
    targets: List[int] = []

class UnknownEvent(BaseEvent):
    """Unknown or unparseable event."""
    event_type: EventType = EventType.UNKNOWN
    raw_message: str
    parse_error: Optional[str] = None

# Union type for all events
GameEvent = Union[
    GameStartEvent,
    GameEndEvent,
    DrawCardEvent,
    PlayCardEvent,
    CastSpellEvent,
    ActivateAbilityEvent,
    DeclareAttackersEvent,
    DeclareBlockersEvent,
    CombatDamageEvent,
    LifeChangeEvent,
    PhaseChangeEvent,
    TurnChangeEvent,
    ZoneChangeEvent,
    CounterChangeEvent,
    TriggeredAbilityEvent,
    UnknownEvent
]

def create_event_from_data(event_type: EventType, data: Dict[str, Any]) -> GameEvent:
    """Create an event instance from parsed data."""
    # This would be implemented to parse specific event types
    # For now, return a basic event structure
    base_data = {
        "event_type": event_type,
        "timestamp": datetime.now(),
        "raw_data": data
    }
    
    if event_type == EventType.GAME_START:
        return GameStartEvent(**base_data)
    elif event_type == EventType.DRAW_CARD:
        return DrawCardEvent(**base_data)
    elif event_type == EventType.PLAY_CARD:
        return PlayCardEvent(**base_data)
    elif event_type == EventType.LIFE_CHANGE:
        return LifeChangeEvent(**base_data)
    elif event_type == EventType.PHASE_CHANGE:
        return PhaseChangeEvent(**base_data)
    else:
        return UnknownEvent(**base_data, raw_message=str(data))
