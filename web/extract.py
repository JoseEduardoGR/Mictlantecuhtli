"""Corre las 4 propuestas, extrae series, métricas y esquemas SVG del estado armado y de apertura máxima."""
import json
import math
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))   # carpeta del proyecto (compuerta.py, params.py)
os.environ["SDL_VIDEODRIVER"] = "dummy"
import compuerta as C
import propuesta_negra as N
from pymunk import Vec2d
from params import P, PN

DEG = C.DEG
caja = C.caja


# ------------------------------------------------------------------ esquemas SVG (mundo -> viewBox 800x340)
def X(x):
    return (x + 0.50) * 1000


def Y(y):
    return (0.085 - y) * 1000


def pts(body, verts):
    return " ".join(f"{X(w.x):.1f},{Y(w.y):.1f}" for w in (body.local_to_world(v) for v in verts))


def zigzag(a, b, amp=0.004, n=22):
    d = b - a
    nn = Vec2d(-d.y, d.x).normalized() if d.length > 1e-9 else Vec2d(0, 1)
    ps = [a] + [a + d * (i / n) + nn * amp * (1 if i % 2 else -1) for i in range(1, n)] + [b]
    return " ".join(f"{X(q.x):.1f},{Y(q.y):.1f}" for q in ps)


def base_svg(sim, p):
    zx0, zx1, zy0, zy1 = p["zona_mecanismo"]
    L, e = p["compuerta_largo"], p["compuerta_espesor"]
    s = []
    s.append(f'<rect class="zone" x="{X(zx0):.1f}" y="{Y(zy1):.1f}" width="{X(zx1)-X(zx0):.1f}" height="{Y(zy0)-Y(zy1):.1f}" rx="2"/>')
    s.append(f'<text class="lbl zonelbl" x="{X(zx1):.1f}" y="{Y(zy0)+34:.1f}" text-anchor="end">zona permitida · 54 × 12 cm</text>')
    # escala 10 cm
    s.append(f'<line class="scale" x1="{X(0.14):.1f}" y1="{Y(-0.205):.1f}" x2="{X(0.24):.1f}" y2="{Y(-0.205):.1f}"/>')
    s.append(f'<text class="lbl" x="{X(0.19):.1f}" y="{Y(-0.205)+16:.1f}" text-anchor="middle">10 cm</text>')
    g = sim.compuerta
    s.append(f'<polygon class="gate" points="{pts(g, caja(0, L, -e/2, e/2))}"/>')
    tip = g.local_to_world((L, 0))
    s.append(f'<circle class="load" cx="{X(tip.x):.1f}" cy="{Y(tip.y):.1f}" r="7"/>')
    s.append(f'<circle class="pivot" cx="{X(0):.1f}" cy="{Y(0):.1f}" r="5"/>')
    s.append(f'<text class="lbl" x="{X(0)-8:.1f}" y="{Y(0)-10:.1f}" text-anchor="end">bisagra fija</text>')
    mid = g.local_to_world((L * 0.5, 0))
    if g.angle > 0:
        s.append(f'<text class="lbl" x="{X(mid.x)-8:.1f}" y="{Y(mid.y)-14:.1f}" text-anchor="end">compuerta 25 cm</text>')
    else:
        s.append(f'<text class="lbl" x="{X(mid.x)+12:.1f}" y="{Y(mid.y)-16:.1f}">compuerta 25 cm</text>')
    return s


def fila(p, items):
    zx0, zx1, zy0, zy1 = p["zona_mecanismo"]
    out = []
    for xm, txt, cls in items:
        out.append(f'<text class="lbl {cls}" x="{X(xm):.1f}" y="{Y(zy0)+16:.1f}">{txt}</text>')
    return out


def lever_svg(sim, p, extra_cord=True):
    s = []
    t, cu, cd, Lp = p["palanca_espesor"], p["brazo_elastico"], p["brazo_cuerda"], p["palanca_largo"]
    for v in (caja(0, Lp, -t / 2, t / 2), caja(-t / 2, t / 2, 0, cu), caja(-t / 2, t / 2, -cd, 0)):
        s.append(f'<polygon class="part" points="{pts(sim.palanca, v)}"/>')
    tp = sim.palanca.local_to_world((Lp, 0))
    s.append(f'<circle class="part" cx="{X(tp.x):.1f}" cy="{Y(tp.y):.1f}" r="{p["punta_radio"]*1000:.1f}"/>')
    pv = sim.piv
    s.append(f'<circle class="pivot" cx="{X(pv.x):.1f}" cy="{Y(pv.y):.1f}" r="4"/>')
    return s


