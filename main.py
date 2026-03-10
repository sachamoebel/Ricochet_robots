import math
import pygame
import random
import time
from solver import RicochetSolver
from solver_thread import SolverThread

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BG_COLOR, GRID_COLS, GRID_ROWS,
    SELECT_TARGET_COLOR, ROBOT_COLORS, TARGET_CENTER_COLOR,
    GOAL_OUTLINE_COLOR, get_cell_size, SAND_TIMER_DURATION,
    HUD_TEXT_COLOR, HUD_BG_COLOR, MENU_BG_COLOR, MENU_TITLE_COLOR,
    MENU_SUBTITLE_COLOR, MENU_BUTTON_COLOR, MENU_BUTTON_HOVER_COLOR,
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
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)        
        pygame.display.set_caption("Rasende Roboter - Bitboard Edition")
        self.clock = pygame.time.Clock()
        self.running = True

        # --- Initialisation du Plateau Bitboard ---
        self.board = Board(GRID_COLS, GRID_ROWS)
        self.board_renderer = BoardRenderer(self.board)

        # --- État Binaire ---
        self.occupied_mask = 0  # Représentation 256 bits des robots
        
        self.robots: list[Robot] = []
        width, height = self.screen.get_size()
        cell_w, cell_h = get_cell_size(int(width * 0.75), height)
        self._spawn_random_robots(4, min(cell_w, cell_h) // 3)

        self.solver_thread = None
        self.solver_bid = None # Le score que l'IA a trouvé
        self.solver_path = None

        # Joueurs et Game Loop
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

        self.scroll_y = 0 
        self.max_scroll_y = 0 

        # Polices
        self.font = pygame.font.SysFont(None, 28)
        self.big_font = pygame.font.SysFont(None, 42)
        self.title_font = pygame.font.SysFont(None, 96)
        self.subtitle_font = pygame.font.SysFont(None, 32)

        self.state: GamePhase = GamePhase.MAIN_MENU
        self.sand_timer: float = SAND_TIMER_DURATION
        self.bidding_started: bool = False
        self.bid_order: list[int] = []

        # main.py additions


    def _trigger_ai_demonstration(self):
        """ Lance l'animation automatique basée sur le chemin trouvé par l'IA """
        if not self.solver_path:
            return

        if self.saved_robot_positions is not None :
            for i, (col, row) in enumerate(self.saved_robot_positions):
                self.robots[i].col = col
                self.robots[i].row = row
                self._update_occupied_mask()
                
        self.state = GamePhase.SHOWING_SOLUTION 
        self.solution_path = self.solver_path
        self.solution_step = 0
        self.solution_timer = 0

    def update(self, dt: float) -> None:
        if self.solver_thread and self.solver_thread.found:
            if self.solver_bid is None: # Si on n'a pas encore enregistré le résultat
                self.solver_path = self.solver_thread.result
                self.solver_bid = len(self.solver_path) if self.solver_path else 99
                print(f"L'IA a trouvé une solution en {self.solver_bid} coups !")

        if self.state == GamePhase.BIDDING and self.bidding_started:
            self.sand_timer -= dt
            if self.sand_timer <= 0: self._end_bidding()
            
        elif self.state == GamePhase.SOLVING and self.current_objective:
            obj_bit = 1 << (self.current_objective.row * GRID_COLS + self.current_objective.col)
            
            # Vérification bitwise de la victoire
            if self.target_robot_index is not None:
                r = self.robots[self.target_robot_index]
                success = (1 << (r.row * GRID_COLS + r.col)) == obj_bit
            else: # Multicolore
                success = bool(self.occupied_mask & obj_bit)

            if success:
                curr_p = self.players[self.active_player_index]
                if self.move_count <= curr_p.bid: self._handle_victory()
                else: self._fail_current_solver()
            elif self.active_player_index is not None:
                if self.move_count > self.players[self.active_player_index].bid:
                    self._fail_current_solver()
        
        if self.state == GamePhase.SHOWING_SOLUTION:
            self.solution_timer += dt
            self.active_player_index = None
            if self.solution_timer > 1.5:  # Speed of animation (0.8 seconds per move)
                self.solution_timer = 0
                if self.solution_step < len(self.solution_path):
                    robot_idx, direction = self.solution_path[self.solution_step]
                    
                    r = self.robots[robot_idx]

                    occ_mask = 0
                    for rb in self.robots: occ_mask |= (1 << (rb.row * GRID_COLS + rb.col))
                    new_idx = self.solver_obj.get_destination(r.row * GRID_COLS + r.col, direction, occ_mask ^ (1 << (r.row * GRID_COLS + r.col)))
                    r.col, r.row = new_idx % GRID_COLS, new_idx // GRID_COLS
                    
                    self.solution_step += 1
                else:
                    time.sleep(2    ) 
                    self._handle_victory() 


    # --- MÉTHODES CORE BITBOARD ---

    def _update_occupied_mask(self) -> None:
        """Synchronise le masque binaire avec les positions des objets Robot."""
        self.occupied_mask = 0
        for r in self.robots:
            self.occupied_mask |= (1 << (r.row * GRID_COLS + r.col))

    def _spawn_random_robots(self, count: int, radius: int) -> None:
        available_colors = ROBOT_COLORS[:]
        random.shuffle(available_colors)
        spawn_mask = self.board.blocked_mask
        for obj in self.board.objectives:
            spawn_mask |= (1 << (obj.row * GRID_COLS + obj.col))

        while len(self.robots) < count:
            c, r = random.randint(0, GRID_COLS - 1), random.randint(0, GRID_ROWS - 1)
            bit = 1 << (r * GRID_COLS + c)
            if not (spawn_mask & bit):
                color = available_colors[len(self.robots)]
                self.robots.append(Robot(col=c, row=r, radius=radius, color=color))
                spawn_mask |= bit
        self._update_occupied_mask()

    def _get_robot_at(self, col: int, row: int) -> Robot | None:
        """Utilise le masque pour vérifier la présence (rapide) puis renvoie l'objet."""
        if not (self.occupied_mask & (1 << (row * GRID_COLS + col))):
            return None
        return next((r for r in self.robots if r.col == col and r.row == row), None)

    # --- LOGIQUE DE JEU ---

    def _pick_next_objective(self) -> bool:
        if not self.remaining_objectives: return False
        self.current_objective = random.choice(self.remaining_objectives)
        self.remaining_objectives.remove(self.current_objective)

        if self.current_objective.is_multicolor:
            self.target_robot_index = None
        else:
            color = self.current_objective.color
            self.target_robot_index = next((i for i, r in enumerate(self.robots) if r.color == color), None)
        return True

    def _start_new_round(self) -> None:
        
        self.move_count = 0
        self.saved_robot_positions = None
        self.selected_robot = None
        self.reachable_cells.clear()
        self.sand_timer = SAND_TIMER_DURATION
        self.bidding_started = False
        self.active_player_index = None
        self.solver_path = None  # On vide le chemin de la manche précédente
        self.solver_bid = None   # On reset le score
        for p in self.players: p.bid = None
        
        if not self._pick_next_objective():
            self.state = GamePhase.GAME_OVER
        else:
            self.state = GamePhase.BIDDING
            self.solver_bid = None
            
            start_pos = [r.row * GRID_COLS + r.col for r in self.robots]
            target_idx = (self.current_objective.row * GRID_COLS) + self.current_objective.col
            
            self.solver_obj = RicochetSolver(self.board)
            
            self.solver_thread = SolverThread(self.solver_obj, start_pos, self.target_robot_index, target_idx)
            self.solver_thread.daemon = True # le thread se ferme avec le jeu
            self.solver_thread.start()

    def _end_bidding(self) -> None:
        if self.state != GamePhase.BIDDING:
            return

        if self.solver_thread and self.solver_thread.found:
            self.solver_path = self.solver_thread.result
            self.solver_bid = len(self.solver_path) if self.solver_path else 99

        self._update_occupied_mask()    
        
        self.state = GamePhase.SOLVING
        self.move_count = 0

        bidders = [(p.bid, i) for i, p in enumerate(self.players) if p.bid is not None]
        if not bidders:
            if self.solver_path:
                print("Aucun humain n'a trouvé de solution. L'IA fait la démonstration.")
                self._trigger_ai_demonstration() 
            else:
                self._start_new_round()
            return
        
        self.saved_robot_positions = [(r.col, r.row) for r in self.robots]
        
        bidders.sort(key=lambda x: x[0]) # Tri du plus petit au plus grand bid
        self.bid_order = [idx for _, idx in bidders]
        self.current_solver_index = 0
        self.active_player_index = self.bid_order[0]
        self.state = GamePhase.SOLVING
        self.move_count = 0

    def _fail_current_solver(self) -> None:
        if self.active_player_index is None: return None

        print(f"Echec du joueur {self.players[self.active_player_index].name}")

        # Remettre les robots à leurs positions de début de manche
        for i, (col, row) in enumerate(self.saved_robot_positions):
            self.robots[i].col = col
            self.robots[i].row = row
        self._update_occupied_mask()


        self.current_solver_index += 1
        if self.current_solver_index < len(self.bid_order):
            # Il reste des joueurs qui ont fait une annonce
            self.active_player_index = self.bid_order[self.current_solver_index]
            self.move_count = 0
            self.selected_robot = None
            self.reachable_cells.clear()
            print(f"Au tour de {self.players[self.active_player_index].name} ({self.players[self.active_player_index].bid} coups)")
        else:
            # Plus personne n'a d'annonce valide
            print("Personne n'a trouvé. Manche suivante.")
            self.round_index += 1
            self._start_new_round()

    def _handle_victory(self) -> None:
        if self.active_player_index is not None:
            self.players[self.active_player_index].score += 1
        self.round_index += 1
        self._start_new_round()

    # --- ÉVÉNEMENTS ET UPDATE ---

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_mouse_click(event.pos)
            elif event.type == pygame.MOUSEWHEEL:
                self.scroll_y -= event.y * 20
                self.scroll_y = max(0, min(self.scroll_y, self.max_scroll_y))

    def _handle_keydown(self, key):
        if key == pygame.K_ESCAPE: self.running = False
        
        if self.state == GamePhase.MAIN_MENU:
            if key in (pygame.K_RETURN, pygame.K_SPACE): self.state = GamePhase.CHOOSE_PLAYERS
        
        elif self.state == GamePhase.CHOOSE_PLAYERS:
            if key in (pygame.K_LEFT, pygame.K_DOWN): self.num_players = max(1, self.num_players - 1)
            elif key in (pygame.K_RIGHT, pygame.K_UP): self.num_players = min(8, self.num_players + 1)
            elif key == pygame.K_RETURN: self._confirm_players_and_start()
            
        elif self.state == GamePhase.BIDDING:
            if key == pygame.K_RIGHT: 
                self.current_player_selection = (self.current_player_selection + 1) % len(self.players)
            elif key == pygame.K_LEFT: 
                self.current_player_selection = (self.current_player_selection - 1) % len(self.players)
            
            elif pygame.K_0 <= key <= pygame.K_9:
                digit = key - pygame.K_0
                p = self.players[self.current_player_selection]
                
                if p.bid is None:
                    p.bid = digit
                else:
                    new_val = p.bid * 10 + digit
                    if new_val <= 99:
                        p.bid = new_val
                
                if not self.bidding_started:
                    self.bidding_started = True
                    self.sand_timer = SAND_TIMER_DURATION

            elif key == pygame.K_BACKSPACE:
                p = self.players[self.current_player_selection]
                if p.bid is not None:
                    p.bid = p.bid // 10
                    if p.bid == 0 and key == pygame.K_BACKSPACE:
                        p.bid = None

            elif key == pygame.K_RETURN: 
                self._end_bidding()

        elif self.state == GamePhase.SOLVING and key == pygame.K_s:
            self._trigger_ai_demonstration()
            
        elif self.state == GamePhase.GAME_OVER:
            if key in (pygame.K_RETURN, pygame.K_SPACE): self._reset_to_main_menu()

    def _handle_mouse_click(self, pos):
        width, height = self.screen.get_size()
        if self.state == GamePhase.MAIN_MENU:
            btns = self._get_main_menu_buttons(width, height)
            if btns["play"].collidepoint(pos): self.state = GamePhase.CHOOSE_PLAYERS
            elif btns["quit"].collidepoint(pos): self.running = False
        
        elif self.state == GamePhase.CHOOSE_PLAYERS:
            layout = self._get_player_select_layout(width, height)
            if layout["minus"].collidepoint(pos): self.num_players = max(1, self.num_players - 1)
            elif layout["plus"].collidepoint(pos): self.num_players = min(8, self.num_players + 1)
            elif layout["start"].collidepoint(pos): self._confirm_players_and_start()
            elif layout["back"].collidepoint(pos): self.state = GamePhase.MAIN_MENU
            
        elif self.state == GamePhase.SOLVING:
            board_w = int(width * 0.75)
            if pos[0] >= board_w: return
            cell_w, cell_h = get_cell_size(board_w, height)
            col, row = pos[0] // cell_w, pos[1] // cell_h
            
            robot = self._get_robot_at(col, row)
            if robot:
                self.selected_robot = robot
                # Utilisation du Bitmask pour trouver les cibles
                self.reachable_cells = self.board.get_move_targets(col, row, self.occupied_mask)
            elif self.selected_robot and (col, row) in self.reachable_cells:
                self.selected_robot.col, self.selected_robot.row = col, row
                self.move_count += 1
                self._update_occupied_mask() # Sync Bitboard
                self.selected_robot = None
                self.reachable_cells.clear()
            else:
                self.selected_robot = None
                self.reachable_cells.clear()

    # --- DESSIN (MÉTHODES GRAPHIQUES) ---

    def draw(self) -> None:
        width, height = self.screen.get_size()
        if self.state == GamePhase.MAIN_MENU: self._draw_main_menu(width, height)
        elif self.state == GamePhase.CHOOSE_PLAYERS: self._draw_player_select_screen(width, height)
        elif self.state == GamePhase.GAME_OVER: self._draw_game_over(width, height)
        else:
            self.screen.fill(BG_COLOR)
            board_w = int(width * 0.75)
            self.board_renderer.draw(self.screen, board_w, height)
            self._draw_goal_cell_highlight(board_w, height)
            
            # Dessin des Robots
            for idx, r in enumerate(self.robots):
                r.draw(self.screen, board_w, height)
                if idx == self.target_robot_index: # Cercle de sélection sur la cible
                    px, py = grid_to_pixel_center(r.col, r.row, board_w, height)
                    cw, ch = get_cell_size(board_w, height)
                    pygame.draw.circle(self.screen, (0,0,0), (px, py), min(cw, ch)//3 + 4, 2)
            
            # Cases atteignables
            for c, r in self.reachable_cells:
                px, py = grid_to_pixel_center(c, r, board_w, height)
                cw, ch = get_cell_size(board_w, height)
                pygame.draw.circle(self.screen, SELECT_TARGET_COLOR, (px, py), min(cw, ch)//6)
            
            self._draw_target_center(board_w, height)
            self._draw_side_panel(width, height, board_w)
            
        pygame.display.flip()

    def _draw_main_menu(self, w, h):
        self.screen.fill(MENU_BG_COLOR)
        title = self.title_font.render("Rasende Roboter", True, MENU_TITLE_COLOR)
        self.screen.blit(title, title.get_rect(center=(w//2, int(h*0.28))))
        btns = self._get_main_menu_buttons(w, h)
        m_pos = pygame.mouse.get_pos()
        self._draw_menu_button(btns["play"], "Jouer", btns["play"].collidepoint(m_pos))
        self._draw_menu_button(btns["quit"], "Quitter", btns["quit"].collidepoint(m_pos))
        hint_surf = self.font.render("Entrée ou clic sur Jouer pour commencer", True, MENU_SUBTITLE_COLOR)
        hint_rect = hint_surf.get_rect(center=(w // 2, int(h * 0.85)))
        self.screen.blit(hint_surf, hint_rect)

    def _draw_menu_button(self, rect, text, hover):
        color = MENU_BUTTON_HOVER_COLOR if hover else MENU_BUTTON_COLOR
        pygame.draw.rect(self.screen, color, rect, border_radius=12)
        pygame.draw.rect(self.screen, MENU_TITLE_COLOR, rect, 2, border_radius=12)
        txt = self.big_font.render(text, True, MENU_BUTTON_TEXT_COLOR)
        self.screen.blit(txt, txt.get_rect(center=rect.center))

    def _get_main_menu_buttons(self, w, h):
        bw, bh = w//4, max(60, h//12)
        play = pygame.Rect(0, 0, bw, bh)
        play.center = (w//2, int(h*0.55))
        quit_btn = pygame.Rect(0, 0, bw, bh)
        quit_btn.center = (w//2, int(h*0.55) + bh + 20)
        return {"play": play, "quit": quit_btn}

    def _get_player_select_layout(self, w, h):
        num_r = pygame.Rect(0, 0, w//6, h//10)
        num_r.center = (w//2, int(h*0.45))
        side = num_r.height
        minus = pygame.Rect(num_r.left - side - 20, num_r.top, side, side)
        plus = pygame.Rect(num_r.right + 20, num_r.top, side, side)
        start = pygame.Rect(0, 0, w//4, max(60, h//14))
        start.center = (w//2, int(h*0.7))
        back = pygame.Rect(40, 40, 120, 40)
        return {"number": num_r, "minus": minus, "plus": plus, "start": start, "back": back}

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
        elif symbol == "pentagon":
            points = []
            for i in range(5):
                angle_deg = 72 * i - 90 
                angle_rad = math.radians(angle_deg)
                points.append((
                    center_x + size * math.cos(angle_rad),
                    center_y + size * math.sin(angle_rad)
                ))
            pygame.draw.polygon(self.screen, color, points)

    def _draw_goal_cell_highlight(self, bw, bh):
        if not self.current_objective: return
        rect = cell_rect(self.current_objective.col, self.current_objective.row, bw, bh)
        pygame.draw.rect(self.screen, GOAL_OUTLINE_COLOR, rect, 4)


    def _draw_side_panel(self, width: int, height: int, board_width: int) -> None:
        panel_rect = pygame.Rect(board_width, 0, width - board_width, height)
        pygame.draw.rect(self.screen, HUD_BG_COLOR, panel_rect)
        
        # --- 1. HEADER (FIXE) ---
        header_rect = panel_rect.copy()
        header_rect.height = 80
        pygame.draw.rect(self.screen, MENU_BUTTON_COLOR, header_rect)
        
        phase_label = "Annonce" if self.state == GamePhase.BIDDING else "Solution" if self.state == GamePhase.SOLVING else ""
        title_surf = self.big_font.render(f"Manche {self.round_index}", True, MENU_BUTTON_TEXT_COLOR)
        self.screen.blit(title_surf, (header_rect.x + 18, header_rect.y + 15))
        
        if phase_label:
            phase_surf = self.font.render(f"Phase : {phase_label}", True, MENU_BUTTON_TEXT_COLOR)
            self.screen.blit(phase_surf, (header_rect.x + 18, header_rect.y + 50))
            
        y_fixed = header_rect.bottom + 12
        
        # --- 2. OBJECTIF ET TIMER (FIXES) ---
        if self.current_objective is not None:
            target_rect = pygame.Rect(panel_rect.x + 12, y_fixed, panel_rect.width - 24, 80)
            pygame.draw.rect(self.screen, TARGET_CENTER_COLOR, target_rect, border_radius=12)
            pygame.draw.rect(self.screen, MENU_BUTTON_COLOR, target_rect, 1, border_radius=12)
            pygame.draw.circle(self.screen, self.current_objective.color, (target_rect.x + 28, target_rect.centery), 12)
            label_surf = self.font.render("Objectif actuel", True, HUD_TEXT_COLOR)
            self.screen.blit(label_surf, (target_rect.x + 52, target_rect.y + 10))
            info_surf = self.font.render(f"Atteindre {self.current_objective.col}, {self.current_objective.row}", True, HUD_TEXT_COLOR)
            self.screen.blit(info_surf, (target_rect.x + 52, target_rect.y + 36))
            y_fixed = target_rect.bottom + 16

        if self.state == GamePhase.BIDDING:
            timer_rect = pygame.Rect(panel_rect.x + 12, y_fixed, panel_rect.width - 24, 72)
            pygame.draw.rect(self.screen, (255, 255, 255), timer_rect, border_radius=12)
            seconds = max(0, int(self.sand_timer if self.bidding_started else SAND_TIMER_DURATION))
            timer_value = self.big_font.render(f"{seconds} s", True, HUD_TEXT_COLOR)
            self.screen.blit(timer_value, timer_value.get_rect(center=timer_rect.center))
            y_fixed = timer_rect.bottom + 16

        # --- 3. ZONE SCROLLABLE (JOUEURS + IA) ---
        players_title = self.font.render("Joueurs", True, HUD_TEXT_COLOR)
        self.screen.blit(players_title, (panel_rect.x + 16, y_fixed))
        y_fixed += 26

        # Définition de la zone de vue (viewport)
        # On s'arrête à height - 150 pour laisser la place aux contrôles fixes en bas
        view_rect = pygame.Rect(panel_rect.x, y_fixed, panel_rect.width, height - y_fixed - 150)
        
        # Calcul de la hauteur totale du contenu
        row_height = 56
        spacing = 8
        total_content_height = (len(self.players) + 1) * (row_height + spacing)
        self.max_scroll_y = max(0, total_content_height - view_rect.height)
        self.scroll_y = max(0, min(self.scroll_y, self.max_scroll_y)) # Sécurité

        # Création de la surface de contenu
        scroll_surf = pygame.Surface((view_rect.width, total_content_height), pygame.SRCALPHA)
        y_scroll = 0 # Position Y relative à la scroll_surf

        # Dessin des joueurs sur la scroll_surf
        for i, p in enumerate(self.players):
            row_rect = pygame.Rect(12, y_scroll, view_rect.width - 24, row_height)
            bg_col = (245, 245, 245)
            if self.state == GamePhase.BIDDING and i == self.current_player_selection: bg_col = MENU_BUTTON_COLOR
            elif self.state == GamePhase.SOLVING and self.active_player_index == i: bg_col = MENU_BUTTON_HOVER_COLOR
            
            pygame.draw.rect(scroll_surf, bg_col, row_rect, border_radius=10)
            pygame.draw.rect(scroll_surf, MENU_BUTTON_COLOR, row_rect, 1, border_radius=10)
            
            txt_col = MENU_BUTTON_TEXT_COLOR if bg_col != (245, 245, 245) else HUD_TEXT_COLOR
            scroll_surf.blit(self.font.render(p.name, True, txt_col), (row_rect.x + 14, row_rect.y + 6))
            scroll_surf.blit(self.font.render(f"Score: {p.score}", True, txt_col), (row_rect.x + 14, row_rect.y + 30))
            bid_txt = "-" if p.bid is None else str(p.bid)
            surf_bid = self.font.render(f"Annonce : {bid_txt}", True, txt_col)
            scroll_surf.blit(surf_bid, (row_rect.right - surf_bid.get_width() - 14, row_rect.y + 18))
            y_scroll += row_height + spacing

        # Dessin de l'IA sur la scroll_surf
        ai_rect = pygame.Rect(12, y_scroll, view_rect.width - 24, row_height)
        if self.solver_thread and not self.solver_thread.found:
            ai_bg, ai_txt_content, ai_txt_col = (255, 100, 100), "IA réfléchit...", (255, 255, 255)
        elif self.solver_bid is not None:
            t = getattr(self.solver_thread, 'time_taken', 0)
            ai_bg, ai_txt_content, ai_txt_col = (100, 255, 100), f"Trouvé en {t:.2f}s", (40, 40, 40)
        else:
            ai_bg, ai_txt_content, ai_txt_col = (220, 220, 220), "IA en attente", (100, 100, 100)

        pygame.draw.rect(scroll_surf, ai_bg, ai_rect, border_radius=10)
        pygame.draw.rect(scroll_surf, MENU_BUTTON_COLOR, ai_rect, 1, border_radius=10)
        scroll_surf.blit(self.font.render("IA Solver", True, ai_txt_col), (ai_rect.x + 14, ai_rect.y + 6))
        scroll_surf.blit(self.font.render(ai_txt_content, True, ai_txt_col), (ai_rect.x + 14, ai_rect.y + 30))
        if self.solver_bid is not None:
            val = str(self.solver_bid) if (self.state != GamePhase.BIDDING or self.sand_timer <= 0) else "?"
            surf_ai_bid = self.font.render(f"Annonce : {val}", True, ai_txt_col)
            scroll_surf.blit(surf_ai_bid, (ai_rect.right - surf_ai_bid.get_width() - 14, ai_rect.y + 18))

        # Affichage de la surface défilante avec clipping
        self.screen.blit(scroll_surf, view_rect.topleft, (0, self.scroll_y, view_rect.width, view_rect.height))

        # --- 4. CONTROLES (FIXES EN BAS) ---
        controls_rect = pygame.Rect(panel_rect.x + 12, height - 142, panel_rect.width - 24, 130)
        pygame.draw.rect(self.screen, (255, 255, 255), controls_rect, border_radius=10)
        pygame.draw.rect(self.screen, MENU_BUTTON_COLOR, controls_rect, 1, border_radius=10)

        cx, cy = controls_rect.x + 14, controls_rect.y + 12
        header_text = "Annonces" if self.state == GamePhase.BIDDING else "Solution"
        self.screen.blit(self.font.render(header_text, True, HUD_TEXT_COLOR), (cx, cy))
        
        if self.state == GamePhase.BIDDING:
            lines = ["<- / -> : changer joueur", "1-99 : saisir annonce", "Entrée : valider"]
        else:
            lines = [f"Coups joués : {self.move_count}"]
            active = self.players[self.active_player_index] if self.active_player_index is not None else None
            if active: lines.append(f"Joueur : {active.name} ({active.bid} max)")
            lines.append("S : montrer solution IA")
        
        for i, line in enumerate(lines):
            self.screen.blit(self.font.render(line, True, HUD_TEXT_COLOR), (cx, cy + 28 + i * 22))

    def _draw_game_over(self, w, h):
        self.screen.fill(MENU_BG_COLOR)
        txt = self.title_font.render("Fin de Partie", True, MENU_TITLE_COLOR)
        self.screen.blit(txt, txt.get_rect(center=(w//2, h//2)))

    def _confirm_players_and_start(self) -> None:
        self.players = [Player(name=f"J{i + 1}") for i in range(self.num_players)]
        self._start_new_round()

    def _reset_to_main_menu(self) -> None:
        self.state = GamePhase.MAIN_MENU

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()


import instance_generator as IG

if __name__ == "__main__":
    Game().run()

    #boards = IG.run_benchmark(100, 16, 3, True)
    #IG.save_difficult_cases(boards, "generated_instances.json")