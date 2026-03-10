import pygame
from dataclasses import dataclass
from src.core.config import get_cell_size, GRID_COLOR, WALL_COLOR, WALL_THICKNESS

GridPosition = tuple[int, int]


def grid_to_pixel_center(col: int, row: int, screen_width: int, screen_height: int) -> tuple[int, int]:
    cell_w, cell_h = get_cell_size(screen_width, screen_height)
    x = col * cell_w + cell_w // 2
    y = row * cell_h + cell_h // 2
    return x, y


def cell_rect(col: int, row: int, screen_width: int, screen_height: int) -> pygame.Rect:
    cell_w, cell_h = get_cell_size(screen_width, screen_height)
    return pygame.Rect(col * cell_w, row * cell_h, cell_w, cell_h)


@dataclass
class Cell:
    col: int
    row: int

    def draw(self, surface: pygame.Surface, screen_width: int, screen_height: int) -> None:
        rect = cell_rect(self.col, self.row, screen_width, screen_height)
        pygame.draw.rect(surface, GRID_COLOR, rect, 1)


@dataclass
class Robot:
    col: int
    row: int
    radius: int
    color: tuple[int, int, int]

    def draw(self, surface: pygame.Surface, screen_width: int, screen_height: int) -> None:
        x, y = grid_to_pixel_center(self.col, self.row, screen_width, screen_height)
        cell_w, cell_h = get_cell_size(screen_width, screen_height)
        r = min(cell_w, cell_h) // 3
        pygame.draw.circle(surface, self.color, (x, y), r)


@dataclass
class Wall:
    col: int
    row: int
    angle: int
    kind: str

    def draw(self, surface: pygame.Surface, screen_width: int, screen_height: int) -> None:
        if self.kind == "L":
            self._draw_L(surface, screen_width, screen_height)

    def _draw_L(self, surface: pygame.Surface, screen_width: int, screen_height: int) -> None:
        rect = cell_rect(self.col, self.row, screen_width, screen_height)
        x1, y1 = rect.topleft
        x2, y2 = rect.topright
        x3, y3 = rect.bottomright
        x4, y4 = rect.bottomleft

        if self.angle == 0:
            pygame.draw.line(surface, WALL_COLOR, (x1, y1), (x2, y2), WALL_THICKNESS)
            pygame.draw.line(surface, WALL_COLOR, (x1, y1), (x4, y4), WALL_THICKNESS)
        elif self.angle == 90:
            pygame.draw.line(surface, WALL_COLOR, (x1, y1), (x2, y2), WALL_THICKNESS)
            pygame.draw.line(surface, WALL_COLOR, (x2, y2), (x3, y3), WALL_THICKNESS)
        elif self.angle == 180:
            pygame.draw.line(surface, WALL_COLOR, (x3, y3), (x2, y2), WALL_THICKNESS)
            pygame.draw.line(surface, WALL_COLOR, (x3, y3), (x4, y4), WALL_THICKNESS)
        elif self.angle == 270:
            pygame.draw.line(surface, WALL_COLOR, (x4, y4), (x3, y3), WALL_THICKNESS)
            pygame.draw.line(surface, WALL_COLOR, (x4, y4), (x1, y1), WALL_THICKNESS)
