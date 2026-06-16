#!/usr/bin/env python3
"""Draw one TTree branch from a ROOT file.

Example:

  python scripts/inspect_branch.py --input data/full.root --branch mass
  python scripts/inspect_branch.py --input data/full.root --branch mass --min 5.0 --max 6.0
"""

import argparse
from pathlib import Path

try:
    import ROOT
except ImportError as exc:
    raise SystemExit(
        "Could not import ROOT. Run this with a Python environment that provides PyROOT."
    ) from exc


TREE_NAME = "DecayTree"


# ---------------------------------------------------------------------------
# Command-line options
# ---------------------------------------------------------------------------

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--input", required=True, help="Input ROOT file")
parser.add_argument("--branch", required=True, help="Branch to draw")
parser.add_argument("--plot", default=None, help="Output plot file")
parser.add_argument("--tree", default=TREE_NAME, help="Name of the TTree")
parser.add_argument("--min", type=float, default=None, help="Minimum x-axis value")
parser.add_argument("--max", type=float, default=None, help="Maximum x-axis value")
parser.add_argument("--bins", type=int, default=80, help="Number of histogram bins")
args = parser.parse_args()

if (args.min is None) != (args.max is None):
    raise ValueError("Please give both --min and --max, or neither.")

if args.min is not None and args.min >= args.max:
    raise ValueError("--min must be smaller than --max")

if args.plot is None:
    args.plot = f"plots/{Path(args.input).stem}_{args.branch}.png"


# Batch mode writes the plot to a file without opening a graphical window.
ROOT.gROOT.SetBatch(True)
Path(args.plot).parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Open the ROOT file and get the TTree
# ---------------------------------------------------------------------------

print("\n=== 1. Open the ROOT file and read the TTree ===")

root_file = ROOT.TFile.Open(args.input)
if not root_file or root_file.IsZombie():
    raise OSError(f"Could not open {args.input}")

tree = root_file.Get(args.tree)
if tree is None:
    raise KeyError(f"Could not find tree {args.tree} in {args.input}")

branch = tree.GetBranch(args.branch)
if branch is None:
    raise KeyError(f"Could not find branch {args.branch} in tree {args.tree}")

print(f"Input file: {args.input}")
print(f"Tree name:  {args.tree}")
print(f"Branch:     {args.branch}")
print(f"Entries:    {tree.GetEntries()}")


# ---------------------------------------------------------------------------
# 2. Draw the branch into a histogram
# ---------------------------------------------------------------------------

print("\n=== 2. Draw the branch ===")

canvas = ROOT.TCanvas("inspect_canvas", "data inspection", 800, 600)

# If no range is given, ask ROOT for the minimum and maximum value in the tree.
if args.min is None:
    x_min = tree.GetMinimum(args.branch)
    x_max = tree.GetMaximum(args.branch)
else:
    x_min = args.min
    x_max = args.max

# Create the histogram ourselves, then fill it from the tree.
# This avoids relying on the return value of TTree.Draw, which can be different
# in different PyROOT versions.
histogram = ROOT.TH1D("branch_hist", "", args.bins, x_min, x_max)
tree.Project("branch_hist", args.branch)

if histogram.GetEntries() <= 0:
    raise RuntimeError(f"No entries were drawn for branch {args.branch}")

histogram.SetTitle(f"{args.branch};{args.branch};Candidates")
histogram.SetLineColor(ROOT.kBlue + 1)
histogram.SetLineWidth(2)
histogram.Draw("hist")


# ---------------------------------------------------------------------------
# 3. Save the plot
# ---------------------------------------------------------------------------

print("\n=== 3. Save the plot ===")

canvas.SaveAs(args.plot)
print(f"Saved plot to {args.plot}")

root_file.Close()
