import string

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QInputDialog,
    QMenu,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)


class DiagramConfig:
    NODE_WIDTH = 25
    NODE_HEIGHT = 15
    ARROW_INSET = 3
    HORIZONTAL_GAP = 80
    VERTICAL_STEP = 40
    ARROW_SIZE = 6
    PEN_COLOR = QColor("black")
    NODE_BRUSH_COLOR = QColor("white")
    ARROW_COLOR = QColor("black")


class ReactionGraphicsRect(QGraphicsRectItem):
    def __init__(self, reaction_node, rect, parent=None):
        super().__init__(rect, parent)
        self.reaction_node = reaction_node
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.RightButton | Qt.MouseButton.LeftButton)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            menu = QMenu()
            add_child_action = menu.addAction("add child")
            connect_to_child_action = menu.addAction("connect to child")
            delete_action = menu.addAction("delete component")

            selected_action = menu.exec(event.screenPos())
            if selected_action == add_child_action:
                self.reaction_node.parent_widget.on_add_child(self.reaction_node.letter)

            elif selected_action == connect_to_child_action:
                self.reaction_node.parent_widget.on_connect_to_child(self.reaction_node.letter)
            elif selected_action == delete_action:
                self.reaction_node.parent_widget.on_delete_reaction_context(self.reaction_node.letter)
        else:
            super().mousePressEvent(event)


class ReactionNode:
    def __init__(self, scene: QGraphicsScene, letter: str, x: float, y: float, parent_widget):
        self.letter = letter
        self.x = x
        self.y = y
        self.scene = scene
        self.parent_widget = parent_widget
        self.rect_item = None
        self.text_item = None
        self.draw()

    def draw(self):
        rect = QRectF(0, 0, DiagramConfig.NODE_WIDTH, DiagramConfig.NODE_HEIGHT)
        self.rect_item = ReactionGraphicsRect(self, rect)
        self.rect_item.setPos(self.x, self.y)
        self.scene.addItem(self.rect_item)

        self.text_item = QGraphicsTextItem(self.letter, self.rect_item)
        text_rect = self.text_item.boundingRect()
        self.text_item.setPos(
            (DiagramConfig.NODE_WIDTH - text_rect.width()) / 2, (DiagramConfig.NODE_HEIGHT - text_rect.height()) / 2
        )

    def center_point(self):
        cx = self.x + DiagramConfig.NODE_WIDTH / 2
        cy = self.y + DiagramConfig.NODE_HEIGHT / 2
        return cx, cy

    def remove(self):
        if self.text_item:
            self.scene.removeItem(self.text_item)
            self.text_item = None
        if self.rect_item:
            self.scene.removeItem(self.rect_item)
            self.rect_item = None


