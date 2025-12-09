import pygame
from dataclasses import dataclass
from config import (
    GRID_COLS,
    GRID_ROWS,
    get_cell_size,
    GRID_COLOR,
    WALL_COLOR,
    WALL_THICKNESS,
)


def grid_to_pixel_center(col, row, screen_width, screen_height):
    cell_w, cell_h = get_cell_size(screen_width, screen_height)
    x = col * cell_w + cell_w // 2
    y = row * cell_h + cell_h // 2
    return x, y


def cell_rect(col, row, screen_width, screen_height):
    cell_w, cell_h = get_cell_size(screen_width, screen_height)
    return pygame.Rect(
        col * cell_w,
        row * cell_h,
        cell_w,
        cell_h,
    )


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
        elif self.kind == "S":
            self._draw_S(surface, screen_width, screen_height)

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

    def _draw_S(self, surface: pygame.Surface, screen_width: int, screen_height: int) -> None:
        c = self.col
        r = self.row

        if self.angle in (0, 180):
            rect_left = cell_rect(c, r, screen_width, screen_height)
            rect_right = cell_rect(c + 1, r, screen_width, screen_height)
            lx1, ly1 = rect_left.topleft
            lx2, ly2 = rect_left.topright
            lx3, ly3 = rect_left.bottomright
            lx4, ly4 = rect_left.bottomleft
            rx1, ry1 = rect_right.topleft
            rx2, ry2 = rect_right.topright
            rx3, ry3 = rect_right.bottomright
            rx4, ry4 = rect_right.bottomleft

            if self.angle == 0:
                pygame.draw.line(surface, WALL_COLOR, (lx1, ly1), (lx2, ly2), WALL_THICKNESS)
                pygame.draw.line(surface, WALL_COLOR, (lx2, ly2), (rx4, ry4), WALL_THICKNESS)
                pygame.draw.line(surface, WALL_COLOR, (rx4, ry4), (rx3, ry3), WALL_THICKNESS)
            else:
                pygame.draw.line(surface, WALL_COLOR, (lx4, ly4), (lx3, ly3), WALL_THICKNESS)
                pygame.draw.line(surface, WALL_COLOR, (lx3, ly3), (rx1, ry1), WALL_THICKNESS)
                pygame.draw.line(surface, WALL_COLOR, (rx1, ry1), (rx2, ry2), WALL_THICKNESS)
        else:
            rect_top = cell_rect(c, r, screen_width, screen_height)
            rect_bottom = cell_rect(c, r + 1, screen_width, screen_height)
            tx1, ty1 = rect_top.topleft
            tx2, ty2 = rect_top.topright
            tx3, ty3 = rect_top.bottomright
            tx4, ty4 = rect_top.bottomleft
            bx1, by1 = rect_bottom.topleft
            bx2, by2 = rect_bottom.topright
            bx3, by3 = rect_bottom.bottomright
            bx4, by4 = rect_bottom.bottomleft

            if self.angle == 90:
                pygame.draw.line(surface, WALL_COLOR, (tx1, ty1), (tx4, ty4), WALL_THICKNESS)
                pygame.draw.line(surface, WALL_COLOR, (tx4, ty4), (bx2, by2), WALL_THICKNESS)
                pygame.draw.line(surface, WALL_COLOR, (bx2, by2), (bx3, by3), WALL_THICKNESS)
            else:
                pygame.draw.line(surface, WALL_COLOR, (tx2, ty2), (tx3, ty3), WALL_THICKNESS)
                pygame.draw.line(surface, WALL_COLOR, (tx3, ty3), (bx1, by1), WALL_THICKNESS)
                pygame.draw.line(surface, WALL_COLOR, (bx1, by1), (bx4, by4), WALL_THICKNESS)
