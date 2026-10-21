"""
Small helpers shared by the notebook and the scripts.

Maze encoding: list of row strings with
  '.' free, '#' wall, '0'-'5' obstacles, 'S' start, 'G' goal.
"""

import heapq

import numpy as np

DIRS4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
WALKABLE = (".", "S", "G")


def to_grid(maze):
    """list of row strings -> 2D char array"""
    return np.array([list(row) for row in maze])


def get_obstacle_labels(maze):
    return sorted({ch for row in maze for ch in row if ch.isdigit()})


def shortest_path(maze):
    """
    Shortest S->G path as a list of (row, col), or None if G can't be reached.

    A* over (cell, previous direction), so that among equally short paths the
    one with the fewest turns is returned.
    """
    grid = to_grid(maze)
    H, W = grid.shape
    if not (grid == "S").any() or not (grid == "G").any():
        return None

    start = tuple(np.argwhere(grid == "S")[0])
    goal = tuple(np.argwhere(grid == "G")[0])

    def h(r, c):
        # Manhattan distance, admissible on a 4-connected grid
        return abs(r - goal[0]) + abs(c - goal[1])

    INF = (float("inf"), float("inf"))
    # heap entries: (f_steps, f_turns, g_steps, g_turns, r, c, prev_dir)
    pq = [(h(*start), 0, 0, 0, start[0], start[1], None)]
    best = {(start[0], start[1], None): (0, 0)}
    parent = {}

    while pq:
        _, _, g_steps, g_turns, r, c, prev_dir = heapq.heappop(pq)
        state = (r, c, prev_dir)
        if best.get(state, INF) < (g_steps, g_turns):
            continue  # stale entry

        if (r, c) == goal:
            path = [(r, c)]
            while state in parent:
                state = parent[state]
                path.append((state[0], state[1]))
            return path[::-1]

        for d in DIRS4:
            nr, nc = r + d[0], c + d[1]
            if not (0 <= nr < H and 0 <= nc < W) or grid[nr, nc] not in WALKABLE:
                continue
            new_g = (g_steps + 1, g_turns + (0 if prev_dir is None or d == prev_dir else 1))
            nxt = (nr, nc, d)
            if new_g < best.get(nxt, INF):
                best[nxt] = new_g
                parent[nxt] = state
                heapq.heappush(pq, (new_g[0] + h(nr, nc), new_g[1], new_g[0], new_g[1], nr, nc, d))

    return None
