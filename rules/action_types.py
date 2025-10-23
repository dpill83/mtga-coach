#!/usr/bin/env python3
"""
Action Types

Defines all possible actions a player can take in Magic: The Gathering.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

from parser.events import CardInfo, ZoneType, CardType
from state.player_state import PlayerState

class ActionType(str, Enum):
    """Types of actions a player can take."""
    # Basic actions
    PLAY_LAND = "play_land"
    CAST_SPELL = "cast_spell"
    ACTIVATE_ABILITY = "activate_ability"
    DECLARE_ATTACKERS = "declare_attackers"
    DECLARE_BLOCKERS = "declare_blocks"
    PASS_PRIORITY = "pass_priority"
    CONCEDE = "concede"
    
    # Special actions
    MULLIGAN = "mulligan"
    SCRY = "scry"
    DRAW_CARD = "draw_card"
    SHUFFLE = "shuffle"
    
    # Combat actions
    ASSIGN_DAMAGE = "assign_damage"
    ASSIGN_COMBAT_DAMAGE = "assign_combat_damage"
    
    # Stack actions
    RESPOND = "respond"
    COUNTER_SPELL = "counter_spell"
    
    # Special game actions
    PAY_COST = "pay_cost"
    CHOOSE_MODE = "choose_mode"
    CHOOSE_TARGETS = "choose_targets"

class ActionPriority(str, Enum):
    """Priority levels for actions."""
    HIGH = "high"          # Must be done immediately (combat damage, triggers)
    NORMAL = "normal"      # Standard priority actions
    LOW = "low"            # Can be done at any time (concede, pass)

class ActionTiming(str, Enum):
    """When actions can be performed."""
    ANY_TIME = "any_time"           # Any time you have priority
    MAIN_PHASE = "main_phase"       # During main phases
    COMBAT_PHASE = "combat_phase"   # During combat phase
    END_STEP = "end_step"          # During end step
    UPKEEP = "upkeep"              # During upkeep
    DRAW_STEP = "draw_step"         # During draw step
    DECLARE_ATTACKERS = "declare_attackers"  # During declare attackers step
    DECLARE_BLOCKERS = "declare_blockers"   # During declare blockers step
    COMBAT_DAMAGE = "combat_damage" # During combat damage step
    END_COMBAT = "end_combat"       # During end of combat step

class BaseAction(BaseModel):
    """Base class for all actions."""
    action_type: ActionType
    player_id: int
    timestamp: datetime = Field(default_factory=datetime.now)
    priority: ActionPriority = ActionPriority.NORMAL
    timing: ActionTiming = ActionTiming.ANY_TIME
    legal: bool = False
    reason: Optional[str] = None
    
    def is_legal(self) -> bool:
        """Check if this action is legal."""
        return self.legal
    
    def set_illegal(self, reason: str) -> None:
        """Mark action as illegal with reason."""
        self.legal = False
        self.reason = reason
    
    def set_legal(self) -> None:
        """Mark action as legal."""
        self.legal = True
        self.reason = None

class PlayLandAction(BaseAction):
    """Action to play a land."""
    action_type: ActionType = ActionType.PLAY_LAND
    timing: ActionTiming = ActionTiming.MAIN_PHASE
    card: CardInfo
    land_type: Optional[str] = None  # Basic, non-basic, etc.
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.MAIN_PHASE

class CastSpellAction(BaseAction):
    """Action to cast a spell."""
    action_type: ActionType = ActionType.CAST_SPELL
    timing: ActionTiming = ActionTiming.ANY_TIME
    spell: CardInfo
    targets: List[int] = Field(default_factory=list)  # Instance IDs of targets
    modes: List[str] = Field(default_factory=list)   # Spell modes
    mana_cost: str = ""
    mana_paid: Dict[str, int] = Field(default_factory=dict)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.ANY_TIME

class ActivateAbilityAction(BaseAction):
    """Action to activate an ability."""
    action_type: ActionType = ActionType.ACTIVATE_ABILITY
    timing: ActionTiming = ActionTiming.ANY_TIME
    source: CardInfo
    ability: str
    targets: List[int] = Field(default_factory=list)
    cost: str = ""
    mana_paid: Dict[str, int] = Field(default_factory=dict)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.ANY_TIME

class DeclareAttackersAction(BaseAction):
    """Action to declare attackers."""
    action_type: ActionType = ActionType.DECLARE_ATTACKERS
    timing: ActionTiming = ActionTiming.DECLARE_ATTACKERS
    attackers: List[CardInfo] = Field(default_factory=list)
    targets: List[int] = Field(default_factory=list)  # Planeswalkers or players
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.DECLARE_ATTACKERS

class DeclareBlockersAction(BaseAction):
    """Action to declare blockers."""
    action_type: ActionType = ActionType.DECLARE_BLOCKERS
    timing: ActionTiming = ActionTiming.DECLARE_BLOCKERS
    blocks: Dict[int, List[int]] = Field(default_factory=dict)  # {attacker_id: [blocker_ids]}
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.DECLARE_BLOCKERS

class PassPriorityAction(BaseAction):
    """Action to pass priority."""
    action_type: ActionType = ActionType.PASS_PRIORITY
    timing: ActionTiming = ActionTiming.ANY_TIME
    priority_passed: bool = True
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.ANY_TIME

class ConcedeAction(BaseAction):
    """Action to concede the game."""
    action_type: ActionType = ActionType.CONCEDE
    timing: ActionTiming = ActionTiming.ANY_TIME
    priority: ActionPriority = ActionPriority.LOW
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.ANY_TIME
        self.priority = ActionPriority.LOW

class MulliganAction(BaseAction):
    """Action to mulligan."""
    action_type: ActionType = ActionType.MULLIGAN
    timing: ActionTiming = ActionTiming.ANY_TIME
    priority: ActionPriority = ActionPriority.HIGH
    cards_to_mulligan: List[CardInfo] = Field(default_factory=list)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.ANY_TIME
        self.priority = ActionPriority.HIGH

class ScryAction(BaseAction):
    """Action to scry."""
    action_type: ActionType = ActionType.SCRY
    timing: ActionTiming = ActionTiming.ANY_TIME
    scry_amount: int = 1
    cards_to_top: List[CardInfo] = Field(default_factory=list)
    cards_to_bottom: List[CardInfo] = Field(default_factory=list)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.ANY_TIME

class DrawCardAction(BaseAction):
    """Action to draw a card."""
    action_type: ActionType = ActionType.DRAW_CARD
    timing: ActionTiming = ActionTiming.ANY_TIME
    amount: int = 1
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.ANY_TIME

class ShuffleAction(BaseAction):
    """Action to shuffle library."""
    action_type: ActionType = ActionType.SHUFFLE
    timing: ActionTiming = ActionTiming.ANY_TIME
    library_owner: int  # Player ID who owns the library
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.ANY_TIME

class AssignDamageAction(BaseAction):
    """Action to assign damage."""
    action_type: ActionType = ActionType.ASSIGN_DAMAGE
    timing: ActionTiming = ActionTiming.COMBAT_DAMAGE
    source: CardInfo
    targets: List[Dict[str, Any]] = Field(default_factory=list)  # [{target_id: amount}]
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.COMBAT_DAMAGE

class RespondAction(BaseAction):
    """Action to respond to something on the stack."""
    action_type: ActionType = ActionType.RESPOND
    timing: ActionTiming = ActionTiming.ANY_TIME
    response_to: int  # Instance ID of what we're responding to
    response_action: BaseAction
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.ANY_TIME

class CounterSpellAction(BaseAction):
    """Action to counter a spell."""
    action_type: ActionType = ActionType.COUNTER_SPELL
    timing: ActionTiming = ActionTiming.ANY_TIME
    target_spell: CardInfo
    counter_spell: CardInfo
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.ANY_TIME

class PayCostAction(BaseAction):
    """Action to pay a cost."""
    action_type: ActionType = ActionType.PAY_COST
    timing: ActionTiming = ActionTiming.ANY_TIME
    cost_type: str  # mana, life, sacrifice, etc.
    cost_amount: int
    cost_target: Optional[CardInfo] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.ANY_TIME

class ChooseModeAction(BaseAction):
    """Action to choose a mode for a spell."""
    action_type: ActionType = ActionType.CHOOSE_MODE
    timing: ActionTiming = ActionTiming.ANY_TIME
    spell: CardInfo
    chosen_mode: str
    available_modes: List[str] = Field(default_factory=list)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.ANY_TIME

class ChooseTargetsAction(BaseAction):
    """Action to choose targets for a spell or ability."""
    action_type: ActionType = ActionType.CHOOSE_TARGETS
    timing: ActionTiming = ActionTiming.ANY_TIME
    source: CardInfo
    targets: List[int] = Field(default_factory=list)
    required_targets: int = 0
    max_targets: int = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        self.timing = ActionTiming.ANY_TIME

# Union type for all actions
Action = (
    PlayLandAction | CastSpellAction | ActivateAbilityAction |
    DeclareAttackersAction | DeclareBlockersAction | PassPriorityAction |
    ConcedeAction | MulliganAction | ScryAction | DrawCardAction |
    ShuffleAction | AssignDamageAction | RespondAction | CounterSpellAction |
    PayCostAction | ChooseModeAction | ChooseTargetsAction
)