class ReactionArrow:
    def __init__(self, scene: QGraphicsScene, parent_node: ReactionNode, child_node: ReactionNode):
        self.scene = scene
        self.parent_node = parent_node
        self.child_node = child_node
        self.line_item = None
        self.arrow_item = None
        self.draw()

    def _intersect_node_edge(self, from_x, from_y, to_x, to_y, node: ReactionNode):  # noqa: C901
        px, py = node.center_point()
        half_w = DiagramConfig.NODE_WIDTH / 2
        half_h = DiagramConfig.NODE_HEIGHT / 2

        dx = to_x - from_x
        dy = to_y - from_y

        if dx == 0 and dy == 0:
            return px, py

        left = px - half_w
        right = px + half_w
        top = py - half_h
        bottom = py + half_h

        t_candidates = []
        if dx != 0:
            t_left = (left - from_x) / dx
            t_right = (right - from_x) / dx
            if 0 < t_left < 1:
                y_intersect = from_y + t_left * dy
                if top <= y_intersect <= bottom:
                    t_candidates.append((t_left, left, y_intersect))
            if 0 < t_right < 1:
                y_intersect = from_y + t_right * dy
                if top <= y_intersect <= bottom:
                    t_candidates.append((t_right, right, y_intersect))

        if dy != 0:
            t_top = (top - from_y) / dy
            t_bottom = (bottom - from_y) / dy
            if 0 < t_top < 1:
                x_intersect = from_x + t_top * dx
                if left <= x_intersect <= right:
                    t_candidates.append((t_top, x_intersect, top))
            if 0 < t_bottom < 1:
                x_intersect = from_x + t_bottom * dx
                if left <= x_intersect <= right:
                    t_candidates.append((t_bottom, x_intersect, bottom))

        if not t_candidates:
            return px, py

        t_candidates.sort(key=lambda x: x[0])
        _, ix, iy = t_candidates[0]

        line_len = ((ix - px) ** 2 + (iy - py) ** 2) ** 0.5
        if line_len != 0:
            ux = (px - ix) / line_len
            uy = (py - iy) / line_len
            ix += ux * DiagramConfig.ARROW_INSET
            iy += uy * DiagramConfig.ARROW_INSET

        return ix, iy

    def draw(self):
        p_cx, p_cy = self.parent_node.center_point()
        c_cx, c_cy = self.child_node.center_point()

        start_x, start_y = self._intersect_node_edge(p_cx, p_cy, c_cx, c_cy, self.parent_node)
        end_x, end_y = self._intersect_node_edge(c_cx, c_cy, p_cx, p_cy, self.child_node)

        self.line_item = self.scene.addLine(start_x, start_y, end_x, end_y, QPen(DiagramConfig.PEN_COLOR))

        dx = end_x - start_x
        dy = end_y - start_y
        line_length = (dx**2 + dy**2) ** 0.5
        if line_length == 0:
            return
        nx = dx / line_length
        ny = dy / line_length

        perp_x = -ny
        perp_y = nx

        arrow_tip_x = end_x
        arrow_tip_y = end_y

        arrow_left_x = arrow_tip_x - nx * DiagramConfig.ARROW_SIZE - perp_x * DiagramConfig.ARROW_SIZE / 2
        arrow_left_y = arrow_tip_y - ny * DiagramConfig.ARROW_SIZE - perp_y * DiagramConfig.ARROW_SIZE / 2
        arrow_right_x = arrow_tip_x - nx * DiagramConfig.ARROW_SIZE + perp_x * DiagramConfig.ARROW_SIZE / 2
        arrow_right_y = arrow_tip_y - ny * DiagramConfig.ARROW_SIZE + perp_y * DiagramConfig.ARROW_SIZE / 2

        arrow_polygon = [
            QPointF(arrow_tip_x, arrow_tip_y),
            QPointF(arrow_left_x, arrow_left_y),
            QPointF(arrow_right_x, arrow_right_y),
        ]

        self.arrow_item = self.scene.addPolygon(
            QPolygonF(arrow_polygon), QPen(DiagramConfig.PEN_COLOR), QBrush(DiagramConfig.ARROW_COLOR)
        )

    def remove(self):
        if self.line_item:
            self.scene.removeItem(self.line_item)
            self.line_item = None
        if self.arrow_item:
            self.scene.removeItem(self.arrow_item)
            self.arrow_item = None


