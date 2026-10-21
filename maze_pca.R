# PCA of the maze complexity measures
#
# Fits a PCA on the 100 generated layouts (grid-012-l ... grid-111-l), checks
# how many components to keep with a permutation test, bootstraps the loadings,
# and scores every layout - the 24 original mazes are projected onto the
# components fitted on the generated ones.
#
# Run from the repo root:   Rscript maze_pca.R
#
# Input:   metrics/structure_metrics.csv   (one row per layout, from the notebook)
# Outputs: pca/pca_scores.csv          PC scores for all 124 layouts
#          pca/pca_loadings.csv        loadings + bootstrap 95% CIs (PC1-4)
#          pca/pca_variance.csv        variance explained vs permutation null
#          pca/pca_model.rds           the fitted prcomp object
#          docs/pca/PC*_loadings.png, docs/pca/scree_permutation.png

library(ggplot2)
library(boot)

set.seed(123)
N_BOOT <- 1000
N_PERM <- 1000
N_PLOT <- 4          # how many PCs get loading plots / CIs

dir.create("pca", showWarnings = FALSE)
dir.create(file.path("docs", "pca"), recursive = TRUE, showWarnings = FALSE)


# ---------------------------------------------------------------------------
# 1. Data
# ---------------------------------------------------------------------------

metrics <- read.csv("metrics/structure_metrics.csv", stringsAsFactors = FALSE)

# measures that go into the PCA, with readable names for the plots
features <- c(
  horizontal_symmetry         = "Horizontal Symmetry",
  vertical_symmetry           = "Vertical Symmetry",
  n_unique_obs                = "Number of Unique Obstacles",
  edge_density                = "Edge Density",
  local_entropy_3             = "Local Entropy",
  mean_sim                    = "Mean Pairwise Similarity",
  mean_dis                    = "Mean Pairwise Distance",
  mean_roughness              = "Mean Roughness",
  mean_nn_distance            = "Mean Nearest-Neighbor Distance",
  var_pairwise_dist           = "Variance in Pairwise Distance",
  var_nn_dist                 = "Variance in Nearest-Neighbor Distance",
  mean_optimal_path_length    = "Mean Optimal Path Length",
  mean_n_turns                = "Mean Number of Turns",
  mean_turn_to_path_ratio     = "Mean Turn to Path Ratio",
  mean_optimal_construal_size = "Mean Optimal Construal Size"
)

# the 24 original mazes are grid-000 ... grid-011 (-l and -n); everything else
# was generated and is used to fit the PCA
maze_num <- as.integer(sub("^grid-(\\d+)-.*$", "\\1", metrics$base_id))
metrics$set <- ifelse(maze_num < 12, "original", "generated")

X       <- metrics[, names(features)]
train_X <- X[metrics$set == "generated", ]

# drop anything that doesn't vary in the training set (it would break scaling)
keep    <- sapply(train_X, function(x) length(unique(x)) > 1)
train_X <- train_X[, keep]
X       <- X[, keep]
features <- features[keep]
p <- ncol(train_X)

cat(nrow(train_X), "training layouts,", p, "measures\n")


# ---------------------------------------------------------------------------
# 2. PCA
# ---------------------------------------------------------------------------

pca <- prcomp(train_X, center = TRUE, scale. = TRUE)

# The sign of a PC is arbitrary. Fix it so each PC points the same way every
# time it's run: the anchor measure gets a positive loading. Later PCs use
# whichever measure loads most strongly.
anchors <- c(PC1 = "local_entropy_3",
             PC2 = "mean_optimal_path_length",
             PC3 = "n_unique_obs",
             PC4 = "edge_density")

for (j in seq_len(ncol(pca$rotation))) {
  pc <- colnames(pca$rotation)[j]
  anchor <- if (pc %in% names(anchors)) anchors[[pc]] else names(which.max(abs(pca$rotation[, j])))
  if (pca$rotation[anchor, j] < 0) {
    pca$rotation[, j] <- -pca$rotation[, j]
    pca$x[, j]        <- -pca$x[, j]
  }
}

saveRDS(pca, "pca/pca_model.rds")


# ---------------------------------------------------------------------------
# 3. How many PCs? Permutation test (parallel analysis)
# ---------------------------------------------------------------------------
# Shuffle each column independently to break the correlations, refit, and
# compare each observed eigenvalue with what shuffled data gives.

real_eigen <- pca$sdev^2

