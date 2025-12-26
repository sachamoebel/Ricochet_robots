from enum import Enum

class GamePhase(str, Enum):
    MAIN_MENU = "main_menu"
    CHOOSE_PLAYERS = "choose_players"
    BIDDING = "bidding"
    SOLVING = "solving"
    GAME_OVER = "game_over"
    SHOWING_SOLUTION = "showing_solution"
