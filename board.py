import pygame
import random
from typing import Set, Tuple, List, FrozenSet
from config import GRID_COLS, GRID_ROWS, CENTER_BLOCK_COLOR
from entities import Cell, Wall, cell_rect


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
        self._create_random_walls()
        self._build_blocked_edges()

    def _neighbors_4(self, c: int, r: int) -> Set[Tuple[int, int]]:
        res: Set[Tuple[int, int]] = set()
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc = c + dc
            nr = r + dr
            if 0 <= nc < self.cols and 0 <= nr < self.rows:
                res.add((nc, nr))
        return res

    def _cells_for_wall(self, kind: str, angle: int, col: int, row: int) -> Set[Tuple[int, int]]:
        cells: Set[Tuple[int, int]] = {(col, row)}
        if kind == "S":
            if angle in (0, 180):
                cells.add((col + 1, row))
            else:
                cells.add((col, row + 1))
        return cells

    def _create_random_walls(self) -> None:
        min_walls = 8
        max_walls = 20
        n_walls = random.randint(min_walls, max_walls)
        forbidden: Set[Tuple[int, int]] = set()
        attempts = 0
        max_attempts = n_walls * 40
        while len(self.walls) < n_walls and attempts < max_attempts:
            attempts += 1
            kind = random.choice(["L", "S"])
            angle = random.choice([0, 90, 180, 270])
            col = random.randint(0, self.cols - 1)
            row = random.randint(0, self.rows - 1)
            if (col, row) in self.center_block_cells:
                continue
            if kind == "S":
                if angle in (0, 180):
                    if col >= self.cols - 1:
                        continue
                    if (col + 1, row) in self.center_block_cells:
                        continue
                else:
                    if row >= self.rows - 1:
                        continue
                    if (col, row + 1) in self.center_block_cells:
                        continue
            wall_cells = self._cells_for_wall(kind, angle, col, row)
            if any(cell in forbidden for cell in wall_cells):
                continue
            self.walls.append(Wall(col=col, row=row, angle=angle, kind=kind))
            for c, r in wall_cells:
                forbidden.add((c, r))
                forbidden.update(self._neighbors_4(c, r))

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
            else:
                if wall.angle in (0, 180):
                    c2 = c + 1
                    if wall.angle == 0:
                        self._add_edge_block(c, r, c, r - 1)
                        self._add_edge_block(c, r, c2, r)
                        self._add_edge_block(c2, r, c2, r + 1)
                    else:
                        self._add_edge_block(c, r, c, r + 1)
                        self._add_edge_block(c, r, c2, r)
                        self._add_edge_block(c2, r, c2, r - 1)
                else:
                    r2 = r + 1
                    if wall.angle == 90:
                        self._add_edge_block(c, r, c - 1, r)
                        self._add_edge_block(c, r, c, r2)
                        self._add_edge_block(c, r2, c + 1, r2)
                    else:
                        self._add_edge_block(c, r, c + 1, r)
                        self._add_edge_block(c, r, c, r2)
                        self._add_edge_block(c, r2, c - 1, r2)

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

    def draw(self, surface: pygame.Surface, screen_width: int, screen_height: int) -> None:
        for (col, row) in self.center_block_cells:
            rect = cell_rect(col, row, screen_width, screen_height)
            pygame.draw.rect(surface, CENTER_BLOCK_COLOR, rect)
        for col in range(self.cols):
            for row in range(self.rows):
                self.cells[col][row].draw(surface, screen_width, screen_height)
        for wall in self.walls:
            wall.draw(surface, screen_width, screen_height)
