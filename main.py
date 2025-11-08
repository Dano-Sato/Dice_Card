from __future__ import annotations

import json
import math
import random
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable

from REMOLib import *


@dataclass
class CardData:
    name: str
    effect: str
    description: str
    targets: int = 0
    card_type: str = "Utility"
    allow_multi_select: bool = False

    def clone(self) -> "CardData":
        return replace(self)


def load_card_library(path: Path) -> dict[str, CardData]:
    with path.open(encoding="utf-8") as card_file:
        data = json.load(card_file)

    library: dict[str, CardData] = {}
    for key, value in data.items():
        library[key] = CardData(
            name=value["name"],
            effect=value["effect"],
            description=value["description"],
            targets=value.get("targets", 0),
            card_type=value.get("card_type", "Utility"),
            allow_multi_select=value.get("allow_multi_select", False),
        )

    return library


CARD_LIBRARY: dict[str, CardData] = load_card_library(
    Path(__file__).with_name("card_library.json")
)


@dataclass
class GameState:
    deck_blueprint: list[str]
    gold: int = 10

    def add_card(self, card_key: str) -> None:
        self.deck_blueprint.append(card_key)


INITIAL_DECK_BLUEPRINT: list[str] = (
    ["reroll"] * 3
    + ["odd_attack"] * 3
    + ["even_shield"] * 3
    + ["clone"] * 3
    + ["mirror"] * 3
    + ["stasis"] * 3
    + ["tinker"] * 3
    + ["strike"] * 3
    + ["fortify"] * 3
    + ["strafe"] * 3
    + ["pair_shot"] * 3
    + ["one_shot"] * 3
    + ["double_guard"] * 3
)


