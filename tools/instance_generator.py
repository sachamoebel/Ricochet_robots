import time
import random
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from collections import defaultdict
import numpy as np
import pickle

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.ai.standard_solver import RicochetSolver as SolverV1
from src.ai.advanced_solver import SolverV2


uncompleted_boards = []

class GeneratedBoard:
    def __init__(self, n: int = 16):
        self.cols = n
        self.rows = n
        self.walls_up = 0
        self.walls_down = 0
        self.walls_right = 0
        self.walls_left = 0
        self.blocked_mask = 0
        
        self.corner_cells = [] 
        self.reserved_cells = set() 

    def pos_to_bit(self, c, r):
        return 1 << (r * self.cols + c)

    def add_wall(self, c, r, direction):
        if not (0 <= c < self.cols and 0 <= r < self.rows):
            return
        bit = self.pos_to_bit(c, r)
        if direction == 'N':
            self.walls_up |= bit
            if r > 0: self.walls_down |= self.pos_to_bit(c, r - 1)
        elif direction == 'S':
            self.walls_down |= bit
            if r < self.rows - 1: self.walls_up |= self.pos_to_bit(c, r + 1)
        elif direction == 'E':
            self.walls_right |= bit
            if c < self.cols - 1: self.walls_left |= self.pos_to_bit(c + 1, r)
        elif direction == 'W':
            self.walls_left |= bit
            if c > 0: self.walls_right |= self.pos_to_bit(c - 1, r)

    def generate(self):
        self._setup_perimeter_and_center()

        mid = self.cols // 2
        quadrants = [
            (range(1, mid), range(1, mid)),          # TL
            (range(mid, self.cols-1), range(1, mid)), # TR
            (range(1, mid), range(mid, self.rows-1)), # BL
            (range(mid, self.cols-1), range(mid, self.rows-1)) # BR
        ]

        for c_range, r_range in quadrants:
            for _ in range(4):
                self._place_random_angle(c_range, r_range)

        bonus_q = random.choice(quadrants)
        self._place_random_angle(bonus_q[0], bonus_q[1])

    def _setup_perimeter_and_center(self):
        n = self.cols
        # Périmètre
        for i in range(n):
            self.add_wall(i, 0, 'N')
            self.add_wall(i, n - 1, 'S')
            self.add_wall(0, i, 'W')
            self.add_wall(n - 1, i, 'E')
        
        # Bloc central
        mid = n // 2
        centers = [(mid-1, mid-1), (mid, mid-1), (mid-1, mid), (mid, mid)]
        for c, r in centers:
            self.blocked_mask |= self.pos_to_bit(c, r)
            self._reserve_area(c, r) # Empêche les angles de coller au centre
            
        self.add_wall(mid-1, mid-1, 'N'); self.add_wall(mid, mid-1, 'N')
        self.add_wall(mid-1, mid, 'S');   self.add_wall(mid, mid, 'S')
        self.add_wall(mid-1, mid-1, 'W'); self.add_wall(mid-1, mid, 'W')
        self.add_wall(mid, mid-1, 'E');   self.add_wall(mid, mid, 'E')

    def _place_8_border_walls(self):
        """Place 2 murs simples perpendiculaires par bordure (Total 8)."""
        n = self.cols
        mid = n // 2

        # TL : Un sur bord Nord, un sur bord Ouest
        self._add_border_simple_wall(random.randint(1, mid-1), 0, 'W')
        self._add_border_simple_wall(0, random.randint(1, mid-1), 'S')

        # TR : Un sur bord Nord, un sur bord Est
        self._add_border_simple_wall(random.randint(mid, n-2), 0, 'W')
        self._add_border_simple_wall(n-1, random.randint(1, mid-1), 'N')

        # BL : Un sur bord Sud, un sur bord Ouest
        self._add_border_simple_wall(random.randint(1, mid-1), n-1, 'E')
        self._add_border_simple_wall(0, random.randint(mid, n-2), 'S')

        # BR : Un sur bord Sud, un sur bord Est
        self._add_border_simple_wall(random.randint(mid, n-2), n-1, 'E')
        self._add_border_simple_wall(n-1, random.randint(mid, n-2), 'N')

    def _add_border_simple_wall(self, c, r, direction):
        self.add_wall(c, r, direction)
        # On réserve la case du mur pour que les angles ne s'y collent pas
        self._reserve_area(c, r)

    def _reserve_area(self, c, r):
        """Marque la case et ses voisines comme interdites pour les angles."""
        for dc in range(-1, 2):
            for dr in range(-1, 2):
                self.reserved_cells.add((c + dc, r + dr))

    def _place_random_angle(self, c_range, r_range):
        """Trouve une place pour un angle L sans contact."""
        cells = [(c, r) for c in c_range for r in r_range]
        random.shuffle(cells)

        for c, r in cells:
            # Règle : l'angle ne doit pas toucher de case réservée (autre angle ou mur ext)
            if (c, r) in self.reserved_cells:
                continue
            
            # Choix aléatoire de l'orientation de l'angle
            d1, d2 = random.choice([('N', 'W'), ('N', 'E'), ('S', 'W'), ('S', 'E')])
            self.add_wall(c, r, d1)
            self.add_wall(c, r, d2)
            
            self.corner_cells.append(r * self.cols + c)
            self._reserve_area(c, r) # Réserve 3x3 pour le prochain
            return True
        return False
    
# Generate board instance according to the boards of the original game 
def generate_instance(size: int, num_helpers: int):
    board = GeneratedBoard(size)
    board.generate()

    robots = []
    while len(robots) < (1 + num_helpers):
        idx = random.randint(0, size*size-1)
        if not (board.blocked_mask & (1 << idx)) and idx not in robots:
            robots.append(idx)
            
    target = random.choice(board.corner_cells)
    return board, robots, target

