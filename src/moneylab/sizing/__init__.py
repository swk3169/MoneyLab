"""Position sizing (planned): e.g. fixed-fraction, capped fractional Kelly.

Kelly for a binary share bought at price p with estimated probability q:
    f* = (q - p) / (1 - p)
Use a fraction of f* and cap it; estimates of q are noisy.
"""
