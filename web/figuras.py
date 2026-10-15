"""
figuras.py -- Genera las figuras de la documentación en docs/img/ (para el README).

  1. Gráficas comparativas (ángulo, velocidad, barras) a partir de web/data.json
  2. Barridos paramétricos: carga en la punta, rigidez, velocidad del volante
  3. Fuerza del elástico y fuerza en la punta de la palanca contra el ángulo (propuesta 1, analítico)
  4. Esquemas de cada mecanismo (armado y apertura máxima), de la zona y del concepto, tomados de docs/index.html

Uso (desde la carpeta del proyecto):
    .venv/bin/python web/extract.py && .venv/bin/python web/build.py     # genera data.json y docs/index.html
    .venv/bin/python web/figuras.py
"""
import json
import os
import re
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)
os.environ["SDL_VIDEODRIVER"] = "dummy"
import compuerta as C
import propuesta_negra as N
from params import P, PN

OUT = os.path.join(RAIZ, "docs", "img")
os.makedirs(OUT, exist_ok=True)
D = json.load(open(os.path.join(AQUI, "data.json")))
KEYS = ["p1", "p2", "p3", "pn"]
NOM = {"p1": "1 · Palanca, elástico y cuerda", "p2": "2 · Volante de inercia", "p3": "3 · Elástico con leva", "pn": "Equipo · Rueda con ranura"}
COL = {"p1": "#2a78d6", "p2": "#eb6834", "p3": "#1baf7a", "pn": "#eda100"}
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.alpha": 0.25, "figure.dpi": 130})


def guardar(fig, nombre):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, nombre))
    plt.close(fig)
    print("figura:", nombre)


