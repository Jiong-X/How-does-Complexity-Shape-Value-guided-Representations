"""
Draw the mazes.

By default this makes:
  figures/overview_base_layouts.png   all base layouts on one page
  figures/variants/<base_id>.png      one page per layout: the base maze + all its S/G variants

With --individual it also saves one PNG per maze to figures/mazes/ (~12.5k files).

Colours: walls black, obstacles orange, S/G blue, optimal path red.

Usage (from the repo root):
  python visualize_mazes.py
  python visualize_mazes.py --individual
  python visualize_mazes.py --ids grid-003-l grid-003-l-SG07
  python visualize_mazes.py --no-path --labels
  python visualize_mazes.py --files mazes/mazes_generated.json --overview-only --out figures/pca_training
"""

import argparse
import heapq
import json
import math
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")  # no window, just files
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

MAZE_FILES = [
    "mazes/mazes_Lateralized.json",
    "mazes/mazes_Nonlateralized.json",
    "mazes/mazes_generated.json",
    "mazes/mazes_sg_variants.json",
]

CMAP = ListedColormap(["white", "black", "orange", "royalblue"])
DIRS4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def load_mazes(files):
    mazes = {}
    for path in files:
        if not os.path.exists(path):
            print(f"skipping {path} (not found)")
            continue
        with open(path, "r", encoding="utf-8") as f:
            mazes.update(json.load(f))
    return mazes


def base_id_of(maze_id):
    return maze_id.split("-SG")[0]


# ---------------------------------------------------------------------------
# optimal path (same A* as the notebook: shortest, then fewest turns)
# ---------------------------------------------------------------------------

def shortest_path(maze):
    grid = np.array([list(row) for row in maze])
    H, W = grid.shape
    if not (grid == "S").any() or not (grid == "G").any():
        return None
    start = tuple(np.argwhere(grid == "S")[0])
    goal = tuple(np.argwhere(grid == "G")[0])

    def h(r, c):
        return abs(r - goal[0]) + abs(c - goal[1])

    INF = (float("inf"), float("inf"))
    pq = [(h(*start), 0, 0, 0, start[0], start[1], None)]
    best = {(start[0], start[1], None): (0, 0)}
    parent = {}

    while pq:
        _, _, g_steps, g_turns, r, c, prev_dir = heapq.heappop(pq)
        state = (r, c, prev_dir)
        if best.get(state, INF) < (g_steps, g_turns):
            continue
        if (r, c) == goal:
            path = [(r, c)]
            while state in parent:
                state = parent[state]
                path.append((state[0], state[1]))
            return path[::-1]
        for d in DIRS4:
            nr, nc = r + d[0], c + d[1]
            if not (0 <= nr < H and 0 <= nc < W) or grid[nr, nc] not in (".", "S", "G"):
                continue
            new_g = (g_steps + 1, g_turns + (0 if prev_dir is None or d == prev_dir else 1))
            nxt = (nr, nc, d)
            if new_g < best.get(nxt, INF):
                best[nxt] = new_g
                parent[nxt] = state
                heapq.heappush(pq, (new_g[0] + h(nr, nc), new_g[1], new_g[0], new_g[1], nr, nc, d))
    return None


# ---------------------------------------------------------------------------
# drawing
# ---------------------------------------------------------------------------

def draw_maze(ax, maze, title=None, show_path=True, labels=False, title_size=9, show_sg=True):
    grid = np.array([list(row) for row in maze])
    H, W = grid.shape

    codes = np.zeros((H, W))
    codes[grid == "#"] = 1
    codes[np.vectorize(str.isdigit)(grid)] = 2
    if show_sg:
        codes[(grid == "S") | (grid == "G")] = 3
    ax.imshow(codes, cmap=CMAP, interpolation="nearest", vmin=0, vmax=3)

    # thin cell borders (drawn as lines - much faster than tick-based gridlines)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.vlines(np.arange(-.5, W), -.5, H - .5, color="lightgray", linewidth=0.4)
    ax.hlines(np.arange(-.5, H), -.5, W - .5, color="lightgray", linewidth=0.4)

    for ch in (("S", "G") if show_sg else ()):
        rc = np.argwhere(grid == ch)
        if len(rc):
            ax.text(rc[0][1], rc[0][0], ch, ha="center", va="center",
                    color="white", fontsize=6, fontweight="bold")

    if labels:
        for r, c in np.argwhere(np.vectorize(str.isdigit)(grid)):
            ax.text(c, r, grid[r, c], ha="center", va="center", fontsize=5)

    if show_path:
        path = shortest_path(maze)
        if path:
            ax.plot([c for _, c in path], [r for r, _ in path], color="red", linewidth=1.5)
        else:
            title = f"{title} (no path)" if title else "no path"

    if title:
        ax.set_title(title, fontsize=title_size)
    ax.set_aspect("equal")


