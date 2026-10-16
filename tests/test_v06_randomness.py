"""research/v06 is exempt from the v0.4 no-shuffle rule (tests/test_research_stats.py) because the
pre-registered B1 test needs permutations. In exchange, all of its randomness must be seeded and
reproducible: only explicit `random.Random(seed)` instances, no global random state, no OS
entropy, no salted `hash()`, identical results across processes and hash seeds."""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from moneylab.research.v06 import montecarlo as MC
from moneylab.research.v06 import procedures as P
from moneylab.research.v06.synthetic import DGP, draw_noise

V06 = Path(__file__).resolve().parents[1] / "src" / "moneylab" / "research" / "v06"
FILES = sorted(V06.glob("*.py"))
GLOBAL_RANDOM = re.compile(r"\brandom\.(random|shuffle|choice|choices|randint|randrange|gauss|normalvariate|"
                           r"gammavariate|uniform|sample|seed|getrandbits|betavariate|expovariate)\(")
UNSEEDED = re.compile(r"random\.Random\(\s*\)")
ENTROPY = re.compile(r"\b(SystemRandom|secrets|urandom|uuid[14]?)\b")
SALTED_HASH = re.compile(r"(?<![\w.])hash\(")
LAYOUT = MC.Layout(warmup=122, confirmatory=400, holdout=150, excluded=5, forward=150, interim=75)
PROC = MC.Procedure(bootstrap=19, draws=9)


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def test_v06_package_files_are_scanned():
    assert {f.stem for f in FILES} >= {"__init__", "procedures", "synthetic", "montecarlo"}


def test_only_seeded_random_instances_are_used():
    for f in FILES:
        text = f.read_text(encoding="utf-8")
        assert not GLOBAL_RANDOM.search(text), f"{f.name}: module-level random state"
        assert not UNSEEDED.search(text), f"{f.name}: random.Random() without a seed"
        assert not ENTROPY.search(text), f"{f.name}: OS entropy"
        assert not SALTED_HASH.search(text), f"{f.name}: hash() is salted per process"


def test_the_static_checks_catch_what_they_claim_to_catch():
    assert GLOBAL_RANDOM.search("x = random.shuffle(xs)") and GLOBAL_RANDOM.search("random.seed(1)")
    assert not GLOBAL_RANDOM.search("rng.shuffle(xs); rng = random.Random(seed)")
    assert UNSEEDED.search("rng = random.Random( )") and not UNSEEDED.search("random.Random(seed)")
    assert ENTROPY.search("random.SystemRandom()") and ENTROPY.search("os.urandom(8)")
    assert SALTED_HASH.search("k = hash(name)") and not SALTED_HASH.search("sha.hash(x); file_hash(x)")


def test_same_seed_same_draws_different_seed_different_draws():
    pos = [1, 1, 0, 0, 1, 0, 1, 1, 1, 0] * 20
    market = [0.001 * ((i * 7) % 11 - 5) for i in range(len(pos))]
    assert P.b1_means(market, pos, -0.003, 30, seed=1) == P.b1_means(market, pos, -0.003, 30, seed=1)
    assert P.b1_means(market, pos, -0.003, 30, seed=1) != P.b1_means(market, pos, -0.003, 30, seed=2)
    assert P.bootstrap_means([market], mean_block=5, resamples=30, seed=3) == \
        P.bootstrap_means([market], mean_block=5, resamples=30, seed=3)
    assert draw_noise(DGP(), 100, 4).a == draw_noise(DGP(), 100, 4).a
    assert draw_noise(DGP(), 100, 4).a != draw_noise(DGP(), 100, 5).a


def test_replication_depends_on_its_seed():
    a = MC.run_replication(DGP(), MC.Costs(), PROC, LAYOUT, False, seed=7)
    b = MC.run_replication(DGP(), MC.Costs(), PROC, LAYOUT, False, seed=8)
    assert digest(a) != digest(b)


def test_replication_is_identical_across_processes_and_hash_seeds():
    """A fresh interpreter with two different PYTHONHASHSEED values reproduces the in-process result."""
    expected = digest(MC.run_replication(DGP(), MC.Costs(), PROC, LAYOUT, False, seed=7))
    code = (
        "import hashlib, json\n"
        "from moneylab.research.v06 import montecarlo as MC\n"
        "from moneylab.research.v06.synthetic import DGP\n"
        "r = MC.run_replication(DGP(), MC.Costs(), MC.Procedure(bootstrap=19, draws=9),\n"
        "    MC.Layout(warmup=122, confirmatory=400, holdout=150, excluded=5, forward=150, interim=75), False, 7)\n"
        "print(hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest())\n"
    )
    for hash_seed in ("0", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": hash_seed}
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=120)
        assert out.returncode == 0, out.stderr
        assert out.stdout.strip() == expected, f"PYTHONHASHSEED={hash_seed}"


def test_derived_seeds_are_stable_and_distinct():
    from moneylab.research.stats import derived_seed

    assert derived_seed(20261012, "conf", "boot") == derived_seed(20261012, "conf", "boot")
    seeds = {derived_seed(20261012, "conf", "b1", n) for n in P.STRATEGIES}
    assert len(seeds) == len(P.STRATEGIES)
