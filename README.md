# Ricochet Robots: AI Solver & Game Engine

A high-performance Python implementation of the board game Ricochet Robots (Rasende Roboter). This project features a modular architecture, a custom 256-bit Bitboard physics engine, and an asynchronous A Search* solver capable of finding optimal solutions in complex state spaces.

## Key Technical Highlights

### Advanced AI Solver
The project implements a highly optimized **A* Search Algorithm** to navigate the game's combinatorial explosion:
*   **Optimal Pathfinding:** Uses a priority queue (`heapq`) to explore states based on the cost-to-reach plus an estimated cost-to-goal ($f = g + h$).
*   **Admissible Static Heuristic:** Features a pre-computed **Distance Map** generated via a reverse **BFS** from the target. This ensures the AI always finds the mathematically shortest path.
*   **Move Pruning:** Implements axis-based pruning (forbidding immediate reversal of a robot's movement) to significantly reduce the search tree branching factor.
*   **Symmetry Breaking:** The solver handles robot symmetry by treating interchangeable "helper" robots as a single state, preventing redundant calculations.

### Bitboard Engine
To overcome the overhead of Python's object handling, I developed a custom physics engine using **Bitboards**.
*   **Performance:** Robot positions and walls are represented as 256-bit integers. Collisions and "sliding" movements are calculated using bitwise shifts and masks.
*   **Efficiency:** This approach allows for millions of state evaluations per second, providing a **40x speedup** over traditional coordinate-based list/set logic.

### Benchmarking & Generation
The project includes a toolset to validate performance against the standards set in the research paper *["Solving Ricochet Robots with Search Algorithms"](https://people.ciirc.cvut.cz/~janotmik/ICAART-23.pdf)*:
*   **Dynamic Generator:** Creates random instances (32x32, 96x96) respecting the "Blocking Stripes" and "2x2 Islands" rules from Section 5.1 of the paper.
*   **Data Visualization:** Integrated Matplotlib suite to plot the correlation between solution depth and computation time.

## Project Structure

The project follows a clean, modular architecture:

```text
├── src/
│   ├── core/         # Bitboard logic, board state, and configurations
│   ├── ai/           # A* Solver, BFS heuristics, and threading
│   └── ui/           # Pygame rendering, scrollable HUD, and event handling
├── tools/            # Research-based instance generator
├── assets/           # Saved game data and benchmarks
├── main.py           # Application entry point
└── requirements.txt  # Project dependencies
```

## Features
*   **Full Game Loop:** From main menu to player selection and bidding.
*   **Interactive Bidding:** Players can input bids up to 99; includes backspace correction and turn management.
*   **Scrollable HUD:** A custom-built scrollable side panel for managing large numbers of players.
*   **AI Demonstration:** Press `S` during the solving phase to watch the AI reset the board and execute the optimal solution step-by-step.

## Installation & Usage

### Prerequisites
*   Python 3.10 or higher
*   pip

### Setup
```bash
# Clone the repository
git clone https://github.com/sacha1403/Rasende_Roboter.git
cd Rasende_Roboter

# Install dependencies
pip install -r requirements.txt
```

### Run the game
```bash
python main.py
```

### Run the benchmark tool
```bash
python tools/instance_generator.py
```
