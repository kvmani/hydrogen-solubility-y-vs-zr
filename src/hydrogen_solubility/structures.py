"""Crystal structures and POSCAR I/O, without external dependencies.

Geometry conventions (space group P6_3/mmc, hcp metal on Wyckoff 2c)::

    a1 = a (1, 0, 0),  a2 = a (-1/2, sqrt(3)/2, 0),  a3 = (0, 0, c)
    metal:        (1/3, 2/3, 1/4), (2/3, 1/3, 3/4)
    octahedral:   (0, 0, 0), (0, 0, 1/2)                      -> 1 site per metal atom
    tetrahedral:  (2/3, 1/3, 1/8), (2/3, 1/3, 3/8),
                  (1/3, 2/3, 5/8), (1/3, 2/3, 7/8)            -> 2 sites per metal atom

Each tetrahedral site is the centroid of three atoms in one basal layer and one atom
directly above/below it; each octahedral site sits midway between two staggered
basal triangles. These fractional positions do not depend on c/a. The site
multiplicities are used by the solubility model (``thermo.SITES_PER_METAL``).
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

Vector = Tuple[float, float, float]

HCP_METAL_FRAC: Tuple[Vector, ...] = ((1 / 3, 2 / 3, 1 / 4), (2 / 3, 1 / 3, 3 / 4))
HCP_OCTAHEDRAL_FRAC: Tuple[Vector, ...] = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.5))
HCP_TETRAHEDRAL_FRAC: Tuple[Vector, ...] = (
    (2 / 3, 1 / 3, 1 / 8),
    (2 / 3, 1 / 3, 3 / 8),
    (1 / 3, 2 / 3, 5 / 8),
    (1 / 3, 2 / 3, 7 / 8),
)


class StructureError(ValueError):
    """Raised for malformed POSCAR files or impossible structure requests."""


@dataclass
class Structure:
    """A periodic structure in fractional coordinates.

    ``selective`` holds per-atom (x, y, z) "may move" flags; ``None`` means all free.
    Atoms are kept grouped by species in the order of :attr:`species_order`, as
    POSCAR requires.
    """

    lattice: List[Vector]
    species: List[str]
    frac: List[Vector]
    comment: str = "structure"
    selective: Optional[List[Tuple[bool, bool, bool]]] = None

    def __post_init__(self) -> None:
        if len(self.lattice) != 3:
            raise StructureError("lattice must have three vectors")
        if len(self.species) != len(self.frac):
            raise StructureError("species and frac must have the same length")
        if self.selective is not None and len(self.selective) != len(self.frac):
            raise StructureError("selective flags must match the number of atoms")

    # ----------------------------------------------------------------- basic properties
    @property
    def natoms(self) -> int:
        return len(self.species)

    @property
    def species_order(self) -> List[str]:
        order: List[str] = []
        for s in self.species:
            if s not in order:
                order.append(s)
        return order

    def count(self, element: str) -> int:
        return sum(1 for s in self.species if s == element)

    @property
    def volume(self) -> float:
        a, b, c = self.lattice
        return abs(_dot(a, _cross(b, c)))

    def lengths(self) -> Tuple[float, float, float]:
        return tuple(_norm(v) for v in self.lattice)  # type: ignore[return-value]

    def cartesian(self, frac: Vector) -> Vector:
        a, b, c = self.lattice
        return tuple(frac[0] * a[i] + frac[1] * b[i] + frac[2] * c[i] for i in range(3))  # type: ignore[return-value]

    def distance(self, i: int, j: int) -> float:
        """Minimum-image distance between atoms ``i`` and ``j`` (images -1..1 per axis)."""

        return self.distance_frac(self.frac[i], self.frac[j])

    def distance_frac(self, p: Vector, q: Vector) -> float:
        d = [q[k] - p[k] - round(q[k] - p[k]) for k in range(3)]
        best = math.inf
        for shift in itertools.product((-1, 0, 1), repeat=3):
            cart = self.cartesian((d[0] + shift[0], d[1] + shift[1], d[2] + shift[2]))
            best = min(best, _norm(cart))
        return best

    def neighbor_distances(self, index: int, element: Optional[str] = None) -> List[float]:
        """Sorted distances from atom ``index`` to all other atoms (optionally of one element)."""

        return sorted(
            self.distance(index, j)
            for j in range(self.natoms)
            if j != index and (element is None or self.species[j] == element)
        )

    # --------------------------------------------------------------------- transforms
    def sorted_by_species(self, order: Sequence[str]) -> "Structure":
        rank = {s: k for k, s in enumerate(order)}
        idx = sorted(range(self.natoms), key=lambda i: (rank[self.species[i]], i))
        return Structure(
            lattice=list(self.lattice),
            species=[self.species[i] for i in idx],
            frac=[self.frac[i] for i in idx],
            comment=self.comment,
            selective=[self.selective[i] for i in idx] if self.selective else None,
        )

    def with_free_species(self, free: Sequence[str]) -> "Structure":
        """Copy with selective dynamics: only atoms of ``free`` species may move."""

        flags = [(s in free,) * 3 for s in self.species]
        if not any(f[0] for f in flags):
            raise StructureError(f"No atoms of species {list(free)} to keep free in {self.species_order}")
        return Structure(list(self.lattice), list(self.species), list(self.frac), self.comment, flags)  # type: ignore[arg-type]

    # -------------------------------------------------------------------------- POSCAR
    def to_poscar(self) -> str:
        order = self.species_order
        ordered = self.sorted_by_species(order)
        lines = [ordered.comment, "1.0"]
        lines += [f"  {v[0]:16.10f} {v[1]:16.10f} {v[2]:16.10f}" for v in ordered.lattice]
        lines.append("  " + "  ".join(order))
        lines.append("  " + "  ".join(str(ordered.count(s)) for s in order))
        if ordered.selective is not None:
            lines.append("Selective dynamics")
        lines.append("Direct")
        for k, (pos, sp) in enumerate(zip(ordered.frac, ordered.species)):
            wrapped = [x % 1.0 for x in pos]
            row = f"  {wrapped[0]:14.10f} {wrapped[1]:14.10f} {wrapped[2]:14.10f}"
            if ordered.selective is not None:
                row += "  " + " ".join("T" if f else "F" for f in ordered.selective[k])
            lines.append(f"{row}  {sp}")
        return "\n".join(lines) + "\n"

    @classmethod
    def from_poscar(cls, text: str) -> "Structure":
        """Parse a VASP 5+ POSCAR/CONTCAR (species line required)."""

        lines = [ln.rstrip() for ln in text.splitlines()]
        try:
            comment = lines[0].strip() or "structure"
            scale = float(lines[1].split()[0])
            lattice = [tuple(float(x) * scale for x in lines[2 + k].split()[:3]) for k in range(3)]
            species_tokens = lines[5].split()
            if all(tok.isdigit() for tok in species_tokens):
                raise StructureError("POSCAR has no species line (VASP 4 format); add element names on line 6.")
            counts = [int(x) for x in lines[6].split()]
            cursor = 7
            selective = lines[cursor].strip().lower().startswith("s")
            if selective:
                cursor += 1
            mode = lines[cursor].strip().lower()
            cursor += 1
            species: List[str] = []
            for sp, n in zip(species_tokens, counts):
                # VASP 6 may write "Y_sv/abc123" style names; keep the element only.
                species += [sp.split("/")[0].split("_")[0]] * n
            frac: List[Vector] = []
            flags: List[Tuple[bool, bool, bool]] = []
            for k in range(len(species)):
                parts = lines[cursor + k].split()
                xyz = tuple(float(x) for x in parts[:3])
                if mode.startswith(("c", "k")):
                    xyz = _cart_to_frac(lattice, tuple(x * scale for x in xyz))  # type: ignore[arg-type]
                frac.append(xyz)  # type: ignore[arg-type]
                if selective:
                    flags.append(tuple(p.upper().startswith("T") for p in parts[3:6]))  # type: ignore[arg-type]
        except (IndexError, ValueError) as exc:
            raise StructureError(f"Could not parse POSCAR: {exc}") from exc
        return cls(lattice, species, frac, comment, flags if selective else None)  # type: ignore[arg-type]

    @classmethod
    def read(cls, path: Path) -> "Structure":
        if not path.is_file():
            raise StructureError(f"Structure file not found: {path}")
        return cls.from_poscar(path.read_text(encoding="utf-8"))


def reciprocal_lengths(structure: Structure) -> Tuple[float, float, float]:
    """Lengths of the reciprocal lattice vectors b1, b2, b3 in 1/Angstrom, including 2*pi."""

    a, b, c = structure.lattice
    vol = structure.volume
    return tuple(2.0 * math.pi * _norm(_cross(u, v)) / vol for u, v in ((b, c), (c, a), (a, b)))  # type: ignore[return-value]


def kpoint_grid_for_spacing(structure: Structure, spacing: float) -> Tuple[int, int, int]:
    """Smallest grid whose k-point spacing is <= ``spacing`` along every axis (VASP KSPACING rule)."""

    return tuple(max(1, math.ceil(length / spacing - 1e-6)) for length in reciprocal_lengths(structure))  # type: ignore[return-value]


def kpoint_spacing_of_grid(structure: Structure, grid: Sequence[int]) -> float:
    """Largest k-point spacing (1/Angstrom, incl. 2*pi) produced by ``grid`` on ``structure``."""

    return max(length / n for length, n in zip(reciprocal_lengths(structure), grid))


# ---------------------------------------------------------------------------- builders


def hcp_lattice(a: float, c: float) -> List[Vector]:
    return [(a, 0.0, 0.0), (-a / 2.0, a * math.sqrt(3.0) / 2.0, 0.0), (0.0, 0.0, c)]


def hcp_primitive(element: str, a: float, c: float) -> Structure:
    """Two-atom primitive hcp cell."""

    return Structure(hcp_lattice(a, c), [element, element], list(HCP_METAL_FRAC), f"{element} hcp primitive")


def make_supercell(structure: Structure, repeats: Sequence[int]) -> Structure:
    """Repeat a cell n1 x n2 x n3 times (diagonal supercell)."""

    n1, n2, n3 = repeats
    lattice = [tuple(x * n for x in vec) for vec, n in zip(structure.lattice, repeats)]
    species: List[str] = []
    frac: List[Vector] = []
    for i, j, k in itertools.product(range(n1), range(n2), range(n3)):
        for sp, (x, y, z) in zip(structure.species, structure.frac):
            species.append(sp)
            frac.append(((x + i) / n1, (y + j) / n2, (z + k) / n3))
    comment = f"{structure.comment} {n1}x{n2}x{n3}"
    return Structure(lattice, species, frac, comment)  # type: ignore[arg-type]


def hcp_supercell(element: str, a: float, c: float, repeats: Sequence[int], h_site: Optional[str] = None) -> Structure:
    """hcp supercell, optionally with one H atom in a tetrahedral or octahedral site."""

    cell = make_supercell(hcp_primitive(element, a, c), repeats)
    if h_site is None:
        return cell
    site_frac = {"tetrahedral": HCP_TETRAHEDRAL_FRAC[1], "octahedral": HCP_OCTAHEDRAL_FRAC[1]}.get(h_site)
    if site_frac is None:
        raise StructureError(f"Unknown h_site '{h_site}' (use tetrahedral or octahedral)")
    n = repeats
    h_frac = tuple(site_frac[k] / n[k] for k in range(3))
    cell.species.append("H")
    cell.frac.append(h_frac)  # type: ignore[arg-type]
    cell.comment = f"{element} hcp {n[0]}x{n[1]}x{n[2]} + H({h_site})"
    return cell


def h2_molecule(box: Sequence[float], bond: float = 0.75) -> Structure:
    """H2 dimer along x, centred in an orthorhombic box (asymmetric box breaks symmetry)."""

    lattice = [(box[0], 0.0, 0.0), (0.0, box[1], 0.0), (0.0, 0.0, box[2])]
    half = 0.5 * bond / box[0]
    return Structure(lattice, ["H", "H"], [(0.5 - half, 0.5, 0.5), (0.5 + half, 0.5, 0.5)], "H2 molecule in box")


def fluorite_dihydride(element: str, a: float) -> Structure:
    """Cubic CaF2-type MH2 conventional cell: 4 metal atoms (fcc) + 8 H in tetrahedral sites."""

    lattice = [(a, 0.0, 0.0), (0.0, a, 0.0), (0.0, 0.0, a)]
    metal = [(0.0, 0.0, 0.0), (0.0, 0.5, 0.5), (0.5, 0.0, 0.5), (0.5, 0.5, 0.0)]
    hydrogen = list(itertools.product((0.25, 0.75), repeat=3))
    return Structure(lattice, [element] * 4 + ["H"] * 8, metal + hydrogen, f"{element}H2 fluorite")  # type: ignore[arg-type]


def hcp_lattice_parameters(structure: Structure) -> Tuple[float, float]:
    """Return (a, c) of a relaxed primitive hcp cell, checking that it is one."""

    if structure.natoms != 2:
        raise StructureError(f"Expected a 2-atom primitive hcp cell, found {structure.natoms} atoms")
    a1, a2, a3 = structure.lattice
    la, lb, lc = _norm(a1), _norm(a2), _norm(a3)
    gamma = math.degrees(math.acos(_dot(a1, a2) / (la * lb)))
    if abs(la - lb) > 1e-3 * la or abs(gamma - 120.0) > 0.1:
        raise StructureError(f"Cell is not hexagonal (|a1|={la:.4f}, |a2|={lb:.4f}, gamma={gamma:.2f} deg)")
    return 0.5 * (la + lb), lc


def classify_h_site(structure: Structure, *, tolerance: float = 0.15) -> Optional[str]:
    """Classify the (single) H atom by its metal coordination: 4 -> tetrahedral, 6 -> octahedral.

    Neighbours are counted within ``(1 + tolerance) * d_min``. Returns ``None`` if
    there is no H, more than one H, or the coordination is neither 4 nor 6 (e.g. the
    H relaxed to a low-symmetry position) -- callers should then inspect the CONTCAR.
    """

    h_atoms = [i for i, s in enumerate(structure.species) if s == "H"]
    if len(h_atoms) != 1:
        return None
    metals = _metal_distances(structure, h_atoms[0])
    if not metals:
        return None
    cutoff = metals[0] * (1.0 + tolerance)
    coordination = sum(1 for d in metals if d <= cutoff)
    return {4: "tetrahedral", 6: "octahedral"}.get(coordination)


def _metal_distances(structure: Structure, index: int) -> List[float]:
    return sorted(structure.distance(index, j) for j in range(structure.natoms) if structure.species[j] != "H")


# ------------------------------------------------------------------------ vector maths


def _dot(u: Sequence[float], v: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(u, v))


def _cross(u: Sequence[float], v: Sequence[float]) -> Vector:
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def _norm(v: Sequence[float]) -> float:
    return math.sqrt(_dot(v, v))


def _cart_to_frac(lattice: Sequence[Vector], cart: Vector) -> Vector:
    a, b, c = lattice
    vol = _dot(a, _cross(b, c))
    # Rows of the inverse lattice matrix are (b x c, c x a, a x b) / volume.
    return tuple(_dot(cart, row) / vol for row in (_cross(b, c), _cross(c, a), _cross(a, b)))  # type: ignore[return-value]
