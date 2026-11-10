"""Base-case results for the snapshot model: feeder-head summary, voltage profiles, loading box plots and circuit maps.

Run from the repository root with ``python analysis/baseline/baseline.py``. Figures are written
next to this file.
"""

import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from altdss import altdss
from matplotlib.cm import ScalarMappable
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D

OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parents[1] / "grid_model" / "opendss" / "snapshot"
KM_PER_MILE = 1.609344
PHASE_COLORS = {1: "#2c6fb0", 2: "#4a9e7a", 3: "#c9651f"}
FEEDER_COLORS = {1: "#2c6fb0", 2: "#c9651f", 3: "#4a9e7a"}
PHASE_NAMES = {1: "A", 2: "B", 3: "C"}


def feeder_of(name: str) -> int:
    """Return the feeder number encoded in an element name.

    Args:
        name: OpenDSS element name such as ``fdr2_tr5``.

    Returns:
        The feeder number, or 0 for elements outside the feeders.

    Example:
        >>> feeder_of("fdr2_tr5")
        2
    """
    return int(name[3]) if name.startswith("fdr") else 0


def phases_of(spec: str) -> list[int]:
    """List the phase nodes (1-3) in an OpenDSS bus specification.

    Args:
        spec: Bus specification such as ``fdr1_5.1.2``.

    Returns:
        Node numbers 1, 2 or 3 present in the specification.

    Example:
        >>> phases_of("fdr1_5.1.2.0")
        [1, 2]
    """
    return [int(n) for n in spec.split(".")[1:] if n in "123"]


def solve() -> None:
    """Compile the snapshot master file, which also solves the base-case power flow.

    Example:
        >>> solve()
        >>> altdss.Solution.Converged
        True
    """
    cwd = Path.cwd()
    os.chdir(MODEL_DIR)
    try:
        altdss("redirect master.dss")
    finally:
        os.chdir(cwd)


def node_voltages() -> dict[str, float]:
    """Return the per-unit voltage magnitude of every node in the solved circuit.

    Returns:
        Mapping from node name (``bus.phase``) to voltage magnitude in per unit.

    Example:
        >>> node_voltages()["fdr1_0.1"]
        1.0389
    """
    ckt = altdss.to_dss_python().ActiveCircuit
    return dict(zip(ckt.AllNodeNames, ckt.AllBusVmagPu))


def bus_distances() -> dict[str, float]:
    """Return the electrical distance of every bus from the energy meter in miles.

    Returns:
        Mapping from bus name to distance in miles.

    Example:
        >>> bus_distances()["fdr1_1"]
        0.43
    """
    ckt = altdss.to_dss_python().ActiveCircuit
    return {b: km / KM_PER_MILE for b, km in zip(ckt.AllBusNames, ckt.AllBusDistances)}


