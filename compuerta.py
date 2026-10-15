"""
compuerta.py -- Compuerta con bisagra "Fija" levantada de golpe desde abajo por una PALANCA de una sola
bisagra, accionada por un elástico y rearmada por un motor. Todo cabe en la zona morada del boceto.

Mapeo boceto -> Pymunk (valores en params.P):
  Compuerta (viga)   -> self.compuerta: Body + Poly (+ carga en la punta). El origen del cuerpo ES la bisagra.
  "Fija" (bisagra)   -> PivotJoint(static_body, compuerta)
  Topes de ángulo    -> RotaryLimitJoint(static_body, compuerta, [cerrado, abierto])
  Palanca            -> self.palanca: Body con 3 Poly (brazo largo, brazo corto arriba, brazo corto abajo)
                        + círculo en la punta; PivotJoint al mundo (UNA bisagra, nada desliza)
                        y RotaryLimitJoint [armado, máx] como topes.
  Elástico           -> self.elastico: DampedSpring(static_body, palanca) sobre el brazo de arriba. Solo tira.
                        Tirar el brazo de arriba hacia la izquierda gira la palanca hacia ARRIBA (golpe).
  Motor + tambor     -> la cuerda se modela como SlideJoint(palanca [brazo de abajo], punto del tambor) cuyo
                        largo máximo se acorta a radio_enrolle * motor_velocidad; max_force = torque / radio.
                        Tirar el brazo de abajo hacia la izquierda gira la palanca hacia ABAJO (rearmar).
                        Esa cuerda tensa es también el seguro: ESPACIO la suelta y el elástico dispara.
Fases: LISTO (armado) -> ESPACIO -> DISPARADO -> (espera) -> REARMANDO (la compuerta baja) -> LISTO.
Teclas: ESPACIO disparar | A rearmar ya | R reiniciar | P pausa | flechas arriba/abajo: k | ESC salir
Uso:  python compuerta.py           (ventana)
      python compuerta.py --auto    (sin ventana: dispara solo, guarda CSV, gráfica y capturas)
"""
import argparse
import csv
import math
import os

import matplotlib
import pymunk
from pymunk import Vec2d

from params import P

DEG = math.pi / 180.0


