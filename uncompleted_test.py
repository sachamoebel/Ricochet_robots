import pickle
import time
import random
import collections
import heapq
from instance_generator import GeneratedBoard
from solver import RicochetSolver
from solverV2 import SolverV2 

try:
    with open("difficult_boards.pkl", "rb") as f:
        data = pickle.load(f)
    print(f"File contents: {type(data)}")
    print(f"List length: {len(data)}")
    if len(data) > 0:
        print(f"First item type: {type(data[0])}")
except Exception as e:
    print(e)

FILENAME = "difficult_boards.pkl"

def run_test():
    print(f"--- Loading data from {FILENAME} ---")
    
    try:
        with open(FILENAME, "rb") as f:
            cases = pickle.load(f)
    except FileNotFoundError:
        print("Error: The file does not exist. Run the benchmark first.")
        return

    print(f"Loaded {len(cases)} difficult cases.")

    if len(cases) == 0:
        print("The file is empty. You need to re-run the benchmark.")
        return

    # --- STEP 2: SOLVE ---
    success_count = 0
    
    for i, data in enumerate(cases):
        # Handle unpacking based on your data structure
        try:
            # Try unpacking 4 values
            board, start_pos, target_idx, target_cell = data
        except ValueError:
            # Fallback for 3 values
            board, start_pos, target_cell = data
            target_idx = None

        print(f"\nRe-testing Case #{i+1}...")
        
        solver1 = RicochetSolver(board)
        solver2 = Solver(board)

        start_time2 = time.time()
        path2 = solver2.solve(start_pos, target_robot_idx=target_idx, target_cell=target_cell)
        duration2 = time.time() - start_time2
        
        start_time = time.time()
        path = solver1.solve(start_pos, target_robot_idx=target_idx, target_cell=target_cell)
        duration = time.time() - start_time

        if path:
            print(f"✅ Solved in {duration:.4f}s ({len(path)} moves)")
            success_count += 1
        else:
            print(f"❌ Failed again ({duration:.4f}s)")


        if path2:
            print(f"✅ Solved in {duration2:.4f}s ({len(path2)} moves)")
            success_count += 1
        else:
            print(f"❌ Failed again ({duration2:.4f}s)")
        continue
    print(f"\nSummary: Solved {success_count}/{len(cases)}")

if __name__ == "__main__":
    run_test()