# ---------------------------------------------------------------- 1. comparativas
def comparativas():
    for clave, y0, y1, ylabel, x1, nombre, ref in (
        ("ang", -50, 20, "ángulo de la compuerta [°]", 1500, "comparativa_angulo.png", 14),
        ("vp", 0, 8, "velocidad de la punta de la compuerta [m/s]", 350, "comparativa_velocidad.png", None),
    ):
        fig, ax = plt.subplots(figsize=(9, 4.4))
        for k in KEYS:
            t = D[k]["t"]
            xs = [a for a in t if -50 <= a <= x1]
            ys = D[k][clave][:len(xs)] if t[0] >= -50 else D[k][clave]
            pts = [(a, b) for a, b in zip(t, D[k][clave]) if -50 <= a <= x1]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=COL[k], lw=1.8, label=NOM[k])
        if ref is not None:
            ax.axhline(ref, color="#6a7088", ls=":", lw=1)
            ax.text(x1 * 0.995, ref - 0.8, "tope superior 14°", ha="right", va="top", fontsize=8, color="#6a7088")
        ax.axvline(0, color="#6a7088", ls=":", lw=1)
        ax.set_xlim(-50 if clave == "ang" else -20, x1)
        ax.set_ylim(y0, y1)
        ax.set_xlabel("tiempo desde el disparo [ms]")
        ax.set_ylabel(ylabel)
        ax.legend(frameon=False, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
        guardar(fig, nombre)

    fig, axs = plt.subplots(1, 3, figsize=(11, 3.4))
    for ax, (clave, titulo, fmt) in zip(axs, (("t_open_ms", "Tiempo hasta 14° [ms]", "{:.0f}"),
                                              ("E", "Energía almacenada [J]", "{:.1f}"),
                                              ("vmax", "Velocidad pico de la punta [m/s]", "{:.1f}"))):
        vals = [D[k][clave] for k in KEYS]
        ax.barh(range(4), vals, color=[COL[k] for k in KEYS])
        ax.set_yticks(range(4))
        ax.set_yticklabels(["1", "2", "3", "Equipo"] if ax is axs[0] else [""] * 4)
        ax.invert_yaxis()
        ax.set_title(titulo, fontsize=10)
        ax.grid(axis="y", alpha=0)
        for i, v in enumerate(vals):
            ax.text(v, i, " " + fmt.format(v), va="center", fontsize=9)
        ax.set_xlim(0, max(vals) * 1.25)
    guardar(fig, "comparativa_barras.png")


# ---------------------------------------------------------------- 2. barridos
def correr(cls, extra, **kw):
    p, pn = dict(P), dict(PN)
    (pn if extra else p).update(kw)
    sim = cls(p, pn) if extra else cls(p)
    dt = p["dt"]
    n = 0
    while sim.fase != "LISTO" and n < 40000:
        sim.paso()
        n += 1
    for _ in range(int(0.05 / dt)):
        sim.paso()
    sim.disparar()
    amax, t14 = -99.0, None
    for _ in range(int(0.8 / dt)):
        sim.paso()
        a = sim.compuerta.angle / C.DEG
        amax = max(amax, a)
        if t14 is None and a >= 13.5:
            t14 = (sim.t - sim.t_lib) * 1000
    return amax, t14


def barridos():
    cargas = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8]
    fig, ax = plt.subplots(figsize=(8, 4))
    for k, cls, extra in (("p1", C.Compuerta, False), ("p2", C.CompuertaVolante, False), ("pn", N.PropuestaNegra, True)):
        ys = [correr(cls, extra, carga_punta_masa=c)[0] for c in cargas]
        ax.plot(cargas, ys, "o-", color=COL[k], label=NOM[k], lw=1.8, ms=4)
        print("  carga", k, [round(y, 1) for y in ys])
    ax.axhline(14, color="#6a7088", ls=":", lw=1)
    ax.text(0.8, 14.6, "tope 14°", ha="right", fontsize=8, color="#6a7088")
    ax.set_xlabel("masa extra en la punta de la compuerta [kg]")
    ax.set_ylabel("ángulo máximo alcanzado [°]")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("Qué carga levanta cada propuesta", fontsize=11)
    guardar(fig, "barrido_carga.png")

    sets = (
        ("Propuesta 1 · rigidez k [N/m]", C.Compuerta, False, "k", [1500, 2000, 2500, 3000, 3400, 4000, 4500], "p1"),
        ("Propuesta 2 · velocidad del volante [rad/s]", C.CompuertaVolante, False, "volante_velocidad", [100, 125, 150, 200, 250], "p2"),
        ("Equipo · rigidez k [N/m]", N.PropuestaNegra, True, "k", [300, 400, 500, 700, 1000, 1500], "pn"),
    )
    fig, axs = plt.subplots(2, 3, figsize=(11, 5.4), sharex="col")
    for j, (titulo, cls, extra, par, vals, k) in enumerate(sets):
        res = [correr(cls, extra, **{par: v}) for v in vals]
        axs[0, j].plot(vals, [r[0] for r in res], "o-", color=COL[k], lw=1.8, ms=4)
        axs[0, j].axhline(14, color="#6a7088", ls=":", lw=1)
        axs[0, j].set_ylim(-20, 20)
        axs[0, j].set_title(titulo, fontsize=9)
        axs[1, j].plot([v for v, r in zip(vals, res) if r[1]], [r[1] for r in res if r[1]], "o-", color=COL[k], lw=1.8, ms=4)
        axs[1, j].set_xlabel(par)
        print("  barrido", k, par, [(v, round(r[0], 1), None if r[1] is None else round(r[1])) for v, r in zip(vals, res)])
    axs[0, 0].set_ylabel("ángulo máximo [°]")
    axs[1, 0].set_ylabel("tiempo hasta 14° [ms]\n(solo si llega)")
    guardar(fig, "barrido_parametros.png")


# ---------------------------------------------------------------- 3. fuerza de la palanca (propuesta 1)
def fuerza_palanca():
    import numpy as np
    sim = C.Compuerta(P)
    angs = np.linspace(-10, 50, 121)
    T, F, E = [], [], []
    for a in angs:
        sim.palanca.angle = a * C.DEG
        sim.palanca.position = sim.piv            # al cambiar el ángulo, Pymunk deja fijo el centro de gravedad: hay que reponer el origen
        top = sim.palanca.local_to_world(sim.pt_arriba)
        ext = (top - sim.ancla_e).length - sim.largo_libre
        t = P["k"] * max(0.0, ext)
        u = (sim.ancla_e - top).normalized()
        par = (top - sim.piv).cross(t * u)          # con signo: positivo = levanta la punta
        T.append(t)
        F.append(par / P["palanca_largo"])
        E.append(0.5 * P["k"] * max(0.0, ext) ** 2)
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8))
    axs[0].plot(angs, np.array(F) / 9.81, color=COL["p1"], lw=2)
    axs[0].axhline(0, color="#6a7088", lw=1)
    axs[0].set_xlabel("ángulo de la palanca [°]")
    axs[0].set_ylabel("fuerza en la punta [kgf]  (+ levanta)")
    axs[0].set_title("Empuje de la palanca (propuesta 1)", fontsize=10)
    ax2 = axs[1]
    ax2.plot(angs, E, color=COL["p1"], lw=2)
    ax2.set_xlabel("ángulo de la palanca [°]")
    ax2.set_ylabel("energía en el elástico [J]")
    ax2.set_title("Energía que queda en el elástico", fontsize=10)
    guardar(fig, "fuerza_palanca_p1.png")
    print("  F punta armada %.1f kgf, E armada %.1f J" % (F[0] / 9.81, E[0]))