def svg_p1(sim, p):
    s = base_svg(sim, p) + lever_svg(sim, p)
    a, b = sim.ancla_e, sim.palanca.local_to_world(sim.pt_arriba)
    s.append(f'<polyline class="elastic" points="{zigzag(a, b)}"/>')
    s.append(f'<circle class="pivot" cx="{X(a.x):.1f}" cy="{Y(a.y):.1f}" r="3.5"/>')
    s.append(f'<text class="lbl acc" x="{X(a.x)+4:.1f}" y="{Y(a.y)-8:.1f}">elástico</text>')
    tc = sim.tambor_c
    s.append(f'<circle class="drum" cx="{X(tc.x):.1f}" cy="{Y(tc.y):.1f}" r="{p["radio_enrolle"]*1000:.1f}"/>')
    m = tc + Vec2d(p["radio_enrolle"] * 0.7, 0).rotated(-sim.angulo_tambor)
    s.append(f'<circle class="pivot" cx="{X(m.x):.1f}" cy="{Y(m.y):.1f}" r="2.5"/>')
    cls = "cord" if sim.cuerda else "cord off"
    d = sim.palanca.local_to_world(sim.pt_abajo)
    s.append(f'<line class="{cls}" x1="{X(d.x):.1f}" y1="{Y(d.y):.1f}" x2="{X(sim.Q.x):.1f}" y2="{Y(sim.Q.y):.1f}"/>')
    s += fila(p, [(-0.485, "motor + tambor", ""), (-0.36, "cuerda (seguro)", ""), (-0.235, "palanca de una bisagra", "")])
    return "\n".join(s)


def svg_p3(sim, p):
    s = base_svg(sim, p) + lever_svg(sim, p)
    a, b = sim.ancla_e, sim.palanca.local_to_world(sim.pt_arriba)
    s.append(f'<polyline class="elastic" points="{zigzag(a, b)}"/>')
    s.append(f'<circle class="pivot" cx="{X(a.x):.1f}" cy="{Y(a.y):.1f}" r="3.5"/>')
    s.append(f'<text class="lbl acc" x="{X(a.x)+4:.1f}" y="{Y(a.y)-8:.1f}">elástico</text>')
    zx0, zx1, zy0, zy1 = p["zona_mecanismo"]
    a_arm, a_top = p["angulo_armado"] * DEG, p["leva_angulo_tope"] * DEG
    r0, r1 = p["leva_radio_min"], p["leva_radio_max"]
    centro = Vec2d(p["leva_x"], zy0 + r1 + 0.002)
    ps = []
    for i in range(120):
        ang = 2 * math.pi * i / 120
        th = sim._theta_cam(sim.phi + ang)
        r = r0 + (r1 - r0) * (th - a_arm) / (a_top - a_arm)
        q = centro + Vec2d(r, 0).rotated(math.pi + ang)
        ps.append(f"{X(q.x):.1f},{Y(q.y):.1f}")
    s.append(f'<polygon class="cam" points="{" ".join(ps)}"/>')
    s += fila(p, [(-0.485, "motor lento", ""), (-0.40, "leva de caracol (modelada)", ""), (-0.215, "palanca de una bisagra", "")])
    return "\n".join(s)


def svg_p2(sim, p):
    s = base_svg(sim, p) + lever_svg(sim, p)
    zx0, zx1, zy0, zy1 = p["zona_mecanismo"]
    R = p["volante_radio"]
    c = sim.vol_c
    s.append(f'<circle class="drum" cx="{X(c.x):.1f}" cy="{Y(c.y):.1f}" r="{R*1000:.1f}"/>')
    pin = sim.manivela.local_to_world(sim.pin_local)
    s.append(f'<line class="crank" x1="{X(c.x):.1f}" y1="{Y(c.y):.1f}" x2="{X(pin.x):.1f}" y2="{Y(pin.y):.1f}"/>')
    d = sim.palanca.local_to_world(sim.pt_abajo)
    cls = "cord" if sim.biela else "cord off"
    s.append(f'<line class="{cls}" x1="{X(pin.x):.1f}" y1="{Y(pin.y):.1f}" x2="{X(d.x):.1f}" y2="{Y(d.y):.1f}"/>')
    s.append(f'<circle class="pivot" cx="{X(pin.x):.1f}" cy="{Y(pin.y):.1f}" r="4"/>')
    s += fila(p, [(-0.485, "volante de inercia", ""), (-0.355, "biela (embrague)", ""), (-0.23, "palanca de una bisagra", "")])
    return "\n".join(s)


