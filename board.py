import pygame
from dataclasses import dataclass
from typing import Set, Tuple, List, FrozenSet
from config import GRID_COLS, GRID_ROWS, CENTER_BLOCK_COLOR, WALL_COLOR, WALL_THICKNESS, ROBOT_COLORS
from entities import Cell, Wall, cell_rect


@dataclass
class Objective:
    col: int
    row: int
    color: tuple[int, int, int]
    symbol: str
    is_multicolor: bool = False


class Board:
    def __init__(self, cols: int, rows: int) -> None:
        self.cols = cols
        self.rows = rows
        self.cells: List[List[Cell]] = [
            [Cell(col, row) for row in range(rows)]
            for col in range(cols)
        ]
        self.center_block_cells: Set[Tuple[int, int]] = {
            (7, 7),
            (7, 8),
            (8, 7),
            (8, 8),
        }
        self.blocked_cells: Set[Tuple[int, int]] = set(self.center_block_cells)
        self.walls: List[Wall] = []
        self.blocked_edges: Set[FrozenSet[Tuple[int, int]]] = set()
        self.objectives: List[Objective] = []
        self._create_fixed_walls()
        self._build_blocked_edges()
        self._create_objectives()

    def _create_fixed_walls(self) -> None:
        quadrant_walls = {
            "TL": [
                (1, 1, 0),
                (3, 4, 90),
                (5, 2, 180),
                (2, 7, 270),
                (6, 5, 180),
            ],
            "TR": [
                (1, 3, 270),
                (2, 6, 0),
                (4, 2, 90),
                (5, 5, 180),
            ],
            "BL": [
                (4, 2, 0),
                (1, 4, 90),
                (4, 6, 180),
                (2, 3, 270),
            ],
            "BR": [
                (3, 1, 270),
                (6, 3, 0),
                (1, 5, 90),
                (2, 4, 0),
            ],
        }
        base_offsets = {
            "TL": (0, 0),
            "TR": (8, 0),
            "BL": (0, 8),
            "BR": (8, 8),
        }
        self.walls = []
        for quadrant_name, walls_local in quadrant_walls.items():
            base_col, base_row = base_offsets[quadrant_name]
            for local_col, local_row, angle in walls_local:
                col = base_col + local_col
                row = base_row + local_row
                if (col, row) in self.center_block_cells:
                    continue
                self.walls.append(Wall(col=col, row=row, angle=angle, kind="L"))

    def _add_edge_block(self, c1: int, r1: int, c2: int, r2: int) -> None:
        if 0 <= c1 < self.cols and 0 <= r1 < self.rows and 0 <= c2 < self.cols and 0 <= r2 < self.rows:
            self.blocked_edges.add(frozenset({(c1, r1), (c2, r2)}))

    def _build_blocked_edges(self) -> None:
        self.blocked_edges.clear()
        for wall in self.walls:
            c = wall.col
            r = wall.row
            if wall.kind == "L":
                if wall.angle == 0:
                    self._add_edge_block(c, r, c, r - 1)
                    self._add_edge_block(c, r, c - 1, r)
                elif wall.angle == 90:
                    self._add_edge_block(c, r, c, r - 1)
                    self._add_edge_block(c, r, c + 1, r)
                elif wall.angle == 180:
                    self._add_edge_block(c, r, c, r + 1)
                    self._add_edge_block(c, r, c + 1, r)
                elif wall.angle == 270:
                    self._add_edge_block(c, r, c, r + 1)
                    self._add_edge_block(c, r, c - 1, r)

    def _create_objectives(self) -> None:
        self.objectives = []
        layout = [
            (1, 1, 0, "diamond", False),
            (3, 4, 1, "square", False),
            (5, 2, 2, "triangle", False),
            (2, 7, 3, "diamond", False),
            (4, 10, 0, "square", False),
            (1, 12, 1, "triangle", False),
            (6, 5, 2, "diamond", False),
            (9, 3, 3, "square", False),
            (10, 6, 0, "triangle", False),
            (12, 2, 1, "diamond", False),
            (13, 5, 2, "square", False),
            (11, 9, 3, "triangle", False),
            (14, 11, 0, "diamond", False),
            (9, 13, 1, "square", False),
            (4, 14, 2, "triangle", False),
            (2, 11, 3, "diamond", False),
            (10, 12, 0, "square", True),
        ]
        for col, row, color_index, symbol, is_multi in layout:
            if (col, row) in self.center_block_cells:
                continue
            if is_multi:
                color = (255, 255, 255)
                obj = Objective(col=col, row=row, color=color, symbol=symbol, is_multicolor=True)
            else:
                color = ROBOT_COLORS[color_index % len(ROBOT_COLORS)]
                obj = Objective(col=col, row=row, color=color, symbol=symbol, is_multicolor=False)
            self.objectives.append(obj)

    def is_blocked(self, col: int, row: int) -> bool:
        return (col, row) in self.blocked_cells

    def get_move_targets(
        self,
        start_col: int,
        start_row: int,
        occupied: Set[Tuple[int, int]],
    ) -> Set[Tuple[int, int]]:
        targets: Set[Tuple[int, int]] = set()
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        for dx, dy in directions:
            c = start_col
            r = start_row
            obstacle_found = False
            stop_c = start_col
            stop_r = start_row
            while True:
                nx = c + dx
                ny = r + dy
                if not (0 <= nx < self.cols and 0 <= ny < self.rows):
                    obstacle_found = True
                    stop_c, stop_r = c, r
                    break
                if frozenset({(c, r), (nx, ny)}) in self.blocked_edges:
                    obstacle_found = True
                    stop_c, stop_r = c, r
                    break
                if self.is_blocked(nx, ny) or (nx, ny) in occupied:
                    obstacle_found = True
                    stop_c, stop_r = c, r
                    break
                c, r = nx, ny
            if obstacle_found and (stop_c, stop_r) != (start_col, start_row):
                targets.add((stop_c, stop_r))
        return targets

    def _draw_objective(self, surface: pygame.Surface, screen_width: int, screen_height: int, obj: Objective) -> None:
        rect = cell_rect(obj.col, obj.row, screen_width, screen_height)
        cx = rect.centerx
        cy = rect.centery
        size = rect.width // 4
        if obj.symbol == "diamond":
            points = [
                (cx, cy - size),
                (cx + size, cy),
                (cx, cy + size),
                (cx - size, cy),
            ]
            pygame.draw.polygon(surface, obj.color, points)
        elif obj.symbol == "square":
            inner = pygame.Rect(0, 0, size * 2, size * 2)
            inner.center = (cx, cy)
            pygame.draw.rect(surface, obj.color, inner)
        elif obj.symbol == "circle":
            pygame.draw.circle(surface, obj.color, (cx, cy), size)
        elif obj.symbol == "triangle":
            points = [
                (cx, cy - size),
                (cx + size, cy + size),
                (cx - size, cy + size),
            ]
            pygame.draw.polygon(surface, obj.color, points)

    def draw(self, surface: pygame.Surface, screen_width: int, screen_height: int) -> None:
        for (col, row) in self.center_block_cells:
            rect = cell_rect(col, row, screen_width, screen_height)
            pygame.draw.rect(surface, CENTER_BLOCK_COLOR, rect)
        for col in range(self.cols):
            for row in range(self.rows):
                self.cells[col][row].draw(surface, screen_width, screen_height)
        for wall in self.walls:
            wall.draw(surface, screen_width, screen_height)
        for obj in self.objectives:
            self._draw_objective(surface, screen_width, screen_height, obj)
        border_rect = pygame.Rect(0, 0, screen_width, screen_height)
        pygame.draw.rect(surface, WALL_COLOR, border_rect, WALL_THICKNESS)
