import pygame
from config import CENTER_BLOCK_COLOR, WALL_COLOR, WALL_THICKNESS
from board import Board, Objective
from entities import Cell, cell_rect


class BoardRenderer:
    def __init__(self, board: Board) -> None:
        self.board = board

    def _draw_objective(
        self,
        surface: pygame.Surface,
        screen_width: int,
        screen_height: int,
        obj: Objective,
    ) -> None:
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
        for (col, row) in self.board.center_block_cells:
            rect = cell_rect(col, row, screen_width, screen_height)
            pygame.draw.rect(surface, CENTER_BLOCK_COLOR, rect)

        for col in range(self.board.cols):
            for row in range(self.board.rows):
                Cell(col, row).draw(surface, screen_width, screen_height)

        for wall in self.board.walls:
            wall.draw(surface, screen_width, screen_height)

        for obj in self.board.objectives:
            self._draw_objective(surface, screen_width, screen_height, obj)

        border_rect = pygame.Rect(0, 0, screen_width, screen_height)
        pygame.draw.rect(surface, WALL_COLOR, border_rect, WALL_THICKNESS)
