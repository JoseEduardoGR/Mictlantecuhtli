import json
import math

import os
SP = os.path.dirname(os.path.abspath(__file__)) + "/"
D = json.load(open(SP + "data.json"))
logo = open(SP + "logo_b64.txt").read()
html = open(SP + "template.html").read()


def X(x):
    return (x + 0.50) * 1000


def Y(y):
    return (0.085 - y) * 1000


def wrap(inner, label):
    return f'<svg viewBox="0 0 800 330" role="img" aria-label="{label}">{inner}</svg>'


names = {
    "p1": "Palanca con elástico y cuerda", "p2": "Volante de inercia", "p3": "Elástico con leva de caracol", "pn": "Rueda con ranura",
}
tags = {"p1": "P1", "p2": "P2", "p3": "P3", "pn": "P4"}
for k in ("p1", "p2", "p3", "pn"):
    t = tags[k]
    d = D[k]
    html = html.replace(f"__{t}_ARM__", wrap(d["armado"], f"{names[k]}, mecanismo armado"))
    html = html.replace(f"__{t}_OPEN__", wrap(d["abierta"], f"{names[k]}, apertura máxima de la compuerta"))
    html = html.replace(f"__{t}_E__", f'{d["E"]:.1f}')
    html = html.replace(f"__{t}_T__", str(d["t_open_ms"]))
    html = html.replace(f"__{t}_V__", f'{d["vmax"]:.1f}')
    html = html.replace(f"__{t}_W__", f'{d["omega"]:.0f}')
    html = html.replace(f"__{t}_C__", f'{d["t_close_s"]:.2f}' if d["t_close_s"] else "—")
    html = html.replace(f"__{t}_Y__", f'{d["ciclo"]:.1f}' if d["ciclo"] else "—")


# ------------------------------------------------------------------ barras
def bars(key, fmt, cls_map=None):
    vals = {k: D[k][key] for k in ("p1", "p2", "p3", "pn")}
    mx = max(vals.values())
    out = ""
    for k, cls in zip(("p1", "p2", "p3", "pn"), ("m1", "m2", "m3", "m4")):
        out += (f'<div class="bar {cls}"><span class="n">{names[k]}</span>'
                f'<div class="track"><div class="fill" style="width:{vals[k]/mx*100:.1f}%"></div></div>'
                f'<span class="v">{fmt(vals[k])}</span></div>')
    return out


html = html.replace("__BAR_T__", bars("t_open_ms", lambda v: f"{v:.0f} ms"))
html = html.replace("__BAR_E__", bars("E", lambda v: f"{v:.1f} J"))
html = html.replace("__BAR_V__", bars("vmax", lambda v: f"{v:.1f} m/s"))

# ------------------------------------------------------------------ figura de concepto (objetivo)
def robot(x, y, rot=0, color="var(--ink-2)", label=None):
    return (f'<g transform="translate({x},{y}) rotate({rot})"><rect x="0" y="-44" width="150" height="44" fill="{color}" opacity=".9" rx="2"/>'
            f'<circle cx="26" cy="2" r="17" fill="var(--ink)"/><circle cx="124" cy="2" r="17" fill="var(--ink)"/>'
            f'<circle cx="26" cy="2" r="7" fill="var(--surface-2)"/><circle cx="124" cy="2" r="7" fill="var(--surface-2)"/></g>')