def visualize_instance(board, robots, target, n):
    fig, ax = plt.subplots(figsize=(6,6))
    ax.set_aspect('equal')
    for r in range(n):
        for c in range(n):
            idx, bit = r*n+c, 1<<(r*n+c)
            if board.blocked_mask & bit: ax.add_patch(patches.Rectangle((c, n-r-1), 1, 1, color='black'))
            if idx == target: ax.add_patch(patches.Rectangle((c, n-r-1), 1, 1, color='red', alpha=0.3))
            if bit & board.walls_up: ax.plot([c, c+1], [n-r, n-r], color='black', lw=2)
            if bit & board.walls_left: ax.plot([c, c], [n-r, n-r-1], color='black', lw=2)
    for i, p in enumerate(robots):
        ax.add_patch(patches.Circle((p%n+0.5, n-(p//n)-0.5), 0.3, color=['red','blue','green','yellow'][i%4]))
    ax.set_xlim(0, n); ax.set_ylim(0, n); plt.title(f"Dernière instance ({n}x{n})")
    plt.show()


def run_benchmark(num_instances=100, size=16, helpers=3, display_stats=True):
    t = time.time()
    stats1 = []
    stats2 = []

    print(f"Benchmark : {num_instances} instances...")
    for i in range(num_instances):
        board, start, target = generate_instance(size, helpers)
        solver1 = SolverV1(board)
        solver2 = SolverV2(board)

        t0 = time.time()
        moves1, nb_noeuds_explores1 = solver1.solve(start, 0, target)
        t1 = time.time()
        timed1 = t1 - t0

        t2 = time.time()
        moves2, nb_noeuds_explores2 = solver2.solve(start, 0, target)
        t3 = time.time()
        timed2 = t3 - t2

        if timed1 > 40 or timed2 > 40:
            uncompleted_boards.append((board, start, target))
        
        if (timed1 > 0 and timed2 > 0):
            print({'moves': moves1, 'time': timed1, 'nodes': nb_noeuds_explores1})
            print({'moves': moves2, 'time': timed2, 'nodes': nb_noeuds_explores2})
        else:
            print({'moves': moves1, 'time': timed1})
            print({'moves': moves2, 'time': timed2})

        print("-----")

        if moves1 is not None:
            stats1.append({'moves': len(moves1), 'time': timed1})
        
        if moves2 is not None:
            stats2.append({'moves': len(moves2), 'time': timed2})
    
 
        if (i+1) % 10 == 0: print(f"Progrès : {i+1}% : time écoulé {time.time()-t:.2f}s")

    if display_stats:
    
        if stats1 and stats2:
            # Prepare data
            mv1 = [s['moves'] for s in stats1]
            tm1 = [s['time'] for s in stats1]
            
            mv2 = [s['moves'] for s in stats2]
            tm2 = [s['time'] for s in stats2]

            plt.figure(figsize=(14, 6))

            plt.subplot(1, 2, 1)
            
            if mv1:
                weights = [100 / len(mv1)] * len(mv1)
                bins = range(min(mv1), max(mv1) + 2)
                
                plt.hist(mv1, bins=bins, weights=weights, color='skyblue', edgecolor='black', align='left')
                
                plt.title("Distribution of minimum number of moves")
                plt.xlabel("Minimum number of moves")
                plt.ylabel("Percentage of instances (%)")
                plt.grid(axis='y', linestyle='--', alpha=0.7)

            plt.subplot(1, 2, 2)

            data_map1 = defaultdict(list)
            data_map2 = defaultdict(list)

            for s in stats1: data_map1[s['moves']].append(s['time'])
            for s in stats2: data_map2[s['moves']].append(s['time'])

            all_moves = sorted(list(set(data_map1.keys()) | set(data_map2.keys())))
            
            means1 = [sum(data_map1[m])/len(data_map1[m]) if m in data_map1 else 0 for m in all_moves]
            means2 = [sum(data_map2[m])/len(data_map2[m]) if m in data_map2 else 0 for m in all_moves]

            x_indices = range(len(all_moves))
            width = 0.4

            plt.bar([x - width/2 for x in x_indices], means1, width=width, 
                    color='cornflowerblue', label='RicochetSolver')
            
            plt.bar([x + width/2 for x in x_indices], means2, width=width, 
                    color='salmon', label='Solver 2')

            plt.xticks(x_indices, all_moves)
            plt.title("Distribution of the average time to solve by minimum number of moves (in seconds)")
            plt.xlabel("Minimum number of moves")
            plt.ylabel("Average time (s)")
            plt.legend()
            plt.grid(axis='y', linestyle='--', alpha=0.5)

            plt.tight_layout()
            plt.show()

        return uncompleted_boards

    

def save_difficult_cases(boards, filename="difficult_boards.pkl"):
    # for board in boards:
    #     visualize_instance(board[0], board[1], board[2], 16)
        
    print(f"Saving {len(uncompleted_boards)} difficult cases to file...")

    with open("difficult_boards.pkl", "wb") as f:
        pickle.dump(uncompleted_boards, f)

    print("Saved.")

if __name__ == "__main__":
    try:
        nb_instances = 100
        if len(sys.argv) > 1 :
            nb_instances = int(sys.argv[1])
        run_benchmark(nb_instances, 16, 3, True)
    except ValueError as e:
        print(f"Invalid argument for number of instances: {sys.argv[1]}. Please provide an integer.")