def draw_sheet(mazes, ids, out_path, title, ncols=10, cell=2.0, **draw_kwargs):
    """Many mazes on one page."""
    n = len(ids)
    ncols = min(ncols, n)
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(cell * ncols, cell * nrows + 0.8))
    axes = np.ravel(axes)

    for ax, maze_id in zip(axes, ids):
        draw_maze(ax, mazes[maze_id], title=maze_id, title_size=7, **draw_kwargs)
    for ax in axes[n:]:
        ax.axis("off")

    # tight_layout is slow with ~100 axes, so set the spacing by hand
    h = fig.get_figheight()
    fig.suptitle(title, fontsize=14, y=1 - 0.2 / h, va="top")
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=1 - 0.8 / h,
                        wspace=0.1, hspace=0.3)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def draw_single(maze, maze_id, out_path, **draw_kwargs):
    fig, ax = plt.subplots(figsize=(4, 4))
    draw_maze(ax, maze, title=maze_id, title_size=12, **draw_kwargs)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Draw the mazes.")
    p.add_argument("--files", nargs="+", default=MAZE_FILES, help="maze JSON files to load")
    p.add_argument("--out", default="figures", help="output folder")
    p.add_argument("--ids", nargs="+", help="only draw these maze ids (one PNG each)")
    p.add_argument("--overview-only", action="store_true", help="only draw the overview page (no variant pages)")
    p.add_argument("--individual", action="store_true", help="also save one PNG per maze")
    p.add_argument("--no-path", action="store_true", help="don't draw the optimal path")
    p.add_argument("--labels", action="store_true", help="write the obstacle label in each obstacle cell")
    args = p.parse_args()

    mazes = load_mazes(args.files)
    if not mazes:
        raise SystemExit("No mazes loaded - check the paths in --files.")
    draw_kwargs = {"show_path": not args.no_path, "labels": args.labels}

    single_dir = os.path.join(args.out, "mazes")

    # just a handful of specific mazes
    if args.ids:
        os.makedirs(single_dir, exist_ok=True)
        for maze_id in args.ids:
            if maze_id not in mazes:
                print(f"{maze_id} not found")
                continue
            draw_single(mazes[maze_id], maze_id, os.path.join(single_dir, f"{maze_id}.png"), **draw_kwargs)
        print(f"saved to {single_dir}")
        return

    base_ids = [k for k in mazes if "-SG" not in k]
    variants = {b: [] for b in base_ids}
    for k in mazes:
        if "-SG" in k and base_id_of(k) in variants:
            variants[base_id_of(k)].append(k)

    os.makedirs(args.out, exist_ok=True)

    # 1. every base layout on one page
    if base_ids:
        draw_sheet(mazes, base_ids, os.path.join(args.out, "overview_base_layouts.png"),
                   f"Base layouts (n = {len(base_ids)})", **draw_kwargs)
        print(f"overview: {len(base_ids)} layouts")
    else:
        print("no base layouts in these files - skipping the overview and variant pages")

    # 2. one page per layout with all its S/G variants
    if not args.overview_only and base_ids:
        var_dir = os.path.join(args.out, "variants")
        os.makedirs(var_dir, exist_ok=True)
        for i, b in enumerate(base_ids, 1):
            draw_sheet(mazes, [b] + sorted(variants[b]), os.path.join(var_dir, f"{b}.png"),
                       f"{b} and its S/G variants", **draw_kwargs)
            print(f"\rvariant sheets: {i}/{len(base_ids)}", end="", flush=True)
        print()

    # 3. optionally, every maze on its own
    if args.individual:
        os.makedirs(single_dir, exist_ok=True)
        for i, (maze_id, maze) in enumerate(mazes.items(), 1):
            draw_single(maze, maze_id, os.path.join(single_dir, f"{maze_id}.png"), **draw_kwargs)
            if i % 100 == 0 or i == len(mazes):
                print(f"\rsingle mazes: {i}/{len(mazes)}", end="", flush=True)
        print()

    print(f"done - figures in {os.path.abspath(args.out)}")


if __name__ == "__main__":
    main()