def svg_negra(sim, p):
    n = sim.n
    s = base_svg(sim, p)
    v = sim.viga
    a, b = v.local_to_world((0, 0)), v.local_to_world((sim.Lr, 0))
    s.append(f'<line class="rod" x1="{X(a.x):.1f}" y1="{Y(a.y):.1f}" x2="{X(b.x):.1f}" y2="{Y(b.y):.1f}"/>')
    sa, sb = v.local_to_world((sim.sa, 0)), v.local_to_world((sim.sb, 0))
    s.append(f'<line class="slot" x1="{X(sa.x):.1f}" y1="{Y(sa.y):.1f}" x2="{X(sb.x):.1f}" y2="{Y(sb.y):.1f}"/>')
    c = sim.C
    s.append(f'<circle class="drum" cx="{X(c.x):.1f}" cy="{Y(c.y):.1f}" r="{n["rueda_radio"]*1000:.1f}"/>')
    pin = sim.rueda.local_to_world(sim.pin_local)
    s.append(f'<line class="crank" x1="{X(c.x):.1f}" y1="{Y(c.y):.1f}" x2="{X(pin.x):.1f}" y2="{Y(pin.y):.1f}"/>')
    s.append(f'<circle class="pivot" cx="{X(pin.x):.1f}" cy="{Y(pin.y):.1f}" r="4"/>')
    th = max(0.0, sim.psi_rest - sim.rueda.angle)
    if th > 0.02:
        arc = " ".join(f"{X(q.x):.1f},{Y(q.y):.1f}" for q in
                       (c + Vec2d(n["rueda_radio"] * 0.8, 0).rotated(sim.rueda.angle + th * i / 30) for i in range(31)))
        s.append(f'<polyline class="elastic" points="{arc}"/>')
    s += fila(p, [(-0.485, "rueda + motor", ""), (-0.375, "viga con ranura (ariete)", "")])
    s.append(f'<text class="lbl acc" x="{X(c.x):.1f}" y="{Y(c.y)-n["rueda_radio"]*1000-10:.1f}" text-anchor="middle">elástico enrollado</text>')
    return "\n".join(s)


# ------------------------------------------------------------------ simulación
def correr(clase, svgf, params, extra=None, fire_t=0.2):
    sim = clase(P, PN) if extra else clase(P)
    dt = P["dt"]
    armado = None
    mejor, mejor_svg = -999.0, None
    tmax = 8.0
    while not sim.terminada and sim.t < tmax:
        if sim.fase == "LISTO" and not sim.liberado and sim.t >= fire_t:
            armado = svgf(sim, P)
            sim.disparar()
        sim.paso()
        if sim.liberado:
            a = sim.compuerta.angle / DEG
            if a > mejor:
                mejor, mejor_svg = a, svgf(sim, P)
    filas = sim.filas
    t0 = sim.t_lib
    return sim, armado, mejor_svg, filas, t0


salida = {}
specs = [
    ("p1", C.Compuerta, svg_p1, False),
    ("p2", C.CompuertaVolante, svg_p2, False),
    ("p3", C.CompuertaLeva, svg_p3, False),
    ("pn", N.PropuestaNegra, svg_negra, True),
]
for key, cls, f, extra in specs:
    sim, arm, best, filas, t0 = correr(cls, f, P, extra)
    ts = [r["t"] - t0 for r in filas]
    ang = [r["angulo_deg"] for r in filas]
    vp = [r["vel_punta"] for r in filas]
    # muestreo 1 ms
    step = max(1, round(0.001 / P["dt"]))
    idx = [i for i in range(0, len(ts), step) if -0.05 <= ts[i] <= 1.6]
    t_open = next((ts[i] for i in range(len(ts)) if ts[i] >= 0 and ang[i] >= 13.5), None)
    t_close = None
    seen_open = False
    for i in range(len(ts)):
        if ts[i] < 0:
            continue
        if ang[i] > -30:
            seen_open = True
        if seen_open and ang[i] <= -44.5:
            t_close = ts[i]
            break
    vmax = max(vp[i] for i in range(len(ts)) if ts[i] >= 0 and ang[i] < 13.9) if any(ts[i] >= 0 for i in range(len(ts))) else 0
    # velocidad pico "de apertura": máximo de la velocidad de la punta mientras sube
    sal = dict(
        t=[round(ts[i] * 1000, 1) for i in idx],
        ang=[round(ang[i], 2) for i in idx],
        vp=[round(vp[i], 3) for i in idx],
        t_open_ms=None if t_open is None else round(t_open * 1000),
        t_close_s=None if t_close is None else round(t_close, 2),
        vmax=round(sim.max_punta, 2),
        omega=round(sim.max_omega, 1),
        amax=round(sim.max_angulo, 1),
        E=round(sim.E_lib, 2),
        ciclo=round(sim.t_fin - sim.t_lib, 2) if sim.t_fin else None,
        armado=arm, abierta=best,
        k=P["k"] if key != "pn" else PN["k"],
    )
    salida[key] = sal
    print(key, {k: v for k, v in sal.items() if k not in ("t", "ang", "vp", "armado", "abierta")})

json.dump(salida, open(os.path.join(AQUI, "data.json"), "w"))
