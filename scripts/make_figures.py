"""Draw docs/img/hero.png, rules.png and capacity.png from the seeded run (seed 11)."""

from collections import Counter

import matplotlib.pyplot as plt
from _style import GOLD, GOLD_DIM, IMG, MUTED, SERIF, TEXT, style, title

from bl_check.engine import load, run
from bl_check.simulate import compare
from bl_check.synthetic import cases

SEED, RATE = 11, 0.03


def hero() -> None:
    r = compare(seed=SEED, rate=RATE)
    fig = plt.figure(figsize=(16, 6.4), dpi=100)
    fig.text(0.05, 0.80, "bl-check", fontfamily=SERIF, fontsize=50, color=TEXT)
    fig.text(0.05, 0.71, "Booking, VGM and B/L draft checked against each other,",
             fontsize=17, color=TEXT)
    fig.text(0.05, 0.655, "and fixed in order of cut-off.", fontsize=17, color=MUTED)
    fig.add_artist(plt.Line2D([0.05, 0.12], [0.6, 0.6], color=GOLD, lw=2))
    n, b = r["none"], r["ranked"]
    fig.text(0.95, 0.82, f"{n.amendments - b.amendments} amendments, {n.rollovers} rollovers "
             "avoided", fontfamily=SERIF, fontsize=32, color=GOLD, ha="right")
    fig.text(0.95, 0.74, "600 synthetic bookings, 3% error rate per type, seed 11",
             fontsize=13, color=MUTED, ha="right")
    ax = fig.add_axes((0.05, 0.08, 0.9, 0.44))
    ax.set_axis_off()
    rows = (("No check", "none", GOLD_DIM), ("Check, first in first out", "fifo", GOLD_DIM),
            ("Check, ranked by cut-off", "ranked", GOLD))
    top = float(n.cost)
    for y, (name, key, col) in enumerate(reversed(rows)):
        o = r[key]  # type: ignore[index]
        ax.barh(y, float(o.cost), color=col, height=0.55)
        ax.text(0, y + 0.4, name, fontsize=13, color=TEXT)
        ax.text(float(o.cost) + top * 0.01, y, f"BRL {o.cost:,.0f}  ({o.amendments} "
                f"amendments, {o.rollovers} rollovers)", va="center", fontsize=12, color=TEXT)
    ax.set_xlim(0, top * 1.6)
    ax.set_ylim(-0.5, 2.9)
    fig.savefig(IMG / "hero.png")
    plt.close(fig)


def rules() -> None:
    rs = load()
    hits = Counter(m.rule for c in cases(600, SEED, RATE) for m in run(c.shipment, rs))
    names = [r.id for r in rs.rules]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.barh(names[::-1], [hits[x] for x in names[::-1]], color=GOLD, height=0.6)
    for k, x in enumerate(names[::-1]):
        ax.text(hits[x] + 0.3, k, str(hits[x]), va="center", color=TEXT)
    ax.set_xlabel("Mismatches raised")
    title(ax, "Mismatches by rule", "600 synthetic bookings, seed 11. One error can raise "
          "two rules.")
    fig.tight_layout()
    fig.savefig(IMG / "rules.png")
    plt.close(fig)


def capacity() -> None:
    xs = list(range(1, 7))
    rs = [compare(seed=SEED, rate=RATE, per_day=k) for k in xs]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(xs, [r["none"].amendments + r["none"].rollovers for r in rs], color=MUTED, lw=2,
            ls="--", label="No check")
    ax.plot(xs, [r["fifo"].amendments + r["fifo"].rollovers for r in rs], color=GOLD_DIM,
            lw=2, marker="o", label="First in, first out")
    ax.plot(xs, [r["ranked"].amendments + r["ranked"].rollovers for r in rs], color=GOLD,
            lw=2, marker="o", label="Ranked by cut-off")
    ax.axhline(rs[0]["none"].not_catchable, color=TEXT, lw=0.8, ls=":")
    ax.text(6, rs[0]["none"].not_catchable + 2, "errors no rule can see", ha="right",
            color=TEXT, fontsize=9)
    ax.set_xlabel("Bookings one analyst can fix per day")
    ax.set_ylabel("Amendments + rollovers")
    ax.set_ylim(0)
    ax.legend(frameon=False)
    title(ax, "What the review order is worth", "600 synthetic bookings, seed 11.")
    fig.tight_layout()
    fig.savefig(IMG / "capacity.png")
    plt.close(fig)


if __name__ == "__main__":
    style()
    hero()
    rules()
    capacity()
