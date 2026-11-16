"""mel: Matching-market Elasticity Lab.

Tools for modelling markets as two-sided matching problems and measuring
inelasticity, scarcity rents, market power and deadweight loss.
"""
from .assignment import AssignmentResult, solve_assignment, core_bounds
from .gale_shapley import deferred_acceptance
from . import metrics, plotting

__all__ = [
    "AssignmentResult",
    "solve_assignment",
    "core_bounds",
    "deferred_acceptance",
    "metrics",
    "plotting",
]
