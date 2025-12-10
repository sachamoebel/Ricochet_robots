from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from board import Board, GridPosition
from entities import Robot


@dataclass(frozen=True)
class RobotConfiguration:
    positions: Tuple[GridPosition, ...]

    @classmethod
    def from_robots(cls, robots: Sequence[Robot]) -> "RobotConfiguration":
        return cls(tuple((r.col, r.row) for r in robots))

    def to_robots(self, robots: Sequence[Robot]) -> None:
        if len(robots) != len(self.positions):
            raise ValueError("Nombre de robots incompatible avec la configuration")
        for robot, (col, row) in zip(robots, self.positions, strict=True):
            robot.col = col
            robot.row = row

    def with_robot_moved(self, robot_index: int, new_pos: GridPosition) -> "RobotConfiguration":
        if not (0 <= robot_index < len(self.positions)):
            raise IndexError("Indice de robot invalide")
        positions = list(self.positions)
        positions[robot_index] = new_pos
        return RobotConfiguration(tuple(positions))


@dataclass(frozen=True)
class Move:
    robot_index: int
    start: GridPosition
    end: GridPosition


@dataclass(frozen=True)
class SearchState:
    configuration: RobotConfiguration
    move_count: int = 0


class GraphSearchDomain:
    def initial_state(self) -> SearchState:
        raise NotImplementedError

    def is_goal(self, state: SearchState) -> bool:
        raise NotImplementedError

    def successors(self, state: SearchState) -> Iterable[tuple[Move, SearchState]]:
        raise NotImplementedError

    def heuristic(self, state: SearchState) -> float:
        return 0.0


def generate_successors(board: Board, configuration: RobotConfiguration) -> List[tuple[Move, RobotConfiguration]]:
    results: List[tuple[Move, RobotConfiguration]] = []
    positions = list(configuration.positions)

    for robot_index, (col, row) in enumerate(positions):
        occupied = {(c, r) for i, (c, r) in enumerate(positions) if i != robot_index}
        targets = board.get_move_targets(col, row, occupied)
        for target_col, target_row in targets:
            move = Move(
                robot_index=robot_index,
                start=(col, row),
                end=(target_col, target_row),
            )
            new_conf = configuration.with_robot_moved(robot_index, (target_col, target_row))
            results.append((move, new_conf))

    return results
