#!/usr/bin/env python3
"""Generate simple neutral-B flavour toy samples for the RooFit exercises.
"""

import argparse
import json
import math
from array import array
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

parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["signal", "mixed"], default="mixed")
parser.add_argument("--n-signal", type=int, default=100000)
parser.add_argument("--n-background", type=int, default=50000)
parser.add_argument("--output", default=None)
parser.add_argument("--truth-output", default=None)
parser.add_argument("--seed", type=int, default=12345)
parser.add_argument("--mass-min", type=float, default=5.0)
parser.add_argument("--mass-max", type=float, default=6.0)
parser.add_argument("--mass-mean", type=float, default=5.28)
parser.add_argument("--mass-sigma", type=float, default=0.02)
parser.add_argument("--mass-slope", type=float, default=-8.0)
parser.add_argument("--tau-signal", type=float, default=1.52)
parser.add_argument("--tau-background", type=float, default=0.2)
parser.add_argument("--time-max", type=float, default=13.0)
parser.add_argument("--delta-m", type=float, default=0.5065)
args = parser.parse_args()

if args.output is None:
    args.output = "data/signal_only.root" if args.mode == "signal" else "data/mixed_student.root"
if args.truth_output is None:
    args.truth_output = "data/mixed_truth.root"


# ---------------------------------------------------------------------------
# Prepare output files and branch buffers
# ---------------------------------------------------------------------------

ROOT.gROOT.SetBatch(True)
rng = ROOT.TRandom3(args.seed)

output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)

truth_output = None
if args.mode == "mixed" and args.truth_output:
    truth_output = Path(args.truth_output)
    truth_output.parent.mkdir(parents=True, exist_ok=True)

mass = array("d", [0.0])
decay_time = array("d", [0.0])
flavour_prod = array("i", [0])
flavour_decay = array("i", [0])
is_signal = array("i", [0])

student_file = ROOT.TFile(str(output), "RECREATE")
student_tree = ROOT.TTree(TREE_NAME, "Student neutral-B flavour toy sample")

# The student sample contains exactly the four public branches used in the exercise.
student_tree.Branch("mass", mass, "mass/D")
student_tree.Branch("decay_time", decay_time, "decay_time/D")
student_tree.Branch("flavour_prod", flavour_prod, "flavour_prod/I")
student_tree.Branch("flavour_decay", flavour_decay, "flavour_decay/I")

truth_file = None
truth_tree = None
if truth_output is not None:
    truth_file = ROOT.TFile(str(truth_output), "RECREATE")
    truth_tree = ROOT.TTree(
        TREE_NAME,
        "Instructor neutral-B flavour toy sample with truth labels",
    )
    truth_tree.Branch("mass", mass, "mass/D")
    truth_tree.Branch("decay_time", decay_time, "decay_time/D")
    truth_tree.Branch("flavour_prod", flavour_prod, "flavour_prod/I")
    truth_tree.Branch("flavour_decay", flavour_decay, "flavour_decay/I")
    truth_tree.Branch("is_signal", is_signal, "is_signal/I")


# ---------------------------------------------------------------------------
# Decide which events are signal and which are background
# ---------------------------------------------------------------------------

if args.mode == "signal":
    event_types = [1] * args.n_signal
else:
    event_types = [1] * args.n_signal + [0] * args.n_background

    # Shuffle signal and background labels so the output tree is not ordered as
    # all signal followed by all background.
    for index in range(len(event_types) - 1, 0, -1):
        swap = rng.Integer(index + 1)
        event_types[index], event_types[swap] = event_types[swap], event_types[index]


# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------

for label in event_types:
    is_signal[0] = label

    if label:
        # -------------------------------------------------------------------
        # Signal generation
        # -------------------------------------------------------------------

        while True:
            candidate_mass = rng.Gaus(args.mass_mean, args.mass_sigma)
            if args.mass_min <= candidate_mass <= args.mass_max:
                mass[0] = candidate_mass
                break

        while True:
            candidate_time = rng.Exp(args.tau_signal)
            if 0.0 <= candidate_time <= args.time_max:
                decay_time[0] = candidate_time
                break

        # Production flavour: equal probability for B0 and anti-B0.
        flavour_prod[0] = 1 if rng.Uniform() < 0.5 else -1

        # Neutral-B mixing toy model:
        #
        #   P(unmixed | t) = (1 + cos(Delta m * t)) / 2
        #
        # If the event is unmixed, production and decay flavours are equal.  If
        # it is mixed, the decay flavour has the opposite sign.
        probability_unmixed = 0.5 * (1.0 + math.cos(args.delta_m * decay_time[0]))
        if rng.Uniform() < probability_unmixed:
            flavour_decay[0] = flavour_prod[0]
        else:
            flavour_decay[0] = -flavour_prod[0]

    else:
        # -------------------------------------------------------------------
        # Background generation
        # -------------------------------------------------------------------

        # Background mass: truncated exponential between mass_min and mass_max.
        # The PDF is proportional to exp(mass_slope * mass).  A negative slope
        # gives more background at low mass and less at high mass.
        if abs(args.mass_slope) < 1e-12:
            mass[0] = rng.Uniform(args.mass_min, args.mass_max)
        else:
            uniform = rng.Uniform()
            exp_low = math.exp(args.mass_slope * args.mass_min)
            exp_high = math.exp(args.mass_slope * args.mass_max)
            mass[0] = math.log(exp_low + uniform * (exp_high - exp_low)) / args.mass_slope

        # Background decay time: also exponential, but with a different lifetime
        # from the signal.
        while True:
            candidate_time = rng.Exp(args.tau_background)
            if 0.0 <= candidate_time <= args.time_max:
                decay_time[0] = candidate_time
                break

        # Background flavours are random and independent.  This means there is
        # no oscillation pattern in the background component.
        flavour_prod[0] = 1 if rng.Uniform() < 0.5 else -1
        flavour_decay[0] = 1 if rng.Uniform() < 0.5 else -1

    student_tree.Fill()
    if truth_tree is not None:
        truth_tree.Fill()


# ---------------------------------------------------------------------------
# Write ROOT files and metadata
# ---------------------------------------------------------------------------

student_file.cd()
student_tree.Write()
student_file.Close()

if truth_file is not None:
    truth_file.cd()
    truth_tree.Write()
    truth_file.Close()

metadata = {
    "tree_name": TREE_NAME,
    "mode": args.mode,
    "n_signal": args.n_signal,
    "n_background": 0 if args.mode == "signal" else args.n_background,
    "seed": args.seed,
    "mass_mean_GeV": args.mass_mean,
    "mass_sigma_GeV": args.mass_sigma,
    "tau_signal_ps": args.tau_signal,
    "tau_background_ps": args.tau_background,
    "delta_m_ps_inverse": args.delta_m,
}
metadata_path = output.with_suffix(".json")
metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

print(f"Wrote student sample: {output}")
print(f"Wrote metadata: {metadata_path}")
if truth_output is not None:
    print(f"Wrote instructor truth sample: {truth_output}")
