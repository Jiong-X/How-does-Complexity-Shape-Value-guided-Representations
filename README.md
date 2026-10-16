# Maze complexity measures

Code for generating the maze set and computing the complexity measures for each maze.

`Complexity_Measures.ipynb` does the following:

1. builds the maze set: the 12 original lateralized and 12 non-lateralized mazes, plus 100 new hemifield-balanced mazes
2. creates 100 start/goal (S/G) variants of each layout
3. computes layout measures once per base layout: symmetry, obstacle spacing, obstacle shape, edge density and local entropy
4. computes optimal path measures for every S/G variant
5. runs value-guided construal (VGC) on every solvable maze and computes a lateralization score from the optimal construal
6. summarises everything at the layout level

## Folder layout

```
.
├── Complexity_Measures.ipynb
├── visualize_mazes.py      # draws the mazes
├── data/
│   ├── mazes_Lateralized.json
│   └── mazes_Nonlateralized.json
├── results/
│   ├── mazes_generated.json      # the 100 generated layouts
│   ├── mazes_sg_variants.json    # all S/G variants
│   └── *.csv                     # written when the notebook runs
├── environment.yml
└── requirements.txt
```

## Setup

```bash
conda env create -f environment.yml
conda activate vgc
```

The VGC model itself (`vgc_project`) isn't included in this repo. It comes from Ho et al. (2022), *People construct simplified mental representations to plan*, and the code is linked from the paper's OSF page: https://doi.org/10.17605/OSF.IO/ZPQ69

Install it into the same environment, or put the `vgc_project/` folder next to the notebook, so that this import works:

```python
from vgc_project.vgc import value_guided_construal
```

## Running

Open the notebook from the repo root and run it top to bottom. The paths in the notebook are relative to the root.

The VGC step (section 6) is by far the slowest part. It runs in parallel and leaves 3 cores free. Its output is saved to `results/maze_with_path_complexity_metrics.csv` as soon as it finishes, so you can start a later run from section 7 without redoing VGC.

## Drawing the mazes

```bash
python visualize_mazes.py                 # overview page + one page of variants per layout
python visualize_mazes.py --individual    # also one PNG per maze (~12.5k files)
python visualize_mazes.py --ids grid-003-l grid-003-l-SG07 --labels

# just the 100 generated layouts the PCA was trained on, on one page
python visualize_mazes.py --files results/mazes_generated.json --overview-only --out figures/pca_training
```

Figures go to `figures/`, which is git-ignored. Walls are black, obstacles orange, S/G blue and the optimal path red. Mazes with no S-G path are marked "(no path)" in the title. This applies to 42 of the 100 generated base layouts: obstacles block their original S/G, and they're left out of the VGC step. All of their S/G variants are solvable.

## Outputs

| File | One row per | Contents |
|---|---|---|
| `results/mazes_generated.json` | new base maze | the 100 generated layouts (`grid-012-l` … `grid-111-l`) |
| `results/mazes_sg_variants.json` | S/G variant | every `<base_id>-SGxx` maze |
| `results/maze_complexity_metrics.csv` | maze (base + S/G variants) | layout and optimal path measures |
| `results/maze_with_path_complexity_metrics.csv` | solvable maze | the above plus the optimal construal, construal size, L/R counts and lateralization score |
| `results/structure_metrics.csv` | base layout | layout measures, plus path and VGC measures averaged over the S/G variants |

The CSVs in `results/` are git-ignored because they're large. The two JSON files are committed, so the exact mazes used stay with the code.

## Settings worth knowing

- `INV_TEMP = 10`: inverse temperature passed to VGC as `construal_inverse_temp`
- `n_variants_per_maze=100` and `min_manhattan=10` (section 3): how many S/G variants each layout gets, and the minimum distance between S and G
- `generate_many(100, TEMPLATE, blocks_per_obstacle=4, seed=123)`: the new mazes

Maze generation uses Python's `random` with fixed seeds. The mazes it produces depend on the Python version, because tuple hashing changed in Python 3.8. Use Python 3.7 to reproduce the original set.
