import threading
import time

class SolverThread(threading.Thread):
    def __init__(self, solver, start_pos, target_robot, target_cell):
        super().__init__()
        self.solver = solver
        self.start_pos = start_pos
        self.target_robot = target_robot
        self.target_cell = target_cell
        
        self.noeuds_explores = 0
        self.result = None
        self.found = False
        self.start_time = time.time()
        self.time_taken = 0

    def run(self):
        path, nb_noeuds_explores = self.solver.solve(self.start_pos, self.target_robot, self.target_cell)
        self.noeuds_explores = nb_noeuds_explores
        self.time_taken = time.time() - self.start_time
        self.result = path
        self.found = True

  