def panel(ox, opened):
    g = f'<g transform="translate({ox},0)">'
    g += '<line x1="6" y1="262" x2="374" y2="262" stroke="var(--ink-3)" stroke-width="2"/>'
    # nuestro robot (izquierda)
    g += '<rect x="14" y="200" width="150" height="44" fill="var(--s1)" rx="2"/>'
    g += '<circle cx="40" cy="246" r="17" fill="var(--ink)"/><circle cx="138" cy="246" r="17" fill="var(--ink)"/>'
    g += '<circle cx="40" cy="246" r="7" fill="var(--surface-2)"/><circle cx="138" cy="246" r="7" fill="var(--surface-2)"/>'
    hx, hy = 164, 206
    ang = 14 if opened else -45
    L = 112
    tx, ty = hx + L * math.cos(math.radians(ang)), hy - L * math.sin(math.radians(ang))
    nx, ny = math.sin(math.radians(ang)) * 4, math.cos(math.radians(ang)) * 4
    g += (f'<polygon points="{hx-nx:.1f},{hy-ny:.1f} {tx-nx:.1f},{ty-ny:.1f} {tx+nx:.1f},{ty+ny:.1f} {hx+nx:.1f},{hy+ny:.1f}" '
          f'fill="var(--gate)" stroke="var(--ink-2)" stroke-width="1.5"/>')
    g += f'<circle cx="{hx}" cy="{hy}" r="5" fill="var(--accent)"/>'
    # oponente
    if opened:
        g += robot(232, 188, -26, "var(--s3)")
        g += '<path d="M 330 150 q 14 -26 4 -46" fill="none" stroke="var(--accent)" stroke-width="2" stroke-dasharray="4 4"/>'
        g += '<polygon points="330,98 338,112 324,110" fill="var(--accent)"/>'
    else:
        g += robot(222, 244, 0, "var(--s3)")
    g += '</g>'
    return g


concepto = ('<svg viewBox="0 0 800 290" role="img" aria-label="Nuestro robot a la izquierda; con la compuerta cerrada el rival está al frente, y con la compuerta abierta el rival queda levantado y volteado">'
            + panel(0, False) + panel(400, True)
            + '<text class="lbl big2" x="14" y="30">REPOSO</text><text class="lbl big2" x="414" y="30">DISPARO</text>'
            + '<text class="lbl big" x="14" y="190">nuestro robot</text><text class="lbl" x="232" y="288" opacity="0">.</text>'
            + '<text class="lbl big" x="236" y="214">rival</text>'
            + '<line x1="400" y1="10" x2="400" y2="270" stroke="var(--line)"/></svg>')
html = html.replace("__SVG_CONCEPTO__", concepto)

# ------------------------------------------------------------------ figura de zonas
zx0, zx1, zy0, zy1 = -0.4920, 0.0518, -0.1965, -0.0766
techo = 0.0629
L = 0.25
gx, gy = L * math.cos(math.radians(-45)), L * math.sin(math.radians(-45))
z = '<defs><pattern id="hat" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" stroke="var(--accent)" stroke-width="1.4" opacity=".55"/></pattern></defs>'
def rect(x0, x1, y0, y1, cls, extra=""):
    return f'<rect {cls} x="{X(x0):.1f}" y="{Y(y1):.1f}" width="{X(x1)-X(x0):.1f}" height="{Y(y0)-Y(y1):.1f}" {extra}/>'
