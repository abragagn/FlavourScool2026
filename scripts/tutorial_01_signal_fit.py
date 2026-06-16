#!/usr/bin/env python3
"""Beginner RooFit example: fit a signal-only mass and lifetime model.

  1. open a ROOT file;
  2. define RooFit observables;
  3. import a TTree into a RooDataSet;
  4. build a PDF;
  5. fit;
  6. draw the result.
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
parser.add_argument("--input", default="data/signal_only.root")
parser.add_argument("--plot", default="plots/tutorial_01_signal_fit.png")
args = parser.parse_args()

ROOT.gROOT.SetBatch(True)
Path(args.plot).parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Open the ROOT file and get the TTree
# ---------------------------------------------------------------------------

print("\n=== 1. Open the ROOT file and read the TTree ===")

root_file = ROOT.TFile.Open(args.input)
if not root_file or root_file.IsZombie():
    raise OSError(f"Could not open {args.input}")

tree = root_file.Get(TREE_NAME)
if tree is None:
    raise KeyError(f"Could not find tree {TREE_NAME} in {args.input}")

print(f"Input file: {args.input}")
print(f"Tree name:  {TREE_NAME}")
print(f"Entries:    {tree.GetEntries()}")


# ---------------------------------------------------------------------------
# 2. Define the observables
# ---------------------------------------------------------------------------

print("\n=== 2. Define RooFit observables ===")

# A RooRealVar is RooFit's basic real-valued variable.
#
# Here the variables are observables, meaning quantities measured event by
# event.  The first argument must match the TTree branch name exactly:
#
#   branch name in tree  ->  RooRealVar name
#   mass                 ->  "mass"
#   decay_time           ->  "decay_time"
#
#  The second argument is a title, which is used for axis labels in plots. 
# The final two numbers define the allowed range.  RooFit normalizes PDFs over
# this range.
mass = ROOT.RooRealVar("mass", "m(B) [GeV]", 5.15, 5.45)
decay_time = ROOT.RooRealVar("decay_time", "decay time [ps]", 0.0, 8.0)

# RooArgSet is a RooFit container.  It tells RooFit which variables to import.
observables = ROOT.RooArgSet(mass, decay_time)

print("Observable:", mass.GetName(), "range =", mass.getMin(), "to", mass.getMax())
print("Observable:", decay_time.GetName(), "range =", decay_time.getMin(), "to", decay_time.getMax())


# ---------------------------------------------------------------------------
# 3. Import the TTree into a RooDataSet
# ---------------------------------------------------------------------------

print("\n=== 3. Import the TTree into a RooDataSet ===")

# RooFit does not fit a TTree directly.  It fits RooDataSet or RooDataHist
# objects.  ROOT.RooFit.Import(tree) tells RooFit to loop over the TTree and copy
# the branches matching the observables above.
data = ROOT.RooDataSet(
    "signal_data",
    "signal-only toy data",
    observables,
    ROOT.RooFit.Import(tree),
)

print(f"Imported {data.numEntries()} candidates into RooFit")


# ---------------------------------------------------------------------------
# 4. Build the signal mass PDF
# ---------------------------------------------------------------------------

print("\n=== 4. Build the signal mass PDF ===")

# These RooRealVars are fit parameters.  Their names do not need to match TTree branches
#
# Constructor pattern:
#   RooRealVar(name, title, initial_value, lower_limit, upper_limit)
# If no limits are given, the parameter is constant
mean = ROOT.RooRealVar("mean", "B mass mean [GeV]", 5.279, 5.24, 5.32)
sigma = ROOT.RooRealVar("sigma", "B mass resolution [GeV]", 0.020, 0.005, 0.060)

# A Gaussian PDF needs one observable plus its mean and width parameters.
# Each roofit pdf class has its own constructor pattern.  See the RooFit documentation for details.
mass_pdf = ROOT.RooGaussian("mass_pdf", "signal mass PDF", mass, mean, sigma)


# ---------------------------------------------------------------------------
# 5. Build the signal decay-time PDF
# ---------------------------------------------------------------------------

print("\n=== 5. Build the signal decay-time PDF ===")

# The generated signal decay time follows exp(-t / tau). The tau parameter is the B lifetime.
tau = ROOT.RooRealVar("tau", "B lifetime [ps]", 1.5, 0.2, 5.0)

# RooGenericPdf lets us write a simple formula.
#
# In the formula:
#   @0 means the first object in RooArgList, here decay_time;
#   @1 means the second object in RooArgList, here tau.
#
# RooFit handles the normalization over the decay_time range [0, 8] ps.
# A more proper signal decay-time model would include the effect of time resolution and
# use dedicated RooFit classes such as RooDecay.  We use RooGenericPdf here for simplicity.
time_pdf = ROOT.RooGenericPdf(
    "time_pdf",
    "signal decay-time PDF",
    "exp(-@0/@1)",
    ROOT.RooArgList(decay_time, tau)
)


# ---------------------------------------------------------------------------
# 6. Combine mass and decay time
# ---------------------------------------------------------------------------

print("\n=== 6. Combine mass and decay time ===")

# The joint PDF is the product of the two PDFs, since mass and decay time are generated independently.
#
#   P(mass, decay_time) = P(mass) * P(decay_time)
model = ROOT.RooProdPdf(
    "signal_model",
    "signal mass x decay-time PDF",
    ROOT.RooArgList(mass_pdf, time_pdf)
)


# ---------------------------------------------------------------------------
# 7. Fit the model to the data
# ---------------------------------------------------------------------------

print("\n=== 7. Fit the model to the data ===")

# fitTo performs an unbinned maximum-likelihood fit.
#
# Save(True) returns a RooFitResult object so we can inspect the result.
# PrintLevel(-1) keeps RooFit's own terminal output quiet for a cleaner lesson.
# NumCPU(2) tells RooFit to use 2 CPU cores for the fit, which can speed up the fit for large datasets.
fit_result = model.fitTo(data,
                         ROOT.RooFit.NumCPU(2),
                         ROOT.RooFit.Save(True),
                         ROOT.RooFit.PrintLevel(-1))

# A status of 0 usually means the minimizer converged.
# covQual is the covariance-matrix quality; 3 is the best common value.
print(f"Fit status: {fit_result.status()}")
print(f"Covariance quality: {fit_result.covQual()}")

print("\nFitted parameters:")
print(f"  mean  = {mean.getVal():.5f} +/- {mean.getError():.5f} GeV")
print(f"  sigma = {sigma.getVal():.5f} +/- {sigma.getError():.5f} GeV")
print(f"  tau   = {tau.getVal():.4f} +/- {tau.getError():.4f} ps")

# ---------------------------------------------------------------------------
# 8. Draw the fitted model
# ---------------------------------------------------------------------------

print("\n=== 8. Draw the fitted model ===")

# The model is two-dimensional, but we usually inspect one variable at a time.
# RooFit calls these one-dimensional views "projections".
canvas = ROOT.TCanvas("tutorial_01_canvas", "signal-only RooFit tutorial", 1100, 450)
canvas.Divide(2, 1)

canvas.cd(1)

# A RooPlot is the frame on which RooFit draws data points and PDF curves.
mass_frame = mass.frame(ROOT.RooFit.Title("Signal mass fit"))
data.plotOn(mass_frame)
model.plotOn(mass_frame)
mass_frame.Draw()

canvas.cd(2)

time_frame = decay_time.frame(ROOT.RooFit.Title("Signal decay-time fit"))
data.plotOn(time_frame)
model.plotOn(time_frame)
time_frame.Draw()

canvas.SaveAs(args.plot)
print(f"Saved plot to {args.plot}")

root_file.Close()
