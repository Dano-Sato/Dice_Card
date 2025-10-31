from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, replace
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


CARD_LIBRARY: dict[str, CardData] = {
    "clone": CardData(
        name="눈 복제",
        effect="clone",
        description="주사위 2개를 선택한 뒤, 왼쪽 주사위의 눈을 오른쪽 주사위로 바꾼다.",
        targets=2,
        card_type="조작",
    ),
    "mirror": CardData(
        name="미러 주사위",
        effect="mirror",
        description="선택한 주사위를 반전한다 (1↔6, 2↔5, 3↔4).",
        targets=1,
        card_type="조작",
        allow_multi_select=True,
    ),
    "stasis": CardData(
        name="Stasis",
        effect="stasis",
        description="선택한 주사위를 다음 턴 시작까지 고정한다.",
        targets=1,
        card_type="조작",
        allow_multi_select=True,
    ),
    "tinker": CardData(
        name="Tinker",
        effect="tinker",
        description="선택한 주사위의 눈을 1 올린다. (6은 그대로)",
        targets=1,
        card_type="강화",
        allow_multi_select=True,
    ),
    "reroll": CardData(
        name="Reroll",
        effect="reroll",
        description="선택한 주사위를 다시 굴립니다.",
        targets=1,
        card_type="조작",
        allow_multi_select=True,
    ),
    "odd_attack": CardData(
        name="Odd Attack",
        effect="odd_attack",
        description="현재 보유한 홀수 주사위 눈의 합만큼 적을 공격한다.",
        targets=0,
        card_type="공격",
    ),
    "even_shield": CardData(
        name="Even Shield",
        effect="even_shield",
        description="현재 보유한 짝수 주사위 눈의 합만큼 방어력을 얻는다.",
        targets=0,
        card_type="방어",
    ),
    "strafe": CardData(
        name="스트레이프",
        effect="strafe",
        description="Small Straight일 경우 30, Big Straight일 경우 60 데미지",
        targets=0,
        card_type="공격",
    ),
    "strike": CardData(
        name="스트라이크",
        effect="strike",
        description="주사위의 합으로 공격한다.",
        targets=0,
        card_type="공격",
    ),
    "fortify": CardData(
        name="Fortify",
        effect="fortify",
        description="주사위의 합으로 방어한다.",
        targets=0,
        card_type="방어",
    ),
    "pair_shot": CardData(
        name="Pair Shot",
        effect="pair_shot",
        description="주사위가 페어일 경우 15 데미지",
        targets=0,
        card_type="공격",
    ),
    "one_shot": CardData(
        name="One Shot",
        effect="one_shot",
        description="1 주사위당 15 데미지",
        targets=0,
        card_type="공격",
    ),
    "double_guard": CardData(
        name="Double Guard",
        effect="double_guard",
        description="2 주사위당 10 방어",
        targets=0,
        card_type="방어",
    ),
}


