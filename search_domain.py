import pygame
import heapq
import collections
import time

GRID_SIZE = 16
CELL_SIZE = 40
WIDTH = GRID_SIZE * CELL_SIZE
HEIGHT = GRID_SIZE * CELL_SIZE
FPS = 60

# Couleurs
COLORS = [(220, 40, 40), (40, 200, 40), (40, 40, 220), (200, 200, 40)] # R, V, B, J
WALL_COLOR = (255, 255, 255)
BG_COLOR = (30, 30, 30)

class RicochetSolver:
    def __init__(self):
        self.walls_n = 0
        self.walls_s = 0
        self.walls_e = 0
        self.walls_w = 0
        self.static_h = {}

    def pos_to_bit(self, r, c):
        return 1 << (r * 16 + c)

    def add_wall(self, r, c, direction):
        bit = self.pos_to_bit(r, c)
        if direction == 'N': self.walls_n |= bit
        elif direction == 'S': self.walls_s |= bit
        elif direction == 'E': self.walls_e |= bit
        elif direction == 'W': self.walls_w |= bit

    def precompute_bfs_heuristic(self, target_idx):
        """ Calcule la distance min pour le robot cible en ignorant les autres robots """
        self.static_h = {target_idx: 0}
        queue = collections.deque([target_idx])
        
        while queue:
            curr = queue.popleft()
            d = self.static_h[curr]
            r, c = curr // 16, curr % 16
            
            # On cherche les voisins qui peuvent s'arrêter sur 'curr' en 1 coup
            for move_dir in ['N', 'S', 'E', 'W']:
                # Reculer dans la direction opposée
                dr, dc = {'N':(1,0), 'S':(-1,0), 'E':(0,-1), 'W':(0,1)}[move_dir]
                # Le recul est possible seulement si curr a un mur qui le stoppe dans move_dir
                stop_bit = self.pos_to_bit(r, c)
                has_stop_wall = (move_dir == 'N' and stop_bit & self.walls_n) or \
                                (move_dir == 'S' and stop_bit & self.walls_s) or \
                                (move_dir == 'E' and stop_bit & self.walls_e) or \
                                (move_dir == 'W' and stop_bit & self.walls_w)
                
                if has_stop_wall:
                    nr, nc = r + dr, c + dc
                    while 0 <= nr < 16 and 0 <= nc < 16:
                        # Vérifier s'il y a un mur entre nr,nc et la case d'avant
                        # (On ne peut pas reculer si on traverse un mur)
                        n_bit = self.pos_to_bit(nr, nc)
                        blocked = (move_dir == 'N' and n_bit & self.walls_s) or \
                                  (move_dir == 'S' and n_bit & self.walls_n) or \
                                  (move_dir == 'E' and n_bit & self.walls_w) or \
                                  (move_dir == 'W' and n_bit & self.walls_e)
                        if blocked: break
                        
                        idx = nr * 16 + nc
                        if idx not in self.static_h:
                            self.static_h[idx] = d + 1
                            queue.append(idx)
                        
                        # Continuer de reculer sur la ligne
                        nr, nc = nr + dr, nc + dc
                        
    def get_destination(self, robot_idx_pos, direction, occupied_mask):
        r, c = robot_idx_pos // 16, robot_idx_pos % 16
        while True:
            bit = 1 << (r * 16 + c)
            if direction == 'N' and (bit & self.walls_n): break
            if direction == 'S' and (bit & self.walls_s): break
            if direction == 'E' and (bit & self.walls_e): break
            if direction == 'W' and (bit & self.walls_w): break
            
            nr, nc = r + ({'N':-1, 'S':1, 'E':0, 'W':0}[direction]), c + ({'N':0, 'S':0, 'E':1, 'W':-1}[direction])
            if not (0 <= nr < 16 and 0 <= nc < 16): break
            
            next_bit = 1 << (nr * 16 + nc)
            if next_bit & occupied_mask: break
            # Mur d'entrée
            if direction == 'N' and (next_bit & self.walls_s): break
            if direction == 'S' and (next_bit & self.walls_n): break
            if direction == 'E' and (next_bit & self.walls_w): break
            if direction == 'W' and (next_bit & self.walls_e): break
            
            r, c = nr, nc
        return r * 16 + c

    def solve(self, start_pos, target_robot, target_cell):
        self.precompute_bfs_heuristic(target_cell)
        
        # On ajoute (last_robot, last_direction) à l'état de la file
        # Format : (f_score, g_score, positions, path, last_move)
        # last_move = (robot_index, direction)
        start_pos = tuple(start_pos)
        h = self.static_h.get(start_pos[target_robot], 10)
        queue = [(h, 0, start_pos, [], (-1, ""))] # -1 signifie aucun robot
        
        visited = {}

        while queue:
            f, g, positions, path, last_move = heapq.heappop(queue)
            last_r, last_d = last_move

            if positions[target_robot] == target_cell:
                return path

            others = sorted([positions[i] for i in range(4) if i != target_robot])
            state_key = (positions[target_robot], tuple(others))
            
            if visited.get(state_key, 99) <= g: continue
            visited[state_key] = g

            occ_mask = 0
            for p in positions: occ_mask |= (1 << p)

            for r_i in range(4):
                # --- OPTIMISATION SECTION D : ÉLAGAGE ---
                # 1. Si c'est le même robot que le coup d'avant, il ne doit pas 
                #    bouger sur le même axe (ni même direction, ni opposée).
                #    Ex: S'il a bougé 'N', il ne peut faire que 'E' ou 'W'.
                forbidden_dirs = []
                if r_i == last_r:
                    if last_d in ['N', 'S']: forbidden_dirs = ['N', 'S']
                    else: forbidden_dirs = ['E', 'W']

                for d in ['N', 'S', 'E', 'W']:
                    if d in forbidden_dirs: continue
                    
                    old_p = positions[r_i]
                    new_p = self.get_destination(old_p, d, occ_mask ^ (1 << old_p))
                    
                    # 2. Vérifier que le mouvement a réellement déplacé le robot
                    if new_p != old_p:
                        new_pos_list = list(positions)
                        new_pos_list[r_i] = new_p
                        new_pos_tuple = tuple(new_pos_list)
                        
                        h_val = self.static_h.get(new_pos_tuple[target_robot], 10)
                        
                        # On pousse le nouvel état avec le mouvement actuel en 'last_move'
                        heapq.heappush(queue, (
                            g + 1 + h_val, 
                            g + 1, 
                            new_pos_tuple, 
                            path + [(r_i, d)],
                            (r_i, d)
                        ))
        return None

