import string
from collections import deque

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
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

from src.core.app_settings import OperationType
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

    def _calculate_intersection_candidates(self, from_x, from_y, dx, dy, node):  # noqa: C901
        """
        Calculate intersection parameters (t-values) for each edge of the node's rectangle.

        :param from_x: X-coordinate of the line start point
        :param from_y: Y-coordinate of the line start point
        :param dx: Horizontal difference (line's delta x)
        :param dy: Vertical difference (line's delta y)
        :param node: ReactionNode whose rectangle edges we check against
        :return: A list of tuples (t_value, x_intersect, y_intersect)
        """
        px, py = node.center_point()
        half_w = DiagramConfig.NODE_WIDTH / 2
        half_h = DiagramConfig.NODE_HEIGHT / 2
        left = px - half_w
        right = px + half_w
        top = py - half_h
        bottom = py + half_h
        t_candidates = []

        # Horizontal edges
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

        # Vertical edges
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

        return t_candidates

    def _adjust_intersection_for_inset(self, px, py, ix, iy):
        """
        Adjust intersection point inwards by DiagramConfig.ARROW_INSET to avoid overlapping with the node rectangle.

        :param px: Node center X
        :param py: Node center Y
        :param ix: Intersection X
        :param iy: Intersection Y
        :return: Adjusted X, Adjusted Y
        """
        line_len = ((ix - px) ** 2 + (iy - py) ** 2) ** 0.5
        # Move the intersection point slightly towards the line start
        if line_len != 0:
            ux = (px - ix) / line_len
            uy = (py - iy) / line_len
            ix += ux * DiagramConfig.ARROW_INSET
            iy += uy * DiagramConfig.ARROW_INSET
        return ix, iy

    def _intersect_node_edge(self, from_x, from_y, to_x, to_y, node):
        """
        Compute the intersection point between a line segment and a node's rectangle edge.

        :param from_x: X-coordinate of the line start
        :param from_y: Y-coordinate of the line start
        :param to_x: X-coordinate of the line end
        :param to_y: Y-coordinate of the line end
        :param node: ReactionNode whose edges we are intersecting
        :return: Intersection X, Intersection Y (or node center if no intersection found)
        """
        px, py = node.center_point()
        dx = to_x - from_x
        dy = to_y - from_y

        # If both dx and dy are 0, line is degenerate
        if dx == 0 and dy == 0:
            return px, py

        t_candidates = self._calculate_intersection_candidates(from_x, from_y, dx, dy, node)
        if not t_candidates:
            return px, py

        # Sort by the t-value to find the first intersection point
        t_candidates.sort(key=lambda x: x[0])
        _, ix, iy = t_candidates[0]
        ix, iy = self._adjust_intersection_for_inset(px, py, ix, iy)
        return ix, iy

    def _create_arrow_polygon(self, start_x, start_y, end_x, end_y):
        """
        Create the arrow polygon used to draw the arrowhead.

        :param start_x: X-coordinate of the arrow line start
        :param start_y: Y-coordinate of the arrow line start
        :param end_x: X-coordinate of the arrow line end
        :param end_y: Y-coordinate of the arrow line end
        :return: QPolygonF representing the arrowhead
        """
        dx = end_x - start_x
        dy = end_y - start_y
        line_length = (dx**2 + dy**2) ** 0.5
        if line_length == 0:
            # No arrow if there's no distance
            return QPolygonF()

        # Normalize direction vectors
        nx = dx / line_length
        ny = dy / line_length
        perp_x = -ny
        perp_y = nx
        arrow_tip_x = end_x
        arrow_tip_y = end_y

        # Calculate the left and right corners of the arrowhead
        arrow_left_x = arrow_tip_x - nx * DiagramConfig.ARROW_SIZE - perp_x * DiagramConfig.ARROW_SIZE / 2
        arrow_left_y = arrow_tip_y - ny * DiagramConfig.ARROW_SIZE - perp_y * DiagramConfig.ARROW_SIZE / 2
        arrow_right_x = arrow_tip_x - nx * DiagramConfig.ARROW_SIZE + perp_x * DiagramConfig.ARROW_SIZE / 2
        arrow_right_y = arrow_tip_y - ny * DiagramConfig.ARROW_SIZE + perp_y * DiagramConfig.ARROW_SIZE / 2

        arrow_polygon = QPolygonF(
            [
                QPointF(arrow_tip_x, arrow_tip_y),
                QPointF(arrow_left_x, arrow_left_y),
                QPointF(arrow_right_x, arrow_right_y),
            ]
        )
        return arrow_polygon

    def draw(self):
        """
        Draw the reaction arrow between parent_node and child_node.
        """
        p_cx, p_cy = self.parent_node.center_point()
        c_cx, c_cy = self.child_node.center_point()

        # Intersect near the edges of parent and child nodes
        start_x, start_y = self._intersect_node_edge(p_cx, p_cy, c_cx, c_cy, self.parent_node)
        end_x, end_y = self._intersect_node_edge(c_cx, c_cy, start_x, start_y, self.child_node)

        # Draw the line
        self.line_item = self.scene.addLine(start_x, start_y, end_x, end_y, QPen(DiagramConfig.PEN_COLOR))

        # Draw the arrowhead
        arrow_polygon = self._create_arrow_polygon(start_x, start_y, end_x, end_y)
        if not arrow_polygon.isEmpty():
            self.arrow_item = self.scene.addPolygon(
                arrow_polygon, QPen(DiagramConfig.PEN_COLOR), QBrush(DiagramConfig.ARROW_COLOR)
            )

    def remove(self):
        if self.line_item:
            self.scene.removeItem(self.line_item)
            self.line_item = None
        if self.arrow_item:
            self.scene.removeItem(self.arrow_item)
            self.arrow_item = None