z += rect(-0.5, 0.3, techo, 0.085, '', 'fill="url(#hat)"')                       # techo
z += rect(zx0, -0.0006, zy1, techo, '', 'fill="url(#hat)"')                    # bloque a la izquierda de la bisagra
z += rect(-0.5, 0.3, -0.22, zy0, '', 'fill="url(#hat)"')                       # piso
z += rect(0.19, 0.3, -0.22, techo, '', 'fill="url(#hat)"')                     # derecha de la compuerta
z += rect(zx0, zx1, zy0, zy1, 'class="zone"')
z += f'<polygon class="gate" points="{X(0):.1f},{Y(0)+5:.1f} {X(gx):.1f},{Y(gy)+5:.1f} {X(gx)+7:.1f},{Y(gy)-2:.1f} {X(0):.1f},{Y(0)-5:.1f}"/>'
z += f'<circle class="pivot" cx="{X(0):.1f}" cy="{Y(0):.1f}" r="5"/>'
z += f'<text class="lbl" x="{X(0)-8:.1f}" y="{Y(0)-10:.1f}" text-anchor="end">bisagra</text>'
z += f'<text class="lbl" x="{X(0.07):.1f}" y="{Y(-0.05):.1f}">compuerta</text>'
z += f'<text class="lbl" x="{X(-0.24):.1f}" y="{Y(-0.136):.1f}" text-anchor="middle" style="fill:var(--ink)">mecanismo aquí</text>'
z += f'<text class="lbl acc" x="{X(-0.38):.1f}" y="{Y(0.07):.1f}">sin piezas</text>'
z += f'<text class="lbl acc" x="{X(-0.38):.1f}" y="{Y(-0.21):.1f}">sin piezas</text>'
z += f'<text class="lbl acc" x="{X(0.205):.1f}" y="{Y(0.0):.1f}">sin piezas</text>'
# cotas
z += f'<line class="scale" x1="{X(zx0):.1f}" y1="{Y(-0.185)+0:.1f}" x2="{X(zx0):.1f}" y2="{Y(-0.185):.1f}"/>'
z += f'<line x1="{X(zx0):.1f}" y1="{Y(zy1)-8:.1f}" x2="{X(zx1):.1f}" y2="{Y(zy1)-8:.1f}" stroke="var(--ink-3)" stroke-width="1"/>'
z += f'<text class="lbl" x="{X((zx0+zx1)/2):.1f}" y="{Y(zy1)-12:.1f}" text-anchor="middle">54 cm de largo (50 cm útiles a la izquierda)</text>'
z += f'<line x1="{X(zx0)-10:.1f}" y1="{Y(zy1):.1f}" x2="{X(zx0)-10:.1f}" y2="{Y(zy0):.1f}" stroke="var(--ink-3)" stroke-width="1"/>'
z += f'<text class="lbl" x="{X(zx0)-14:.1f}" y="{Y((zy0+zy1)/2):.1f}" text-anchor="end" dy="4">12 cm</text>'
html = html.replace("__SVG_ZONA__", wrap(z, "Zona permitida para el mecanismo: 54 por 12 centímetros, a la izquierda y debajo de la bisagra; arriba, abajo y a la derecha de la compuerta no puede haber piezas"))


DOC, ARM, HW, SW = "Documentación", "Armado", "Diseño · hardware", "Diseño · software"
PEOPLE = [
 ("Acevedo Cipriano Yamir Eduardo", [], [ARM]),
 ("Aguilar Pérez Christian Yahel", ["Jefe de diseño"], [HW]),
 ("Benítez Vizuet Erick Elías", [], [ARM]),
 ("Carera Barreto Jayro Julián", [], [DOC]),
 ("Castro Castillo Grisel Jaqueline", [], [HW]),
 ("Domínguez Cárdenas Esteban", [], []),
 ("García Ruiz David Garek", ["Programador"], [ARM, SW]),
 ("González Rosales José Eduardo", ["Jefe general", "Jefe de programación"], [SW]),
 ("Jiménez Abad Dafne Guadalupe", [], [DOC]),
 ("Maturano Cano Edgar Oswaldo", [], [ARM]),
 ("Medina López Olinzi", ["Secretaria", "Tesorera"], [DOC]),
 ("Mena Piña Vania Elizabeth", ["Subjefe"], [DOC, HW]),
 ("Mendoza Paz Héctor Isaac", [], [ARM]),
 ("Morales Hernández César Adrián", [], []),
 ("Nahuacatl Caballero Kenji Omar", [], [HW]),
 ("Razo Vázquez Alfredo Ulises", ["Jefe de construcción"], [ARM]),
 ("Reyna Zainos Sebastián", [], [DOC, ARM]),
 ("Rico García Stephanie Odette", [], [HW]),
 ("Sánchez Calderón Aldo", [], [HW, ARM]),
 ("Vázquez Alvarado Enrique Antonio", [], []),
]
JEFES = {DOC: None, ARM: "Razo Vázquez Alfredo Ulises", HW: "Aguilar Pérez Christian Yahel", SW: "González Rosales José Eduardo"}
ORDEN = {
 DOC: ["Mena Piña Vania Elizabeth", "Medina López Olinzi", "Jiménez Abad Dafne Guadalupe", "Carera Barreto Jayro Julián", "Reyna Zainos Sebastián"],
 ARM: ["Razo Vázquez Alfredo Ulises", "García Ruiz David Garek", "Mendoza Paz Héctor Isaac", "Maturano Cano Edgar Oswaldo", "Acevedo Cipriano Yamir Eduardo", "Benítez Vizuet Erick Elías", "Reyna Zainos Sebastián", "Sánchez Calderón Aldo"],
 HW: ["Aguilar Pérez Christian Yahel", "Mena Piña Vania Elizabeth", "Rico García Stephanie Odette", "Nahuacatl Caballero Kenji Omar", "Castro Castillo Grisel Jaqueline", "Sánchez Calderón Aldo"],
 SW: ["González Rosales José Eduardo", "García Ruiz David Garek"],
}
TITULO = {DOC: "Documentación", ARM: "Armado (construcción)", HW: "Diseño · hardware", SW: "Diseño · software (programación)"}
def area_card(a):
    li = ""
    for n in ORDEN[a]:
        tag = "<small>jefe</small>" if JEFES[a] == n else ""
        li += f"<li><span>{n}</span>{tag}</li>"
    return f'<div class="card2"><h4>{TITULO[a]}</h4><ul class="members">{li}</ul></div>'
