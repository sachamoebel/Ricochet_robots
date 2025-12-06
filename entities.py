import pygame
from dataclasses import dataclass
from config import (
    CELL_WIDTH,
    CELL_HEIGHT,
    GRID_COLOR,
    WALL_COLOR,
    WALL_THICKNESS,
)


def grid_to_pixel_center(col: int, row: int) -> tuple[int, int]:
    x = col * CELL_WIDTH + CELL_WIDTH // 2
    y = row * CELL_HEIGHT + CELL_HEIGHT // 2
    return x, y


def cell_rect(col: int, row: int) -> pygame.Rect:
    return pygame.Rect(
        col * CELL_WIDTH,
        row * CELL_HEIGHT,
        CELL_WIDTH,
        CELL_HEIGHT,
    )


@dataclass
class Cell:
    col: int
    row: int

    @property
    def rect(self) -> pygame.Rect:
        return cell_rect(self.col, self.row)

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, GRID_COLOR, self.rect, 1)


@dataclass
class Robot:
    col: int
    row: int
    radius: int
    color: tuple[int, int, int]

    def draw(self, surface: pygame.Surface) -> None:
        x, y = grid_to_pixel_center(self.col, self.row)
        pygame.draw.circle(surface, self.color, (x, y), self.radius)


@dataclass
class Wall:
    col: int
    row: int
    angle: int
    kind: str

    def draw(self, surface: pygame.Surface) -> None:
        if self.kind == "L":
            self._draw_L(surface)
        elif self.kind == "S":
            self._draw_S(surface)

    def _draw_L(self, surface: pygame.Surface) -> None:
        rect = cell_rect(self.col, self.row)
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

    def _draw_S(self, surface: pygame.Surface) -> None:
        c = self.col
        r = self.row

        if self.angle in (0, 180):
            rect_left = cell_rect(c, r)
            rect_right = cell_rect(c + 1, r)
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
            rect_top = cell_rect(c, r)
            rect_bottom = cell_rect(c, r + 1)
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
