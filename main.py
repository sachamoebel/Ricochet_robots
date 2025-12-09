import pygame
import random
from dataclasses import dataclass

from config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BG_COLOR,
    GRID_COLS,
    GRID_ROWS,
    SELECT_TARGET_COLOR,
    ROBOT_COLORS,
    TARGET_CENTER_COLOR,
    GOAL_OUTLINE_COLOR,
    get_cell_size,
)
from board import Board
from entities import Robot, grid_to_pixel_center, cell_rect


@dataclass
class Target:
    robot_index: int
    goal_col: int
    goal_row: int


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.RESIZABLE,
        )
        pygame.display.set_caption("Rasende Roboter")
        self.clock = pygame.time.Clock()
        self.running = True

        self.board = Board(GRID_COLS, GRID_ROWS)

        width, height = self.screen.get_size()
        cell_w, cell_h = get_cell_size(width, height)
        robot_radius = min(cell_w, cell_h) // 3

        self.robots: list[Robot] = []
        self._spawn_random_robots(4, robot_radius)

        self.selected_robot: Robot | None = None
        self.reachable_cells: set[tuple[int, int]] = set()
        self.target: Target = self._create_random_target()
        self.move_count: int = 0
        self.font = pygame.font.SysFont(None, 32)

    def _spawn_random_robots(self, count: int, radius: int) -> None:
        available_colors = ROBOT_COLORS[:]
        random.shuffle(available_colors)
        occupied = set(self.board.blocked_cells)
        while len(self.robots) < count:
            col = random.randint(0, GRID_COLS - 1)
            row = random.randint(0, GRID_ROWS - 1)
            if (col, row) in occupied:
                continue
            color = available_colors[len(self.robots)]
            robot = Robot(col=col, row=row, radius=radius, color=color)
            self.robots.append(robot)
            occupied.add((col, row))

    def _create_random_target(self) -> Target:
        robot_index = random.randrange(len(self.robots))
        robot_cells = {(r.col, r.row) for r in self.robots}
        forbidden = set(self.board.center_block_cells) | robot_cells
        while True:
            col = random.randint(0, GRID_COLS - 1)
            row = random.randint(0, GRID_ROWS - 1)
            if (col, row) in forbidden:
                continue
            return Target(robot_index=robot_index, goal_col=col, goal_row=row)

    def run(self) -> None:
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)
        pygame.quit()

    def _get_robot_at(self, col: int, row: int) -> Robot | None:
        for robot in self.robots:
            if robot.col == col and robot.row == row:
                return robot
        return None

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                width, height = self.screen.get_size()
                cell_w, cell_h = get_cell_size(width, height)
                x, y = event.pos
                col = x // cell_w
                row = y // cell_h
                if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
                    robot = self._get_robot_at(col, row)
                    if robot is not None:
                        self.selected_robot = robot
                        occupied = {
                            (r.col, r.row)
                            for r in self.robots
                            if r is not self.selected_robot
                        }
                        self.reachable_cells = self.board.get_move_targets(
                            robot.col,
                            robot.row,
                            occupied,
                        )
                    elif self.selected_robot is not None and (col, row) in self.reachable_cells:
                        self.selected_robot.col = col
                        self.selected_robot.row = row
                        self.move_count += 1
                        self.selected_robot = None
                        self.reachable_cells.clear()
                    else:
                        self.selected_robot = None
                        self.reachable_cells.clear()

            elif event.type == pygame.VIDEORESIZE:
                # On NE rappelle PAS set_mode ici.
                # On laisse juste Pygame redimensionner la surface.
                # Tout le rendu utilise self.screen.get_size() à chaque frame.
                pass

    def update(self) -> None:
        pass

    def _draw_target_center(self, width: int, height: int) -> None:
        center_x = width // 2
        center_y = height // 2
        color = self.robots[self.target.robot_index].color
        cell_w, cell_h = get_cell_size(width, height)
        radius_outer = min(cell_w, cell_h) // 3
        radius_inner = radius_outer // 2
        pygame.draw.circle(self.screen, TARGET_CENTER_COLOR, (center_x, center_y), radius_outer)
        pygame.draw.circle(self.screen, color, (center_x, center_y), radius_inner)

    def _draw_goal_cell(self, width: int, height: int) -> None:
        rect = cell_rect(self.target.goal_col, self.target.goal_row, width, height)
        pygame.draw.rect(self.screen, GOAL_OUTLINE_COLOR, rect, 3)

    def _draw_hud(self) -> None:
        text = f"Coups: {self.move_count} | Robot cible: {self.target.robot_index + 1}"
        surf = self.font.render(text, True, (255, 255, 255))
        self.screen.blit(surf, (10, 10))

    def draw(self) -> None:
        width, height = self.screen.get_size()
        self.screen.fill(BG_COLOR)

        self.board.draw(self.screen, width, height)
        self._draw_goal_cell(width, height)

        for idx, robot in enumerate(self.robots):
            robot.draw(self.screen, width, height)
            if idx == self.target.robot_index:
                x, y = grid_to_pixel_center(robot.col, robot.row, width, height)
                cell_w, cell_h = get_cell_size(width, height)
                r = min(cell_w, cell_h) // 3 + 4
                pygame.draw.circle(self.screen, (255, 255, 255), (x, y), r, 2)

        for col, row in self.reachable_cells:
            x, y = grid_to_pixel_center(col, row, width, height)
            cell_w, cell_h = get_cell_size(width, height)
            radius = min(cell_w, cell_h) // 6
            pygame.draw.circle(self.screen, SELECT_TARGET_COLOR, (x, y), radius)

        self._draw_target_center(width, height)
        self._draw_hud()
        pygame.display.flip()


if __name__ == "__main__":
    Game().run()