def main():
    solver = RicochetSolver()
    
    # 1. SETUP DU PLATEAU (Exemple de murs en L)
    # Carré central
    for i in [7, 8]:
        solver.add_wall(7, i, 'N'); solver.add_wall(8, i, 'S')
        solver.add_wall(i, 7, 'W'); solver.add_wall(i, 8, 'E')
    
    # Quelques murs aléatoires pour le puzzle
    solver.add_wall(0, 2, 'W')
    solver.add_wall(0, 10, 'E')
    solver.add_wall(1, 4, 'N') # Mur Nord de la cible
    solver.add_wall(1, 4, 'W') # Mur Ouest de la cible
    solver.add_wall(1, 9, 'S'); solver.add_wall(1, 9, 'W')
    solver.add_wall(2, 1, 'N'); solver.add_wall(2, 1, 'E')
    solver.add_wall(2, 14, 'N'); solver.add_wall(2, 14, 'E')
    solver.add_wall(3, 6, 'S'); solver.add_wall(3, 6, 'E')
    solver.add_wall(4, 15, 'S')
    solver.add_wall(8, 15, 'S')
    solver.add_wall(5, 0, 'S')
    solver.add_wall(11, 0, 'S')
    solver.add_wall(6, 3, 'S'); solver.add_wall(6, 3, 'W')
    solver.add_wall(6, 11, 'N'); solver.add_wall(6, 11, 'W')
    solver.add_wall(8, 5, 'S'); solver.add_wall(8, 5, 'W')
    solver.add_wall(9, 2, 'N'); solver.add_wall(9, 2, 'W')
    solver.add_wall(10, 8, 'N'); solver.add_wall(10, 8, 'W')
    solver.add_wall(10, 13, 'N'); solver.add_wall(10, 13, 'W')
    solver.add_wall(11, 10, 'S'); solver.add_wall(11, 10, 'E')
    solver.add_wall(12, 14, 'S'); solver.add_wall(2, 14, 'W')
    solver.add_wall(13, 4, 'N'); solver.add_wall(13, 4, 'E')
    solver.add_wall(14, 1, 'S'); solver.add_wall(14, 1, 'E')
    solver.add_wall(14, 9, 'N'); solver.add_wall(14, 9, 'E')
    solver.add_wall(15, 5, 'E')
    solver.add_wall(15, 11, 'E')


    # 2. DEFINIR LE PUZZLE
    start_positions = [15, 198, 235, 115] # R, V, B, J (coins)
    target_robot = 0 # Le rouge doit atteindre la cible
    target_cell = 6 * 16 + 11 # Case (10, 12)

    print("Calcul de la solution...")
    start_t = time.time()
    solution = solver.solve(start_positions, target_robot, target_cell)
    print(f"Trouvé en {time.time()-start_t:.2f}s | Coups: {len(solution) if solution else 'Inf'}")

    # 3. VISUALISATION PYGAME
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Solution Rasende Roboter")
    
    step = 0
    curr_positions = list(start_positions)
    animating = True
    last_update = time.time()

    while animating:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: animating = False

        # Animation pas à pas
        if solution and step < len(solution) and time.time() - last_update > 1:
            r_idx, move_dir = solution[step]
            occ = 0
            for p in curr_positions: occ |= (1 << p)
            curr_positions[r_idx] = solver.get_destination(curr_positions[r_idx], move_dir, occ ^ (1 << curr_positions[r_idx]))
            step += 1
            last_update = time.time()

        screen.fill(BG_COLOR)
        
        # Dessiner Grille et Murs
        for r in range(16):
            for c in range(16):
                rect = (c*CELL_SIZE, r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                bit = 1 << (r*16 + c)
                if bit == target_cell: pygame.draw.rect(screen, (80, 0, 0), rect)
                pygame.draw.rect(screen, (50, 50, 50), rect, 1)
                
                if bit & solver.walls_n: pygame.draw.line(screen, WALL_COLOR, (c*CELL_SIZE, r*CELL_SIZE), ((c+1)*CELL_SIZE, r*CELL_SIZE), 3)
                if bit & solver.walls_s: pygame.draw.line(screen, WALL_COLOR, (c*CELL_SIZE, (r+1)*CELL_SIZE), ((c+1)*CELL_SIZE, (r+1)*CELL_SIZE), 3)
                if bit & solver.walls_e: pygame.draw.line(screen, WALL_COLOR, ((c+1)*CELL_SIZE, r*CELL_SIZE), ((c+1)*CELL_SIZE, (r+1)*CELL_SIZE), 3)
                if bit & solver.walls_w: pygame.draw.line(screen, WALL_COLOR, (c*CELL_SIZE, r*CELL_SIZE), (c*CELL_SIZE, (r+1)*CELL_SIZE), 3)

        # Dessiner Robots
        for i, p in enumerate(curr_positions):
            pr, pc = p // 16, p % 16
            pygame.draw.circle(screen, COLORS[i], (pc*CELL_SIZE+20, pr*CELL_SIZE+20), 15)
            if i == target_robot: pygame.draw.circle(screen, (255,255,255), (pc*CELL_SIZE+20, pr*CELL_SIZE+20), 18, 2)

        pygame.display.flip()
    pygame.quit()