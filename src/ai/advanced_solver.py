import heapq
import collections
import time

class SolverV2:
    def __init__(self, board):
        # We link directly to your existing board bitboards
        self.walls_n = board.walls_up
        self.walls_s = board.walls_down
        self.walls_e = board.walls_right
        self.walls_w = board.walls_left
        self.cols = board.cols
        self.rows = board.rows
        self.static_h = {}
        
        # Pre-define direction deltas for speed
        self.dirs = {
            'N': (-1, 0, self.walls_n, self.walls_s),
            'S': (1, 0, self.walls_s, self.walls_n),
            'E': (0, 1, self.walls_e, self.walls_w),
            'W': (0, -1, self.walls_w, self.walls_e)
        }

    def precompute_bfs_heuristic(self, target_idx):
        self.static_h = {target_idx: 0}
        queue = collections.deque([target_idx])
        while queue:
            curr = queue.popleft()
            d = self.static_h[curr]
            r, c = curr // self.cols, curr % self.cols
            for move_dir in ['N', 'S', 'E', 'W']:
                # Logic to determine reverse moves for BFS mapping
                dr, dc = {'N': (1, 0), 'S': (-1, 0), 'E': (0, -1), 'W': (0, 1)}[move_dir]
                stop_bit = 1 << curr
                
                # Check if there is a wall that would stop a robot coming FROM move_dir
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
        dr, dc, wall_check, next_wall_check = self.dirs[direction]
        
        while True:
            bit = 1 << (r * self.cols + c)
            if bit & wall_check: break
            
            nr, nc = r + dr, c + dc
            if not (0 <= nr < self.rows and 0 <= nc < self.cols): break
            
            next_bit = 1 << (nr * self.cols + nc)
            if next_bit & occupied_mask: break
            if next_bit & next_wall_check: break # Wall on the entry side of next cell
            
            r, c = nr, nc
            
        return r * self.cols + c

    def calculate_heuristic(self, positions, target_robot_idx):
        """
        Improved A* Estimate:
        1. Base estimate is the precomputed wall-only BFS distance.
        2. Improvement: Check if the 'optimal' next move suggested by the static BFS
           is actually physically possible given current robot positions.
           If the optimal path is blocked by another robot (stopping short), add a penalty.
        """
        # Create a mask of all robot positions
        occupied_mask = 0
        for p in positions:
            occupied_mask |= (1 << p)

        def get_single_robot_h(r_idx):
            pos = positions[r_idx]
            base_h = self.static_h.get(pos, 100) # Default high if unreachable
            
            # If we are already there, or unreachable, return base
            if base_h == 0 or base_h == 100:
                return base_h

            # Remove current robot from mask (it can't block itself)
            my_mask = occupied_mask ^ (1 << pos)
            
            can_follow_optimal = False
            
            # Check all 4 directions
            for d in ['N', 'S', 'E', 'W']:
                # 1. Determine where we WOULD go if only walls existed (Static BFS assumption)
                # We pass mask=0 to ignore other robots
                static_dest = self.get_destination(pos, d, 0)
                
                # 2. Is this move considered 'optimal' by our static map?
                # i.e. does it bring us closer to the target?
                if self.static_h.get(static_dest, 100) < base_h:
                    # 3. Can we ACTUALLY reach that destination right now?
                    # We pass the actual robot mask
                    actual_dest = self.get_destination(pos, d, my_mask)
                    
                    if actual_dest == static_dest:
                        # Yes, the path is clear. No penalty needed.
                        can_follow_optimal = True
                        break
            
            # If no direction allows us to follow the optimal static path, apply penalty
            return base_h if can_follow_optimal else base_h + 1

        if target_robot_idx is not None:
            return get_single_robot_h(target_robot_idx)
        else:
            # For multicolor (target_robot_idx is None), heuristic is min of all robots
            return min(get_single_robot_h(i) for i in range(len(positions)))

    def solve(self, start_pos, target_robot_idx, target_cell):
        self.precompute_bfs_heuristic(target_cell)
        start_pos = tuple(start_pos)
        
        # Initial Heuristic
        h_start = self.calculate_heuristic(start_pos, target_robot_idx)
        
        # Priority Queue: (f_score, g_score, positions_tuple, path, last_move)
        queue = [(h_start, 0, start_pos, [], (-1, ""))]
        visited = {}

        nb_noeuds_explores = 0

        while queue:
            nb_noeuds_explores += 1
            f, g, positions, path, last_move = heapq.heappop(queue)
            last_r, last_d = last_move

            # Check success
            if target_robot_idx is not None:
                if positions[target_robot_idx] == target_cell: return path, nb_noeuds_explores
            else:
                if any(p == target_cell for p in positions): return path, nb_noeuds_explores

            # Visited Check
            state_key = positions # positions is already a tuple
            if visited.get(state_key, 999) <= g: continue
            visited[state_key] = g

            # Prepare mask for movement
            occ_mask = 0
            for p in positions: occ_mask |= (1 << p)

            # Generate Moves
            for r_i in range(len(positions)):
                # Simple optimization: don't reverse direction immediately
                forbidden_dirs = []
                if r_i == last_r:
                    if last_d in ['N', 'S']: forbidden_dirs = ['N', 'S']
                    else: forbidden_dirs = ['E', 'W']

                current_robot_pos = positions[r_i]
                # Robot can't block itself, remove from mask for calculation
                move_mask = occ_mask ^ (1 << current_robot_pos)

                for d in ['N', 'S', 'E', 'W']:
                    if d in forbidden_dirs: continue
                    
                    new_p = self.get_destination(current_robot_pos, d, move_mask)
                    
                    if new_p != current_robot_pos:
                        # Construct new state
                        new_pos_list = list(positions)
                        new_pos_list[r_i] = new_p
                        new_pos_tuple = tuple(new_pos_list)
                        
                        # Calculate new costs
                        new_g = g + 1
                        
                        # Use improved heuristic calculation
                        new_h = self.calculate_heuristic(new_pos_tuple, target_robot_idx)
                        
                        heapq.heappush(queue, (new_g + new_h, new_g, new_pos_tuple, path + [(r_i, d)], (r_i, d)))
        return None