perm_eigen <- t(replicate(N_PERM, {
  X_perm <- apply(train_X, 2, sample)
  prcomp(X_perm, center = TRUE, scale. = TRUE)$sdev^2
}))

variance <- data.frame(
  PC               = colnames(pca$rotation),
  eigenvalue       = real_eigen,
  var_explained    = 100 * real_eigen / sum(real_eigen),
  perm_mean        = 100 * colMeans(perm_eigen) / p,
  perm_95          = 100 * apply(perm_eigen, 2, quantile, 0.95) / p,
  p_value          = sapply(seq_len(p), function(j) mean(perm_eigen[, j] >= real_eigen[j]))
)
variance$cumulative <- cumsum(variance$var_explained)
write.csv(variance, "pca/pca_variance.csv", row.names = FALSE)
print(head(variance, 6), digits = 3)

scree <- rbind(
  data.frame(PC = seq_len(p), variance = variance$var_explained, type = "Observed"),
  data.frame(PC = seq_len(p), variance = variance$perm_95, type = "Permutation (95th pct)")
)
g <- ggplot(scree, aes(PC, variance, colour = type, linetype = type)) +
  geom_line(linewidth = 1) +
  geom_point(size = 2.5) +
  scale_colour_manual(values = c("Observed" = "#E69F00", "Permutation (95th pct)" = "grey50")) +
  scale_x_continuous(breaks = seq_len(p)) +
  labs(x = "Principal component", y = "Variance explained (%)", colour = NULL, linetype = NULL,
       title = "Observed vs permuted variance explained") +
  theme_minimal(base_size = 12) +
  theme(legend.position = c(0.75, 0.85))
ggsave("docs/pca/scree_permutation.png", g, width = 7, height = 4.5, dpi = 200)


# ---------------------------------------------------------------------------
# 4. Bootstrap the loadings
# ---------------------------------------------------------------------------
# Resample layouts, refit, and line each bootstrap PC up with the main fit
# (flip it if it points the other way) before taking means and 95% CIs.

boot_rotation <- function(data, idx) {
  as.vector(prcomp(data[idx, ], center = TRUE, scale. = TRUE)$rotation)
}
boot_res <- boot(train_X, boot_rotation, R = N_BOOT)

loadings <- do.call(rbind, lapply(seq_len(N_PLOT), function(j) {
  B   <- boot_res$t[, ((j - 1) * p + 1):(j * p)]
  ref <- pca$rotation[, j]
  flip <- sign(B %*% ref)
  flip[flip == 0] <- 1
  B <- B * as.vector(flip)
  data.frame(
    PC        = paste0("PC", j),
    variable  = colnames(train_X),
    label     = unname(features[colnames(train_X)]),
    loading   = ref,
    boot_mean = colMeans(B),
    lower     = apply(B, 2, quantile, 0.025),
    upper     = apply(B, 2, quantile, 0.975),
    row.names = NULL
  )
}))
loadings$ci_excludes_zero <- loadings$lower > 0 | loadings$upper < 0
write.csv(loadings, "pca/pca_loadings.csv", row.names = FALSE)

for (j in seq_len(N_PLOT)) {
  d <- loadings[loadings$PC == paste0("PC", j), ]
  g <- ggplot(d, aes(x = reorder(label, boot_mean), y = boot_mean, fill = ci_excludes_zero)) +
    geom_col() +
    geom_errorbar(aes(ymin = lower, ymax = upper), width = 0.2) +
    scale_fill_manual(values = c("TRUE" = "#E69F00", "FALSE" = "grey70"),
                      labels = c("TRUE" = "Excludes zero", "FALSE" = "Includes zero"),
                      name = "95% CI") +
    coord_flip() +
    labs(title = sprintf("PC%d loadings (%.1f%% of variance)", j, variance$var_explained[j]),
         x = NULL, y = "Bootstrap mean loading") +
    theme_minimal(base_size = 12)
  ggsave(sprintf("docs/pca/PC%d_loadings.png", j), g, width = 8, height = 5, dpi = 200)
}


# ---------------------------------------------------------------------------
# 5. Scores for every layout
# ---------------------------------------------------------------------------
# The originals weren't used to fit the PCA; predict() projects them with the
# training centre/scale and rotation.

scores <- predict(pca, X)
out <- data.frame(base_id = metrics$base_id, set = metrics$set, round(scores, 4))
write.csv(out, "pca/pca_scores.csv", row.names = FALSE)

cat("done - wrote pca/pca_*.csv and docs/pca/*.png\n")
