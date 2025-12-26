from dataclasses import dataclass
from typing import List, Set, Tuple, FrozenSet
from config import ROBOT_COLORS
from entities import Wall

@dataclass(frozen=True)
class Objective:
    col: int
    row: int
    color: tuple[int, int, int]
    symbol: str
    is_multicolor: bool = False
    bit_index: int = 0

class Board:
    def __init__(self, cols: int, rows: int) -> None:
        self.cols = cols
        self.rows = rows

        self.center_block_cells: Set[Tuple[int, int]] = set()
        self.blocked_cells: Set[Tuple[int, int]] = set()
        self.blocked_edges: Set[FrozenSet[Tuple[int, int]]] = set()
        self.walls: List[Wall] = []
        self.objectives: List[Objective] = []

        self.walls_up = 0
        self.walls_down = 0
        self.walls_left = 0
        self.walls_right = 0
        self.blocked_mask = 0
        
        self.ray_masks = {'U': [0]*256, 'D': [0]*256, 'L': [0]*256, 'R': [0]*256}
        self._precompute_rays()

        # L'ordre est important : d'abord le bloc, puis les murs
        self._setup_center_block()
        self._create_fixed_walls()
        self._build_bitboard_walls() 
        self._create_objectives()

    def _pos_to_bit(self, c: int, r: int) -> int:
        if 0 <= c < self.cols and 0 <= r < self.rows:
            return 1 << (r * self.cols + c)
        return 0

    def _precompute_rays(self):
        for r in range(self.rows):
            for c in range(self.cols):
                idx = r * self.cols + c
                for nc in range(c + 1, self.cols): self.ray_masks['R'][idx] |= (1 << (r * self.cols + nc))
                for nc in range(0, c): self.ray_masks['L'][idx] |= (1 << (r * self.cols + nc))
                for nr in range(r + 1, self.rows): self.ray_masks['D'][idx] |= (1 << (nr * self.cols + c))
                for nr in range(0, r): self.ray_masks['U'][idx] |= (1 << (nr * self.cols + c))

    def _setup_center_block(self) -> None:
        mid_c, mid_r = self.cols // 2, self.rows // 2
        self.center_block_cells = {
            (mid_c-1, mid_r-1), (mid_c-1, mid_r),
            (mid_c, mid_r-1), (mid_c, mid_r)
        }
        self.blocked_cells = set(self.center_block_cells)
        
        for c, r in self.blocked_cells:
            self.blocked_mask |= self._pos_to_bit(c, r)
            # Murs empêchant d'entrer dans le centre
            self.walls_down |= self._pos_to_bit(c, r-1)
            self.walls_up |= self._pos_to_bit(c, r+1)
            self.walls_right |= self._pos_to_bit(c-1, r)
            self.walls_left |= self._pos_to_bit(c+1, r)

    def _add_edge_block(self, c1, r1, c2, r2):
        if 0 <= c1 < self.cols and 0 <= r1 < self.rows and 0 <= c2 < self.cols and 0 <= r2 < self.rows:
            self.blocked_edges.add(frozenset({(c1, r1), (c2, r2)}))

    def _create_fixed_walls(self) -> None:
        quadrant_walls = {
            "TL": [(1, 1, 0), (3, 4, 90), (5, 2, 180), (2, 7, 270), (6, 5, 180)],
            "TR": [(1, 3, 270), (2, 6, 0), (4, 2, 90), (5, 5, 180)],
            "BL": [(4, 2, 0), (1, 4, 90), (4, 6, 180), (2, 3, 270)],
            "BR": [(3, 1, 270), (6, 3, 0), (1, 5, 90), (2, 4, 0)],
        }
        h_c, h_r = self.cols // 2, self.rows // 2
        base_offsets = {"TL": (0, 0), "TR": (h_c, 0), "BL": (0, h_r), "BR": (h_c, h_r)}
        for q, walls_local in quadrant_walls.items():
            bc, br = base_offsets[q]
            for lc, lr, angle in walls_local:
                c, r = bc + lc, br + lr
                if (c, r) not in self.blocked_cells:
                    self.walls.append(Wall(col=c, row=r, angle=angle, kind="L"))

    def _build_bitboard_walls(self) -> None:

        # 1. Bordures du plateau
        for i in range(self.cols):
            self.walls_up |= self._pos_to_bit(i, 0)
            self.walls_down |= self._pos_to_bit(i, self.rows - 1)
            self.walls_left |= self._pos_to_bit(0, i)
            self.walls_right |= self._pos_to_bit(self.cols - 1, i)

        # 2. Murs intérieurs
        for w in self.walls:
            c, r = w.col, w.row
            if w.angle == 0:
                self.walls_up |= self._pos_to_bit(c, r)
                self.walls_left |= self._pos_to_bit(c, r)
                if r > 0: self.walls_down |= self._pos_to_bit(c, r-1)
                if c > 0: self.walls_right |= self._pos_to_bit(c-1, r)
                self._add_edge_block(c, r, c, r-1); self._add_edge_block(c, r, c-1, r)
            elif w.angle == 90:
                self.walls_up |= self._pos_to_bit(c, r)
                self.walls_right |= self._pos_to_bit(c, r)
                if r > 0: self.walls_down |= self._pos_to_bit(c, r-1)
                if c < self.cols-1: self.walls_left |= self._pos_to_bit(c+1, r)
                self._add_edge_block(c, r, c, r-1); self._add_edge_block(c, r, c+1, r)
            elif w.angle == 180:
                self.walls_down |= self._pos_to_bit(c, r)
                self.walls_right |= self._pos_to_bit(c, r)
                if r < self.rows-1: self.walls_up |= self._pos_to_bit(c, r+1)
                if c < self.cols-1: self.walls_left |= self._pos_to_bit(c+1, r)
                self._add_edge_block(c, r, c, r+1); self._add_edge_block(c, r, c+1, r)
            elif w.angle == 270:
                self.walls_down |= self._pos_to_bit(c, r)
                self.walls_left |= self._pos_to_bit(c, r)
                if r < self.rows-1: self.walls_up |= self._pos_to_bit(c, r+1)
                if c > 0: self.walls_right |= self._pos_to_bit(c-1, r)
                self._add_edge_block(c, r, c, r+1); self._add_edge_block(c, r, c-1, r)

    def get_move_targets(self, start_col: int, start_row: int, occupied_mask: int) -> Set[Tuple[int, int]]:
        idx = start_row * self.cols + start_col
        # On inclut le bloc central dans les obstacles "robots"
        robots = (occupied_mask & ~(1 << idx)) | self.blocked_mask
        targets = set()

        # --- DROITE ---
        # Si on n'est pas déjà bloqué par un mur ou un robot à droite
        if not ((self.walls_right | (robots >> 1)) & (1 << idx)):
            # On cherche l'obstacle suivant dans le rayon
            stop_cells = self.walls_right | (self.walls_left >> 1) | (robots >> 1)
            obs = stop_cells & self.ray_masks['R'][idx]
            if obs:
                dest = (obs & -obs).bit_length() - 1
                targets.add((dest % self.cols, dest // self.cols))
            else:
                dest = (idx // self.cols * self.cols) + 15
                if dest != idx: targets.add((dest % self.cols, dest // self.cols))

        # --- GAUCHE ---
        if not ((self.walls_left | (robots << 1)) & (1 << idx)):
            stop_cells = self.walls_left | (self.walls_right << 1) | (robots << 1)
            obs = stop_cells & self.ray_masks['L'][idx]
            if obs:
                dest = obs.bit_length() - 1
                targets.add((dest % self.cols, dest // self.cols))
            else:
                dest = (idx // self.cols * self.cols)
                if dest != idx: targets.add((dest % self.cols, dest // self.cols))

        # --- BAS ---
        if not ((self.walls_down | (robots >> self.cols)) & (1 << idx)):
            stop_cells = self.walls_down | (self.walls_up >> self.cols) | (robots >> self.cols)
            obs = stop_cells & self.ray_masks['D'][idx]
            if obs:
                dest = (obs & -obs).bit_length() - 1
                targets.add((dest % self.cols, dest // self.cols))
            else:
                dest = (15 * self.cols) + (idx % self.cols)
                if dest != idx: targets.add((dest % self.cols, dest // self.cols))

        # --- HAUT ---
        if not ((self.walls_up | (robots << self.cols)) & (1 << idx)):
            stop_cells = self.walls_up | (self.walls_down << self.cols) | (robots << self.cols)
            obs = stop_cells & self.ray_masks['U'][idx]
            if obs:
                dest = obs.bit_length() - 1
                targets.add((dest % self.cols, dest // self.cols))
            else:
                dest = idx % self.cols
                if dest != idx: targets.add((dest % self.cols, dest // self.cols))

        return targets
    
    def _create_objectives(self) -> None:
        layout = [
            (1, 1, 0, "diamond", False), 
            (3, 4, 1, "square",  False),
            (5, 2, 2, "triangle", False),
            (2, 7, 3, "pentagon", False),
            (4, 10, 1, "diamond", False), 
            (1, 12, 2, "square", False),
            (6, 5, 3, "triangle", False), 
            (9, 3, 0, "pentagon", False),
            (10, 6, 2, "diamond", False), 
            (12, 2, 3, "square", False),
            (13, 5, 0, "triangle", False), 
            (11, 9, 1, "pentagon", False),
            (14, 11, 3, "diamond", False), 
            (9, 13, 0, "square", False),
            (4, 14, 1, "triangle", False), 
            (10, 12, 2, "pentagon", False),
        ]
        self.objectives = []
        for col, row, color_idx, symbol, is_multi in layout:
            color = (255, 255, 255) if is_multi else ROBOT_COLORS[color_idx % len(ROBOT_COLORS)]
            self.objectives.append(Objective(
                col=col, row=row, color=color, symbol=symbol, 
                is_multicolor=is_multi, bit_index=(row * self.cols + col)
            ))

    def is_blocked(self, col: int, row: int) -> bool:
        return (col, row) in self.blocked_cells