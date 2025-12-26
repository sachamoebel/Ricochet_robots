import threading
import time

class SolverThread(threading.Thread):
    def __init__(self, solver, start_pos, target_robot, target_cell):
        super().__init__()
        self.solver = solver
        self.start_pos = start_pos
        self.target_robot = target_robot
        self.target_cell = target_cell

        self.result = None
        self.found = False
        self.start_time = time.time() # Enregistre l'heure de début
        self.time_taken = 0

    def run(self):
        path = self.solver.solve(self.start_pos, self.target_robot, self.target_cell)
        self.time_taken = time.time() - self.start_time
        self.result = path
        self.found = True

  