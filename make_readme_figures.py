"""
Figures for the README: the layouts with the lowest and highest scores on
the first three principal components.

Reads pca/pca_scores.csv (written by maze_pca.R) and the maze JSON files.
By default only the 24 original mazes are shown - the held-out test set,
projected onto the PCA fitted on the 100 generated layouts. Use --set
generated or --set all to pick from the training layouts instead. Writes docs/pc1_extremes.png ... docs/pc3_extremes.png.

Usage (from the repo root):
  Rscript maze_pca.R
  python make_readme_figures.py
  python make_readme_figures.py --n 4 --pcs PC1 PC2 PC3 PC4
"""

import argparse
import json
import os

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from visualize_mazes import draw_maze


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scores", default="pca/pca_scores.csv")
    p.add_argument("--mazes", nargs="+", default=[
        "mazes/mazes_Lateralized.json",
        "mazes/mazes_Nonlateralized.json",
        "mazes/mazes_generated.json",
    ])
    p.add_argument("--out", default="docs")
    p.add_argument("--pcs", nargs="+", default=["PC1", "PC2", "PC3"])
    p.add_argument("--n", type=int, default=5, help="mazes per end of each PC")
    p.add_argument("--set", choices=["original", "generated", "all"], default="original",
                   help="which layouts to pick from (default: the 24 original/test mazes)")
    args = p.parse_args()

    scores = pd.read_csv(args.scores, index_col="base_id")
    if args.set != "all":
        scores = scores[scores["set"] == args.set]
    mazes = {}
    for path in args.mazes:
        with open(path, "r", encoding="utf-8") as f:
            mazes.update(json.load(f))
    os.makedirs(args.out, exist_ok=True)

    for pc in args.pcs:
        ranked = scores[pc].sort_values()
        rows = [("Lowest", ranked.index[:args.n]), ("Highest", ranked.index[::-1][:args.n])]

        fig, axes = plt.subplots(2, args.n, figsize=(2.1 * args.n, 5.0))
        for r, (label, ids) in enumerate(rows):
            for c, maze_id in enumerate(ids):
                # path and S/G are left out: the path measures in the PCA are
                # averages over all S/G variants, not the base S/G
                tag = " (original)" if args.set == "all" and scores.loc[maze_id, "set"] == "original" else ""
                draw_maze(axes[r, c], mazes[maze_id], show_path=False, show_sg=False,
                          title=f"{maze_id}{tag}\n{pc} = {ranked[maze_id]:.2f}", title_size=8)
            axes[r, 0].set_ylabel(label, fontsize=11)

        which = {"original": "original (test) mazes", "generated": "generated (training) layouts",
                 "all": "all layouts"}[args.set]
        fig.suptitle(f"{pc}: lowest vs highest scoring {which}", fontsize=13)
        fig.subplots_adjust(left=0.05, right=0.99, top=0.86, bottom=0.02, wspace=0.08, hspace=0.35)
        out_path = os.path.join(args.out, f"{pc.lower()}_extremes.png")
        fig.savefig(out_path, dpi=130)
        plt.close(fig)
        print("saved", out_path)


if __name__ == "__main__":
    main()
