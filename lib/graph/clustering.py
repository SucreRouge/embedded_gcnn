from six.moves import xrange

import numpy as np
import scipy.sparse as sp


def normalized_cut(adj, rid=None):
    if rid is None:
        np.random.seed()
        rid = np.random.permutation(np.arange(adj.shape[0]))

    n = adj.shape[0]
    cluster_map = np.zeros(n, np.int32)
    marked = np.zeros(n, np.bool)
    clustercount = 0

    # Sort by row index.
    rows, cols, weights = sp.find(adj)
    perm = np.argsort(rows)
    rows = rows[perm]
    cols = cols[perm]
    weights = weights[perm]
    degree = np.array(adj.sum(axis=0)).flatten()

    # Get the beginning indices and the count of every row.
    _, rowstart, rowlength = np.unique(
        rows, return_index=True, return_counts=True)

    for r in xrange(n):
        # Iterate randomly.
        tid = rid[r]

        if not marked[tid]:
            marked[tid] = True
            wmax = 0.0
            rs = rowstart[tid]
            bestneighbor = -1

            # Find best neighbor (Localized Normcal Cut).
            for c in range(rowlength[tid]):
                nid = cols[rs + c]
                tval = weights[rs + c] * (1.0 / degree[tid] + 1.0 / degree[nid]
                                          ) if not marked[nid] else 0.0
                if tval > wmax:
                    wmax = tval
                    bestneighbor = nid

            cluster_map[tid] = clustercount
            if bestneighbor > -1:
                cluster_map[bestneighbor] = clustercount
                marked[bestneighbor] = True
            clustercount += 1

    return cluster_map
