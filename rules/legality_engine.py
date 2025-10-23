#!/usr/bin/env python3
"""
Action Legality Engine

Determines which actions are legal based on the current game state.
Implements Magic: The Gathering rules and timing restrictions.
"""

from typing import List, Dict, Optional, Set, Any
from datetime import datetime
import logging

from state.game_state import GameState, GameStatus
from state.player_state import PlayerState, PlayerType
from parser.events import Phase, ZoneType, CardType
from rules.action_types import (
    Action, ActionType, ActionTiming, ActionPriority,
    PlayLandAction, CastSpellAction, ActivateAbilityAction,
    DeclareAttackersAction, DeclareBlockersAction, PassPriorityAction,
    ConcedeAction, MulliganAction, ScryAction, DrawCardAction,
    ShuffleAction, AssignDamageAction, RespondAction, CounterSpellAction,
    PayCostAction, ChooseModeAction, ChooseTargetsAction
)

logger = logging.getLogger(__name__)

class LegalityEngine:
    """Engine for determining action legality."""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.legal_actions_cache: Dict[str, List[Action]] = {}
        self.cache_timestamp: Optional[datetime] = None
        self.cache_duration = 1.0  # seconds
    
    def get_legal_actions(self, player_id: int, force_refresh: bool = False) -> List[Action]:
        """Get all legal actions for a player."""
        # Check cache
        if not force_refresh and self._is_cache_valid():
            cached_actions = self.legal_actions_cache.get(str(player_id), [])
            if cached_actions:
                return cached_actions
        
        # Generate legal actions
        legal_actions = self._generate_legal_actions(player_id)
        
        # Cache results
        self.legal_actions_cache[str(player_id)] = legal_actions
        self.cache_timestamp = datetime.now()
        
        return legal_actions
    
    def is_action_legal(self, action: Action) -> bool:
        """Check if a specific action is legal."""
        try:
            # Validate basic requirements
            if not self._validate_basic_requirements(action):
                return False
            
            # Validate timing
            if not self._validate_timing(action):
                return False
            
            # Validate specific action type
            if not self._validate_action_type(action):
                return False
            
            # Validate resources
            if not self._validate_resources(action):
                return False
            
            # Validate targets
            if not self._validate_targets(action):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating action {action.action_type}: {e}")
            return False
    
    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        if self.cache_timestamp is None:
            return False
        
        elapsed = (datetime.now() - self.cache_timestamp).total_seconds()
        return elapsed < self.cache_duration
    
    def _generate_legal_actions(self, player_id: int) -> List[Action]:
        """Generate all legal actions for a player."""
        legal_actions = []
        
        try:
            # Get player state
            player = self.game_state.get_player(player_id)
            if not player:
                return legal_actions
            
            # Check if it's the player's turn
            is_active_player = (self.game_state.active_player == player_id)
            
            # Generate actions based on current phase and state
            if self.game_state.current_phase == Phase.FIRST_MAIN or self.game_state.current_phase == Phase.SECOND_MAIN:
                legal_actions.extend(self._generate_main_phase_actions(player, is_active_player))
            
            elif self.game_state.current_phase == Phase.COMBAT_BEGIN:
                legal_actions.extend(self._generate_combat_phase_actions(player, is_active_player))
            
            elif self.game_state.current_phase == Phase.DECLARE_ATTACKERS:
                legal_actions.extend(self._generate_attack_actions(player, is_active_player))
            
            elif self.game_state.current_phase == Phase.DECLARE_BLOCKERS:
                legal_actions.extend(self._generate_block_actions(player, is_active_player))
            
            elif self.game_state.current_phase == Phase.COMBAT_DAMAGE:
                legal_actions.extend(self._generate_damage_actions(player, is_active_player))
            
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
    
    def _generate_main_phase_actions(self, player: PlayerState, is_active_player: bool) -> List[Action]:
        """Generate actions available during main phases."""
        actions = []
        
        # Play land (once per turn)
        if is_active_player and player.can_play_land():
            for land in player.hand.cards:
                if CardType.LAND in land.card_types:
                    action = PlayLandAction(
                        player_id=player.player_id,
                        card=land,
                        land_type=self._get_land_type(land)
                    )
                    actions.append(action)
        
        # Cast spells
        for spell in player.hand.cards:
            if self._can_cast_spell(spell, player):
                action = CastSpellAction(
                    player_id=player.player_id,
                    spell=spell,
                    mana_cost=spell.mana_cost
                )
                actions.append(action)
        
        # Activate abilities
        for card in player.battlefield.get_all_cards():
            if self._can_activate_ability(card, player):
                for ability in card.abilities:
                    action = ActivateAbilityAction(
                        player_id=player.player_id,
                        source=card,
                        ability=ability
                    )
                    actions.append(action)
        
        return actions
    
    def _generate_combat_phase_actions(self, player: PlayerState, is_active_player: bool) -> List[Action]:
        """Generate actions available during combat phase."""
        actions = []
        
        if is_active_player:
            # Declare attackers
            if player.can_attack():
                creatures = player.battlefield.get_creatures()
                if creatures:
                    action = DeclareAttackersAction(
                        player_id=player.player_id,
                        attackers=creatures
                    )
                    actions.append(action)
        
        return actions
    
    def _generate_attack_actions(self, player: PlayerState, is_active_player: bool) -> List[Action]:
        """Generate actions available during declare attackers step."""
        actions = []
        
        if is_active_player:
            # Declare attackers
            if player.can_attack():
                creatures = player.battlefield.get_creatures()
                if creatures:
                    action = DeclareAttackersAction(
                        player_id=player.player_id,
                        attackers=creatures
                    )
                    actions.append(action)
        
        return actions
    
    def _generate_block_actions(self, player: PlayerState, is_active_player: bool) -> List[Action]:
        """Generate actions available during declare blockers step."""
        actions = []
        
        if not is_active_player:
            # Declare blockers
            creatures = player.battlefield.get_creatures()
            if creatures:
                action = DeclareBlockersAction(
                    player_id=player.player_id,
                    blocks={}  # Would be populated based on attackers
                )
                actions.append(action)
        
        return actions
    
    def _generate_damage_actions(self, player: PlayerState, is_active_player: bool) -> List[Action]:
        """Generate actions available during combat damage step."""
        actions = []
        
        # Assign combat damage
        for creature in player.battlefield.get_creatures():
            if creature.power and creature.power > 0:
                action = AssignDamageAction(
                    player_id=player.player_id,
                    source=creature,
                    targets=[]
                )
                actions.append(action)
        
        return actions
    
    def _generate_always_available_actions(self, player: PlayerState) -> List[Action]:
        """Generate actions that are always available."""
        actions = []
        
        # Pass priority
        actions.append(PassPriorityAction(player_id=player.player_id))
        
        # Concede
        actions.append(ConcedeAction(player_id=player.player_id))
        
        # Draw card (if ability allows)
        if self._can_draw_card(player):
            actions.append(DrawCardAction(player_id=player.player_id))
        
        # Scry (if ability allows)
        if self._can_scry(player):
            actions.append(ScryAction(player_id=player.player_id))
        
        return actions
    
    def _validate_basic_requirements(self, action: Action) -> bool:
        """Validate basic requirements for an action."""
        # Check if game is active
        if not self.game_state.is_game_active():
            action.set_illegal("Game is not active")
            return False
        
        # Check if player exists
        player = self.game_state.get_player(action.player_id)
        if not player:
            action.set_illegal("Player not found")
            return False
        
        # Check if player is alive
        if not player.is_alive():
            action.set_illegal("Player is not alive")
            return False
        
        return True
    
    def _validate_timing(self, action: Action) -> bool:
        """Validate timing requirements for an action."""
        current_phase = self.game_state.current_phase
        current_step = self.game_state.current_step
        
        # Check if action can be performed at current timing
        if action.timing == ActionTiming.MAIN_PHASE:
            if current_phase not in [Phase.FIRST_MAIN, Phase.SECOND_MAIN]:
                action.set_illegal(f"Action can only be performed during main phases, current phase: {current_phase}")
                return False
        
        elif action.timing == ActionTiming.COMBAT_PHASE:
            if current_phase not in [Phase.COMBAT_BEGIN, Phase.DECLARE_ATTACKERS, 
                                   Phase.DECLARE_BLOCKERS, Phase.COMBAT_DAMAGE, Phase.END_COMBAT]:
                action.set_illegal(f"Action can only be performed during combat phase, current phase: {current_phase}")
                return False
        
        elif action.timing == ActionTiming.DECLARE_ATTACKERS:
            if current_phase != Phase.DECLARE_ATTACKERS:
                action.set_illegal(f"Action can only be performed during declare attackers step, current phase: {current_phase}")
                return False
        
        elif action.timing == ActionTiming.DECLARE_BLOCKERS:
            if current_phase != Phase.DECLARE_BLOCKERS:
                action.set_illegal(f"Action can only be performed during declare blockers step, current phase: {current_phase}")
                return False
        
        elif action.timing == ActionTiming.COMBAT_DAMAGE:
            if current_phase != Phase.COMBAT_DAMAGE:
                action.set_illegal(f"Action can only be performed during combat damage step, current phase: {current_phase}")
                return False
        
        return True
    
    def _validate_action_type(self, action: Action) -> bool:
        """Validate specific action type requirements."""
        if action.action_type == ActionType.PLAY_LAND:
            return self._validate_play_land(action)
        elif action.action_type == ActionType.CAST_SPELL:
            return self._validate_cast_spell(action)
        elif action.action_type == ActionType.ACTIVATE_ABILITY:
            return self._validate_activate_ability(action)
        elif action.action_type == ActionType.DECLARE_ATTACKERS:
            return self._validate_declare_attackers(action)
        elif action.action_type == ActionType.DECLARE_BLOCKERS:
            return self._validate_declare_blockers(action)
        else:
            return True  # Other action types have basic validation
    
    def _validate_play_land(self, action: PlayLandAction) -> bool:
        """Validate playing a land."""
        player = self.game_state.get_player(action.player_id)
        if not player:
            return False
        
        # Check if player can play a land this turn
        if not player.can_play_land():
            action.set_illegal("Player has already played a land this turn")
            return False
        
        # Check if card is in hand
        if not player.hand.get_card(action.card.instance_id):
            action.set_illegal("Card is not in hand")
            return False
        
        # Check if card is a land
        if CardType.LAND not in action.card.card_types:
            action.set_illegal("Card is not a land")
            return False
        
        return True
    
    def _validate_cast_spell(self, action: CastSpellAction) -> bool:
        """Validate casting a spell."""
        player = self.game_state.get_player(action.player_id)
        if not player:
            return False
        
        # Check if card is in hand
        if not player.hand.get_card(action.spell.instance_id):
            action.set_illegal("Spell is not in hand")
            return False
        
        # Check if player can pay mana cost
        if not self._can_pay_mana_cost(action.spell.mana_cost, player):
            action.set_illegal("Player cannot pay mana cost")
            return False
        
        return True
    
    def _validate_activate_ability(self, action: ActivateAbilityAction) -> bool:
        """Validate activating an ability."""
        player = self.game_state.get_player(action.player_id)
        if not player:
            return False
        
        # Check if source is on battlefield
        if not player.battlefield.get_card(action.source.instance_id):
            action.set_illegal("Source is not on battlefield")
            return False
        
        # Check if player can use this ability
        if not player.can_use_ability(action.ability):
            action.set_illegal("Player cannot use this ability this turn")
            return False
        
        return True
    
    def _validate_declare_attackers(self, action: DeclareAttackersAction) -> bool:
        """Validate declaring attackers."""
        player = self.game_state.get_player(action.player_id)
        if not player:
            return False
        
        # Check if it's the player's turn
        if self.game_state.active_player != action.player_id:
            action.set_illegal("Not the player's turn")
            return False
        
        # Check if player can attack
        if not player.can_attack():
            action.set_illegal("Player has already attacked this turn")
            return False
        
        # Check if all attackers are on battlefield
        for attacker in action.attackers:
            if not player.battlefield.get_card(attacker.instance_id):
                action.set_illegal(f"Attacker {attacker.name} is not on battlefield")
                return False
        
        return True
    
    def _validate_declare_blockers(self, action: DeclareBlockersAction) -> bool:
        """Validate declaring blockers."""
        player = self.game_state.get_player(action.player_id)
        if not player:
            return False
        
        # Check if it's not the player's turn
        if self.game_state.active_player == action.player_id:
            action.set_illegal("Cannot block on your own turn")
            return False
        
        # Check if all blockers are on battlefield
        for attacker_id, blocker_ids in action.blocks.items():
            for blocker_id in blocker_ids:
                if not player.battlefield.get_card(blocker_id):
                    action.set_illegal(f"Blocker {blocker_id} is not on battlefield")
                    return False
        
        return True
    
    def _validate_resources(self, action: Action) -> bool:
        """Validate resource requirements."""
        player = self.game_state.get_player(action.player_id)
        if not player:
            return False
        
        # Check mana costs
        if hasattr(action, 'mana_cost') and action.mana_cost:
            if not self._can_pay_mana_cost(action.mana_cost, player):
                action.set_illegal("Cannot pay mana cost")
                return False
        
        return True
    
    def _validate_targets(self, action: Action) -> bool:
        """Validate target requirements."""
        # Basic target validation - would be expanded for specific spells
        if hasattr(action, 'targets') and action.targets:
            # Check if targets are valid
            for target_id in action.targets:
                if not self._is_valid_target(target_id, action):
                    action.set_illegal(f"Invalid target: {target_id}")
                    return False
        
        return True
    
    def _can_cast_spell(self, spell: CardInfo, player: PlayerState) -> bool:
        """Check if a spell can be cast."""
        # Check if it's a spell (not a land)
        if CardType.LAND in spell.card_types:
            return False
        
        # Check mana cost
        if not self._can_pay_mana_cost(spell.mana_cost, player):
            return False
        
        return True
    
    def _can_activate_ability(self, card: CardInfo, player: PlayerState) -> bool:
        """Check if an ability can be activated."""
        # Check if player can use abilities
        if not player.can_use_ability("general"):
            return False
        
        # Check if card has abilities
        if not card.abilities:
            return False
        
        return True
    
    def _can_pay_mana_cost(self, mana_cost: str, player: PlayerState) -> bool:
        """Check if player can pay a mana cost."""
        if not mana_cost:
            return True
        
        # Simplified mana cost checking
        # In a real implementation, this would parse the mana cost properly
        total_cost = len(mana_cost.replace('{', '').replace('}', ''))
        return player.mana_pool.total_mana() >= total_cost
    
    def _can_draw_card(self, player: PlayerState) -> bool:
        """Check if player can draw a card."""
        # Basic check - would be expanded for specific abilities
        return True
    
    def _can_scry(self, player: PlayerState) -> bool:
        """Check if player can scry."""
        # Basic check - would be expanded for specific abilities
        return False
    
    def _is_valid_target(self, target_id: int, action: Action) -> bool:
        """Check if a target is valid."""
        # Basic target validation - would be expanded for specific spells
        return True
    
    def _get_land_type(self, land: CardInfo) -> str:
        """Get the type of land."""
        # Simplified land type detection
        if "Basic" in land.type_line:
            return "basic"
        else:
            return "non-basic"
