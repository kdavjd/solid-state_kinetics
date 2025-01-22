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

from src.core.logger_config import logger


class DiagramConfig:
    NODE_WIDTH = 30
    NODE_HEIGHT = 20
    ARROW_INSET = 3
    HORIZONTAL_GAP = 45
    VERTICAL_STEP = 22
    ARROW_SIZE = 3
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
                logger.debug(f"Add child for node: {self.reaction_node.letter}")
                self.reaction_node.parent_widget.on_add_child(self.reaction_node.letter)
            elif selected_action == connect_to_child_action:
                logger.debug(f"Connect to child for node: {self.reaction_node.letter}")
                self.reaction_node.parent_widget.on_connect_to_child(self.reaction_node.letter)
            elif selected_action == delete_action:
                logger.debug(f"Delete node: {self.reaction_node.letter}")
                self.reaction_node.parent_widget.on_delete_reaction_context(self.reaction_node.letter)
        else:
            super().mousePressEvent(event)


class ReactionNode:
    def __init__(self, scene, letter, x, y, parent_widget):
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
    def __init__(self, scene, parent_node, child_node):
        self.scene = scene
        self.parent_node = parent_node
        self.child_node = child_node
        self.line_item = None
        self.arrow_item = None
        self.draw()

    def _intersect_node_edge(self, from_x, from_y, to_x, to_y, node):  # noqa: C901
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
        end_x, end_y = self._intersect_node_edge(c_cx, c_cy, start_x, start_y, self.child_node)
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
        logger.debug("ModelsScheme: __init__ start")
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
        self.temp_id_counter = 0
        root_id = self._get_new_temp_id()
        child_id = self._get_new_temp_id()
        self.generation_map[root_id] = 0
        self.generation_map[child_id] = 1
        self.add_reaction_node(root_id, 0, 0)
        px, py = self.reactions[root_id].x, self.reactions[root_id].y
        child_x, child_y = self.find_position_for_new_node(1, px, py)
        self.add_reaction_node(child_id, child_x, child_y)
        self.children_map[root_id] = [child_id]
        self.rename_all_nodes()
        self.update_scene()
        logger.debug("ModelsScheme: __init__ end")

    def _get_new_temp_id(self):
        t = f"temp{self.temp_id_counter}"
        self.temp_id_counter += 1
        return t

    def add_reaction_node(self, unique_id, x, y):
        node = ReactionNode(self.scene, unique_id, x, y, self)
        self.reactions[unique_id] = node
        gen = self.generation_map.get(unique_id, 0)
        if gen not in self.occupied_positions:
            self.occupied_positions[gen] = []
        self.occupied_positions[gen].append((y, y + DiagramConfig.NODE_HEIGHT))
        return node

    def add_reaction_edge(self, parent_id, child_id):
        parent_node = self.reactions[parent_id]
        child_node = self.reactions[child_id]
        arrow = ReactionArrow(self.scene, parent_node, child_node)
        self.arrows.append(arrow)

    def find_position_for_new_node(self, generation, parent_x, parent_y):
        x = parent_x + DiagramConfig.HORIZONTAL_GAP
        y = parent_y

        def overlaps(y_pos):
            if generation not in self.occupied_positions:
                return False
            for y_start, y_end in self.occupied_positions[generation]:
                if not (y_pos + DiagramConfig.NODE_HEIGHT < y_start or y_end < y_pos):
                    return True
            return False

        while overlaps(y):
            y += DiagramConfig.VERTICAL_STEP
        return x, y

    def on_add_child(self, parent_letter):
        logger.debug(f"on_add_child called with parent_letter={parent_letter}")
        if parent_letter not in self.reactions:
            logger.debug("on_add_child: parent not found in reactions")
            return
        new_id = self._get_new_temp_id()
        parent_gen = self.generation_map.get(parent_letter, 0)
        new_gen = parent_gen + 1
        self.generation_map[new_id] = new_gen
        parent_node = self.reactions[parent_letter]
        px, py = parent_node.x, parent_node.y
        x, y = self.find_position_for_new_node(new_gen, px, py)
        self.add_reaction_node(new_id, x, y)
        self.children_map.setdefault(parent_letter, []).append(new_id)
        self.rename_all_nodes()
        self.update_scene()

    def on_connect_to_child(self, parent_letter):
        logger.debug(f"on_connect_to_child called with parent_letter={parent_letter}")
        existing = [l for l in self.reactions.keys() if l != parent_letter]  # noqa: E741
        if not existing:
            QMessageBox.information(self, "Info", "No existing reactions available to connect as a child.")
            return
        child, ok = QInputDialog.getItem(
            self, "Connect to child", "Choose a reaction to become a child:", existing, 0, False
        )
        if ok and child:
            if self.is_cyclic(parent_letter, child):
                QMessageBox.warning(self, "Error", "Cannot connect because it would create a cycle.")
                return
            self.children_map.setdefault(parent_letter, [])
            if child not in self.children_map[parent_letter]:
                self.children_map[parent_letter].append(child)
            self.rename_all_nodes()
            self.update_scene()

    def on_delete_reaction_context(self, letter):
        logger.debug(f"on_delete_reaction_context called with letter={letter}")
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
            self.rename_all_nodes()
            self.update_scene()

    def remove_reaction(self, letter):  # noqa: C901
        logger.debug(f"remove_reaction called with letter={letter}")
        if letter == "A":
            QMessageBox.warning(self, "Error", "Component 'A' cannot be deleted.")
            return
        if letter in self.children_map:
            children = list(self.children_map[letter])
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

    def is_cyclic(self, parent, child):
        logger.debug(f"is_cyclic check: parent={parent}, child={child}")
        to_visit = [parent]
        while to_visit:
            current = to_visit.pop()
            if current == child:
                return True
            if current in self.children_map:
                to_visit.extend(self.children_map[current])
        return False

    def update_scene(self):
        logger.debug("update_scene: start")
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
        logger.debug("update_scene: end")

    def get_reaction_scheme_as_json(self):
        logger.debug("get_reaction_scheme_as_json called")
        nodes = []
        for letter, node in self.reactions.items():
            nodes.append({"id": letter, "x": node.x, "y": node.y})
        edges = []
        for parent, children in self.children_map.items():
            for child in children:
                edges.append({"from": parent, "to": child})
        scheme = {"nodes": nodes, "edges": edges}
        return scheme

    def rename_all_nodes(self):  # noqa: C901
        logger.debug("rename_all_nodes: start")
        if not self.reactions:
            logger.debug("rename_all_nodes: no nodes in reactions, exit")
            return
        all_nodes = set(self.reactions.keys())
        all_children = set()
        for ch_list in self.children_map.values():
            all_children.update(ch_list)
        possible_roots = all_nodes - all_children
        if not possible_roots:
            logger.debug("rename_all_nodes: no root node found, exit")
            return
        root = list(possible_roots)[0]
        queue = [root]
        visited = []
        while queue:
            current = queue.pop(0)
            visited.append(current)
            if current in self.children_map:
                for ch in self.children_map[current]:
                    if ch not in visited and ch not in queue:
                        queue.append(ch)
        if len(visited) > 26:
            QMessageBox.warning(
                self, "Warning", "More than 26 nodes in the tree. Labels beyond 'Z' will be left as temporary IDs."
            )
        old_to_new = {}
        for i, old_id in enumerate(visited):
            if i < 26:
                new_letter = self.alphabet[i]
            else:
                new_letter = old_id
            old_to_new[old_id] = new_letter
        new_children_map = {}
        for old_parent, child_list in self.children_map.items():
            new_parent = old_to_new.get(old_parent, old_parent)
            new_list = []
            for ch in child_list:
                new_list.append(old_to_new.get(ch, ch))
            new_children_map.setdefault(new_parent, []).extend(new_list)
        new_reactions = {}
        new_generation_map = {}
        for old_id, node in self.reactions.items():
            new_label = old_to_new.get(old_id, old_id)
            node.letter = new_label
            new_reactions[new_label] = node
            old_gen = self.generation_map.get(old_id, 0)
            new_generation_map[new_label] = old_gen
        self.children_map = new_children_map
        self.reactions = new_reactions
        self.generation_map = new_generation_map
        logger.debug("rename_all_nodes: end")