def line_table() -> pl.DataFrame:
    """Tabulate end buses, power, loading and type of every line.

    Returns:
        One row per line with columns ``name``, ``feeder``, ``from_bus``, ``to_bus``, ``nodes``,
        ``p_kw``, ``q_kvar`` (terminal 1), ``loading_pct`` (of normal ampacity), ``secondary``,
        ``switch`` and ``is_open``.

    Example:
        >>> line_table().filter(pl.col("is_open")).height
        6
    """
    rows = []
    for ln in altdss.Line:
        if ln.Name.startswith("source"):
            continue
        p = ln.Powers()
        s = p[: len(p) // 2]
        geometry = ln.Geometry_str or ""
        rows.append(
            (
                ln.Name,
                feeder_of(ln.Name),
                ln.Bus1.split(".")[0],
                ln.Bus2.split(".")[0],
                ln.Bus1,
                float(s.real.sum()),
                float(s.imag.sum()),
                float(ln.pctNormal()),
                "triplex" in geometry or "quadruplex" in geometry,
                bool(ln.Switch),
                bool(ln.IsOpen(1, 0)),
            )
        )
    schema = [
        "name",
        "feeder",
        "from_bus",
        "to_bus",
        "nodes",
        "p_kw",
        "q_kvar",
        "loading_pct",
        "secondary",
        "switch",
        "is_open",
    ]
    return pl.DataFrame(rows, schema=schema, orient="row")


def transformer_table() -> pl.DataFrame:
    """Tabulate loading of distribution transformers and regulators inside the feeders.

    Returns:
        One row per transformer with columns ``name``, ``feeder``, ``primary``, ``secondary`` (bus
        specifications), ``kva``, ``loading_pct`` (apparent power over kVA rating) and ``regulator``.

    Example:
        >>> transformer_table().filter(pl.col("loading_pct") > 100).height
        4
    """
    rows = []
    for tr in altdss.Transformer:
        if not tr.Name.startswith("fdr"):
            continue
        p = tr.Powers()
        s = np.abs(p[: len(p) // 2].sum())
        rows.append(
            (
                tr.Name,
                feeder_of(tr.Name),
                tr.Buses[0],
                tr.Buses[1],
                float(tr.kVAs[0]),
                100 * float(s) / float(tr.kVAs[0]),
                "_reg" in tr.Name,
            )
        )
    schema = [
        "name",
        "feeder",
        "primary",
        "secondary",
        "kva",
        "loading_pct",
        "regulator",
    ]
    return pl.DataFrame(rows, schema=schema, orient="row")


def feeder_head(lines: pl.DataFrame, volts: dict[str, float]) -> pl.DataFrame:
    """Summarize the active power, reactive power and voltage at each feeder head.

    Args:
        lines: Output of ``line_table``.
        volts: Output of ``node_voltages``.

    Returns:
        One row per feeder with ``p_kw``, ``q_kvar`` and per-phase voltages ``v_a``, ``v_b``, ``v_c``.

    Example:
        >>> feeder_head(line_table(), node_voltages()).row(0)
        (1, 1024.0, 190.0, 1.039, 1.04, 1.04)
    """
    head = (
        lines.filter(pl.col("name").str.contains(r"^fdr\d_0-"))
        .group_by("feeder")
        .agg(pl.col("p_kw").sum(), pl.col("q_kvar").sum())
        .sort("feeder")
    )
    for k, ph in PHASE_NAMES.items():
        head = head.with_columns(
            pl.Series(
                f"v_{ph.lower()}", [volts[f"fdr{f}_0.{k}"] for f in head["feeder"]]
            )
        )
    return head


def feeder_balance(head: pl.DataFrame) -> pl.DataFrame:
    """Break the feeder-head flow into connected load, PV, losses and capacitor injection.

    Losses cover lines, distribution transformers and regulators inside each feeder, not the
    substation transformers. Negative ``loss_kvar`` is net line charging.

    Args:
        head: Output of ``feeder_head``.

    Returns:
        One row per feeder with ``load_kw``, ``load_kvar``, ``pv_kw``, ``loss_kw``, ``loss_kvar``,
        ``cap_kvar`` and the head values ``p_kw``, ``q_kvar``, ``v_a``, ``v_b``, ``v_c``.

    Example:
        >>> round(feeder_balance(feeder_head(line_table(), node_voltages()))["pv_kw"][2], 1)
        48.5
    """

    def total(collection, feeder: int, flip: bool = False) -> complex:
        """Sum the terminal powers of one element class in one feeder, in kW and kvar."""
        s = sum(
            (np.sum(e.Powers()) for e in collection if feeder_of(e.Name) == feeder),
            0j,
        )
        return -s if flip else s

    rows = []
    for f in head["feeder"]:
        load = total(altdss.Load, f)
        pv = total(altdss.PVSystem, f, flip=True)
        cap = total(altdss.Capacitor, f, flip=True)
        loss = total(altdss.Line, f) + total(altdss.Transformer, f)
        rows.append(
            (f, load.real, load.imag, pv.real + 0.0, loss.real, loss.imag, cap.imag)
        )
    schema = [
        "feeder",
        "load_kw",
        "load_kvar",
        "pv_kw",
        "loss_kw",
        "loss_kvar",
        "cap_kvar",
    ]
    bal = pl.DataFrame(rows, schema=schema, orient="row")
    return bal.join(head, on="feeder").sort("feeder")


def profile_segments(
    lines: pl.DataFrame,
    xfmrs: pl.DataFrame,
    volts: dict[str, float],
    dist: dict[str, float],
) -> pl.DataFrame:
    """Build per-phase voltage-profile segments for primary and secondary circuits.

    Primary lines and regulators give solid segments. Distribution transformers and the secondary
    lines behind them give dashed segments, coloured by the primary phase that supplies them
    (three-phase secondaries are drawn once per phase).

    Args:
        lines: Output of ``line_table``.
        xfmrs: Output of ``transformer_table``.
        volts: Output of ``node_voltages``.
        dist: Output of ``bus_distances``.

    Returns:
        Segments with columns ``feeder``, ``phase``, ``secondary``, ``d0``, ``v0``, ``d1``, ``v1``.

    Example:
        >>> profile_segments(line_table(), transformer_table(), node_voltages(), bus_distances()).columns
        ['feeder', 'phase', 'secondary', 'd0', 'v0', 'd1', 'v1']
    """
    closed = lines.filter(~pl.col("is_open"))
    sec = closed.filter(pl.col("secondary"))
    adjacent: dict[str, list[str]] = {}
    for a, b in sec.select("from_bus", "to_bus").iter_rows():
        adjacent.setdefault(a, []).append(b)
        adjacent.setdefault(b, []).append(a)
    label: dict[str, int] = {}
    dist_xfmrs = xfmrs.filter(~pl.col("regulator"))
    for x in dist_xfmrs.iter_rows(named=True):
        ph = phases_of(x["primary"])
        stack = [x["secondary"].split(".")[0]]
        while stack:
            bus = stack.pop()
            if bus not in label:
                label[bus] = 0 if len(ph) == 3 else ph[0]
                stack += adjacent.get(bus, [])

    def volt(bus: str, k: int) -> float:
        """Voltage of ``bus`` on phase ``k``; split-phase secondary nodes are averaged."""
        if label.get(bus):
            return (volts[f"{bus}.1"] + volts[f"{bus}.2"]) / 2
        return volts[f"{bus}.{k}"]

    rows = []

    def add(feeder: int, k: int, secondary: bool, b0: str, b1: str) -> None:
        """Append one segment when both buses have a distance and are energized."""
        try:
            row = (feeder, k, secondary, dist[b0], volt(b0, k), dist[b1], volt(b1, k))
        except KeyError:
            return
        if min(row[4], row[6]) > 0:
            rows.append(row)

    for r in closed.filter(~pl.col("secondary")).iter_rows(named=True):
        for k in phases_of(r["nodes"]):
            add(r["feeder"], k, False, r["from_bus"], r["to_bus"])
    for r in sec.iter_rows(named=True):
        for k in (
            [1, 2, 3]
            if label.get(r["from_bus"]) == 0
            else [label.get(r["from_bus"], 1)]
        ):
            add(r["feeder"], k, True, r["from_bus"], r["to_bus"])
    for x in xfmrs.iter_rows(named=True):
        pb, sb = x["primary"].split(".")[0], x["secondary"].split(".")[0]
        ks = phases_of(x["primary"])
        for k in ks if (x["regulator"] or len(ks) == 3) else ks[:1]:
            add(x["feeder"], k, not x["regulator"], pb, sb)
    return pl.DataFrame(
        rows,
        schema=["feeder", "phase", "secondary", "d0", "v0", "d1", "v1"],
        orient="row",
    )


def style() -> None:
    """Apply compact single-column figure styling.

    Example:
        >>> style()
    """
    plt.rcParams.update(
        {
            "font.size": 6.5,
            "axes.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.15,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
        }
    )


def plot_voltage_profiles(segs: pl.DataFrame, path: Path) -> None:
    """Plot per-phase voltage against distance for each feeder.

    Args:
        segs: Output of ``profile_segments``.
        path: Output file; the extension selects the format.

    Example:
        >>> plot_voltage_profiles(segs, OUT_DIR / "voltage_profiles.png")
    """
    fig, axes = plt.subplots(
        1, 3, sharey=True, figsize=(3.5, 2.2), layout="constrained"
    )
    for ax, f in zip(axes, (1, 2, 3)):
        ax.set_title(f"Feeder {f}", fontsize=7)
        for (k, sec), g in segs.filter(pl.col("feeder") == f).group_by(
            ["phase", "secondary"]
        ):
            xy = g.select("d0", "v0", "d1", "v1").to_numpy().reshape(-1, 2, 2)
            ax.add_collection(
                LineCollection(
                    xy,
                    colors=PHASE_COLORS[k],
                    linewidths=0.6,
                    linestyles="--" if sec else "-",
                )
            )
            ax.scatter(xy[:, :, 0], xy[:, :, 1], s=0.8, color=PHASE_COLORS[k], zorder=3)
        ax.axhline(0.95, color="gray", ls=":", lw=0.6)
        ax.axhline(1.05, color="gray", ls=":", lw=0.6)
        ax.set_xlim(0, segs["d1"].max() * 1.03)
        ax.set_ylim(0.94, 1.06)
    handles = [
        Line2D([], [], color=PHASE_COLORS[k], lw=1, label=f"Phase {p}")
        for k, p in PHASE_NAMES.items()
    ]
    handles.append(Line2D([], [], color="#444444", lw=1, ls="--", label="Secondary"))
    fig.legend(
        handles=handles,
        ncol=4,
        loc="outside upper center",
        frameon=False,
        handlelength=1.4,
        columnspacing=1,
    )
    fig.supxlabel("Distance (mi)", fontsize=7)
    axes[0].set_ylabel("Voltage (pu)")
    fig.savefig(path, dpi=300)


def plot_loading(lines: pl.DataFrame, xfmrs: pl.DataFrame, path: Path) -> None:
    """Box plots of conductor (ampacity) and transformer (kVA) loading by feeder.

    Args:
        lines: Output of ``line_table``; switches and open lines are ignored.
        xfmrs: Output of ``transformer_table``; regulators are ignored.
        path: Output file; the extension selects the format.

    Example:
        >>> plot_loading(line_table(), transformer_table(), OUT_DIR / "loading.png")
    """
    data = [
        (
            "Lines and service conductors",
            lines.filter(~pl.col("switch") & ~pl.col("is_open")),
        ),
        ("Distribution transformers", xfmrs.filter(~pl.col("regulator"))),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(3.5, 1.9), layout="constrained")
    for ax, (title, df) in zip(axes, data):
        box = ax.boxplot(
            [df.filter(pl.col("feeder") == f)["loading_pct"] for f in (1, 2, 3)],
            widths=0.55,
            patch_artist=True,
            medianprops={"color": "black", "lw": 0.8},
            flierprops={"markersize": 2, "markeredgewidth": 0.4},
            boxprops={"lw": 0.5},
            whiskerprops={"lw": 0.5},
            capprops={"lw": 0.5},
        )
        for patch, f in zip(box["boxes"], (1, 2, 3)):
            patch.set_facecolor(FEEDER_COLORS[f])
        ax.axhline(100, color="#444444", ls="--", lw=0.7)
        ax.set(
            title=title,
            xlabel="Feeder ID",
            ylim=(0, max(110, df["loading_pct"].max() * 1.05)),
        )
        ax.set_xticklabels(["1", "2", "3"])
        ax.set_title(title, fontsize=6.5)
    axes[0].set_ylabel("Loading (% of rating)")
    fig.savefig(path, dpi=300)


def bus_coords() -> dict[str, tuple[float, float]]:
    """Return planar bus coordinates (longitude scaled by cos(latitude), latitude), in degrees.

    Returns:
        Mapping from bus name to ``(x, y)`` for buses with defined coordinates.

    Example:
        >>> bus_coords()["fdr1_0"]
        (-80.77, 39.73)
    """
    ckt = altdss.to_dss_python().ActiveCircuit
    pts = {
        b: (ckt.Buses[b].x, ckt.Buses[b].y)
        for b in ckt.AllBusNames
        if ckt.Buses[b].Coorddefined
    }
    scale = np.cos(np.radians(np.mean([y for _, y in pts.values()])))
    return {b: (x * scale, y) for b, (x, y) in pts.items()}


def bus_voltage_value(volts: dict[str, float]) -> dict[str, float]:
    """Reduce each bus to one value for colouring: the mean voltage, or the worst phase if out of band.

    Args:
        volts: Output of ``node_voltages``.

    Returns:
        Mapping from bus name to per-unit voltage; de-energized buses are omitted.

    Example:
        >>> bus_voltage_value(node_voltages())["fdr2_19"]
        1.001
    """
    by_bus: dict[str, list[float]] = {}
    for node, v in volts.items():
        bus, _, ph = node.rpartition(".")
        if ph in "123" and v > 0:
            by_bus.setdefault(bus, []).append(v)
    return {
        b: lo
        if (lo := min(v)) < 0.95
        else hi
        if (hi := max(v)) > 1.05
        else float(np.mean(v))
        for b, v in by_bus.items()
    }


def circuit_axes(
    coords: dict[str, tuple[float, float]],
    lines: pl.DataFrame,
    label: str,
    norm: Normalize,
    cmap: str,
    extend: str,
) -> tuple[plt.Figure, plt.Axes]:
    """Create an axis-free circuit map with feeder labels and a horizontal colour bar.

    Args:
        coords: Output of ``bus_coords``.
        lines: Output of ``line_table``; used to place the feeder labels at the feeder ends.
        label: Colour-bar label.
        norm: Colour normalisation for the heat map.
        cmap: Matplotlib colormap name; values outside ``norm`` are drawn red.
        extend: Colour-bar extension, ``"both"`` or ``"max"``.

    Returns:
        The figure and its map axis. The colour-bar label sits just below the bar.

    Example:
        >>> fig, ax = circuit_axes(bus_coords(), line_table(), "Voltage (pu)", Normalize(0.95, 1.05), "viridis", "both")
    """
    fig, ax = plt.subplots(figsize=(2.0, 3.2), layout="constrained")
    ax.set_aspect("equal")
    ax.axis("off")
    for f in (1, 2, 3):
        ends = [
            coords[b]
            for b in lines.filter(pl.col("feeder") == f)["to_bus"]
            if b in coords
        ]
        x, y = min(ends, key=lambda p: p[1])
        ax.text(
            x,
            y - 0.0035,
            f"F{f}",
            ha="center",
            va="top",
            fontsize=5.5,
            fontweight="bold",
        )
    cm = plt.get_cmap(cmap).with_extremes(under="red", over="red")
    bar = fig.colorbar(
        ScalarMappable(norm, cm),
        ax=ax,
        orientation="horizontal",
        location="top",
        shrink=0.8,
        aspect=35,
        pad=0.0,
        extend=extend,
    )
    bar.set_ticks(np.linspace(norm.vmin, norm.vmax, 3))
    bar.ax.xaxis.set_label_position("bottom")
    bar.set_label(label, fontsize=5, labelpad=1)
    bar.ax.tick_params(labelsize=4.5, width=0.4, length=1.5, pad=1)
    bar.outline.set_linewidth(0.4)
    return fig, ax


def draw_branches(
    ax: plt.Axes,
    lines: pl.DataFrame,
    coords: dict[str, tuple[float, float]],
    values: dict[str, float],
    norm: Normalize,
    cmap: str,
) -> None:
    """Draw closed branches coloured by value and open switches as dashed grey lines.

    Args:
        ax: Target axis.
        lines: Output of ``line_table``.
        coords: Output of ``bus_coords``.
        values: Mapping from line name to the value used for colouring.
        norm: Colour normalisation.
        cmap: Matplotlib colormap name; values outside ``norm`` are drawn red.

    Example:
        >>> draw_branches(ax, line_table(), bus_coords(), {"fdr1_1-fdr1_2": 0.5}, Normalize(0, 1), "viridis")
    """
    cm = plt.get_cmap(cmap).with_extremes(under="red", over="red")
    seg = lambda df: [
        (coords[a], coords[b]) for a, b in df.select("from_bus", "to_bus").iter_rows()
    ]
    known = lines.filter(
        pl.col("from_bus").is_in(list(coords)) & pl.col("to_bus").is_in(list(coords))
    )
    ax.add_collection(
        LineCollection(
            seg(known.filter(pl.col("is_open"))),
            colors="#555555",
            linewidths=0.5,
            linestyles="--",
        )
    )
    closed = (
        known.filter(~pl.col("is_open") & pl.col("name").is_in(list(values)))
        .with_columns(v=pl.col("name").replace_strict(values, return_dtype=pl.Float64))
        .sort("v")
    )
    ax.add_collection(
        LineCollection(
            seg(closed),
            array=closed["v"].to_numpy(),
            cmap=cm,
            norm=norm,
            linewidths=1.3,
            capstyle="round",
        )
    )
    ax.autoscale()
    ax.margins(0.04, 0.03)


def plot_circuit_voltage(
    lines: pl.DataFrame,
    volts: dict[str, float],
    coords: dict[str, tuple[float, float]],
    path: Path,
) -> None:
    """Map the base-case voltage on every branch (to-bus) and secondary load bus.

    Args:
        lines: Output of ``line_table``.
        volts: Output of ``node_voltages``.
        coords: Output of ``bus_coords``.
        path: Output image file.

    Example:
        >>> plot_circuit_voltage(line_table(), node_voltages(), bus_coords(), OUT_DIR / "circuit_voltage.png")
    """
    norm, bus_v = Normalize(0.95, 1.05), bus_voltage_value(volts)
    fig, ax = circuit_axes(coords, lines, "Voltage (pu)", norm, "viridis", "both")
    values = {
        n: bus_v[b] for n, b in lines.select("name", "to_bus").iter_rows() if b in bus_v
    }
    draw_branches(ax, lines, coords, values, norm, "viridis")
    sec = [
        b
        for b in lines.filter(pl.col("secondary"))["to_bus"].unique()
        if b in bus_v and b in coords
    ]
    ax.scatter(
        *zip(*[coords[b] for b in sec]),
        c=[bus_v[b] for b in sec],
        s=3,
        cmap=plt.get_cmap("viridis").with_extremes(under="red", over="red"),
        norm=norm,
        linewidths=0,
        zorder=3,
    )
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.03)


def plot_circuit_loading(
    lines: pl.DataFrame,
    xfmrs: pl.DataFrame,
    coords: dict[str, tuple[float, float]],
    path: Path,
) -> None:
    """Map line loading (ampacity) and distribution-transformer loading (kVA), red above 100%.

    Overloaded lines, mostly short service conductors, are circled in red.

    Args:
        lines: Output of ``line_table``.
        xfmrs: Output of ``transformer_table``.
        coords: Output of ``bus_coords``.
        path: Output image file.

    Example:
        >>> plot_circuit_loading(line_table(), transformer_table(), bus_coords(), OUT_DIR / "circuit_loading.png")
    """
    norm = Normalize(0, 100)
    fig, ax = circuit_axes(coords, lines, "Loading (%)", norm, "cividis", "max")
    draw_branches(
        ax,
        lines,
        coords,
        dict(lines.select("name", "loading_pct").iter_rows()),
        norm,
        "cividis",
    )
    over = [
        coords[b]
        for b in lines.filter(pl.col("loading_pct") > 100)["to_bus"]
        if b in coords
    ]
    ax.scatter(
        *zip(*over), s=16, facecolors="none", edgecolors="red", linewidths=0.6, zorder=4
    )
    dist = xfmrs.filter(
        ~pl.col("regulator")
        & pl.col("secondary").str.split(".").list.first().is_in(list(coords))
    )
    dist = dist.with_columns(bus=pl.col("secondary").str.split(".").list.first()).sort(
        "loading_pct"
    )
    ax.scatter(
        *zip(*[coords[b] for b in dist["bus"]]),
        c=dist["loading_pct"],
        s=7,
        marker="s",
        norm=norm,
        cmap=plt.get_cmap("cividis").with_extremes(over="red"),
        edgecolors="black",
        linewidths=0.25,
        zorder=3,
    )
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.03)


def main() -> None:
    """Solve the base case, write all figures, and print the feeder-head table and loading statistics.

    Example:
        >>> main()
    """
    solve()
    volts, dist = node_voltages(), bus_distances()
    lines, xfmrs = line_table(), transformer_table()
    head = feeder_head(lines, volts)
    style()
    plot_voltage_profiles(
        profile_segments(lines, xfmrs, volts, dist), OUT_DIR / "voltage_profiles.png"
    )
    plot_loading(lines, xfmrs, OUT_DIR / "loading_boxplots.png")
    coords = bus_coords()
    plot_circuit_voltage(lines, volts, coords, OUT_DIR / "circuit_voltage.png")
    plot_circuit_loading(lines, xfmrs, coords, OUT_DIR / "circuit_loading.png")
    balance = feeder_balance(head)
    power = [c for c in balance.columns if c.endswith(("_kw", "_kvar"))]
    total = balance.select(pl.lit("total").alias("feeder"), pl.col(power).sum())
    with pl.Config(tbl_cols=-1, tbl_rows=-1, tbl_width_chars=200):
        print(
            pl.concat([balance.with_columns(pl.col("feeder").cast(pl.String)), total], how="diagonal")
            .with_columns(pl.col(power).round(1) + 0.0, pl.col("^v_.$").round(3))
        )
    print(
        lines.filter(~pl.col("switch") & ~pl.col("is_open"))
        .group_by("feeder")
        .agg(
            pl.col("loading_pct").median().alias("median"),
            pl.col("loading_pct").max().alias("max"),
        )
        .sort("feeder")
    )
    print(
        xfmrs.filter(~pl.col("regulator"))
        .group_by("feeder")
        .agg(
            pl.col("loading_pct").median().alias("median"),
            pl.col("loading_pct").max().alias("max"),
            (pl.col("loading_pct") > 100).sum().alias("over"),
        )
        .sort("feeder")
    )


if __name__ == "__main__":
    main()