class ModelsScheme(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.layout.addWidget(self.view)

        self.reactions = {}
        self.children_map = {}
        self.generation_map = {}
        self.occupied_positions = {}
        self.arrows = []

        self.alphabet = list(string.ascii_uppercase)
        self._next_letter_index = 0

        a = self._get_next_reaction_letter()  # 'A'
        b = self._get_next_reaction_letter()  # 'B'

        self.generation_map[a] = 0
        self.add_reaction_node(a, 0, 0)

        self.generation_map[b] = 1
        b_x, b_y = self.find_position_for_new_node(1, 0, 0)
        self.add_reaction_node(b, b_x, b_y)
        self.add_reaction_edge(a, b)

        self.update_scene()

    def _get_next_reaction_letter(self):
        if self._next_letter_index < len(self.alphabet):
            letter = self.alphabet[self._next_letter_index]
            self._next_letter_index += 1
            return letter
        else:
            return None

    def add_reaction_node(self, letter, x, y):
        node = ReactionNode(self.scene, letter, x, y, self)
        self.reactions[letter] = node

        gen = self.generation_map[letter]
        if gen not in self.occupied_positions:
            self.occupied_positions[gen] = []
        self.occupied_positions[gen].append((y, y + DiagramConfig.NODE_HEIGHT))
        return node

    def add_reaction_edge(self, parent, child):
        self.children_map.setdefault(parent, []).append(child)
        parent_node = self.reactions[parent]
        child_node = self.reactions[child]
        arrow = ReactionArrow(self.scene, parent_node, child_node)
        self.arrows.append(arrow)

    def find_position_for_new_node(self, generation, parent_x, parent_y):
        x = parent_x + DiagramConfig.HORIZONTAL_GAP
        y = parent_y

        def overlaps(y_pos):
            if generation not in self.occupied_positions:
                return False
            for y_start, y_end in self.occupied_positions[generation]:
                if not (y + DiagramConfig.NODE_HEIGHT < y_start or y_end < y):
                    return True
            return False

        while overlaps(y):
            y += DiagramConfig.VERTICAL_STEP
        return x, y

    def on_add_child(self, parent_letter):
        new_letter = self._get_next_reaction_letter()
        if new_letter is None:
            QMessageBox.warning(self, "Error", "No more letters available.")
            return

        parent_gen = self.generation_map[parent_letter]
        new_gen = parent_gen + 1
        self.generation_map[new_letter] = new_gen

        parent_node = self.reactions[parent_letter]
        px, py = parent_node.x, parent_node.y
        x, y = self.find_position_for_new_node(new_gen, px, py)

        self.add_reaction_node(new_letter, x, y)
        self.add_reaction_edge(parent_letter, new_letter)
        self.update_scene()

    def on_connect_to_child(self, parent_letter):
        existing = [l for l in self.reactions.keys() if l != parent_letter]  # noqa: E741
        if not existing:
            QMessageBox.information(self, "Info", "No existing reactions available to connect as a child.")
            return

        child, ok = QInputDialog.getItem(
            self, "Connect to child", "Choose a reaction to become a child:", existing, 0, False
        )
        if ok and child:
            if child == "A":
                QMessageBox.warning(self, "Error", "Node 'A' cannot have a parent.")
                return

            if self.is_cyclic(parent_letter, child):
                QMessageBox.warning(self, "Error", "Cannot connect because it would create a cycle.")
                return

            self.children_map.setdefault(parent_letter, []).append(child)
            self.update_scene()

    def get_subtree(self, root_letter):
        result = []
        to_visit = [root_letter]
        while to_visit:
            current = to_visit.pop()
            result.append(current)
            if current in self.children_map:
                to_visit.extend(self.children_map[current])
        return result

    def remove_node_position(self, letter):
        if letter in self.reactions and letter in self.generation_map:
            node = self.reactions[letter]
            gen = self.generation_map[letter]
            node_y_start = node.y
            node_y_end = node.y + DiagramConfig.NODE_HEIGHT
            if gen in self.occupied_positions:
                self.occupied_positions[gen] = [
                    (s, e) for (s, e) in self.occupied_positions[gen] if not (s == node_y_start and e == node_y_end)
                ]
                if not self.occupied_positions[gen]:
                    del self.occupied_positions[gen]

    def is_cyclic(self, parent, child):
        to_visit = [parent]
        while to_visit:
            current = to_visit.pop()
            if current == child:
                return True
            if current in self.children_map:
                to_visit.extend(self.children_map[current])
        return False

    def on_delete_reaction_context(self, letter):
        if letter == "A":
            QMessageBox.warning(self, "Error", "Component 'A' cannot be deleted.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete component '{letter}' and all its descendants?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.remove_reaction(letter)
            self.update_scene()

    def remove_reaction(self, letter):  # noqa: C901
        if letter == "A":
            QMessageBox.warning(self, "Error", "Component 'A' cannot be deleted.")
            return

        if letter in self.children_map:
            children = self.children_map[letter].copy()
            for child in children:
                self.remove_reaction(child)
            self.children_map.pop(letter, None)

        if letter in self.reactions:
            node = self.reactions[letter]
            gen = self.generation_map[letter]
            node_y_start = node.y
            node_y_end = node.y + DiagramConfig.NODE_HEIGHT
            if gen in self.occupied_positions:
                self.occupied_positions[gen] = [
                    (s, e) for (s, e) in self.occupied_positions[gen] if not (s == node_y_start and e == node_y_end)
                ]
                if not self.occupied_positions[gen]:
                    del self.occupied_positions[gen]
            node.remove()
            del self.reactions[letter]
            del self.generation_map[letter]

            arrows_to_remove = [
                arrow
                for arrow in self.arrows
                if arrow.parent_node.letter == letter or arrow.child_node.letter == letter
            ]
            for arrow in arrows_to_remove:
                arrow.remove()
                self.arrows.remove(arrow)

        for p, ch_list in list(self.children_map.items()):
            if letter in ch_list:
                ch_list.remove(letter)
                if not ch_list:
                    self.children_map.pop(p, None)

    def update_scene(self):
        self.scene.clear()
        self.arrows.clear()

        for letter, node in self.reactions.items():
            node.draw()

        for parent, children in self.children_map.items():
            for child in children:
                if parent in self.reactions and child in self.reactions:
                    parent_node = self.reactions[parent]
                    child_node = self.reactions[child]
                    arrow = ReactionArrow(self.scene, parent_node, child_node)
                    self.arrows.append(arrow)

        self.view.setScene(self.scene)
        self.view.setRenderHint(self.view.renderHints() | self.view.renderHints().Antialiasing)
        self.scene.update()