# ---------------------------------------------------------------- 4. esquemas
CSS = """
:root{--ink:#0f1424;--ink-2:#454c63;--ink-3:#6a7088;--line:#d3d8e4;--surface:#fcfcfb;--surface-2:#f1f3f8;--accent:#c92f2a;
--gate:#aebcd6;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100}
body{margin:0;background:#fff}svg{display:block;width:100%;height:auto;background:#fff}
.zone{fill:#e8e2f2;stroke:#8b78b8;stroke-dasharray:5 4;stroke-width:1.2}
.gate{fill:var(--gate);stroke:var(--ink-2);stroke-width:1.2}.load{fill:var(--ink-2)}.pivot{fill:var(--accent)}
.part{fill:var(--mc);stroke:#0f1424;stroke-width:.8;stroke-opacity:.55}
.elastic{fill:none;stroke:var(--accent);stroke-width:2;stroke-linejoin:round}
.cord{stroke:var(--ink-2);stroke-width:2.5}.cord.off{stroke-dasharray:3 5;opacity:.45}
.drum,.cam{fill:#fcfcfb;stroke:var(--ink-3);stroke-width:1.6}.crank{stroke:var(--ink-3);stroke-width:2}
.rod{stroke:var(--mc);stroke-width:9}.slot{stroke:#fcfcfb;stroke-width:3}.scale{stroke:var(--ink-3);stroke-width:2}
.lbl{font:11px monospace;fill:var(--ink-2)}.lbl.acc{fill:var(--accent)}.zonelbl{fill:var(--ink-3)}
.lbl.big{font-size:20px}.lbl.big2{font-size:24px;letter-spacing:.08em}
"""


def esquemas():
    pagina = open(os.path.join(RAIZ, "docs", "index.html"), encoding="utf-8").read()
    svgs = re.findall(r'<svg viewBox="0 0 800 (?:330|290)".*?</svg>', pagina, flags=re.S)
    nombres = ["zona", "p1_armado", "p1_abierta", "p2_armado", "p2_abierta", "p3_armado", "p3_abierta", "pn_armado", "pn_abierta"]
    concepto = [s for s in svgs if 'viewBox="0 0 800 290"' in s]
    mec = [s for s in svgs if 'viewBox="0 0 800 330"' in s]
    items = list(zip(nombres, mec)) + [("concepto", concepto[0])]
    mc = {"p1": "var(--s1)", "p2": "var(--s2)", "p3": "var(--s3)", "pn": "var(--s4)"}
    for nombre, svg in items:
        color = mc.get(nombre.split("_")[0], "var(--s1)")
        alto = 580 if nombre == "concepto" else 660
        html = f"<!doctype html><meta charset=utf-8><style>{CSS} svg{{--mc:{color}}}</style><body>{svg}</body>"
        h = os.path.join(OUT, f"_{nombre}.html")
        open(h, "w", encoding="utf-8").write(html)
        subprocess.run(["google-chrome-stable", "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        "--default-background-color=ffffffff", f"--window-size=1600,{alto}",
                        f"--screenshot={os.path.join(OUT, 'esquema_' + nombre + '.png')}", "file://" + h],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
        os.remove(h)
        print("figura: esquema_%s.png" % nombre)


if __name__ == "__main__":
    comparativas()
    fuerza_palanca()
    barridos()
    esquemas()