class HandCardWidget(rectObj):
    WIDTH = 160
    HEIGHT = 220

    def __init__(self, card: CardData, scene: "DiceCardScene") -> None:
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

        self.base_color = Cs.dark(Cs.steelblue)
        self.hover_color = Cs.light(self.base_color)
        if card.card_type == "공격":
            self.base_color = Cs.dark(Cs.red)
            self.hover_color = Cs.light(self.base_color)
        elif card.card_type == "방어":
            self.base_color = Cs.dark(Cs.teal)
            self.hover_color = Cs.light(self.base_color)
        elif card.card_type == "강화":
            self.base_color = Cs.dark(Cs.purple)
            self.hover_color = Cs.light(self.base_color)
        elif card.card_type == "조작":
            self.base_color = Cs.dark(Cs.blue)
            self.hover_color = Cs.light(self.base_color)

        self.color = self.base_color

        self.title = textObj(card.name, size=26, color=Cs.white)
        self.title.setParent(self, depth=1)
        self.title.centerx = self.offsetRect.centerx
        self.title.y = 18

        self.type_text = textObj(card.card_type, size=18, color=Cs.lightgrey)
        self.type_text.setParent(self, depth=1)
        self.type_text.centerx = self.offsetRect.centerx
        self.type_text.y = self.title.rect.bottom + 4

        self.desc = longTextObj(
            card.description,
            pos=RPoint(0, 0),
            size=18,
            color=Cs.white,
            textWidth=self.WIDTH - 30,
        )
        self.desc.setParent(self, depth=1)
        self.desc.centerx = self.offsetRect.centerx
        self.desc.y = self.type_text.rect.bottom + 12

    def set_home(self, pos: RPoint) -> None:
        self.home_pos = RPoint(pos.x, pos.y)
        self.pos = RPoint(pos.x, pos.y)

    def snap_home(self) -> None:
        self.pos = RPoint(self.home_pos.x, self.home_pos.y)

    def handle_events(self) -> None:
        self.color = self.hover_color if self.collideMouse() else self.base_color

        if self.scene.game_over:
            return
        if self.scene.pending_card and self.scene.pending_card.card is not self.card:
            return

        def on_start() -> None:
            self.dragging = True
            self.color = self.hover_color

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

    def initOnce(self) -> None:
        screen_rect = Rs.screenRect()
        self.background = rectObj(screen_rect, color=Cs.darkslategray)

        self.title = textObj("주사위 카드 로그라이크", pos=(40, 40), size=48, color=Cs.white)
        self.subtitle = textObj(
            "5개의 주사위를 굴리고 카드를 드래그하여 적을 제압하세요!",
            pos=(40, 100),
            size=24,
            color=Cs.lightgrey,
        )

        self.turn_label = textObj("턴 1", pos=(40, 150), size=26, color=Cs.yellow)
        self.player_label = textObj("플레이어 HP", pos=(40, 190), size=26, color=Cs.white)
        self.enemy_label = textObj("적 HP", pos=(40, 230), size=26, color=Cs.white)
        self.enemy_intent_label = textObj("적 의도", pos=(40, 270), size=24, color=Cs.tiffanyBlue)
        self.deck_label = textObj("덱", pos=(40, 306), size=22, color=Cs.lightgrey)

        dice_start_x = 420
        dice_y = 180
        dice_spacing = 120
        self.dice: list[dict[str, Any]] = []
        self.dice_buttons: list[textButton] = []
        for i in range(5):
            rect = pygame.Rect(dice_start_x + i * dice_spacing, dice_y, 100, 120)
            button = textButton(
                "1",
                rect,
                size=48,
                radius=24,
                color=Cs.dark(Cs.blue),
                textColor=Cs.white,
            )

            def make_handler(index: int) -> Callable[[], None]:
                return lambda: self.on_die_clicked(index)

            button.connect(make_handler(i))
            self.dice_buttons.append(button)
            self.dice.append({"value": 1, "frozen": 0, "button": button})

        self.play_zone = rectObj(
            pygame.Rect(640, 360, 280, 180),
            color=Cs.dark(Cs.grey),
            edge=4,
            radius=26,
        )
        self.play_zone_label = textObj(
            "카드를 여기로 드래그",
            size=24,
            color=Cs.white,
        )
        self.play_zone_label.setParent(self.play_zone, depth=1)
        self.play_zone_label.center = self.play_zone.offsetRect.center

        self.log_box = longTextObj(
            "카드를 위로 드래그하면 사용됩니다.",
            pos=RPoint(40, 360),
            size=20,
            color=Cs.white,
            textWidth=340,
        )
        self.instruction_text = textObj("", pos=(40, 600), size=24, color=Cs.orange)

        self.end_turn_button = textButton(
            "턴 종료",
            pygame.Rect(980, 80, 180, 60),
            size=28,
            radius=18,
            color=Cs.orange,
            textColor=Cs.black,
        )
        self.end_turn_button.connect(self.end_turn)

        self.confirm_selection_button = textButton(
            "선택 완료",
            pygame.Rect(980, 160, 180, 60),
            size=26,
            radius=18,
            color=Cs.lime,
            textColor=Cs.black,
        )
        self.confirm_selection_button.connect(self.confirm_pending_selection)

        self.reset_button = textButton(
            "새 전투",
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

        self.player_hp = 40
        self.player_block = 0
        self.enemy_hp = 45
        self.enemy_block = 0
        self.enemy_intent: tuple[str, int] = ("attack", 6)
        self.turn_count = 1

        self.deck_blueprint = (
            ["clone"] * 2
            + ["mirror"] * 2
            + ["stasis"] * 2
            + ["reroll"] * 2
            + ["tinker"] * 2
            + ["odd_attack"] * 3
            + ["even_shield"] * 3
            + ["strafe"] * 2
            + ["strike"] * 2
            + ["fortify"] * 2
            + ["pair_shot"] * 2
            + ["one_shot"] * 2  
            + ["double_guard"] * 2
        )

        self.reset_combat(initial=True)

    def init(self) -> None:
        return

    # -- State helpers -------------------------------------------------
    def reset_combat(self, *, initial: bool = False) -> None:
        self.game_over = False
        self.player_hp = 40
        self.player_block = 0
        self.enemy_hp = 50
        self.enemy_block = 0
        self.turn_count = 1
        self.pending_card = None
        self.hand.clear()
        self.hand_widgets.clear()
        self.draw_pile = [CARD_LIBRARY[key].clone() for key in self.deck_blueprint]
        random.shuffle(self.draw_pile)
        self.discard_pile.clear()
        for die in self.dice:
            die["frozen"] = 0
        self.log_box.text = "카드를 위로 드래그하면 사용됩니다."
        self.instruction_text.text = ""
        self.roll_dice(initial=True)
        self.draw_cards(self.HAND_LIMIT)
        self.roll_enemy_intent()
        self.update_interface()
        if not initial:
            self.add_log("새로운 전투를 시작합니다!")
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
        self.add_log("버림패를 섞어 새 덱을 구성했습니다.")

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
            button.text = str(die["value"])
            if die["frozen"] > 0:
                button.color = Cs.dark(Cs.cyan)
            else:
                button.color = Cs.dark(Cs.blue)
            if self.pending_card and idx in self.pending_card.selected:
                button.color = Cs.dark(Cs.purple)

    def update_interface(self) -> None:
        self.turn_label.text = f"턴 {self.turn_count}"
        self.player_label.text = (
            f"플레이어 HP {self.player_hp}/40 · 방어 {self.player_block}"
        )
        self.enemy_label.text = (
            f"적 HP {self.enemy_hp}/50 · 방어 {self.enemy_block}"
        )
        intent_type, intent_value = self.enemy_intent
        intent_name = "공격" if intent_type == "attack" else "방어"
        self.enemy_intent_label.text = f"적 의도: {intent_name} {intent_value}"
        self.update_deck_label()

    def update_deck_label(self) -> None:
        self.deck_label.text = (
            f"남은 덱 {len(self.draw_pile)}장 · 버림패 {len(self.discard_pile)}장"
        )

    def add_log(self, message: str) -> None:
        lines = self.log_box.text.split("\n") if self.log_box.text else []
        lines.append(message)
        self.log_box.text = "\n".join(lines[-7:])

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
            self.add_log(f"{card.name}을(를) 사용합니다. {self.instruction_text.text}")
        else:
            self.resolve_card_effect(card, [])
            self.discard_pile.append(card)
            self.instruction_text.text = f"{card.name} 사용!"
            self.finalize_card_resolution()
        self.update_interface()
        self.update_confirm_button_state()

    def instruction_for_card(self, card: CardData) -> str:
        if card.effect == "clone":
            return "왼쪽과 오른쪽 주사위를 순서대로 선택하세요."
        if card.effect == "mirror":
            if card.allow_multi_select:
                return "반전할 주사위를 선택하세요. 선택 완료 버튼으로 확정합니다."
            return "반전할 주사위를 선택하세요."
        if card.effect == "stasis":
            if card.allow_multi_select:
                return "고정할 주사위를 선택하세요. 선택 완료 버튼을 누르면 적용됩니다."
            return "고정할 주사위를 선택하세요."
        if card.effect == "tinker":
            if card.allow_multi_select:
                return "강화할 주사위를 선택하세요. 선택 완료 버튼으로 마무리합니다."
            return "강화할 주사위를 선택하세요."
        if card.effect == "reroll":
            return "다시 굴릴 주사위를 원하는 만큼 선택한 뒤 선택 완료를 누르세요."
        return "주사위를 선택하세요."

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
            self.add_log(f"{index + 1}번 주사위: {die['value']}")
            return

        pending = self.pending_card
        if pending.allow_multi_select:
            already_selected = index in pending.selected
            pending.add_target(index)
            self.update_dice_display()
            if pending.has_minimum_selection():
                self.instruction_text.text = "선택 완료 버튼을 눌러 카드 효과를 발동하세요."
            else:
                remaining = max(0, pending.required - len(pending.selected))
                if remaining > 0:
                    self.instruction_text.text = f"주사위를 {remaining}개 더 선택하세요."
                else:
                    self.instruction_text.text = "적용할 주사위를 선택하세요."
            if already_selected and index not in pending.selected:
                self.add_log(f"{index + 1}번 주사위 선택을 해제했습니다.")
            elif index in pending.selected:
                self.add_log(f"{index + 1}번 주사위를 선택했습니다.")
            self.update_confirm_button_state()
        else:
            pending.add_target(index)
            self.update_dice_display()
            if pending.is_complete():
                self.resolve_card_effect(pending.card, pending.selected)
                self.discard_pile.append(pending.card)
                self.instruction_text.text = f"{pending.card.name} 사용 완료!"
                self.finalize_card_resolution()
            else:
                remaining = pending.required - len(pending.selected)
                self.instruction_text.text = f"주사위를 {remaining}개 더 선택하세요."

    def confirm_pending_selection(self) -> None:
        if self.game_over:
            return
        if not self.pending_card or not self.pending_card.allow_multi_select:
            return
        pending = self.pending_card
        if not pending.has_minimum_selection():
            self.instruction_text.text = "적용할 주사위를 선택하세요."
            return
        self.resolve_card_effect(pending.card, pending.selected)
        self.discard_pile.append(pending.card)
        self.instruction_text.text = f"{pending.card.name} 사용 완료!"
        self.finalize_card_resolution()

    def resolve_card_effect(self, card: CardData, selection: list[int]) -> None:
        if card.effect == "clone" and len(selection) >= 2:
            left, right = selection[0], selection[1]
            value = self.dice[left]["value"]
            self.dice[right]["value"] = value
            self.add_log(
                f"눈 복제! {left + 1}번 주사위의 눈({value})을 {right + 1}번에 복제했습니다."
            )
        elif card.effect == "mirror" and selection:
            for idx in selection:
                old = self.dice[idx]["value"]
                self.dice[idx]["value"] = 7 - old
                self.add_log(
                    f"미러 주사위! {idx + 1}번 주사위가 {old} → {self.dice[idx]['value']}로 반전되었습니다."
                )
        elif card.effect == "stasis" and selection:
            for idx in selection:
                self.dice[idx]["frozen"] = max(self.dice[idx]["frozen"], 1)
                self.add_log(f"Stasis! {idx + 1}번 주사위를 다음 턴까지 고정합니다.")
        elif card.effect == "tinker" and selection:
            for idx in selection:
                old = self.dice[idx]["value"]
                if old < 6:
                    self.dice[idx]["value"] = old + 1
                self.add_log(
                    f"Tinker! {idx + 1}번 주사위가 {old} → {self.dice[idx]['value']}가 되었습니다."
                )
        elif card.effect == "reroll" and selection:
            for idx in selection:
                old = self.dice[idx]["value"]
                self.dice[idx]["value"] = random.randint(1, 6)
                self.add_log(
                    f"Reroll! {idx + 1}번 주사위를 {old}에서 {self.dice[idx]['value']}로 다시 굴렸습니다."
                )
        elif card.effect == "odd_attack":
            damage = sum(die["value"] for die in self.dice if die["value"] % 2 == 1)
            self.deal_damage(damage, source="Odd Attack")
        elif card.effect == "even_shield":
            block = sum(die["value"] for die in self.dice if die["value"] % 2 == 0)
            self.player_block += block
            self.add_log(f"Even Shield! {block}의 방어를 얻었습니다.")
        elif card.effect == "strafe":
            values = [die["value"] for die in self.dice]
            value_set = set(values)
            big_straights = ({1, 2, 3, 4, 5}, {2, 3, 4, 5, 6})
            small_straights = ({1, 2, 3, 4}, {2, 3, 4, 5}, {3, 4, 5, 6})
            damage = 0
            if any(straight.issubset(value_set) for straight in big_straights):
                damage = 60
                self.add_log("스트레이프! Big Straight으로 60 피해를 줍니다.")
            elif any(straight.issubset(value_set) for straight in small_straights):
                damage = 30
                self.add_log("스트레이프! Small Straight으로 30 피해를 줍니다.")
            else:
                self.add_log("스트레이프! 스트레이트가 없어 공격에 실패했습니다.")
            self.deal_damage(damage, source="스트레이프")
        elif card.effect == "strike":
            damage = sum(die["value"] for die in self.dice)
            self.add_log(f"스트라이크! 주사위 합 {damage}으로 공격합니다.")
            self.deal_damage(damage, source="스트라이크")
        elif card.effect == "fortify":
            block = sum(die["value"] for die in self.dice)
            self.player_block += block
            self.add_log(f"Fortify! 주사위 합 {block}의 방어를 얻었습니다.")
        elif card.effect == "pair_shot":
            counts = Counter(die["value"] for die in self.dice)
            if any(count >= 2 for count in counts.values()):
                damage = 15
                self.add_log("Pair Shot! 페어를 맞춰 15 피해를 줍니다.")
                self.deal_damage(damage, source="Pair Shot")
            else:
                self.add_log("Pair Shot! 페어가 없어 공격에 실패했습니다.")
        elif card.effect == "one_shot":
            ones = sum(1 for die in self.dice if die["value"] == 1)
            damage = ones * 15
            self.add_log(f"One Shot! 주사위 {ones}개로 {damage} 피해를 가합니다.")
            self.deal_damage(damage, source="One Shot")
        elif card.effect == "double_guard":
            twos = sum(1 for die in self.dice if die["value"] == 2)
            block = twos * 10
            if block > 0:
                self.player_block += block
                self.add_log(f"Double Guard! {twos}개의 주사위로 {block} 방어를 얻었습니다.")
            else:
                self.add_log("Double Guard! 방어를 얻을 수 있는 주사위가 부족합니다.")
        else:
            self.add_log("카드 효과가 제대로 적용되지 않았습니다.")

    def deal_damage(self, amount: int, *, source: str) -> None:
        if amount <= 0:
            self.add_log(f"{source}! 공격이 통하지 않았습니다.")
            return
        blocked = min(amount, self.enemy_block)
        if blocked:
            self.enemy_block -= blocked
        damage = amount - blocked
        self.enemy_hp -= damage
        self.add_log(
            f"{source}! {blocked} 방어를 제거하고 {damage} 피해를 입혔습니다."
        )

    def on_victory(self) -> None:
        if self.game_over:
            return
        self.game_over = True
        self.add_log("적을 쓰러뜨렸습니다! 새 전투로 계속 플레이하세요.")
        self.instruction_text.text = "승리했습니다!"

    def on_defeat(self) -> None:
        if self.game_over:
            return
        self.game_over = True
        self.add_log("패배했습니다. 새 전투를 눌러 다시 시작하세요.")
        self.instruction_text.text = "패배..."

    # -- Turn flow -----------------------------------------------------
    def end_turn(self) -> None:
        if self.game_over:
            return
        if self.pending_card is not None:
            self.add_log("카드 효과 선택을 마친 뒤 턴을 종료하세요.")
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
                f"적이 {intent_value} 공격! 방어 {blocked}, 피해 {damage}.")
        else:
            self.enemy_block += intent_value
            self.add_log(f"적이 {intent_value}의 방어를 올렸습니다.")

        self.player_block = 0
        if self.player_hp <= 0:
            self.on_defeat()
            self.update_interface()
            return

        self.turn_count += 1
        self.roll_dice()
        self.draw_cards(self.HAND_LIMIT)
        self.roll_enemy_intent()
        self.update_interface()
        self.instruction_text.text = "새 턴이 시작되었습니다."

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
        self.enemy_label.draw()
        self.enemy_intent_label.draw()
        self.deck_label.draw()
        for button in self.dice_buttons:
            button.draw()
        self.play_zone.draw()
        self.log_box.draw()
        self.instruction_text.draw()
        if self.should_show_confirm_button():
            self.confirm_selection_button.draw()
        self.end_turn_button.draw()
        self.reset_button.draw()
        for widget in self.hand_widgets:
            widget.draw()


class Scenes:
    mainScene = DiceCardScene()


if __name__ == "__main__":
    window = REMOGame(
        window_resolution=(1600, 900),
        screen_size=(1600, 900),
        fullscreen=False,
        caption="Dice Card Roguelike",
    )
    window.setCurrentScene(Scenes.mainScene)
    window.run()