def card_color_palette(card_type: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    base_color = Cs.dark(Cs.steelblue)
    if card_type == "Attack":
        base_color = Cs.dark(Cs.red)
    elif card_type == "Defense":
        base_color = Cs.dark(Cs.skyblue)
    elif card_type == "Enhance":
        base_color = Cs.dark(Cs.purple)
    elif card_type == "Manipulation":
        base_color = Cs.dark(Cs.blue)

    return base_color, Cs.light(base_color)


class HandCardWidget(rectObj):
    WIDTH = 280
    HEIGHT = 390

    def __init__(
        self, card: CardData, scene: "DiceCardScene" | None
    ) -> None:
        super().__init__(
            pygame.Rect(0, 0, self.WIDTH, self.HEIGHT),
            color=Cs.dark(Cs.steelblue),
            edge=4,
            radius=18,
        )
        self.card = card
        self.scene = scene
        self.home_pos = RPoint(0, 0)
        self.dragging = False
        self.is_hovered = False

        self.base_color, self.hover_color = card_color_palette(card.card_type)

        self.background_image = imageObj("card_base.png")
        base_scale = self.HEIGHT / self.background_image.rect.height
        self.background_image.scale = base_scale
        self.background_image.setParent(self, depth=0)
        self.background_image.center = self.offsetRect.center

        overlay_rect = pygame.Rect(0, 0, self.WIDTH, self.HEIGHT)
        self.color_overlay = rectObj(
            overlay_rect,
            color=self.base_color,
            radius=18,
        )
        self.color_overlay.setParent(self, depth=1)
        self.color_overlay.alpha = 60

        self.color_overlay.center = self.offsetRect.center

        self.title = textObj(card.name, size=26, color=Cs.white)
        self.title.setParent(self, depth=2)
        self.title.centerx = self.offsetRect.centerx
        self.title.y = 30

        try:
            self.illustration = imageObj("card_{}.png".format(card.effect))
        except:
            try:
                self.illustration = imageObj("card_{}.png".format(card.effect.replace("_plus","")))
            except:
                self.illustration = imageObj("sample.png")
        illus_scale = min(
            (self.WIDTH - 36) / self.illustration.rect.width,
            (self.HEIGHT * 0.42) / self.illustration.rect.height,
        )
        self.illustration.scale = illus_scale *1.2
        self.illustration.setParent(self, depth=0)
        self.illustration.centerx = self.offsetRect.centerx
        self.illustration.y = self.title.rect.bottom + 25

        self.desc = longTextObj(
            card.description,
            pos=RPoint(0, 0),
            size=16,
            color=Cs.white,
            textWidth=self.WIDTH - 70,
        )
        self.desc.setParent(self, depth=1)
        self.desc.centerx = self.offsetRect.centerx
        self.desc.y = self.illustration.rect.bottom + 22

        self.pos = RPoint(1920,1080) - RPoint(100,100)

        self._has_home = False
        self._float_amplitude = random.uniform(2,4)
        self._float_frequency = random.uniform(0.6, 0.9)
        self._float_speed = self._float_frequency * 2 * math.pi
        self._float_phase = random.uniform(0, 2 * math.pi)


    def set_home(self, pos: RPoint) -> None:
        self.home_pos = RPoint(pos.x, pos.y)
        self._has_home = True
        self.easeout("pos", self.home_pos,steps=20)

    def snap_home(self) -> None:
        self.pos = RPoint(self.home_pos.x, self.home_pos.y)

    def _update_idle_motion(self) -> None:
        if (
            not self.scene
            or not self._has_home
            or self.dragging
            or self.onInterpolation()
        ):
            return

        time_seconds = pygame.time.get_ticks() / 1000.0
        offset = math.sin(self._float_phase + time_seconds * self._float_speed)
        offset *= self._float_amplitude
        target_pos = RPoint(self.home_pos.x, self.home_pos.y + offset)
        if self.pos != target_pos:
            self.pos = target_pos

    def handle_events(self) -> None:
        self._update_idle_motion()
        is_hovered = self.collideMouse()
        self.is_hovered = is_hovered
        if self.scene is None:
            if is_hovered:
                self.color_overlay.color = self.hover_color
                self.color_overlay.alpha = 80
            else:
                self.color_overlay.color = self.base_color
                self.color_overlay.alpha = 60
            return
        if self.dragging or is_hovered:
            self.color_overlay.color = self.hover_color
            self.color_overlay.alpha = 80
        else:
            self.color_overlay.color = self.base_color
            self.color_overlay.alpha = 60

        if self.scene.game_over:
            return
        if self.scene.pending_card and self.scene.pending_card.card is not self.card:
            return

        def on_start() -> None:
            self.dragging = True
            self.color_overlay.color = self.hover_color
            self.color_overlay.alpha = 160

        def on_drop() -> None:
            self.dragging = False
            self.scene.on_card_dropped(self)

        Rs.dragEventHandler(
            self,
            draggedObj=self,
            dragStartFunc=on_start,
            dropFunc=on_drop,
            filterFunc=lambda: self.scene.can_drag_card(self),
        )


class PendingCard:
    def __init__(self, card: CardData, required: int, allow_multi: bool) -> None:
        self.card = card
        self.required = required
        self.selected: list[int] = []
        self.allow_multi_select = allow_multi

    def add_target(self, die_index: int) -> None:
        if self.allow_multi_select:
            if die_index in self.selected:
                self.selected.remove(die_index)
            else:
                self.selected.append(die_index)
        else:
            self.selected.append(die_index)

    def is_complete(self) -> bool:
        return len(self.selected) >= self.required

    def has_minimum_selection(self) -> bool:
        if self.required <= 0:
            return bool(self.selected)
        return len(self.selected) >= self.required


class DiceCardScene(Scene):
    HAND_LIMIT = 4
    PLAYER_MAX_HP = 40
    ENEMY_MAX_HP = 50

    def __init__(self, game_state: GameState) -> None:
        super().__init__()
        self.game_state = game_state

    def initOnce(self) -> None:
        
        Rs.playMusic("bgm.mp3")

        screen_rect = Rs.screenRect()
        self.background = imageObj("background.png", screen_rect)

        self.title = textObj("Dice Card Roguelike", pos=(40, 40), size=48, color=Cs.white)
        self.subtitle = textObj(
            "Roll five dice and drag cards to defeat your enemy!",
            pos=(40, 100),
            size=24,
            color=Cs.lightgrey,
        )

        self.turn_label = textObj("Turn 1", pos=(40, 150), size=26, color=Cs.yellow)
        self.player_label = textObj("Player", pos=(40, 190), size=26, color=Cs.white)

        player_bar_rect = pygame.Rect(40, 226, 360, 30)
        self.player_hp_bar_bg = rectObj(
            player_bar_rect,
            color=Cs.dark(Cs.grey),
            edge=3,
            radius=18,
        )
        player_fill_rect = player_bar_rect.inflate(-8, -8)
        self.player_hp_bar_fill = rectObj(
            player_fill_rect,
            color=Cs.lime,
            radius=14,
        )
        self.player_hp_bar_fill_origin = RPoint(player_fill_rect.topleft)
        self.player_hp_bar_fill_max_width = player_fill_rect.width
        self.player_hp_bar_fill_height = player_fill_rect.height
        self.player_hp_value = textObj(
            f"{self.PLAYER_MAX_HP}/{self.PLAYER_MAX_HP}",
            size=20,
            color=Cs.white,
        )
        self.player_hp_value.center = self.player_hp_bar_bg.center
        self.player_block_label = textObj(
            "Block 0",
            pos=(40, player_bar_rect.bottom + 12),
            size=22,
            color=Cs.skyblue,
        )

        enemy_panel_rect = pygame.Rect(screen_rect.width - 360, 150, 320, 200)
        self.enemy_panel = rectObj(
            enemy_panel_rect,
            color=Cs.dark(Cs.grey),
            edge=4,
            radius=26,
        )
        enemy_content_x = enemy_panel_rect.x + 24
        enemy_content_y = enemy_panel_rect.y + 22
        self.enemy_label = textObj(
            "Enemy",
            pos=(enemy_content_x, enemy_content_y),
            size=26,
            color=Cs.white,
        )
        enemy_bar_rect = pygame.Rect(
            enemy_content_x,
            enemy_content_y + 40,
            enemy_panel_rect.width - 48,
            28,
        )
        self.enemy_hp_bar_bg = rectObj(
            enemy_bar_rect,
            color=Cs.dark(Cs.grey),
            edge=3,
            radius=18,
        )
        enemy_fill_rect = enemy_bar_rect.inflate(-8, -8)
        self.enemy_hp_bar_fill = rectObj(
            enemy_fill_rect,
            color=Cs.crimson,
            radius=14,
        )
        self.enemy_hp_bar_fill_origin = RPoint(enemy_fill_rect.topleft)
        self.enemy_hp_bar_fill_max_width = enemy_fill_rect.width
        self.enemy_hp_bar_fill_height = enemy_fill_rect.height
        self.enemy_hp_value = textObj(
            f"{self.ENEMY_MAX_HP}/{self.ENEMY_MAX_HP}",
            size=20,
            color=Cs.white,
        )
        self.enemy_hp_value.center = self.enemy_hp_bar_bg.center
        self.enemy_block_label = textObj(
            "Block 0",
            pos=(enemy_content_x, enemy_bar_rect.bottom + 12),
            size=22,
            color=Cs.skyblue,
        )
        self.enemy_intent_label = textObj(
            "Enemy Intent",
            pos=(enemy_content_x, enemy_bar_rect.bottom + 48),
            size=24,
            color=Cs.tiffanyBlue,
        )
        self.deck_label = textObj("Deck", pos=(40, 306), size=22, color=Cs.lightgrey)
        self.gold_label = textObj("Gold 10", pos=(40, 340), size=22, color=Cs.yellow)

        dice_start_x = 600
        dice_y = 180
        dice_spacing = 120
        self.dice: list[dict[str, Any]] = []
        self.dice_buttons: list[imageButton] = []
        for i in range(5):
            rect = pygame.Rect(dice_start_x + i * dice_spacing, dice_y, 100, 100)
            button = imageButton(
                "die_1.png",
                rect,
                enableShadow=False,
            )

            overlay_rect = pygame.Rect(0, 0, rect.width, rect.height)
            frozen_overlay = rectObj(
                overlay_rect,
                color=Cs.cyan,
                radius=4,
            )
            frozen_overlay.alpha = 0
            frozen_overlay.setParent(button, depth=1)
            frozen_overlay.center = button.offsetRect.center

            selection_overlay = rectObj(
                overlay_rect,
                color=Cs.purple,
                radius=4,
            )
            selection_overlay.alpha = 0
            selection_overlay.setParent(button, depth=2)
            selection_overlay.center = button.offsetRect.center

            def make_handler(index: int) -> Callable[[], None]:
                return lambda: self.on_die_clicked(index)

            button.connect(make_handler(i))
            self.dice_buttons.append(button)
            self.dice.append({
                "value": 1,
                "frozen": 0,
                "button": button,
                "rect": rect.copy(),
                "frozen_overlay": frozen_overlay,
                "selection_overlay": selection_overlay,
            })

        self.play_zone = rectObj(
            pygame.Rect(640, 360, 280, 180),
            color=Cs.dark(Cs.grey),
            edge=4,
            radius=26,
        )
        self.play_zone.center = Rs.screenRect().center - RPoint(0, 60)
        self.play_zone_label = textObj(
            "Drag cards here",
            size=24,
            color=Cs.white,
        )
        self.play_zone_label.setParent(self.play_zone, depth=1)
        self.play_zone_label.center = self.play_zone.offsetRect.center

        self.log_box = longTextObj(
            "Drag a card upward to play it.",
            pos=RPoint(40, 370),
            size=20,
            color=Cs.white,
            textWidth=500,
        )
        self.instruction_text = textObj("", pos=(40, 550), size=24, color=Cs.orange)

        self.end_turn_button = textButton(
            "End Turn",
            pygame.Rect(980, 80, 180, 60),
            size=28,
            radius=18,
            color=Cs.orange,
            textColor=Cs.black,
        )
        self.end_turn_button.connect(self.end_turn)

        self.confirm_selection_button = textButton(
            "Confirm Selection",
            pygame.Rect(1200, 160, 180, 60),
            size=26,
            radius=18,
            color=Cs.lime,
            textColor=Cs.black,
        )
        self.confirm_selection_button.connect(self.confirm_pending_selection)

        self.reset_button = textButton(
            "New Battle",
            pygame.Rect(1180, 80, 180, 60),
            size=28,
            radius=18,
            color=Cs.mint,
            textColor=Cs.black,
        )
        self.reset_button.connect(self.reset_combat)

        self.hand_widgets: list[HandCardWidget] = []
        self.hand: list[CardData] = []
        self.draw_pile: list[CardData] = []
        self.discard_pile: list[CardData] = []

        self.pending_card: PendingCard | None = None
        self.game_over = False

        self.player_hp = self.PLAYER_MAX_HP
        self.player_block = 0
        self.enemy_hp = self.ENEMY_MAX_HP
        self.enemy_block = 0
        self.enemy_intent: tuple[str, int] = ("attack", 6)
        self.turn_count = 1

        self.reset_combat(initial=True)

    def init(self) -> None:
        return

    # -- State helpers -------------------------------------------------
    def reset_combat(self, *, initial: bool = False) -> None:
        self.game_over = False
        self.player_hp = self.PLAYER_MAX_HP
        self.player_block = 0
        self.enemy_hp = self.ENEMY_MAX_HP
        self.enemy_block = 0
        self.turn_count = 1
        self.pending_card = None
        self.hand.clear()
        self.hand_widgets.clear()
        self.draw_pile = [CARD_LIBRARY[key].clone() for key in self.game_state.deck_blueprint]
        random.shuffle(self.draw_pile)
        self.discard_pile.clear()
        for die in self.dice:
            die["frozen"] = 0
        self.log_box.text = "Drag a card upward to play it."
        self.instruction_text.text = ""
        self.roll_dice(initial=True)
        self.draw_cards(self.HAND_LIMIT)
        self.roll_enemy_intent()
        self.update_interface()
        if not initial:
            self.add_log("A new battle begins!")
        self.set_confirm_button_enabled(False)

    def roll_dice(self, *, initial: bool = False) -> None:
        for die in self.dice:
            if die["frozen"] > 0 and not initial:
                die["frozen"] -= 1
                continue
            die["value"] = random.randint(1, 6)
            if initial:
                die["frozen"] = 0
        self.update_dice_display()

    def draw_cards(self, count: int) -> None:
        Rs.playSound("get_card.mp3")
        for _ in range(count):
            if not self.draw_pile:
                self.reshuffle_discard()
            if not self.draw_pile:
                break
            card = self.draw_pile.pop()
            self.hand.append(card)
            widget = HandCardWidget(card, self)
            self.hand_widgets.append(widget)
        self.position_hand_widgets()
        self.update_deck_label()

    def reshuffle_discard(self) -> None:
        if not self.discard_pile:
            return
        random.shuffle(self.discard_pile)
        self.draw_pile.extend(self.discard_pile)
        self.discard_pile.clear()
        self.add_log("Shuffled the discard pile back into the deck.")

    def position_hand_widgets(self) -> None:
        count = len(self.hand_widgets)
        if count == 0:
            return
        total_width = count * HandCardWidget.WIDTH + (count - 1) * 20
        start_x = (Rs.screenRect().width - total_width) / 2
        y = 600
        for index, widget in enumerate(self.hand_widgets):
            x = start_x + index * (HandCardWidget.WIDTH + 20)
            widget.set_home(RPoint(x, y))

    def roll_enemy_intent(self) -> None:
        roll = random.random()
        if roll < 0.7:
            value = random.randint(6, 10)
            self.enemy_intent = ("attack", value)
        else:
            value = random.randint(4, 8)
            self.enemy_intent = ("block", value)

    def update_dice_display(self) -> None:
        for idx, die in enumerate(self.dice):
            button = die["button"]
            image_path = f"die_{die['value']}.png"
            button.setImage(image_path)
            button.alpha = 255
            target_rect: pygame.Rect | None = die.get("rect")
            if target_rect is not None:
                button.rect = target_rect
            frozen_overlay: rectObj | None = die.get("frozen_overlay")
            selection_overlay: rectObj | None = die.get("selection_overlay")
            if frozen_overlay is not None:
                frozen_overlay.rect = pygame.Rect(0, 0, button.rect.width, button.rect.height)
                frozen_overlay.center = button.offsetRect.center
                frozen_overlay.alpha = 100 if die["frozen"] > 0 else 0
            if selection_overlay is not None:
                selection_overlay.rect = pygame.Rect(0, 0, button.rect.width, button.rect.height)
                selection_overlay.center = button.offsetRect.center
                selection_overlay.alpha = (
                    100 if self.pending_card and idx in self.pending_card.selected else 0
                )
            if hasattr(button, "hoverObj"):
                button.hoverObj.setImage(image_path)
                button.hoverObj.rect = button.offsetRect
                button.hoverObj.colorize(Cs.white, alpha=60)

    def update_interface(self) -> None:
        self.turn_label.text = f"Turn {self.turn_count}"
        self.player_label.text = "Player"
        self._update_health_bar(
            self.player_hp,
            self.PLAYER_MAX_HP,
            self.player_hp_bar_fill,
            self.player_hp_bar_fill_origin,
            self.player_hp_bar_fill_max_width,
            self.player_hp_bar_fill_height,
        )
        self.player_hp_value.text = f"{self.player_hp}/{self.PLAYER_MAX_HP}"
        self.player_hp_value.center = self.player_hp_bar_bg.center
        self.player_block_label.text = f"Block {self.player_block}"

        self.enemy_label.text = "Enemy"
        self._update_health_bar(
            self.enemy_hp,
            self.ENEMY_MAX_HP,
            self.enemy_hp_bar_fill,
            self.enemy_hp_bar_fill_origin,
            self.enemy_hp_bar_fill_max_width,
            self.enemy_hp_bar_fill_height,
        )
        self.enemy_hp_value.text = f"{self.enemy_hp}/{self.ENEMY_MAX_HP}"
        self.enemy_hp_value.center = self.enemy_hp_bar_bg.center
        self.enemy_block_label.text = f"Block {self.enemy_block}"
        intent_type, intent_value = self.enemy_intent
        intent_name = "Attack" if intent_type == "attack" else "Block"
        self.enemy_intent_label.text = f"Enemy Intent: {intent_name} {intent_value}"
        self.update_deck_label()
        self.gold_label.text = f"Gold {self.game_state.gold}"

    def _update_health_bar(
        self,
        value: int,
        maximum: int,
        bar_fill: rectObj,
        origin: RPoint,
        max_width: int,
        height: int,
    ) -> None:
        clamped = max(0, min(value, maximum))
        if maximum <= 0:
            ratio = 0
        else:
            ratio = clamped / maximum
        width = int(max_width * ratio)
        if width <= 0 or ratio <= 0:
            bar_fill.alpha = 0
        else:
            bar_fill.alpha = 255
            bar_fill.rect = pygame.Rect(
                int(origin.x),
                int(origin.y),
                max(1, width),
                height,
            )

    def update_deck_label(self) -> None:
        self.deck_label.text = (
            f"Draw pile: {len(self.draw_pile)} · Discard pile: {len(self.discard_pile)}"
        )

    def add_log(self, message: str) -> None:
        lines = self.log_box.text.split("\n") if self.log_box.text else []
        lines.append(message)
        self.log_box.text = "\n".join(lines[-4:])

    def set_confirm_button_enabled(self, enabled: bool) -> None:
        self.confirm_selection_button.enabled = enabled
        if enabled:
            self.confirm_selection_button.showChilds(0)
        else:
            self.confirm_selection_button.hideChilds(0)

    def should_show_confirm_button(self) -> bool:
        return (
            self.pending_card is not None
            and self.pending_card.allow_multi_select
        )

    def update_confirm_button_state(self) -> None:
        if self.should_show_confirm_button():
            self.set_confirm_button_enabled(self.pending_card.has_minimum_selection())
        else:
            self.set_confirm_button_enabled(False)

    # -- Card interactions --------------------------------------------
    def can_drag_card(self, widget: HandCardWidget) -> bool:
        return (
            not self.game_over
            and (self.pending_card is None or self.pending_card.card is widget.card)
        )

    def on_card_dropped(self, widget: HandCardWidget) -> None:
        if self.game_over:
            widget.snap_home()
            return
        if self.pending_card and self.pending_card.card is not widget.card:
            widget.snap_home()
            return
        if widget.geometry.centery > self.play_zone.bottomleft.y:
            widget.snap_home()
            return

        # Consume the card from the hand.
        for idx, card in enumerate(self.hand):
            if card is widget.card:
                self.hand.pop(idx)
                break
        if widget in self.hand_widgets:
            self.hand_widgets.remove(widget)
        self.position_hand_widgets()

        card = widget.card
        if card.targets > 0:
            self.pending_card = PendingCard(card, card.targets, card.allow_multi_select)
            self.instruction_text.text = self.instruction_for_card(card)
            self.add_log(f"Playing {card.name}. {self.instruction_text.text}")
        else:
            self.resolve_card_effect(card, [])
            self.discard_pile.append(card)
            self.instruction_text.text = f"{card.name} played!"
            self.finalize_card_resolution()
        self.update_interface()
        self.update_confirm_button_state()

    def instruction_for_card(self, card: CardData) -> str:
        if card.effect == "clone":
            return "Select the left die, then the right die."
        if card.effect == "mirror":
            if card.allow_multi_select:
                return "Choose dice to invert, then confirm to apply."
            return "Choose a die to invert."
        if card.effect == "stasis":
            if card.allow_multi_select:
                return "Select dice to freeze and confirm to apply."
            return "Select a die to freeze."
        if card.effect == "tinker":
            if card.allow_multi_select:
                return "Select dice to tune up, then confirm to finish."
            return "Select a die to tune up."
        if card.effect == "reroll":
            return "Choose dice to reroll, then confirm when ready."
        return "Select dice."

    def finalize_card_resolution(self) -> None:
        self.pending_card = None
        self.update_dice_display()
        self.update_interface()
        self.update_deck_label()
        self.update_confirm_button_state()
        if self.enemy_hp <= 0:
            self.on_victory()

    def on_die_clicked(self, index: int) -> None:
        if self.game_over:
            return
        if self.pending_card is None:
            die = self.dice[index]
            self.add_log(f"Die {index + 1}: {die['value']}")
            return

        pending = self.pending_card
        if pending.allow_multi_select:
            already_selected = index in pending.selected
            pending.add_target(index)
            self.update_dice_display()
            if pending.has_minimum_selection():
                self.instruction_text.text = "Press Confirm to trigger the card."
            else:
                remaining = max(0, pending.required - len(pending.selected))
                if remaining > 0:
                    noun = "die" if remaining == 1 else "dice"
                    self.instruction_text.text = f"Select {remaining} more {noun}."
                else:
                    self.instruction_text.text = "Select dice to apply the effect."
            if already_selected and index not in pending.selected:
                self.add_log(f"Deselected die {index + 1}.")
            elif index in pending.selected:
                self.add_log(f"Selected die {index + 1}.")
            self.update_confirm_button_state()
        else:
            pending.add_target(index)
            self.update_dice_display()
            if pending.is_complete():
                self.resolve_card_effect(pending.card, pending.selected)
                self.discard_pile.append(pending.card)
                self.instruction_text.text = f"{pending.card.name} resolved!"
                self.finalize_card_resolution()
            else:
                remaining = pending.required - len(pending.selected)
                noun = "die" if remaining == 1 else "dice"
                self.instruction_text.text = f"Select {remaining} more {noun}."

    def confirm_pending_selection(self) -> None:
        if self.game_over:
            return
        if not self.pending_card or not self.pending_card.allow_multi_select:
            return
        pending = self.pending_card
        if not pending.has_minimum_selection():
            self.instruction_text.text = "Select dice to apply the effect."
            return
        self.resolve_card_effect(pending.card, pending.selected)
        self.discard_pile.append(pending.card)
        self.instruction_text.text = f"{pending.card.name} resolved!"
        self.finalize_card_resolution()

    def resolve_card_effect(self, card: CardData, selection: list[int]) -> None:
        if card.effect == "clone" and len(selection) >= 2:
            left, right = selection[0], selection[1]
            value = self.dice[left]["value"]
            self.dice[right]["value"] = value
            self.add_log(
                f"Pip Clone! Copied die {left + 1} value ({value}) to die {right + 1}."
            )
        elif card.effect == "mirror" and selection:
            for idx in selection:
                old = self.dice[idx]["value"]
                self.dice[idx]["value"] = 7 - old
                self.add_log(
                    f"Mirror Dice! Die {idx + 1} flipped from {old} to {self.dice[idx]['value']}."
                )
        elif card.effect == "stasis" and selection:
            for idx in selection:
                self.dice[idx]["frozen"] = max(self.dice[idx]["frozen"], 1)
                self.add_log(f"Stasis! Locked die {idx + 1} until next turn.")
        elif card.effect == "tinker" and selection:
            for idx in selection:
                old = self.dice[idx]["value"]
                if old < 6:
                    self.dice[idx]["value"] = old + 1
                self.add_log(
                    f"Tinker! Die {idx + 1} changed from {old} to {self.dice[idx]['value']}."
                )
        elif card.effect == "tinker_plus" and selection:
            for idx in selection:
                old = self.dice[idx]["value"]
                self.dice[idx]["value"] = min(6, old + 2)
                self.add_log(
                    "Tinker+! Die {} boosted from {} to {}.".format(
                        idx + 1, old, self.dice[idx]["value"]
                    )
                )
        elif card.effect == "reroll" and selection:
            for idx in selection:
                old = self.dice[idx]["value"]
                self.dice[idx]["value"] = random.randint(1, 6)
                self.add_log(
                    f"Reroll! Die {idx + 1} rerolled from {old} to {self.dice[idx]['value']}."
                )
        elif card.effect == "reroll_plus" and selection:
            for idx in selection:
                old = self.dice[idx]["value"]
                roll_one = random.randint(1, 6)
                roll_two = random.randint(1, 6)
                self.dice[idx]["value"] = max(roll_one, roll_two)
                self.add_log(
                    "Reroll+! Die {} rerolled from {} to {} ({} vs {}).".format(
                        idx + 1,
                        old,
                        self.dice[idx]["value"],
                        roll_one,
                        roll_two,
                    )
                )
        elif card.effect == "odd_attack":
            damage = sum(die["value"] for die in self.dice if die["value"] % 2 == 1)
            self.deal_damage(damage, source="Odd Attack")
        elif card.effect == "even_shield":
            block = sum(die["value"] for die in self.dice if die["value"] % 2 == 0)
            self.player_block += block
            self.add_log(f"Even Shield! Gained {block} block.")
        elif card.effect == "strafe":
            values = [die["value"] for die in self.dice]
            value_set = set(values)
            big_straights = ({1, 2, 3, 4, 5}, {2, 3, 4, 5, 6})
            small_straights = ({1, 2, 3, 4}, {2, 3, 4, 5}, {3, 4, 5, 6})
            damage = 0
            if any(straight.issubset(value_set) for straight in big_straights):
                damage = 60
                self.add_log("Strafe! Big Straight deals 60 damage.")
            elif any(straight.issubset(value_set) for straight in small_straights):
                damage = 30
                self.add_log("Strafe! Small Straight deals 30 damage.")
            else:
                self.add_log("Strafe! No straight—attack failed.")
            self.deal_damage(damage, source="Strafe")
        elif card.effect == "strike":
            damage = sum(die["value"] for die in self.dice)
            self.add_log(f"Strike! Attacking with total dice value {damage}.")
            self.deal_damage(damage, source="Strike")
        elif card.effect == "strike_plus":
            total = sum(die["value"] for die in self.dice)
            damage = total + 6
            self.add_log(
                f"Strike+! Base {total} plus 6 bonus for {damage} damage."
            )
            self.deal_damage(damage, source="Strike+")
        elif card.effect == "fortify":
            block = sum(die["value"] for die in self.dice)
            self.player_block += block
            self.add_log(f"Fortify! Gained {block} block from the total dice.")
        elif card.effect == "fortify_plus":
            total = sum(die["value"] for die in self.dice)
            block = total + 6
            self.player_block += block
            self.add_log(
                f"Fortify+! Base {total} plus 6 bonus for {block} block."
            )
        elif card.effect == "pair_shot":
            counts = Counter(die["value"] for die in self.dice)
            if any(count >= 2 for count in counts.values()):
                damage = 15
                self.add_log("Pair Shot! Pair hit for 15 damage.")
                self.deal_damage(damage, source="Pair Shot")
            else:
                self.add_log("Pair Shot! No pair—attack failed.")
        elif card.effect == "pair_shot_plus":
            counts = Counter(die["value"] for die in self.dice)
            if any(count >= 2 for count in counts.values()):
                damage = 25
                self.add_log("Pair Shot+! Enhanced pair hit for 25 damage.")
                self.deal_damage(damage, source="Pair Shot+")
            else:
                self.add_log("Pair Shot+! No pair—attack failed.")
        elif card.effect == "one_shot":
            ones = sum(1 for die in self.dice if die["value"] == 1)
            damage = ones * 15
            self.add_log(f"One Shot! {ones} dice deal {damage} damage.")
            self.deal_damage(damage, source="One Shot")
        elif card.effect == "one_shot_plus":
            ones = sum(1 for die in self.dice if die["value"] == 1)
            damage = ones * 20
            self.add_log(f"One Shot+! {ones} dice deal {damage} damage.")
            self.deal_damage(damage, source="One Shot+")
        elif card.effect == "double_guard":
            twos = sum(1 for die in self.dice if die["value"] == 2)
            block = twos * 10
            if block > 0:
                self.player_block += block
                self.add_log(f"Double Guard! {twos} dice grant {block} block.")
            else:
                self.add_log("Double Guard! Not enough dice showing 2.")
        elif card.effect == "double_guard_plus":
            twos = sum(1 for die in self.dice if die["value"] == 2)
            block = twos * 12
            if block > 0:
                self.player_block += block
                self.add_log(f"Double Guard+! {twos} dice grant {block} block.")
            else:
                self.add_log("Double Guard+! Not enough dice showing 2.")
        else:
            self.add_log("The card effect failed to resolve.")

    def deal_damage(self, amount: int, *, source: str) -> None:
        if amount <= 0:
            self.add_log(f"{source}! The attack had no effect.")
            return
        Rs.playSound("attack_sound.mp3")
        blocked = min(amount, self.enemy_block)
        if blocked:
            self.enemy_block -= blocked
        damage = amount - blocked
        self.enemy_hp -= damage
        self.add_log(
            f"{source}! Removed {blocked} block and dealt {damage} damage."
        )

    def on_victory(self) -> None:
        if self.game_over:
            return
        self.game_over = True
        reward = random.randint(5, 8)
        self.game_state.gold += reward
        self.add_log(
            f"Defeated the enemy! Gained {reward} gold."
        )
        next_scene = random.choice(["shop", "upgrade"])
        if next_scene == "shop":
            Scenes.shopScene.queue_reward(reward)
            destination = "shop"
            target_scene = Scenes.shopScene
        else:
            Scenes.upgradeScene.queue_open()
            destination = "upgrade chamber"
            target_scene = Scenes.upgradeScene
        self.instruction_text.text = f"Victory! Heading to the {destination}."
        self.update_interface()
        Rs.setCurrentScene(target_scene)

    def on_defeat(self) -> None:
        if self.game_over:
            return
        self.game_over = True
        self.add_log("Defeated. Press New Battle to try again.")
        self.instruction_text.text = "Defeat..."

    # -- Turn flow -----------------------------------------------------
    def end_turn(self) -> None:
        if self.game_over:
            return
        if self.pending_card is not None:
            self.add_log("Finish resolving the card before ending the turn.")
            return

        if self.hand:
            self.discard_pile.extend(self.hand)
            self.hand.clear()
            self.hand_widgets.clear()
        self.position_hand_widgets()

        intent_type, intent_value = self.enemy_intent
        if intent_type == "attack":
            blocked = min(intent_value, self.player_block)
            damage = intent_value - blocked
            self.player_block = max(0, self.player_block - intent_value)
            if damage > 0:
                self.player_hp -= damage
            self.add_log(
                f"Enemy attacks for {intent_value}! Blocked {blocked}, took {damage} damage.")
        else:
            self.enemy_block += intent_value
            self.add_log(f"Enemy gained {intent_value} block.")

        if self.player_hp <= 0:
            self.on_defeat()
            self.update_interface()
            return

        self.turn_count += 1
        self.roll_dice()
        self.draw_cards(self.HAND_LIMIT)
        self.roll_enemy_intent()
        self.update_interface()
        self.instruction_text.text = "A new turn begins."

    # -- Scene lifecycle -----------------------------------------------
    def update(self) -> None:
        for widget in list(self.hand_widgets):
            widget.handle_events()
        for dice in self.dice_buttons:
            dice.update()
        if self.should_show_confirm_button():
            self.confirm_selection_button.update()
        self.reset_button.update()
        self.end_turn_button.update()

    def draw(self) -> None:
        self.background.draw()
        self.title.draw()
        self.subtitle.draw()
        self.turn_label.draw()
        self.player_label.draw()
        self.player_hp_bar_bg.draw()
        if self.player_hp_bar_fill.alpha:
            self.player_hp_bar_fill.draw()
        self.player_hp_value.draw()
        self.player_block_label.draw()
        self.enemy_panel.draw()
        self.enemy_label.draw()
        self.enemy_hp_bar_bg.draw()
        if self.enemy_hp_bar_fill.alpha:
            self.enemy_hp_bar_fill.draw()
        self.enemy_hp_value.draw()
        self.enemy_block_label.draw()
        self.enemy_intent_label.draw()
        self.deck_label.draw()
        self.gold_label.draw()
        for button in self.dice_buttons:
            button.draw()
        if Rs.draggedObj != None:
            self.play_zone.draw()
        self.log_box.draw()
        self.instruction_text.draw()
        if self.should_show_confirm_button():
            self.confirm_selection_button.draw()
        self.end_turn_button.draw()
        self.reset_button.draw()
        for widget in self.hand_widgets:
            widget.draw()


class ShopCardItem:
    def __init__(
        self,
        card_key: str,
        card: CardData,
        price: int,
        scene: "ShopScene",
    ) -> None:
        self.card_key = card_key
        self.card = card
        self.price = price
        self.scene = scene
        self.sold = False

        self.card_widget = HandCardWidget(card, scene=None)
        self.card_widget.color_overlay.alpha = 50

        button_rect = pygame.Rect(0, 0, self.card_widget.WIDTH - 40, 54)
        self.buy_button = textButton(
            self._button_text(),
            button_rect,
            size=24,
            radius=16,
            color=Cs.orange,
            textColor=Cs.black,
        )
        self.buy_button.setParent(self.card_widget, depth=3)
        self.buy_button.centerx = self.card_widget.offsetRect.centerx
        self.buy_button.midtop = (
            self.card_widget.offsetRect.midbottom + RPoint(0, 18)
        )
        self.buy_button.connect(self.on_buy)

    def _button_text(self) -> str:
        return f"Buy ({self.price} gold)"

    def set_position(self, x: float, y: float) -> None:
        self.card_widget.pos = RPoint(x, y)

    def on_buy(self) -> None:
        self.scene.attempt_purchase(self)

    def mark_sold(self) -> None:
        self.sold = True
        self.buy_button.enabled = False
        self.buy_button.text = "Purchased"
        self.buy_button.color = Cs.dark(Cs.grey)
        self.card_widget.color_overlay.color = Cs.dark(Cs.grey)
        self.card_widget.color_overlay.alpha = 140

    def update(self) -> None:
        if not self.sold:
            self.card_widget.handle_events()
        self.buy_button.update()

    def draw(self) -> None:
        self.card_widget.draw()
        self.buy_button.draw()


class ShopScene(Scene):
    CARD_PRICE = 5

    def __init__(self, game_state: GameState) -> None:
        super().__init__()
        self.game_state = game_state
        self.cards_for_sale: list[ShopCardItem] = []
        self.pending_reward: int | None = None

    def initOnce(self) -> None:
        screen_rect = Rs.screenRect()
        self.background = imageObj("background.png", screen_rect)
        self.title = textObj("Shop", pos=(60, 60), size=52, color=Cs.white)
        self.subtitle = textObj(
            "Spend your reward to buy new cards!",
            pos=(60, 120),
            size=26,
            color=Cs.lightgrey,
        )
        self.gold_label = textObj("Gold 10", pos=(60, 170), size=28, color=Cs.yellow)
        self.message = longTextObj(
            "",
            pos=RPoint(60, 210),
            size=22,
            color=Cs.white,
            textWidth=460,
        )

        self.continue_button = textButton(
            "Start Next Battle",
            pygame.Rect(60, 760, 240, 70),
            size=26,
            radius=20,
            color=Cs.mint,
            textColor=Cs.black,
        )
        self.continue_button.connect(self.start_next_combat)

    def init(self) -> None:
        if self.pending_reward is not None:
            self._open_shop()

    def queue_reward(self, reward: int) -> None:
        self.pending_reward = reward
        if getattr(self, "initiated", False):
            self._open_shop()

    def _open_shop(self) -> None:
        reward = self.pending_reward if self.pending_reward is not None else 0
        self.pending_reward = None
        self.message.text = (
            f"You earned {reward} gold from battle. Pick any card you like."
        )
        self.generate_cards()
        self.update_gold_label()

    def update_gold_label(self) -> None:
        self.gold_label.text = f"Gold {self.game_state.gold}"

    def generate_cards(self) -> None:
        self.cards_for_sale.clear()

        available_keys = list(CARD_LIBRARY.keys())
        random.shuffle(available_keys)
        selected_keys = available_keys[:3]

        start_x = 520
        spacing = 280
        y = 260
        for index, key in enumerate(selected_keys):
            card = CARD_LIBRARY[key].clone()
            view = ShopCardItem(key, card, self.CARD_PRICE, self)
            view.set_position(start_x + index * spacing, y)
            self.cards_for_sale.append(view)

    def attempt_purchase(self, view: ShopCardItem) -> None:
        if view.sold:
            return
        if self.game_state.gold < view.price:
            self.message.text = "Not enough gold."
            return
        self.game_state.gold -= view.price
        self.game_state.add_card(view.card_key)
        view.mark_sold()
        self.update_gold_label()
        self.message.text = f"Added {view.card.name} to your deck."

    def start_next_combat(self) -> None:
        Scenes.mainScene.reset_combat()
        Rs.setCurrentScene(Scenes.mainScene)

    def update(self) -> None:
        for view in self.cards_for_sale:
            view.update()
        self.continue_button.update()

    def draw(self) -> None:
        self.background.draw()
        self.title.draw()
        self.subtitle.draw()
        self.gold_label.draw()
        self.message.draw()
        for view in self.cards_for_sale:
            view.draw()
        self.continue_button.draw()


class UpgradeCardOption:
    def __init__(self, base_key: str, scene: "UpgradeScene") -> None:
        self.base_key = base_key
        self.upgraded_key = f"{base_key}_plus"
        self.scene = scene

        base_card = CARD_LIBRARY[self.base_key].clone()
        self.base_card_widget = HandCardWidget(base_card, scene=None)
        self.base_card_widget.color_overlay.alpha = 50

        upgraded_card = CARD_LIBRARY[self.upgraded_key].clone()
        self.card_widget = HandCardWidget(upgraded_card, scene=None)
        self.card_widget.color_overlay.alpha = 50

        button_rect = pygame.Rect(0, 0, self.card_widget.WIDTH - 40, 54)
        self.upgrade_button = textButton(
            "Enhance",
            button_rect,
            size=24,
            radius=16,
            color=Cs.lime,
            textColor=Cs.black,
        )
        self.upgrade_button.setParent(self.card_widget, depth=3)
        self.upgrade_button.centerx = self.card_widget.offsetRect.centerx
        self.upgrade_button.midtop = (
            self.card_widget.offsetRect.midbottom + RPoint(0, 18)
        )
        self.upgrade_button.connect(self.on_select)

    def set_position(self, x: float, y: float) -> None:
        self.card_widget.pos = RPoint(x, y)
        gap = 40
        self.base_card_widget.pos = RPoint(1500, y)

    def on_select(self) -> None:
        self.scene.apply_upgrade(self)

    def mark_selected(self) -> None:
        self.upgrade_button.enabled = False
        self.upgrade_button.text = "Enhanced!"
        self.upgrade_button.color = Cs.lime

    def mark_unavailable(self) -> None:
        self.upgrade_button.enabled = False
        self.upgrade_button.text = "Unavailable"
        self.upgrade_button.color = Cs.dark(Cs.grey)
        self.card_widget.color_overlay.color = Cs.dark(Cs.grey)
        self.card_widget.color_overlay.alpha = 140

    def update(self) -> None:
        self.card_widget.handle_events()
        self.upgrade_button.update()

    def draw(self) -> None:
        self.card_widget.draw()
        if self.card_widget.is_hovered:
            self.base_card_widget.draw()
        self.upgrade_button.draw()


class UpgradeScene(Scene):
    def __init__(self, game_state: GameState) -> None:
        super().__init__()
        self.game_state = game_state
        self.options: list[UpgradeCardOption] = []
        self.pending_open = False
        self.has_upgraded = False

    def initOnce(self) -> None:
        screen_rect = Rs.screenRect()
        self.background = imageObj("background.png", screen_rect)
        self.title = textObj("Enhance Cards", pos=(60, 60), size=52, color=Cs.white)
        self.subtitle = textObj(
            "Select one card to upgrade into its enhanced form.",
            pos=(60, 120),
            size=26,
            color=Cs.lightgrey,
        )
        self.message = longTextObj(
            "",
            pos=RPoint(60, 200),
            size=22,
            color=Cs.white,
            textWidth=460,
        )
        self.continue_button = textButton(
            "Start Next Battle",
            pygame.Rect(60, 760, 240, 70),
            size=26,
            radius=20,
            color=Cs.mint,
            textColor=Cs.black,
        )
        self.continue_button.connect(self.start_next_combat)
        self.continue_button.enabled = False

    def init(self) -> None:
        if self.pending_open:
            self._open_upgrade()

    def queue_open(self) -> None:
        self.pending_open = True
        if getattr(self, "initiated", False):
            self._open_upgrade()

    def _open_upgrade(self) -> None:
        self.pending_open = False
        self.has_upgraded = False
        self.message.text = (
            "Choose one of your cards to enhance. The upgraded version replaces a copy in your deck."
        )
        self.continue_button.enabled = False
        self.generate_options()

    def generate_options(self) -> None:
        self.options.clear()
        seen: set[str] = set()
        upgradable_keys: list[str] = []
        for key in self.game_state.deck_blueprint:
            upgraded_key = f"{key}_plus"
            if upgraded_key in CARD_LIBRARY and key not in seen:
                seen.add(key)
                upgradable_keys.append(key)

        if not upgradable_keys:
            self.message.text = (
                "No cards in your deck can be enhanced right now. Continue to the next battle."
            )
            self.continue_button.enabled = True
            return

        random.shuffle(upgradable_keys)
        selected_keys = upgradable_keys[:3]

        count = len(selected_keys)
        spacing = 280
        start_x = 520 - int((3 - count) * spacing / 2)
        y = 260

        self.options = []
        for index, key in enumerate(selected_keys):
            option = UpgradeCardOption(key, self)
            option.set_position(start_x + index * spacing, y)
            self.options.append(option)

    def apply_upgrade(self, option: UpgradeCardOption) -> None:
        if self.has_upgraded:
            return
        try:
            index = self.game_state.deck_blueprint.index(option.base_key)
        except ValueError:
            self.message.text = "Could not find that card in your deck."
            return

        self.game_state.deck_blueprint[index] = option.upgraded_key
        self.has_upgraded = True
        option.mark_selected()
        for other in self.options:
            if other is not option:
                other.mark_unavailable()

        base_name = CARD_LIBRARY[option.base_key].name
        upgraded_name = CARD_LIBRARY[option.upgraded_key].name
        self.message.text = f"Upgraded {base_name} into {upgraded_name}!"
        self.continue_button.enabled = True

    def start_next_combat(self) -> None:
        Scenes.mainScene.reset_combat()
        Rs.setCurrentScene(Scenes.mainScene)

    def update(self) -> None:
        for option in self.options:
            option.update()
        self.continue_button.update()

    def draw(self) -> None:
        self.background.draw()
        self.title.draw()
        self.subtitle.draw()
        self.message.draw()
        for option in self.options:
            option.draw()
        self.continue_button.draw()


class Scenes:
    game_state = GameState(deck_blueprint=list(INITIAL_DECK_BLUEPRINT))
    mainScene = DiceCardScene(game_state)
    shopScene = ShopScene(game_state)
    upgradeScene = UpgradeScene(game_state)


if __name__ == "__main__":
    window = REMOGame(
        window_resolution=(1920,1080),
        screen_size=(1920, 1080),
        fullscreen=False,
        caption="Dice Card Roguelike",
    )
    window.setCurrentScene(Scenes.mainScene)
    window.run()
