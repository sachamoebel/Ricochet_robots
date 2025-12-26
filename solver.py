# solver.py
import heapq
import collections
import time

class RicochetSolver:
    def __init__(self, board):
        # We link directly to your existing board bitboards
        self.walls_n = board.walls_up
        self.walls_s = board.walls_down
        self.walls_e = board.walls_right
        self.walls_w = board.walls_left
        self.cols = board.cols
        self.rows = board.rows
        self.static_h = {}

    def precompute_bfs_heuristic(self, target_idx):
        self.static_h = {target_idx: 0}
        queue = collections.deque([target_idx])
        while queue:
            curr = queue.popleft()
            d = self.static_h[curr]
            r, c = curr // self.cols, curr % self.cols
            for move_dir in ['N', 'S', 'E', 'W']:
                dr, dc = {'N': (1, 0), 'S': (-1, 0), 'E': (0, -1), 'W': (0, 1)}[move_dir]
                stop_bit = 1 << curr
                has_stop_wall = (move_dir == 'N' and stop_bit & self.walls_n) or \
                                (move_dir == 'S' and stop_bit & self.walls_s) or \
                                (move_dir == 'E' and stop_bit & self.walls_e) or \
                                (move_dir == 'W' and stop_bit & self.walls_w)
                if has_stop_wall:
                    nr, nc = r + dr, c + dc
                    while 0 <= nr < self.rows and 0 <= nc < self.cols:
                        n_bit = 1 << (nr * self.cols + nc)
                        blocked = (move_dir == 'N' and n_bit & self.walls_s) or \
                                  (move_dir == 'S' and n_bit & self.walls_n) or \
                                  (move_dir == 'E' and n_bit & self.walls_w) or \
                                  (move_dir == 'W' and n_bit & self.walls_e)
                        if blocked: break
                        idx = nr * self.cols + nc
                        if idx not in self.static_h:
                            self.static_h[idx] = d + 1
                            queue.append(idx)
                        nr, nc = nr + dr, nc + dc

    def get_destination(self, robot_idx_pos, direction, occupied_mask):
        r, c = robot_idx_pos // self.cols, robot_idx_pos % self.cols
        while True:
            bit = 1 << (r * self.cols + c)
            if direction == 'N' and (bit & self.walls_n): break
            if direction == 'S' and (bit & self.walls_s): break
            if direction == 'E' and (bit & self.walls_e): break
            if direction == 'W' and (bit & self.walls_w): break
            nr, nc = r + {'N': -1, 'S': 1, 'E': 0, 'W': 0}[direction], c + {'N': 0, 'S': 0, 'E': 1, 'W': -1}[direction]
            if not (0 <= nr < self.rows and 0 <= nc < self.cols): break
            next_bit = 1 << (nr * self.cols + nc)
            if next_bit & occupied_mask: break
            if direction == 'N' and (next_bit & self.walls_s): break
            if direction == 'S' and (next_bit & self.walls_n): break
            if direction == 'E' and (next_bit & self.walls_w): break
            if direction == 'W' and (next_bit & self.walls_e): break
            r, c = nr, nc
        return r * self.cols + c

    def solve(self, start_pos, target_robot_idx, target_cell):
        self.precompute_bfs_heuristic(target_cell)
        start_pos = tuple(start_pos)
        
        # If multicolor, target_robot_idx might be None. 
        # We need a specific heuristic or pick a robot. 
        # For simplicity, if None, we assume any robot can hit it.
        def get_h(pos_tuple):
            if target_robot_idx is not None:
                return self.static_h.get(pos_tuple[target_robot_idx], 10)
            return min(self.static_h.get(p, 10) for p in pos_tuple)

        queue = [(get_h(start_pos), 0, start_pos, [], (-1, ""))]
        visited = {}

        while queue:
            f, g, positions, path, last_move = heapq.heappop(queue)
            last_r, last_d = last_move

            # Goal check
            if target_robot_idx is not None:
                if positions[target_robot_idx] == target_cell: return path
            else:
                if any(p == target_cell for p in positions): return path

            state_key = (positions, target_robot_idx)
            if visited.get(state_key, 99) <= g: continue
            visited[state_key] = g

            occ_mask = 0
            for p in positions: occ_mask |= (1 << p)

            for r_i in range(len(positions)):
                forbidden_dirs = []
                if r_i == last_r:
                    if last_d in ['N', 'S']: forbidden_dirs = ['N', 'S']
                    else: forbidden_dirs = ['E', 'W']

                for d in ['N', 'S', 'E', 'W']:
                    if d in forbidden_dirs: continue
                    old_p = positions[r_i]
                    new_p = self.get_destination(old_p, d, occ_mask ^ (1 << old_p))
                    if new_p != old_p:
                        new_pos_list = list(positions)
                        new_pos_list[r_i] = new_p
                        new_pos_tuple = tuple(new_pos_list)
                        h_val = get_h(new_pos_tuple)
                        heapq.heappush(queue, (g + 1 + h_val, g + 1, new_pos_tuple, path + [(r_i, d)], (r_i, d)))
        return None