def caja(x0, x1, y0, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


class Compuerta:
    def __init__(self, params):
        self.p = dict(params)
        self.reiniciar()

    # ------------------------------------------------------------------ construcción
    def reiniciar(self):
        p = self.p
        self.space = pymunk.Space()
        self.space.gravity = (0, -p["gravedad"])
        self.space.iterations = p["iteraciones"]
        est = self.space.static_body
        self.t, self.t_lib, self.t_fin = 0.0, None, None
        self.liberado = self.guardado = self.ciclo_completo = False
        self.filas, self.archivos, self.avisos = [], "", []
        f_g = pymunk.ShapeFilter(categories=0b01, mask=0b10)       # la compuerta solo choca con la palanca
        f_p = pymunk.ShapeFilter(categories=0b10, mask=0b01)

        # --- Compuerta ---
        L, e, m, mc = p["compuerta_largo"], p["compuerta_espesor"], p["compuerta_masa"], p["carga_punta_masa"]
        M = m + mc
        cg = Vec2d((m * L / 2 + mc * L) / M, 0)
        I0 = pymunk.moment_for_poly(m, caja(0, L, -e / 2, e / 2)) + mc * L * L   # respecto a la bisagra
        self.compuerta = pymunk.Body(M, I0 - M * cg.length_squared)
        self.compuerta.center_of_gravity = cg
        a0 = p["angulo_cerrado"] * DEG
        self.compuerta.angle = a0
        self.compuerta.position = p["bisagra"]
        forma = pymunk.Poly(self.compuerta, caja(0, L, -e / 2, e / 2))
        forma.filter, forma.friction, forma.elasticity = f_g, p["friccion_contacto"], 0.0
        self.space.add(self.compuerta, forma, pymunk.PivotJoint(est, self.compuerta, p["bisagra"]))
        self.space.add(pymunk.DampedRotarySpring(est, self.compuerta, 0, 0, p["friccion_bisagra"]))
        self.space.add(pymunk.RotaryLimitJoint(est, self.compuerta, a0 - 0.005, p["angulo_abierto"] * DEG))

        # --- Palanca: origen en el pivote; partes -> masa, centro de gravedad e inercia ---
        Lp, t, rp = p["palanca_largo"], p["palanca_espesor"], p["punta_radio"]
        cu, cd = p["brazo_elastico"], p["brazo_cuerda"]
        mp = p["palanca_masa"]
        partes = [  # (vértices, masa)
            (caja(0, Lp, -t / 2, t / 2), 0.80 * mp),
            (caja(-t / 2, t / 2, 0, cu), 0.10 * mp),
            (caja(-t / 2, t / 2, -cd, 0), 0.10 * mp),
        ]
        Mp = sum(x[1] for x in partes)
        cen = lambda v: Vec2d(sum(a for a, _ in v) / len(v), sum(b for _, b in v) / len(v))
        cog_p = sum((cen(v) * mm for v, mm in partes), Vec2d(0, 0)) / Mp
        I0p = sum(pymunk.moment_for_poly(mm, v) for v, mm in partes)
        self.palanca = pymunk.Body(Mp, I0p - Mp * cog_p.length_squared)
        self.palanca.center_of_gravity = cog_p
        ap = p["angulo_armado"] * DEG
        self.palanca.angle = ap
        # El pivote va a la altura configurada; x se fija para que la punta armada quede en el borde derecho de la zona
        zx0, zx1, zy0, zy1 = p["zona_mecanismo"]
        self.piv = Vec2d(zx1 - p["margen_derecho"] - (Lp + rp) * math.cos(ap), p["palanca_pivote_y"])
        self.palanca.position = self.piv
        shp = [pymunk.Poly(self.palanca, v) for v, _ in partes]
        shp.append(pymunk.Circle(self.palanca, rp, (Lp, 0)))
        for s in shp:
            s.filter, s.friction, s.elasticity = f_p, p["friccion_contacto"], 0.0
        self.space.add(self.palanca, *shp, pymunk.PivotJoint(est, self.palanca, self.piv))
        self.space.add(pymunk.RotaryLimitJoint(est, self.palanca, ap - 0.03, p["angulo_max"] * DEG))
        self.Lp = Lp

        self.pt_arriba, self.pt_abajo = (0.0, cu), (0.0, -cd)
        self.fase, self.angulo_tambor = "LISTO", 0.0
        self.max_omega = self.max_punta = self.max_palanca = 0.0
        self.max_angulo = self.compuerta.angle / DEG
        self.E_lib = 0.0
        self.F_pico, self.F_suma, self.F_n = 0.0, 0.0, 0
        self._accionamiento()
        self.F_armada = self.fuerza_punta_armada()

        # --- Avisos de zona ---
        if self.piv.x - 0 < zx0 or self.piv.x + (Lp + rp) * math.cos(ap) > zx1 + 1e-6:
            self.avisos.append("la palanca sobrepasa la zona por la derecha o la izquierda")
        if self.piv.y - cd < zy0 or self.piv.y + cu > zy1:
            self.avisos.append("los brazos de la palanca se salen de la altura de la zona")
        if self.piv.y + (Lp + rp) * math.sin(ap) - rp < zy0:
            self.avisos.append("la punta armada queda por debajo de la zona")
        self._avisos_accionamiento(zx0, zx1, zy0, zy1)

    # ------------------------------------------------------------------ accionamiento (propuesta 1: elástico + cuerda del motor)
    ETIQ_FUERZA = "tensión del elástico"
    ETIQ_ENERGIA = "elástico"
    NOMBRE = "propuesta1_elastico_cuerda"

    def _crear_elastico(self):
        """Elástico del extremo del brazo de arriba a un ancla fija a la izquierda."""
        p, est = self.p, self.space.static_body
        top = self.palanca.local_to_world(self.pt_arriba)
        self.ancla_e = Vec2d(p["ancla_elastico_x"], top.y)
        self.largo_libre = (top - self.ancla_e).length - p["extension_armado"]
        self.elastico = pymunk.DampedSpring(est, self.palanca, self.ancla_e, self.pt_arriba,
                                            self.largo_libre, p["k"], p["amortiguamiento"])
        self.space.add(self.elastico)

    def _accionamiento(self):
        p = self.p
        self._crear_elastico()
        # Cuerda del motor: del extremo del brazo de abajo al punto de salida del tambor (a su izquierda)
        self.tambor_c = Vec2d(p["tambor_x"], self.piv.y - p["brazo_cuerda"] + p["radio_enrolle"])
        self.Q = Vec2d(p["tambor_x"], self.piv.y - p["brazo_cuerda"])   # punto donde la cuerda sale del tambor
        self.cuerda = None
        self.long_hold = None
        self._poner_cuerda()

    def _avisos_accionamiento(self, zx0, zx1, zy0, zy1):
        p = self.p
        if self.ancla_e.x < zx0 or p["tambor_x"] - p["radio_enrolle"] < zx0 or 2 * p["radio_enrolle"] > zy1 - zy0 + 1e-6:
            self.avisos.append("el ancla del elástico o el tambor se salen de la zona")

    def _elastico_unilateral(self):
        p = self.p
        if self.extension() > 0:                      # estirado: tira
            self.elastico.stiffness, self.elastico.damping = p["k"], p["amortiguamiento"]
        else:                                         # flojo: un elástico no empuja
            self.elastico.stiffness = self.elastico.damping = 0.0

    def _antes_paso(self):
        p, dt = self.p, self.p["dt"]
        self._elastico_unilateral()
        if self.fase == "REARMANDO":
            self.long_cuerda = max(0.001, self.long_cuerda - p["radio_enrolle"] * p["motor_velocidad"] / p["reduccion"] * dt)
            self.cuerda.max = self.long_cuerda
            self.angulo_tambor += p["motor_velocidad"] / p["reduccion"] * dt
            if self.palanca.angle <= p["angulo_armado"] * DEG + 0.01:      # llegó a su posición armada
                self.fase = "LISTO"
                self.cuerda.max = self.long_cuerda                          # queda tensa = seguro
                if self.liberado and not self.ciclo_completo:
                    self.ciclo_completo, self.t_fin = True, self.t
        elif self.fase == "DISPARADO" and self.t - self.t_lib >= p["espera_rearmado"]:
            self.rearmar()

    def hud_accionamiento(self):
        return (f"k = {self.p['k']:6.1f} N/m   extensión = {self.extension()*1000:5.1f} mm   "
                f"tensión = {self.tension():5.1f} N")

    def dibujar_accionamiento(self, pg, pan, s, esc):
        p = self.p
        tp = s(self.tambor_c)
        pg.draw.circle(pan, (230, 200, 120), tp, int(p["radio_enrolle"] * esc))
        pg.draw.circle(pan, (120, 80, 10), tp, int(p["radio_enrolle"] * esc), 2)
        m = self.tambor_c + Vec2d(p["radio_enrolle"] * 0.7, 0).rotated(-self.angulo_tambor)
        pg.draw.circle(pan, (120, 80, 10), s(m), 3)
        pg.draw.line(pan, (0, 130, 0) if self.cuerda else (180, 180, 180),
                     s(self.palanca.local_to_world(self.pt_abajo)), s(self.Q), 2)
        self._dibujar_elastico(pg, pan, s)

    def _dibujar_elastico(self, pg, pan, s):
        a, b = self.ancla_e, self.palanca.local_to_world(self.pt_arriba)
        d = b - a
        nn = Vec2d(-d.y, d.x).normalized()
        zz = [a] + [a + d * (i / 20) + nn * 0.0015 * (1 if i % 2 else -1) for i in range(1, 20)] + [b]
        pg.draw.lines(pan, (200, 40, 40) if self.extension() > 0 else (60, 140, 60), False, [s(q) for q in zz], 2)
        pg.draw.circle(pan, (200, 30, 30), s(self.ancla_e), 4)

    # ------------------------------------------------------------------ cuerda / motor
    def _poner_cuerda(self):
        p = self.p
        # largo máximo un poco menor que la distancia real: un SlideJoint justo en su límite no ejerce fuerza
        d = (self.palanca.local_to_world(self.pt_abajo) - self.Q).length
        self.long_cuerda = max(0.001, d - 0.0005)
        if self.long_hold is None:
            self.long_hold = self.long_cuerda
        self.cuerda = pymunk.SlideJoint(self.palanca, self.space.static_body, self.pt_abajo, self.Q,
                                        0.0, self.long_cuerda)
        self.cuerda.max_force = p["motor_torque"] * p["reduccion"] / p["radio_enrolle"]
        self.space.add(self.cuerda)

    def disparar(self):
        if self.fase != "LISTO":
            return
        self.E_lib = self.energia()
        self.space.remove(self.cuerda)
        self.cuerda = None
        self.fase, self.liberado, self.t_lib = "DISPARADO", True, self.t
        self.max_omega = self.max_punta = self.max_palanca = 0.0
        self.max_angulo = self.compuerta.angle / DEG
        self.F_pico, self.F_suma, self.F_n = 0.0, 0.0, 0

    def rearmar(self):
        if self.fase != "DISPARADO":
            return
        self._poner_cuerda()
        self.fase = "REARMANDO"

    soltar = disparar

    # ------------------------------------------------------------------ mediciones
    def punta(self):
        return self.compuerta.local_to_world((self.p["compuerta_largo"], 0))

    def punta_palanca(self):
        return self.palanca.local_to_world((self.Lp, 0))

    def extension(self):
        return (self.palanca.local_to_world(self.pt_arriba) - self.ancla_e).length - self.largo_libre

    def tension(self):
        return self.p["k"] * max(0.0, self.extension())

    def energia(self):
        return 0.5 * self.p["k"] * max(0.0, self.extension()) ** 2

    def vel_punta(self):
        return self.compuerta.velocity_at_local_point((self.p["compuerta_largo"], 0)).length

    def fuerza_contacto(self):
        """Fuerza total palanca -> compuerta en el último subpaso [N] (la compuerta solo choca con la palanca)."""
        imp = 0.0

        def f(arb):
            nonlocal imp
            imp += arb.total_impulse.length
        self.compuerta.each_arbiter(f)
        return imp / self.p["dt"]

    def fuerza_punta_armada(self):
        """Fuerza estática hacia arriba en la punta de la palanca con el elástico armado [N]."""
        top = self.palanca.local_to_world(self.pt_arriba)
        u = (self.ancla_e - top).normalized()
        par = self.piv_a_top().cross(u) * self.tension() if hasattr(self, "piv_a_top") else 0.0
        return abs(par) / self.Lp

    def piv_a_top(self):
        return self.palanca.local_to_world(self.pt_arriba) - self.piv

    def vel_punta_palanca(self):
        return self.palanca.velocity_at_local_point((self.Lp, 0)).length

    # ------------------------------------------------------------------ física
    def paso(self):
        p, dt = self.p, self.p["dt"]
        self._antes_paso()
        self.space.step(dt)
        self.t += dt
        c = self.compuerta
        vp, vl = self.vel_punta(), self.vel_punta_palanca()
        fc = self.fuerza_contacto()
        if self.liberado and self.fase == "DISPARADO" and c.angle / DEG < p["angulo_abierto"] - 0.5 and fc > 1.0:
            self.F_pico = max(self.F_pico, fc)
            self.F_suma += fc
            self.F_n += 1
        if self.liberado:
            self.max_omega = max(self.max_omega, abs(c.angular_velocity))
            self.max_punta = max(self.max_punta, vp)
            self.max_palanca = max(self.max_palanca, vl)
            self.max_angulo = max(self.max_angulo, c.angle / DEG)
        self.filas.append(dict(
            t=round(self.t, 6), fase=self.fase, angulo_deg=c.angle / DEG, omega=c.angular_velocity,
            vel_punta=vp, angulo_palanca_deg=self.palanca.angle / DEG, vel_punta_palanca=vl,
            altura_punta=self.punta().y, fuerza_contacto=fc, tension=self.tension(), energia_elastico=self.energia(),
            energia_cinetica_compuerta=c.kinetic_energy, energia_cinetica_palanca=self.palanca.kinetic_energy,
            k=p["k"]))

    @property
    def terminada(self):
        return self.ciclo_completo and self.t - self.t_fin >= self.p["t_extra_final"]

    def F_media(self):
        return self.F_suma / self.F_n if self.F_n else 0.0

    def cambiar_k(self, s):
        self.p["k"] = max(1.0, self.p["k"] + s * self.p["paso_k"])

    def resumen(self):
        return (f"ángulo máx {self.max_angulo:.1f}° (techo {self.p['angulo_abierto']:.0f}°) | "
                f"ω máx {self.max_omega:.1f} rad/s | v punta compuerta máx {self.max_punta:.2f} m/s | "
                f"v punta palanca máx {self.max_palanca:.2f} m/s | E almacenada {self.E_lib:.2f} J (k={self.p['k']:.0f}) | "
                f"fuerza estática en la punta armada {self.F_armada:.0f} N ({self.F_armada/9.81:.1f} kgf) | "
                f"fuerza de contacto media {self.F_media()/9.81:.1f} kgf, pico {self.F_pico/9.81:.0f} kgf")

    def guardar(self):
        import matplotlib.pyplot as plt
        self.guardado = True
        os.makedirs(self.p["carpeta_salida"], exist_ok=True)
        base = os.path.join(self.p["carpeta_salida"], self.NOMBRE)   # siempre el mismo nombre: sobrescribe el último resultado
        with open(base + ".csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(self.filas[0].keys()))
            w.writeheader()
            w.writerows(self.filas)
        col = lambda n: [f[n] for f in self.filas]
        fig, ax = plt.subplots(4, 1, sharex=True, figsize=(9, 11))
        series = [("ángulo [°]", [("angulo_deg", "compuerta"), ("angulo_palanca_deg", "palanca")]),
                  ("velocidad", [("omega", "ω compuerta [rad/s]"), ("vel_punta", "punta compuerta [m/s]"),
                                 ("vel_punta_palanca", "punta palanca [m/s]")]),
                  ("fuerza [N]", [("tension", self.ETIQ_FUERZA), ("fuerza_contacto", "contacto palanca-compuerta")]),
                  ("energía [J]", [("energia_elastico", self.ETIQ_ENERGIA), ("energia_cinetica_compuerta", "cinética compuerta"),
                                   ("energia_cinetica_palanca", "cinética palanca")])]
        for a, (yl, ss) in zip(ax, series):
            for c, lg in ss:
                a.plot(col("t"), col(c), label=lg)
            if self.t_lib is not None:
                a.axvline(self.t_lib, color="gray", ls="--", lw=1)
            a.set_ylabel(yl)
            a.grid(alpha=0.3)
            a.legend(loc="best", fontsize=8)
        ax[-1].set_xlabel("tiempo [s]   (línea punteada = disparo)")
        fig.suptitle(self.resumen().replace(" | ", "\n", 3), fontsize=7)
        fig.tight_layout()
        fig.savefig(base + ".png", dpi=120)
        plt.close(fig)
        self.archivos = base + ".csv / .png"
        print("Guardado:", self.archivos)
        print(self.resumen())

    def hud(self):
        c = self.compuerta
        return [
            f"COMPUERTA   fase: {self.fase}   t = {self.t:6.3f} s",
            self.hud_accionamiento(),
            f"ángulo        = {c.angle/DEG:8.2f} °    (máx {self.max_angulo:6.2f}, techo {self.p['angulo_abierto']:.0f})",
            f"ω             = {c.angular_velocity:8.2f} rad/s   (máx {self.max_omega:6.2f})",
            f"vel. punta    = {self.vel_punta():8.3f} m/s     (máx {self.max_punta:6.3f})",
            f"punta palanca = {self.vel_punta_palanca():8.3f} m/s     (máx {self.max_palanca:6.3f})",
            f"E almacenada  = {self.energia():8.3f} J       (al disparar: {self.E_lib:.3f} J)",
            f"fuerza palanca = {self.F_armada/9.81:5.1f} kgf estática armada | contacto media {self.F_media()/9.81:5.1f} kgf",
            ("AVISO: " + self.avisos[0]) if self.avisos else (f"archivos: {self.archivos}" if self.archivos else ""),
        ]


# ---------------------------------------------------------------------- propuesta 2: volante de inercia (sin elástico)
class CompuertaVolante(Compuerta):
    """Sin elástico. Un motor acelera un VOLANTE DE INERCIA (energía cinética 1/2 I w^2). Al disparar, un
    embrague engancha una BIELA entre la manivela del volante y el brazo de abajo de la palanca en la fase correcta;
    el volante da UNA vuelta empujando y regresando la palanca y se suelta. La compuerta baja sola por gravedad.
    Mapeo Pymunk: volante = Body + PivotJoint al mundo; motor = SimpleMotor (se apaga al enganchar);
    embrague = PinJoint(volante[manivela], palanca[brazo abajo]) que se agrega/quita."""
    NOMBRE = "propuesta2_volante"
    ETIQ_FUERZA = "fuerza en la biela [N]"
    ETIQ_ENERGIA = "energía cinética del volante"

    def _accionamiento(self):
        p, est = self.p, self.space.static_body
        zx0, zx1, zy0, zy1 = p["zona_mecanismo"]
        R, rc = p["volante_radio"], p["manivela_radio"]
        self.vol_c = Vec2d(p["volante_x"], zy0 + R + 0.002)
        self.I_vol = 0.5 * p["volante_masa"] * R * R
        self.volante = pymunk.Body(p["volante_masa"], self.I_vol)
        self.volante.position = self.vol_c
        self.space.add(self.volante, pymunk.PivotJoint(est, self.volante, self.vol_c))
        # Manivela: eje concéntrico, unida al volante por un tren de engranes con reducción N (gira N veces más lento).
        # Así la inercia del volante "pesa" N^2 veces más en la palanca (inercia reflejada), que es lo que se necesita
        # para mover una compuerta pesada con una zona tan chica.
        self.manivela = pymunk.Body(0.2, 0.5 * 0.2 * (1.2 * rc) ** 2)
        self.manivela.position = self.vol_c
        self.space.add(self.manivela, pymunk.PivotJoint(est, self.manivela, self.vol_c))
        self.engrane = pymunk.GearJoint(self.volante, self.manivela, 0.0, p["volante_reduccion"])   # w_manivela = w_volante / N
        self.space.add(self.engrane)
        self.motor = pymunk.SimpleMotor(est, self.volante, -p["volante_velocidad"])   # Chipmunk: w_b - w_a = -rate
        self.motor.max_force = p["volante_torque"]
        self.space.add(self.motor)
        self.pin_local = (-rc, 0.0)           # a ángulo 0 la manivela apunta a la izquierda (lejos de la palanca)
        self.biela = None
        self.fase = "ACELERANDO"
        self.ang_enganche = 0.0
        self._k_prev = 0

    def _avisos_accionamiento(self, zx0, zx1, zy0, zy1):
        p = self.p
        if p["volante_x"] - p["volante_radio"] < zx0 or 2 * p["volante_radio"] > zy1 - zy0 + 1e-6:
            self.avisos.append("el volante se sale de la zona")

    def energia(self):
        return 0.5 * self.I_vol * self.volante.angular_velocity ** 2

    def extension(self):
        return 0.0

    def tension(self):
        return abs(self.biela.impulse) / self.p["dt"] if self.biela else 0.0

    def fuerza_punta_armada(self):
        return 0.0

    def _antes_paso(self):
        p = self.p
        ang = self.manivela.angle
        k = math.floor(ang / (2 * math.pi))
        if self.fase == "ACELERANDO" and self.volante.angular_velocity >= 0.97 * p["volante_velocidad"]:
            self.fase = "LISTO"
            if self.liberado and not self.ciclo_completo:
                self.ciclo_completo, self.t_fin = True, self.t
        elif self.fase == "ENGANCHANDO" and k > self._k_prev:      # la manivela pasa por la fase de enganche
            self.biela = pymunk.PinJoint(self.manivela, self.palanca, self.pin_local, self.pt_abajo)
            self.space.add(self.biela)
            self.motor.max_force = 0.0                              # el motor se desconecta: solo trabaja el volante
            self.E_lib = self.energia()
            self.ang_enganche = ang
            self.fase, self.liberado, self.t_lib = "DISPARADO", True, self.t
            self.max_omega = self.max_punta = self.max_palanca = 0.0
            self.max_angulo = self.compuerta.angle / DEG
        elif self.fase == "DISPARADO" and ang >= self.ang_enganche + 2 * math.pi:   # una vuelta: se desembraga
            self.space.remove(self.biela)
            self.biela = None
            self.motor.max_force = p["volante_torque"]
            self.fase = "ACELERANDO"
        self._k_prev = k

    def disparar(self):
        if self.fase == "LISTO":
            self.fase = "ENGANCHANDO"

    def rearmar(self):
        pass

    soltar = disparar

    def cambiar_k(self, s):
        self.p["volante_velocidad"] = max(20.0, self.p["volante_velocidad"] + s * 25.0)
        self.motor.rate = -self.p["volante_velocidad"]

    def hud_accionamiento(self):
        return (f"volante = {self.volante.angular_velocity:6.1f} rad/s (objetivo {self.p['volante_velocidad']:.0f}, "
                f"flechas)   fuerza biela = {self.tension():6.0f} N")

    def resumen(self):
        return (f"ángulo máx {self.max_angulo:.1f}° (techo {self.p['angulo_abierto']:.0f}°) | "
                f"ω máx {self.max_omega:.1f} rad/s | v punta compuerta máx {self.max_punta:.2f} m/s | "
                f"v punta palanca máx {self.max_palanca:.2f} m/s | E del volante al engranar {self.E_lib:.1f} J "
                f"({self.p['volante_velocidad']:.0f} rad/s, reducción {self.p['volante_reduccion']:.0f}:1) | fuerza de contacto media {self.F_media()/9.81:.1f} kgf, "
                f"pico {self.F_pico/9.81:.0f} kgf")

    def dibujar_accionamiento(self, pg, pan, s, esc):
        p = self.p
        c = s(self.vol_c)
        pg.draw.circle(pan, (200, 200, 205), c, int(p["volante_radio"] * esc))
        pg.draw.circle(pan, (90, 90, 100), c, int(p["volante_radio"] * esc), 2)
        pin = self.manivela.local_to_world(self.pin_local)
        pg.draw.line(pan, (90, 90, 100), c, s(pin), 2)
        pg.draw.circle(pan, (200, 30, 30), s(pin), 4)
        pg.draw.line(pan, (0, 130, 0) if self.biela else (170, 170, 170), s(pin),
                     s(self.palanca.local_to_world(self.pt_abajo)), 3 if self.biela else 1)


# ---------------------------------------------------------------------- propuesta 3: elástico + leva de caracol
class CompuertaLeva(Compuerta):
    """Elástico + LEVA DE CARACOL accionada por un motor lento. La leva sube el escalón poco a poco empujando la
    palanca hacia abajo (estira el elástico = arma) y, al caer el escalón, el elástico dispara la palanca de golpe.
    No hay cuerda ni seguro aparte: la leva es la retracción y el seguro a la vez. Cada vuelta = un disparo.
    Modelado: la leva se representa como un RotaryLimitJoint cuyo tope máximo (ángulo de la palanca) depende del
    ángulo de la leva: baja linealmente durante el armado y salta de golpe en el escalón (el contacto leva-rodillo
    no se simula con colisiones, así que no necesita convexos ni rieles). Mapeo: motor+leva = tope móvil."""
    NOMBRE = "propuesta3_leva"

    def _theta_cam(self, phi):
        p = self.p
        fm = phi % (2 * math.pi)
        a_arm, a_top = p["angulo_armado"] * DEG, p["leva_angulo_tope"] * DEG
        if fm < p["leva_caida"]:
            return a_top - (a_top - a_arm) * fm / p["leva_caida"]
        return a_top

    def _accionamiento(self):
        p = self.p
        self._crear_elastico()
        self.cuerda = None
        self.phi_stop = p["leva_caida"] - 0.02
        self.phi = self.phi_stop
        self.phi_fin = None
        self.motor_on = False
        self.tope_leva = pymunk.RotaryLimitJoint(self.space.static_body, self.palanca, -3.0, self._theta_cam(self.phi))
        self.tope_leva.max_force = p["motor_torque"] * p["reduccion"]      # par máximo que la leva puede ejercer
        self.space.add(self.tope_leva)

    def _antes_paso(self):
        p, dt = self.p, self.p["dt"]
        self._elastico_unilateral()
        if not self.motor_on:
            return
        self.phi += p["leva_velocidad"] * dt
        self.angulo_tambor = self.phi
        self.tope_leva.max = self._theta_cam(self.phi)
        if not self.liberado and self.phi >= p["leva_caida"]:               # cae el escalón: dispara
            self.fase, self.liberado, self.t_lib = "DISPARADO", True, self.t
            self.max_omega = self.max_punta = self.max_palanca = 0.0
            self.max_angulo = self.compuerta.angle / DEG
        if self.phi >= self.phi_fin:                                        # vuelta completa: armada otra vez
            self.motor_on = False
            self.phi = self.phi_stop
            self.tope_leva.max = self._theta_cam(self.phi)
            self.fase = "LISTO"
            if self.liberado and not self.ciclo_completo:
                self.ciclo_completo, self.t_fin = True, self.t

    def disparar(self):
        if self.fase == "LISTO":
            self.E_lib = self.energia()
            self.phi_fin = self.phi_stop + 2 * math.pi
            self.motor_on = True
            self.fase = "GIRANDO"

    def rearmar(self):
        pass

    soltar = disparar

    def hud_accionamiento(self):
        return (f"k = {self.p['k']:6.1f} N/m   extensión = {self.extension()*1000:5.1f} mm   "
                f"leva = {math.degrees(self.phi % (2*math.pi)):5.0f}°")

    def dibujar_accionamiento(self, pg, pan, s, esc):
        p = self.p
        zx0, zx1, zy0, zy1 = p["zona_mecanismo"]
        a_arm, a_top = p["angulo_armado"] * DEG, p["leva_angulo_tope"] * DEG
        r0, r1 = p["leva_radio_min"], p["leva_radio_max"]
        cy = zy0 + r1 + 0.002
        centro = Vec2d(p["leva_x"], cy)
        pts = []
        for i in range(120):                                               # perfil del caracol, girando con la leva
            a = 2 * math.pi * i / 120
            th = self._theta_cam(self.phi + a)
            r = r0 + (r1 - r0) * (th - a_arm) / (a_top - a_arm)
            ang = math.pi + a                                              # a = 0 queda apuntando hacia la palanca (izquierda)
            pts.append(s(centro + Vec2d(r, 0).rotated(ang)))
        pg.draw.polygon(pan, (230, 200, 120), pts)
        pg.draw.polygon(pan, (120, 80, 10), pts, 2)
        pg.draw.circle(pan, (200, 30, 30), s(centro), 3)
        self._dibujar_elastico(pg, pan, s)


# ---------------------------------------------------------------------- visor y bucle
def dibujar(pg, pan, fuente, sim):
    p = sim.p
    esc, org = p["escala"], p["origen_px"]
    s = lambda q: (int(org[0] + q[0] * esc), int(org[1] - q[1] * esc))
    W, Hh = p["ventana"]
    pan.fill((250, 250, 250))
    zx0, zx1, zy0, zy1 = p["zona_mecanismo"]

    def rect(x0, x1, y0, y1, color):
        a, b = s((x0, y1)), s((x1, y0))
        pg.draw.rect(pan, color, (a[0], a[1], b[0] - a[0], b[1] - a[1]))

    rect(zx0, zx1, zy0, zy1, (225, 170, 225))                    # zona del mecanismo (morado)

    c = sim.compuerta
    pts = [s(c.local_to_world(v)) for v in
           caja(0, p["compuerta_largo"], -p["compuerta_espesor"] / 2, p["compuerta_espesor"] / 2)]
    pg.draw.polygon(pan, (120, 170, 220), pts)
    pg.draw.polygon(pan, (30, 60, 110), pts, 2)
    if p["carga_punta_masa"] > 0:
        pg.draw.circle(pan, (90, 90, 90), s(sim.punta()), 5)
    # palanca
    t, cu, cd, Lp = p["palanca_espesor"], p["brazo_elastico"], p["brazo_cuerda"], p["palanca_largo"]
    for v in (caja(0, Lp, -t / 2, t / 2), caja(-t / 2, t / 2, 0, cu), caja(-t / 2, t / 2, -cd, 0)):
        poly = [s(sim.palanca.local_to_world(q)) for q in v]
        pg.draw.polygon(pan, (230, 150, 90), poly)
        pg.draw.polygon(pan, (120, 60, 10), poly, 1)
    pg.draw.circle(pan, (230, 150, 90), s(sim.punta_palanca()), max(2, int(p["punta_radio"] * esc)))
    pg.draw.circle(pan, (200, 30, 30), s(sim.piv), 4)
    sim.dibujar_accionamiento(pg, pan, s, esc)
    pg.draw.circle(pan, (200, 30, 30), s(p["bisagra"]), 5)
    for i, linea in enumerate(sim.hud()):
        pan.blit(fuente.render(linea, True, (20, 20, 20)), (10, Hh - 215 + 18 * i))
    pan.blit(fuente.render("ESPACIO disparar | A rearmar | R reiniciar | P pausa | flechas arriba/abajo: k", True, (90, 90, 90)),
             (10, Hh - 24))
    pg.display.flip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--propuesta", type=int, choices=(1, 2, 3), default=1,
                    help="1 = elástico + cuerda (palanca), 2 = volante de inercia (sin elástico), 3 = elástico + leva")
    args = ap.parse_args()
    auto = args.auto
    if auto:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        matplotlib.use("Agg")
    import pygame
    pygame.init()
    pan = pygame.display.set_mode(P["ventana"])
    clase = {1: Compuerta, 2: CompuertaVolante, 3: CompuertaLeva}[args.propuesta]
    pygame.display.set_caption(f"Compuerta - propuesta {args.propuesta}")
    fuente = pygame.font.SysFont("monospace", 15)
    sim = clase(P)
    for a in sim.avisos:
        print("AVISO:", a)

    if auto:
        os.makedirs(P["carpeta_salida"], exist_ok=True)
        fotos = [0.004, 0.012, 0.03]
        while not sim.terminada and sim.t < 20:
            if sim.fase == "LISTO" and sim.t >= 0.2 and not sim.liberado:
                dibujar(pygame, pan, fuente, sim)
                pygame.image.save(pan, os.path.join(P["carpeta_salida"], "antes.png"))
                sim.disparar()
            sim.paso()
            if sim.liberado and fotos and sim.t - sim.t_lib > fotos[0]:
                dibujar(pygame, pan, fuente, sim)
                pygame.image.save(pan, os.path.join(P["carpeta_salida"], f"despues{len(fotos)}.png"))
                fotos.pop(0)
        sim.guardar()
        return

    pygame.key.set_repeat(250, 50)
    reloj, pausa, acum, vivo = pygame.time.Clock(), False, 0.0, True
    while vivo:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                vivo = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    vivo = False
                elif ev.key == pygame.K_SPACE:
                    sim.disparar()
                elif ev.key == pygame.K_a:
                    sim.rearmar()
                elif ev.key == pygame.K_r:
                    sim.reiniciar()
                elif ev.key == pygame.K_p:
                    pausa = not pausa
                elif ev.key == pygame.K_UP:
                    sim.cambiar_k(+1)
                elif ev.key == pygame.K_DOWN:
                    sim.cambiar_k(-1)
        acum += min(reloj.tick(60) / 1000.0, 0.05)
        while acum >= sim.p["dt"]:
            if not pausa and not sim.terminada:
                sim.paso()
            acum -= sim.p["dt"]
        if sim.terminada and not sim.guardado:
            sim.guardar()
        dibujar(pygame, pan, fuente, sim)
    if sim.liberado and not sim.guardado and sim.filas:
        sim.guardar()
    pygame.quit()


if __name__ == "__main__":
    main()
