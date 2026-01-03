# solver_fast.py
import heapq
# Import the class from your previous file (Solver 2)
# Ensure your previous file is named 'solver_ameliore.py' or adjust import
from solverV2 import SolverV2 

class SolverV3(SolverV2):
    """
    Solver 3: Weighted A* with Move Ordering.
    Drastically faster, slightly less optimal.
    """
    
    def solve(self, start_pos, target_robot_idx, target_cell):
        # 1. Precompute the wall-only distances (Same as Solver 2)
        self.precompute_bfs_heuristic(target_cell)
        
        start_pos = tuple(start_pos)
        
        # Configuration for Weighted A*
        # WEIGHT = 1.0 -> Standard A* (Optimal, Slower)
        # WEIGHT = 1.3 -> Balanced (Much Faster, rarely suboptimal)
        # WEIGHT = 2.0 -> Greedy (Instant, often suboptimal)
        WEIGHT = 1.3 
        
        # Initial Heuristic
        h_start = self.calculate_heuristic(start_pos, target_robot_idx)
        
        # Priority Queue Structure: 
        # (f_score, h_score, g_score, positions_tuple, path, last_move)
        # We put 'h_score' second so Python breaks ties by choosing the state closer to the goal.
        queue = [(h_start * WEIGHT, h_start, 0, start_pos, [], (-1, ""))]
        
        visited = {}

        # 2. Optimization: Move Ordering List
        # We always want to try moving the target robot FIRST.
        robots_indices = list(range(len(start_pos)))
        if target_robot_idx is not None:
            # Move target index to the front of the list
            robots_indices.remove(target_robot_idx)
            robots_indices.insert(0, target_robot_idx)

        # Counter for stats
        nodes_explored = 0

        while queue:
            nodes_explored += 1
            f, h, g, positions, path, last_move = heapq.heappop(queue)
            last_r, last_d = last_move

            # Check success
            if target_robot_idx is not None:
                if positions[target_robot_idx] == target_cell: 
                    return path, nodes_explored
            else:
                if any(p == target_cell for p in positions): 
                    return path, nodes_explored

            # Visited Check
            state_key = positions
            if visited.get(state_key, 999) <= g: continue
            visited[state_key] = g

            # Prepare mask for movement
            occ_mask = 0
            for p in positions: occ_mask |= (1 << p)

            # Generate Moves (Using optimized order)
            for r_i in robots_indices:
                # Optimization: Don't reverse direction immediately
                forbidden_dirs = []
                if r_i == last_r:
                    if last_d in ['N', 'S']: forbidden_dirs = ['N', 'S']
                    else: forbidden_dirs = ['E', 'W']

                current_robot_pos = positions[r_i]
                move_mask = occ_mask ^ (1 << current_robot_pos)

                for d in ['N', 'S', 'E', 'W']:
                    if d in forbidden_dirs: continue
                    
                    # Reuse the efficient get_destination from Solver 2
                    new_p = self.get_destination(current_robot_pos, d, move_mask)
                    
                    if new_p != current_robot_pos:
                        new_pos_list = list(positions)
                        new_pos_list[r_i] = new_p
                        new_pos_tuple = tuple(new_pos_list)
                        
                        new_g = g + 1
                        new_h = self.calculate_heuristic(new_pos_tuple, target_robot_idx)
                        
                        # WEIGHTED A* FORMULA
                        new_f = new_g + (new_h * WEIGHT)
                        
                        heapq.heappush(queue, (new_f, new_h, new_g, new_pos_tuple, path + [(r_i, d)], (r_i, d)))
        
        return None, nodes_explored