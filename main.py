import pygame
import random

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
    SAND_TIMER_DURATION,
    HUD_TEXT_COLOR,
    HUD_BG_COLOR,
    MENU_BG_COLOR,
    MENU_TITLE_COLOR,
    MENU_SUBTITLE_COLOR,
    MENU_BUTTON_COLOR,
    MENU_BUTTON_HOVER_COLOR,
    MENU_BUTTON_TEXT_COLOR,
)
from board import Board
from board_render import BoardRenderer
from entities import Robot, grid_to_pixel_center, cell_rect
from game_phase import GamePhase
from player import Player


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
        self.board_renderer = BoardRenderer(self.board)

        width, height = self.screen.get_size()
        board_width = int(width * 0.75)
        board_height = height
        cell_w, cell_h = get_cell_size(board_width, board_height)
        robot_radius = min(cell_w, cell_h) // 3

        self.robots: list[Robot] = []
        self._spawn_random_robots(4, robot_radius)

        self.players: list[Player] = []
        self.num_players: int = 2
        self.current_player_selection: int = 0
        self.active_player_index: int | None = None

        self.selected_robot: Robot | None = None
        self.reachable_cells: set[tuple[int, int]] = set()
        self.current_objective = None
        self.remaining_objectives = self.board.objectives[:]
        self.target_robot_index: int | None = None
        self.move_count: int = 0
        self.round_index: int = 1

        self.font = pygame.font.SysFont(None, 28)
        self.big_font = pygame.font.SysFont(None, 42)
        self.title_font = pygame.font.SysFont(None, 96)
        self.subtitle_font = pygame.font.SysFont(None, 32)

        self.state: GamePhase = GamePhase.MAIN_MENU
        self.sand_timer: float = SAND_TIMER_DURATION
        self.bidding_started: bool = False
        self.bid_order: list[int] = []
        self.current_solver_index: int = 0

    def _spawn_random_robots(self, count: int, radius: int) -> None:
        available_colors = ROBOT_COLORS[:]
        random.shuffle(available_colors)
        occupied = set(self.board.blocked_cells)
        occupied.update((obj.col, obj.row) for obj in self.board.objectives)
        while len(self.robots) < count:
            col = random.randint(0, GRID_COLS - 1)
            row = random.randint(0, GRID_ROWS - 1)
            if (col, row) in occupied:
                continue
            color = available_colors[len(self.robots)]
            robot = Robot(col=col, row=row, radius=radius, color=color)
            self.robots.append(robot)
            occupied.add((col, row))

    def _robot_index_for_color(self, color: tuple[int, int, int]) -> int | None:
        for i, r in enumerate(self.robots):
            if r.color == color:
                return i
        return None

    def _pick_next_objective(self) -> bool:
        if not self.remaining_objectives:
            return False
        self.current_objective = random.choice(self.remaining_objectives)
        self.remaining_objectives.remove(self.current_objective)
        if self.current_objective.is_multicolor:
            self.target_robot_index = None
        else:
            self.target_robot_index = self._robot_index_for_color(self.current_objective.color)
        return True

    def _start_new_round(self) -> None:
        self.move_count = 0
        self.selected_robot = None
        self.reachable_cells.clear()
        self.sand_timer = SAND_TIMER_DURATION
        self.bidding_started = False
        self.active_player_index = None
        self.bid_order = []
        self.current_solver_index = 0
        for p in self.players:
            p.bid = None
        if not self._pick_next_objective():
            self.state = GamePhase.GAME_OVER
            self.current_objective = None
            self.active_player_index = None
            return
        self.state = GamePhase.BIDDING

    def _end_bidding(self) -> None:
        if self.state != GamePhase.BIDDING:
            return
        bidders = [(p.bid, i) for i, p in enumerate(self.players) if p.bid is not None]
        if not bidders:
            self.sand_timer = SAND_TIMER_DURATION
            self.bidding_started = False
            for p in self.players:
                p.bid = None
            return
        bidders.sort(key=lambda x: x[0])
        self.bid_order = [idx for _, idx in bidders]
        self.current_solver_index = 0
        self.active_player_index = self.bid_order[0]
        self.state = GamePhase.SOLVING
        self.move_count = 0
        self.selected_robot = None
        self.reachable_cells.clear()
        self.bidding_started = False

    def _fail_current_solver(self) -> None:
        if not self.bid_order:
            self.round_index += 1
            self._start_new_round()
            return
        if self.current_solver_index + 1 < len(self.bid_order):
            self.current_solver_index += 1
            self.active_player_index = self.bid_order[self.current_solver_index]
            self.move_count = 0
            self.selected_robot = None
            self.reachable_cells.clear()
        else:
            self.round_index += 1
            self._start_new_round()

    def _handle_victory(self) -> None:
        if self.active_player_index is not None:
            player = self.players[self.active_player_index]
            player.score += 1
        self.round_index += 1
        self._start_new_round()

    def _confirm_players_and_start(self) -> None:
        self.players = [Player(name=f"J{i + 1}") for i in range(self.num_players)]
        self.current_player_selection = 0
        self.remaining_objectives = self.board.objectives[:]
        self.round_index = 1
        for p in self.players:
            p.score = 0
        self._start_new_round()

    def _reset_to_main_menu(self) -> None:
        self.remaining_objectives = self.board.objectives[:]
        self.round_index = 1
        for p in self.players:
            p.score = 0
            p.bid = None
        self.current_objective = None
        self.active_player_index = None
        self.state = GamePhase.MAIN_MENU

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

    def _get_robot_at(self, col: int, row: int) -> Robot | None:
        for robot in self.robots:
            if robot.col == col and robot.row == row:
                return robot
        return None

    def _get_main_menu_buttons(self, width: int, height: int) -> dict[str, pygame.Rect]:
        button_width = width // 4
        button_height = max(60, height // 12)
        center_x = width // 2
        start_y = int(height * 0.55)
        spacing = button_height + 20
        play_rect = pygame.Rect(0, 0, button_width, button_height)
        play_rect.center = (center_x, start_y)
        quit_rect = pygame.Rect(0, 0, button_width, button_height)
        quit_rect.center = (center_x, start_y + spacing)
        return {"play": play_rect, "quit": quit_rect}

    def _draw_menu_button(self, rect: pygame.Rect, text: str, hovered: bool) -> None:
        base_color = MENU_BUTTON_HOVER_COLOR if hovered else MENU_BUTTON_COLOR
        border_color = MENU_TITLE_COLOR
        pygame.draw.rect(self.screen, base_color, rect, border_radius=12)
        pygame.draw.rect(self.screen, border_color, rect, 2, border_radius=12)
        font = self.big_font if rect.height >= 60 else self.font
        text_surf = font.render(text, True, MENU_BUTTON_TEXT_COLOR)
        text_rect = text_surf.get_rect(center=rect.center)
        self.screen.blit(text_surf, text_rect)

    def _draw_main_menu(self, width: int, height: int) -> None:
        self.screen.fill(MENU_BG_COLOR)
        title_surf = self.title_font.render("Rasende Roboter", True, MENU_TITLE_COLOR)
        title_rect = title_surf.get_rect(center=(width // 2, int(height * 0.28)))
        self.screen.blit(title_surf, title_rect)

        mouse_x, mouse_y = pygame.mouse.get_pos()
        buttons = self._get_main_menu_buttons(width, height)
        play_rect = buttons["play"]
        quit_rect = buttons["quit"]
        self._draw_menu_button(play_rect, "Jouer", play_rect.collidepoint(mouse_x, mouse_y))
        self._draw_menu_button(quit_rect, "Quitter", quit_rect.collidepoint(mouse_x, mouse_y))
        hint_surf = self.font.render("Entrée ou clic sur Jouer pour commencer", True, MENU_SUBTITLE_COLOR)
        hint_rect = hint_surf.get_rect(center=(width // 2, int(height * 0.85)))
        self.screen.blit(hint_surf, hint_rect)

    def _get_player_select_layout(self, width: int, height: int) -> dict[str, pygame.Rect]:
        center_x = width // 2
        number_rect = pygame.Rect(0, 0, width // 6, height // 10)
        number_rect.center = (center_x, int(height * 0.45))
        button_side = number_rect.height
        minus_rect = pygame.Rect(0, 0, button_side, button_side)
        minus_rect.centery = number_rect.centery
        minus_rect.right = number_rect.left - 20
        plus_rect = pygame.Rect(0, 0, button_side, button_side)
        plus_rect.centery = number_rect.centery
        plus_rect.left = number_rect.right + 20
        start_width = width // 4
        start_height = max(60, height // 14)
        start_rect = pygame.Rect(0, 0, start_width, start_height)
        start_rect.center = (center_x, int(height * 0.7))
        back_rect = pygame.Rect(0, 0, 120, 40)
        back_rect.topleft = (40, 40)
        return {
            "number": number_rect,
            "minus": minus_rect,
            "plus": plus_rect,
            "start": start_rect,
            "back": back_rect,
        }

    def _draw_player_select_screen(self, width: int, height: int) -> None:
        self.screen.fill(MENU_BG_COLOR)
        title_surf = self.title_font.render("Sélection des joueurs", True, MENU_TITLE_COLOR)
        title_rect = title_surf.get_rect(center=(width // 2, int(height * 0.2)))
        self.screen.blit(title_surf, title_rect)
        subtitle_surf = self.subtitle_font.render("Choisis le nombre de participants", True, MENU_SUBTITLE_COLOR)
        subtitle_rect = subtitle_surf.get_rect(center=(width // 2, int(height * 0.28)))
        self.screen.blit(subtitle_surf, subtitle_rect)
        layout = self._get_player_select_layout(width, height)
        number_rect = layout["number"]
        minus_rect = layout["minus"]
        plus_rect = layout["plus"]
        start_rect = layout["start"]
        back_rect = layout["back"]
        mouse_x, mouse_y = pygame.mouse.get_pos()
        pygame.draw.rect(self.screen, MENU_BUTTON_COLOR, number_rect, border_radius=18)
        pygame.draw.rect(self.screen, MENU_TITLE_COLOR, number_rect, 2, border_radius=18)
        num_text = self.title_font.render(str(self.num_players), True, MENU_BUTTON_TEXT_COLOR)
        num_rect = num_text.get_rect(center=(number_rect.centerx, number_rect.centery - 10))
        self.screen.blit(num_text, num_rect)
        label_text = self.font.render("joueur" if self.num_players == 1 else "joueurs", True, MENU_BUTTON_TEXT_COLOR)
        label_rect = label_text.get_rect(center=(number_rect.centerx, number_rect.centery + number_rect.height // 4))
        self.screen.blit(label_text, label_rect)
        self._draw_menu_button(minus_rect, "−", minus_rect.collidepoint(mouse_x, mouse_y))
        self._draw_menu_button(plus_rect, "+", plus_rect.collidepoint(mouse_x, mouse_y))
        self._draw_menu_button(start_rect, "Commencer", start_rect.collidepoint(mouse_x, mouse_y))
        self._draw_menu_button(back_rect, "Retour", back_rect.collidepoint(mouse_x, mouse_y))
        if self.num_players > 0:
            chip_size = 32
            spacing = 12
            total_width = self.num_players * chip_size + (self.num_players - 1) * spacing
            start_x = width // 2 - total_width // 2
            y = int(height * 0.55)
            for i in range(self.num_players):
                rect = pygame.Rect(start_x + i * (chip_size + spacing), y, chip_size, chip_size)
                color = ROBOT_COLORS[i % len(ROBOT_COLORS)]
                pygame.draw.rect(self.screen, color, rect, border_radius=16)
                pygame.draw.rect(self.screen, MENU_TITLE_COLOR, rect, 1, border_radius=16)
                label = self.font.render(str(i + 1), True, MENU_BUTTON_TEXT_COLOR)
                label_rect = label.get_rect(center=rect.center)
                self.screen.blit(label, label_rect)

    def _draw_game_over(self, width: int, height: int) -> None:
        self.screen.fill(MENU_BG_COLOR)
        title_surf = self.title_font.render("Fin de partie", True, MENU_TITLE_COLOR)
        title_rect = title_surf.get_rect(center=(width // 2, int(height * 0.2)))
        self.screen.blit(title_surf, title_rect)
        if not self.players:
            info = "Aucun joueur"
        else:
            max_score = max(p.score for p in self.players)
            winners = [p for p in self.players if p.score == max_score]
            if len(winners) == 1:
                info = f"Vainqueur : {winners[0].name} ({max_score} pts)"
            else:
                names = ", ".join(p.name for p in winners)
                info = f"Vainqueurs : {names} ({max_score} pts)"
        info_surf = self.big_font.render(info, True, MENU_SUBTITLE_COLOR)
        info_rect = info_surf.get_rect(center=(width // 2, int(height * 0.32)))
        self.screen.blit(info_surf, info_rect)
        y = int(height * 0.42)
        header = self.font.render("Scores :", True, MENU_TITLE_COLOR)
        header_rect = header.get_rect(center=(width // 2, y))
        self.screen.blit(header, header_rect)
        y += 28
        for p in sorted(self.players, key=lambda pl: pl.score, reverse=True):
            line = f"{p.name} : {p.score} pts"
            surf = self.font.render(line, True, MENU_BUTTON_TEXT_COLOR)
            rect = surf.get_rect(center=(width // 2, y))
            self.screen.blit(surf, rect)
            y += 24
        hint_surf = self.font.render("Entrée / Espace : revenir au menu principal", True, MENU_SUBTITLE_COLOR)
        hint_rect = hint_surf.get_rect(center=(width // 2, int(height * 0.85)))
        self.screen.blit(hint_surf, hint_rect)

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif self.state == GamePhase.MAIN_MENU:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.state = GamePhase.CHOOSE_PLAYERS
                elif self.state == GamePhase.CHOOSE_PLAYERS:
                    if event.key in (pygame.K_LEFT, pygame.K_DOWN):
                        self.num_players = max(1, self.num_players - 1)
                    elif event.key in (pygame.K_RIGHT, pygame.K_UP):
                        self.num_players = min(8, self.num_players + 1)
                    elif event.key == pygame.K_RETURN:
                        self._confirm_players_and_start()
                elif self.state == GamePhase.BIDDING:
                    if event.key == pygame.K_RIGHT and self.players:
                        self.current_player_selection = (self.current_player_selection + 1) % len(self.players)
                    elif event.key == pygame.K_LEFT and self.players:
                        self.current_player_selection = (self.current_player_selection - 1) % len(self.players)
                    elif pygame.K_1 <= event.key <= pygame.K_9 and self.players:
                        value = event.key - pygame.K_0
                        self.players[self.current_player_selection].bid = value
                        if not self.bidding_started:
                            self.bidding_started = True
                            self.sand_timer = SAND_TIMER_DURATION
                    elif event.key == pygame.K_RETURN:
                        self._end_bidding()
                elif self.state == GamePhase.GAME_OVER:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self._reset_to_main_menu()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == GamePhase.MAIN_MENU:
                    width, height = self.screen.get_size()
                    buttons = self._get_main_menu_buttons(width, height)
                    if buttons["play"].collidepoint(event.pos):
                        self.state = GamePhase.CHOOSE_PLAYERS
                    elif buttons["quit"].collidepoint(event.pos):
                        self.running = False
                elif self.state == GamePhase.CHOOSE_PLAYERS:
                    width, height = self.screen.get_size()
                    layout = self._get_player_select_layout(width, height)
                    if layout["minus"].collidepoint(event.pos):
                        self.num_players = max(1, self.num_players - 1)
                    elif layout["plus"].collidepoint(event.pos):
                        self.num_players = min(8, self.num_players + 1)
                    elif layout["start"].collidepoint(event.pos):
                        self._confirm_players_and_start()
                    elif layout["back"].collidepoint(event.pos):
                        self.state = GamePhase.MAIN_MENU
                elif self.state == GamePhase.SOLVING:
                    width, height = self.screen.get_size()
                    board_width = int(width * 0.75)
                    board_height = height
                    cell_w, cell_h = get_cell_size(board_width, board_height)
                    x, y = event.pos
                    if x >= board_width:
                        continue
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

    def update(self, dt: float) -> None:
        if self.state == GamePhase.BIDDING:
            if self.bidding_started:
                self.sand_timer -= dt
                if self.sand_timer <= 0:
                    self._end_bidding()
        elif self.state == GamePhase.SOLVING and self.current_objective is not None:
            current_player = None
            if self.active_player_index is not None and 0 <= self.active_player_index < len(self.players):
                current_player = self.players[self.active_player_index]
            if self.target_robot_index is not None:
                target_robot = self.robots[self.target_robot_index]
                success = (target_robot.col, target_robot.row) == (self.current_objective.col, self.current_objective.row)
            else:
                success = any(
                    (r.col, r.row) == (self.current_objective.col, self.current_objective.row)
                    for r in self.robots
                )
            if success:
                if current_player is None or current_player.bid is None or self.move_count <= current_player.bid:
                    self._handle_victory()
                else:
                    self._fail_current_solver()
            else:
                if current_player is not None and current_player.bid is not None and self.move_count > current_player.bid:
                    self._fail_current_solver()

    def _draw_target_center(self, board_width: int, board_height: int) -> None:
        if self.current_objective is None:
            return
        center_x = board_width // 2
        center_y = board_height // 2
        cell_w, cell_h = get_cell_size(board_width, board_height)
        radius_outer = min(cell_w, cell_h) // 3
        pygame.draw.circle(self.screen, TARGET_CENTER_COLOR, (center_x, center_y), radius_outer)
        size = radius_outer - 12
        color = self.current_objective.color
        symbol = self.current_objective.symbol
        if symbol == "diamond":
            points = [
                (center_x, center_y - size),
                (center_x + size, center_y),
                (center_x, center_y + size),
                (center_x - size, center_y),
            ]
            pygame.draw.polygon(self.screen, color, points)
        elif symbol == "square":
            rect = pygame.Rect(0, 0, size * 2, size * 2)
            rect.center = (center_x, center_y)
            pygame.draw.rect(self.screen, color, rect)
        elif symbol == "circle":
            pygame.draw.circle(self.screen, color, (center_x, center_y), size)
        elif symbol == "triangle":
            points = [
                (center_x, center_y - size),
                (center_x + size, center_y + size),
                (center_x - size, center_y + size),
            ]
            pygame.draw.polygon(self.screen, color, points)

    def _draw_goal_cell_highlight(self, board_width: int, board_height: int) -> None:
        if self.current_objective is None:
            return
        rect = cell_rect(self.current_objective.col, self.current_objective.row, board_width, board_height)
        pygame.draw.rect(self.screen, GOAL_OUTLINE_COLOR, rect, 3)

    def _draw_side_panel(self, width: int, height: int, board_width: int) -> None:
        panel_rect = pygame.Rect(board_width, 0, width - board_width, height)
        pygame.draw.rect(self.screen, HUD_BG_COLOR, panel_rect)
        header_rect = panel_rect.copy()
        header_rect.height = 80
        pygame.draw.rect(self.screen, MENU_BUTTON_COLOR, header_rect)
        if self.state == GamePhase.BIDDING:
            phase_label = "Annonce"
        elif self.state == GamePhase.SOLVING:
            phase_label = "Solution"
        else:
            phase_label = ""
        title_text = f"Manche {self.round_index}"
        phase_text = f"Phase : {phase_label}" if phase_label else ""
        title_surf = self.big_font.render(title_text, True, MENU_BUTTON_TEXT_COLOR)
        title_rect = title_surf.get_rect(midleft=(header_rect.x + 18, header_rect.y + 24))
        self.screen.blit(title_surf, title_rect)
        if phase_text:
            phase_surf = self.font.render(phase_text, True, MENU_BUTTON_TEXT_COLOR)
            phase_rect = phase_surf.get_rect(midleft=(header_rect.x + 18, header_rect.y + 52))
            self.screen.blit(phase_surf, phase_rect)
        y = header_rect.bottom + 12
        if self.current_objective is not None:
            target_rect = pygame.Rect(panel_rect.x + 12, y, panel_rect.width - 24, 80)
            pygame.draw.rect(self.screen, TARGET_CENTER_COLOR, target_rect, border_radius=12)
            pygame.draw.rect(self.screen, MENU_BUTTON_COLOR, target_rect, 1, border_radius=12)
            circle_x = target_rect.x + 28
            circle_y = target_rect.centery
            pygame.draw.circle(self.screen, self.current_objective.color, (circle_x, circle_y), 12)
            pygame.draw.circle(self.screen, MENU_BUTTON_COLOR, (circle_x, circle_y), 12, 2)
            label_surf = self.font.render("Objectif actuel", True, HUD_TEXT_COLOR)
            label_rect = label_surf.get_rect(topleft=(circle_x + 24, target_rect.y + 10))
            self.screen.blit(label_surf, label_rect)
            info_surf = self.font.render("Atteindre la case correspondante sur le plateau", True, HUD_TEXT_COLOR)
            info_rect = info_surf.get_rect(topleft=(circle_x + 24, target_rect.y + 36))
            self.screen.blit(info_surf, info_rect)
            y = target_rect.bottom + 16
        if self.state == GamePhase.BIDDING:
            timer_rect = pygame.Rect(panel_rect.x + 12, y, panel_rect.width - 24, 72)
            pygame.draw.rect(self.screen, (255, 255, 255), timer_rect, border_radius=12)
            pygame.draw.rect(self.screen, MENU_BUTTON_COLOR, timer_rect, 1, border_radius=12)
            seconds = max(0, int(self.sand_timer if self.bidding_started else SAND_TIMER_DURATION))
            label = "Temps restant" if self.bidding_started else "En attente de la 1ère annonce"
            timer_label = self.font.render(label, True, HUD_TEXT_COLOR)
            timer_label_rect = timer_label.get_rect(midtop=(timer_rect.centerx, timer_rect.y + 8))
            self.screen.blit(timer_label, timer_label_rect)
            timer_value = self.big_font.render(f"{seconds} s", True, HUD_TEXT_COLOR)
            timer_value_rect = timer_value.get_rect(midbottom=(timer_rect.centerx, timer_rect.bottom - 8))
            self.screen.blit(timer_value, timer_value_rect)
            y = timer_rect.bottom + 18
        players_title = self.font.render("Joueurs", True, HUD_TEXT_COLOR)
        self.screen.blit(players_title, (panel_rect.x + 16, y))
        y += 26
        row_height = 56
        for i, p in enumerate(self.players):
            if y + row_height > panel_rect.bottom - 150:
                break
            row_rect = pygame.Rect(panel_rect.x + 12, y, panel_rect.width - 24, row_height)
            base_color = (245, 245, 245)
            highlight_color = base_color
            if self.state == GamePhase.BIDDING and i == self.current_player_selection:
                highlight_color = MENU_BUTTON_COLOR
            elif self.state == GamePhase.SOLVING and self.active_player_index is not None and i == self.active_player_index:
                highlight_color = MENU_BUTTON_HOVER_COLOR
            pygame.draw.rect(self.screen, highlight_color, row_rect, border_radius=10)
            pygame.draw.rect(self.screen, MENU_BUTTON_COLOR, row_rect, 1, border_radius=10)
            text_color = MENU_BUTTON_TEXT_COLOR if highlight_color != base_color else HUD_TEXT_COLOR
            name_surf = self.font.render(p.name, True, text_color)
            name_rect = name_surf.get_rect(topleft=(row_rect.x + 14, row_rect.y + 6))
            self.screen.blit(name_surf, name_rect)
            score_text = f"{p.score} pt" if p.score == 1 else f"{p.score} pts"
            score_surf = self.font.render(f"Score : {score_text}", True, text_color)
            score_rect = score_surf.get_rect(topleft=(row_rect.x + 14, row_rect.y + 30))
            self.screen.blit(score_surf, score_rect)
            bid_str = "-" if p.bid is None else str(p.bid)
            bid_surf = self.font.render(f"Annonce : {bid_str}", True, text_color)
            bid_rect = bid_surf.get_rect(topright=(row_rect.right - 14, row_rect.y + 18))
            self.screen.blit(bid_surf, bid_rect)
            y += row_height + 8
        y += 12
        controls_height = 130
        if y + controls_height > panel_rect.bottom - 12:
            controls_height = max(80, panel_rect.bottom - 12 - y)
        controls_rect = pygame.Rect(panel_rect.x + 12, y, panel_rect.width - 24, controls_height)
        pygame.draw.rect(self.screen, (255, 255, 255), controls_rect, border_radius=10)
        pygame.draw.rect(self.screen, MENU_BUTTON_COLOR, controls_rect, 1, border_radius=10)
        cx = controls_rect.x + 14
        cy = controls_rect.y + 12
        if self.state == GamePhase.BIDDING:
            header = self.font.render("Annonces", True, HUD_TEXT_COLOR)
            self.screen.blit(header, (cx, cy))
            cy += 26
            lines = [
                "<- / -> : changer de joueur",
                "1–9 : saisir une annonce",
                "Entrée : lancer la résolution",
            ]
        else:
            header = self.font.render("Solution", True, HUD_TEXT_COLOR)
            self.screen.blit(header, (cx, cy))
            cy += 26
            lines = [f"Coups joués : {self.move_count}"]
            active = self.players[self.active_player_index] if self.active_player_index is not None and 0 <= self.active_player_index < len(self.players) else None
            if active is not None and active.bid is not None:
                remaining = active.bid - self.move_count
                lines.append(f"Annonce de {active.name} : {active.bid} coups")
                lines.append(f"Restants : {remaining} coups")
            lines.append("Clique sur un robot puis")
            lines.append("sur une case en surbrillance")
        for line in lines:
            if cy + 22 > controls_rect.bottom - 6:
                break
            text_surf = self.font.render(line, True, HUD_TEXT_COLOR)
            self.screen.blit(text_surf, (cx, cy))
            cy += 22

    def draw(self) -> None:
        width, height = self.screen.get_size()
        if self.state == GamePhase.MAIN_MENU:
            self._draw_main_menu(width, height)
            pygame.display.flip()
            return
        if self.state == GamePhase.CHOOSE_PLAYERS:
            self._draw_player_select_screen(width, height)
            pygame.display.flip()
            return
        if self.state == GamePhase.GAME_OVER:
            self._draw_game_over(width, height)
            pygame.display.flip()
            return
        self.screen.fill(BG_COLOR)
        board_width = int(width * 0.75)
        board_height = height
        self.board_renderer.draw(self.screen, board_width, board_height)
        self._draw_goal_cell_highlight(board_width, board_height)
        if self.target_robot_index is not None and 0 <= self.target_robot_index < len(self.robots):
            for idx, robot in enumerate(self.robots):
                robot.draw(self.screen, board_width, board_height)
                if idx == self.target_robot_index:
                    x, y = grid_to_pixel_center(robot.col, robot.row, board_width, board_height)
                    cell_w, cell_h = get_cell_size(board_width, board_height)
                    r = min(cell_w, cell_h) // 3 + 4
                    pygame.draw.circle(self.screen, (0, 0, 0), (x, y), r, 2)
        else:
            for robot in self.robots:
                robot.draw(self.screen, board_width, board_height)
        for col, row in self.reachable_cells:
            x, y = grid_to_pixel_center(col, row, board_width, board_height)
            cell_w, cell_h = get_cell_size(board_width, board_height)
            radius = min(cell_w, cell_h) // 6
            pygame.draw.circle(self.screen, SELECT_TARGET_COLOR, (x, y), radius)
        self._draw_target_center(board_width, board_height)
        self._draw_side_panel(width, height, board_width)
        pygame.display.flip()


if __name__ == "__main__":
    Game().run()