html = html.replace("__AREAS__", "".join(area_card(a) for a in (DOC, ARM, HW, SW)))
def persona(n, roles, areas):
    r = "".join(f'<span class="role">{x}</span>' for x in roles) + "".join(f'<span class="area">{x}</span>' for x in areas)
    return f'<li><span class="nm">{n}</span>{r}</li>'
html = html.replace("__PEOPLE__", "".join(persona(n, r, a) for n, r, a in PEOPLE))

html = html.replace("__LOGO_S__", open(SP + "logo_small_b64.txt").read())
import base64
for marca, nombre in (("__IMG_CARGA__", "barrido_carga.png"), ("__IMG_PARAM__", "barrido_parametros.png"), ("__IMG_FUERZA__", "fuerza_palanca_p1.png")):
    ruta = os.path.join(os.path.dirname(SP.rstrip("/")), "docs", "img", nombre)
    html = html.replace(marca, base64.b64encode(open(ruta, "rb").read()).decode())
html = html.replace("__ICON__", open(SP + "icon_b64.txt").read())
html = html.replace("__LOGO__", logo)
data = {k: {kk: D[k][kk] for kk in ("t", "ang", "vp")} for k in D}
html = html.replace("__DATA__", json.dumps(data, separators=(",", ":")))
left = [s for s in html.split("__") if s and s[:1].isupper() and s.isupper() and len(s) < 14]
print("placeholders sobrantes:", [m for m in __import__("re").findall(r"__[A-Z0-9_]+__", html)])
# Documento completo y autocontenido para publicarlo (GitHub Pages sirve la carpeta docs/)
corte = html.index('<div class="top">')
cabeza, cuerpo = html[:corte].replace('<meta name="claude:viewport-fit-sides" content="cover">\n', ''), html[corte:]
doc = ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       + cabeza + '</head>\n<body>\n' + cuerpo + '\n</body>\n</html>\n')
destino = os.path.join(os.path.dirname(SP.rstrip("/")), "docs", "index.html")
os.makedirs(os.path.dirname(destino), exist_ok=True)
open(destino, "w", encoding="utf-8").write(doc)
open(os.path.join(os.path.dirname(destino), ".nojekyll"), "w").close()
print("escrito", destino, len(doc))