class ModelsScheme(QWidget):
    scheme_change_signal = pyqtSignal(dict)

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

        # # Create a small initial example
        # root_id = self._get_new_temp_id()
        # child_id = self._get_new_temp_id()
        # self.generation_map[root_id] = 0
        # self.generation_map[child_id] = 1
        # self.add_reaction_node(root_id, 0, 0)
        # px, py = self.reactions[root_id].x, self.reactions[root_id].y
        # child_x, child_y = self.find_position_for_new_node(1, px, py)
        # self.add_reaction_node(child_id, child_x, child_y)
        # self.children_map[root_id] = [child_id]

        # self.rename_all_nodes()
        # self.update_scene()
        # logger.debug("ModelsScheme: __init__ end")

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
            # Check if the new node's y-range overlaps with any existing node in the same generation
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
        self.emit_scheme_change_signal()

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
            self.emit_scheme_change_signal()

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
            self.emit_scheme_change_signal()

    def remove_reaction(self, letter):
        """
        Removes a reaction node (and its descendants) from the diagram.

        :param letter: Label of the node to remove
        """
        logger.debug(f"remove_reaction called with letter={letter}")
        if letter in ["A", "B"]:
            QMessageBox.warning(self, "Error", "Components 'A' and 'B' cannot be deleted.")
            return

        # 1) Remove all descendants recursively
        self._remove_descendants(letter)

        # 2) Remove this node itself
        self._remove_node(letter)

        # 3) Remove arrows that connect from or to this node
        self._remove_arrows(letter)

        # 4) Cleanup references in parent-child relationships
        self._cleanup_parent_links(letter)

    def _remove_descendants(self, letter):
        """
        Remove all children of the given node in a recursive manner.
        """
        if letter in self.children_map:
            children = list(self.children_map[letter])
            for child in children:
                self.remove_reaction(child)
            self.children_map.pop(letter, None)

    def _remove_node(self, letter):
        """
        Remove the node from the reactions dict and occupied_positions.
        """
        if letter in self.reactions:
            node = self.reactions[letter]
            gen = self.generation_map[letter]
            node_y_start = node.y
            node_y_end = node.y + DiagramConfig.NODE_HEIGHT

            # Remove the vertical space from occupied_positions
            if gen in self.occupied_positions:
                self.occupied_positions[gen] = [
                    (s, e) for (s, e) in self.occupied_positions[gen] if not (s == node_y_start and e == node_y_end)
                ]
                if not self.occupied_positions[gen]:
                    del self.occupied_positions[gen]

            node.remove()
            del self.reactions[letter]
            del self.generation_map[letter]

    def _remove_arrows(self, letter):
        """
        Remove all arrows connecting to or from the given node.
        """
        arrows_to_remove = [
            arrow for arrow in self.arrows if arrow.parent_node.letter == letter or arrow.child_node.letter == letter
        ]
        for arrow in arrows_to_remove:
            arrow.remove()
            self.arrows.remove(arrow)

    def _cleanup_parent_links(self, letter):
        """
        Remove references to this node from any parent's children list.
        """
        for p, ch_list in list(self.children_map.items()):
            if letter in ch_list:
                ch_list.remove(letter)
                if not ch_list:
                    self.children_map.pop(p, None)

    def is_cyclic(self, parent, child):
        logger.debug(f"is_cyclic check: parent={parent}, child={child}")
        # BFS or DFS approach to see if child is reachable from parent
        to_visit = [parent]
        while to_visit:
            current = to_visit.pop()
            if current == child:
                return True
            if current in self.children_map:
                to_visit.extend(self.children_map[current])
        return False

    def update_scene(self):
        """
        Updates the QGraphicsScene by clearing it and redrawing all nodes and arrows.
        """
        self.scene.clear()
        self.arrows.clear()

        # Redraw nodes
        for letter, node in self.reactions.items():
            node.draw()

        # Redraw arrows
        for parent, children in self.children_map.items():
            for child in children:
                if parent in self.reactions and child in self.reactions:
                    parent_node = self.reactions[parent]
                    child_node = self.reactions[child]
                    arrow = ReactionArrow(self.scene, parent_node, child_node)
                    self.arrows.append(arrow)

        # Configure the view
        self.view.setScene(self.scene)
        self.view.setRenderHint(self.view.renderHints() | self.view.renderHints().Antialiasing)
        self.scene.update()

    def get_reaction_scheme_as_json(self):
        """
        Returns a JSON-compatible dictionary representing the reaction scheme.
        """
        logger.debug("get_reaction_scheme_as_json called")
        nodes = []
        for letter, node in self.reactions.items():
            nodes.append({"id": letter})
        edges = []
        for parent, children in self.children_map.items():
            for child in children:
                edges.append({"from": parent, "to": child})
        scheme = {"components": nodes, "reactions": edges}
        return scheme

    def emit_scheme_change_signal(self):
        scheme = self.get_reaction_scheme_as_json()
        data = {"reaction_scheme": scheme, "operation": OperationType.SCHEME_CHANGE}
        self.scheme_change_signal.emit(data)

    def rename_all_nodes(self):
        """
        Renames all nodes in a breadth-first manner from the root to avoid duplicates.
        If there are more than 26 nodes, IDs after 'Z' remain temporary.
        """
        if not self.reactions:
            logger.debug("rename_all_nodes: no nodes in reactions, exit")
            return

        # 1) Identify root(s) of the diagram
        possible_roots = self._get_root_nodes()
        if not possible_roots:
            logger.debug("rename_all_nodes: no root node found, exit")
            return

        # 2) BFS order of nodes
        visited = self._bfs_traverse(list(possible_roots)[0])

        # 3) Create a mapping from old IDs to new letters
        old_to_new = self._create_old_to_new_map(visited)

        # 4) Apply the new naming to children_map, reactions, generation_map
        self._apply_renaming(old_to_new)

    def _get_root_nodes(self):
        """
        Determine possible roots for the BFS (those that are not children of any node).
        """
        all_nodes = set(self.reactions.keys())
        all_children = set()
        for ch_list in self.children_map.values():
            all_children.update(ch_list)
        return all_nodes - all_children

    def _bfs_traverse(self, root):
        """
        Perform a BFS traversal from the given root node.

        :param root: The root node ID
        :return: Ordered list of visited node IDs
        """
        queue = [root]
        visited = []
        while queue:
            current = queue.pop(0)
            visited.append(current)

            if current in self.children_map:
                for ch in self.children_map[current]:
                    if ch not in visited and ch not in queue:
                        queue.append(ch)
        return visited

    def _create_old_to_new_map(self, visited):
        """
        Create a dictionary mapping old IDs to new labels using the English alphabet.
        If the index exceeds 25, keep the old ID.

        :param visited: BFS ordered list of node IDs
        :return: Dictionary of {old_id: new_label}
        """
        old_to_new = {}
        if len(visited) > 26:
            QMessageBox.warning(
                self, "Warning", "More than 26 nodes in the tree. Labels beyond 'Z' will be left as temporary IDs."
            )
        for i, old_id in enumerate(visited):
            if i < 26:
                new_letter = self.alphabet[i]
            else:
                new_letter = old_id
            old_to_new[old_id] = new_letter
        return old_to_new

    def _apply_renaming(self, old_to_new):
        """
        Apply the renaming dictionary to children_map, reactions, and generation_map.

        :param old_to_new: Dictionary {old_id: new_label}
        """
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

    def update_from_scheme(self, scheme_data: dict, reactions_list: list):
        self._clear_scheme()

        node_ids = self._extract_node_ids(scheme_data)
        children_map, child_nodes = self._build_children_map(reactions_list)
        roots = self._determine_roots(node_ids, child_nodes)
        logger.debug(f"Roots: {roots}")

        generations = self._calculate_generations(roots, children_map, node_ids)
        generation_to_nodes = self._group_nodes_by_generation(generations)
        self._assign_positions(generation_to_nodes)

        self.children_map = children_map

        self.update_scene()

    def _clear_scheme(self):
        self.scene.clear()
        self.reactions.clear()
        self.children_map.clear()
        self.generation_map.clear()
        self.occupied_positions.clear()
        self.arrows.clear()

    def _extract_node_ids(self, scheme_data: dict):
        components = scheme_data.get("components", [])
        return [comp.get("id") for comp in components if comp.get("id")]

    def _build_children_map(self, reactions_list: list):
        children_map = {}
        child_nodes = set()
        for reaction in reactions_list:
            parent = reaction.get("from")
            child = reaction.get("to")
            if parent and child:
                children_map.setdefault(parent, []).append(child)
                child_nodes.add(child)
        return children_map, child_nodes

    def _determine_roots(self, node_ids, child_nodes):
        roots = [node for node in node_ids if node not in child_nodes]
        if not roots:
            roots = node_ids
        return roots

    def _calculate_generations(self, roots, children_map, node_ids):
        generations = {}
        queue = deque()
        for root in roots:
            generations[root] = 0
            queue.append(root)
        while queue:
            current = queue.popleft()
            for child in children_map.get(current, []):
                if child not in generations or generations[current] + 1 < generations[child]:
                    generations[child] = generations[current] + 1
                    queue.append(child)

        for node in node_ids:
            if node not in generations:
                generations[node] = 0
        return generations

    def _group_nodes_by_generation(self, generations: dict):
        generation_to_nodes = {}
        for node, gen in generations.items():
            generation_to_nodes.setdefault(gen, []).append(node)

        for gen in generation_to_nodes:
            generation_to_nodes[gen].sort()
        return generation_to_nodes

    def _assign_positions(self, generation_to_nodes: dict):
        for gen in sorted(generation_to_nodes.keys()):
            nodes_in_gen = generation_to_nodes[gen]
            for idx, node_id in enumerate(nodes_in_gen):
                x = gen * DiagramConfig.HORIZONTAL_GAP
                y = idx * (DiagramConfig.NODE_HEIGHT + DiagramConfig.VERTICAL_STEP)
                self.generation_map[node_id] = gen
                self.add_reaction_node(node_id, x, y)
