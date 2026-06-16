#!/usr/bin/env python3
"""Function: fit a mixed signal-plus-background sample.
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
parser.add_argument("--input", default="data/mixed_student.root")
parser.add_argument("--plot", default="plots/tutorial_02_mixed_fit.png")
args = parser.parse_args()


# Batch mode writes plots to files without opening graphical windows.
ROOT.gROOT.SetBatch(True)
Path(args.plot).parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Open the ROOT file and get the TTree
# ---------------------------------------------------------------------------

print("\n=== 1. Open the mixed ROOT file and read the TTree ===")

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

# We fit only mass and decay_time in this tutorial.
# RooFit will import only the variables listed in this RooArgSet.
mass = ROOT.RooRealVar("mass", "m(B) [GeV]", XXX, XXX) # TOFILL
decay_time = ROOT.RooRealVar("decay_time", "decay time [ps]", XXX, XXX) # TOFILL
observables = ROOT.RooArgSet(mass, decay_time)

print("Observable:", mass.GetName(), "range =", mass.getMin(), "to", mass.getMax())
print("Observable:", decay_time.GetName(), "range =", decay_time.getMin(), "to", decay_time.getMax())


# ---------------------------------------------------------------------------
# 3. Import the TTree into a RooDataSet
# ---------------------------------------------------------------------------

print("\n=== 3. Import the TTree into a RooDataSet ===")

# RooDataSet is RooFit's unbinned dataset class.  ROOT.RooFit.Import(tree) tells
# RooFit to copy the matching branches from the TTree.
data = ROOT.RooDataSet("mixed_data",
    "mixed signal plus background data",
    observables,
    ROOT.RooFit.Import(tree)
)

print(f"Imported {data.numEntries()} candidates into RooFit")


# ---------------------------------------------------------------------------
# 4. Build the signal mass model
# ---------------------------------------------------------------------------

print("\n=== 4. Build the signal mass PDF ===")

# The signal peak is described by a Gaussian.
mean = ROOT.RooRealVar("mean", "B mass mean [GeV]", XXX, XXX, XXX) # TOFILL
sigma = ROOT.RooRealVar("sigma", "B mass resolution [GeV]", XXX, XXX, XXX) # TOFILL
sig_mass = ROOT.RooGaussian("sig_mass", "signal mass PDF", mass, mean, sigma)


# ---------------------------------------------------------------------------
# 5. Build the background mass model
# ---------------------------------------------------------------------------

print("\n=== 5. Build the background mass PDF ===")

# The random background was generated with an exponential mass shape.  In
# RooFit, RooExponential represents:
#
#   exp(coefficient * observable)
#
# A negative coefficient gives a falling background as mass increases.
bkg_slope = ROOT.RooRealVar("bkg_slope", "background mass slope", XXX, XXX, XXX) # TOFILL
bkg_mass = ROOT.RooExponential("bkg_mass", "background mass PDF", mass, bkg_slope)


# ---------------------------------------------------------------------------
# 6. Build the signal and background decay-time models
# ---------------------------------------------------------------------------

print("\n=== 6. Build the decay-time PDFs ===")

# The signal and background both use simple exponential decay-time shapes, but
# with different lifetimes.  The signal lifetime for a B should be close to 1.5 ps,
# while the toy background lifetime is shorter.
tau_sig = ROOT.RooRealVar("tau_sig", "signal lifetime [ps]", XXX, XXX, XXX) # TOFILL
tau_bkg = ROOT.RooRealVar("tau_bkg", "background lifetime [ps]", XXX, XXX, XXX) # TOFILL

# RooGenericPdf is used here for transparency:
#
#   exp(-@0/@1) means exp(-decay_time / tau)
#
# RooFit normalizes the PDF over the decay_time range.  In a more realistic
# decay-time analysis, one would often use RooDecay with a resolution model.
sig_time = ROOT.RooGenericPdf(
    "sig_time",
    "signal decay-time PDF",
    "exp(-@0/@1)",
    ROOT.RooArgList(decay_time, tau_sig)
)
bkg_time = ROOT.RooGenericPdf(
    "bkg_time",
    "background decay-time PDF",
    "exp(-@0/@1)",
    ROOT.RooArgList(decay_time, tau_bkg)
)

# ---------------------------------------------------------------------------
# 7. Combine mass and decay time inside each component
# ---------------------------------------------------------------------------

print("\n=== 7. Build signal and background component PDFs ===")

# For each component, we assume mass and decay time are independent:
#
#   signal PDF     = signal mass PDF     x signal time PDF
#   background PDF = background mass PDF x background time PDF
#
# RooProdPdf represents each product.
sig_pdf = ROOT.RooProdPdf(
    "sig_pdf",
    "signal mass x time PDF",
    ROOT.RooArgList(sig_mass, sig_time)
)
bkg_pdf = ROOT.RooProdPdf(
    "bkg_pdf",
    "background mass x time PDF",
    ROOT.RooArgList(bkg_mass, bkg_time)
)

# ---------------------------------------------------------------------------
# 8. Add signal and background with floating yields
# ---------------------------------------------------------------------------

print("\n=== 8. Build the extended signal-plus-background model ===")

# A normal mixture model would use a signal fraction, for example:
#
#   model = f_sig * sig_pdf + (1 - f_sig) * bkg_pdf
#
# An extended model instead uses yields:
#
#   model = n_sig * sig_pdf + n_bkg * bkg_pdf
#
# The fit then estimates both the shape parameters and the event counts.
n_events = data.numEntries()
n_sig = ROOT.RooRealVar("n_sig", "signal yield", XXX, XXX, XXX) # TOFILL
n_bkg = ROOT.RooRealVar("n_bkg", "background yield", XXX, XXX, XXX) # TOFILL

model = ROOT.RooAddPdf(
    "model",
    "extended signal plus background PDF",
    ROOT.RooArgList(sig_pdf, bkg_pdf),
    ROOT.RooArgList(n_sig, n_bkg),
)


# ---------------------------------------------------------------------------
# 9. Fit the extended model
# ---------------------------------------------------------------------------

print("\n=== 9. Fit the model to the mixed data ===")

# Extended(True) tells RooFit that the coefficients n_sig and n_bkg are event
# yields, not fractions.  The total expected yield is n_sig + n_bkg.
fit_result = model.fitTo(
    data,
    ROOT.RooFit.NumCPU(2),
    ROOT.RooFit.Save(True),
    ROOT.RooFit.Extended(True),
    ROOT.RooFit.PrintLevel(-1),
)

print(f"Fit status: {fit_result.status()}")
print(f"Covariance quality: {fit_result.covQual()}")

print("\nFitted yields:")
print(f"  n_sig = {n_sig.getVal():.1f} +/- {n_sig.getError():.1f}")
print(f"  n_bkg = {n_bkg.getVal():.1f} +/- {n_bkg.getError():.1f}")

print("\nFitted signal parameters:")
print(f"  mean    = {mean.getVal():.5f} +/- {mean.getError():.5f} GeV")
print(f"  sigma   = {sigma.getVal():.5f} +/- {sigma.getError():.5f} GeV")
print(f"  tau_sig = {tau_sig.getVal():.4f} +/- {tau_sig.getError():.4f} ps")

print("\nFitted background parameters:")
print(f"  bkg_slope = {bkg_slope.getVal():.4f} +/- {bkg_slope.getError():.4f}")
print(f"  tau_bkg   = {tau_bkg.getVal():.4f} +/- {tau_bkg.getError():.4f} ps")


# ---------------------------------------------------------------------------
# 10. Draw mass and decay-time projections
# ---------------------------------------------------------------------------

print("\n=== 10. Draw the fitted model ===")

# The model is two-dimensional.  We inspect it through one-dimensional
# projections: one in mass and one in decay time.
canvas = ROOT.TCanvas("tutorial_02_canvas", "mixed RooFit tutorial", 1100, 450)
canvas.Divide(2, 1)

canvas.cd(1)

mass_frame = mass.frame(ROOT.RooFit.Title("Mass projection"))
data.plotOn(mass_frame)

# Draw the full model first.
model.plotOn(mass_frame)

# Then draw the individual components.  The component names are the object names
# used when creating sig_pdf and bkg_pdf above.
model.plotOn(
    mass_frame,
    ROOT.RooFit.Components("bkg_pdf"),
    ROOT.RooFit.LineStyle(ROOT.kDashed),
    ROOT.RooFit.LineColor(ROOT.kRed),
)
model.plotOn(
    mass_frame,
    ROOT.RooFit.Components("sig_pdf"),
    ROOT.RooFit.LineStyle(ROOT.kDotted),
    ROOT.RooFit.LineColor(ROOT.kBlue + 1),
)
mass_frame.Draw()

canvas.cd(2)

time_frame = decay_time.frame(ROOT.RooFit.Title("Decay-time projection"))

data.plotOn(time_frame)
model.plotOn(time_frame)

model.plotOn(
    time_frame,
    ROOT.RooFit.Components("bkg_pdf"),
    ROOT.RooFit.LineStyle(ROOT.kDashed),
    ROOT.RooFit.LineColor(ROOT.kRed),
)
model.plotOn(
    time_frame,
    ROOT.RooFit.Components("sig_pdf"),
    ROOT.RooFit.LineStyle(ROOT.kDotted),
    ROOT.RooFit.LineColor(ROOT.kBlue + 1),
)
time_frame.Draw()

canvas.SaveAs(args.plot)
print(f"Saved plot to {args.plot}")


root_file.Close()
