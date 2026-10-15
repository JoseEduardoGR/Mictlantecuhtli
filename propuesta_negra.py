"""
propuesta_negra.py -- Réplica de la propuesta del boceto negro: rueda con motor + viga horizontal con ranura
("ariete") atada a la punta de la compuerta + elástico enrollado en la rueda.

Mapeo boceto -> Pymunk (valores en params.PN y params.P):
  Compuerta ("Fija")   -> self.compuerta: Body + PivotJoint a la bisagra, RotaryLimitJoint [cerrado, abierto]
  Rueda + motor        -> self.rueda: Body (disco) + PivotJoint al mundo; self.motor: SimpleMotor (solo para retraer)
  Elástico enrollado   -> DampedRotarySpring(mundo, rueda): resorte de torsión equivalente k_t = k R^2 (el elástico se
                          enrolla en el borde de la rueda, así que la fuerza F = k x da el par F R)
  Seguro               -> self.seguro: RotaryLimitJoint temporal que sostiene la rueda armada; ESPACIO lo quita
  Viga horizontal      -> self.viga: Body (sin forma: no choca con nada)
  Ranura / "curva"     -> GrooveJoint(viga, rueda): el pasador de la rueda corre por una ranura de la viga con juego
                          libre; en el fondo de la ranura golpea y empuja (ariete); al regresar, jala (retraer).
                          La ranura se modela recta (a lo largo de la viga).
  Viga atada a la punta-> PivotJoint(viga, compuerta) en la punta de la compuerta: empuja para abrir, jala para cerrar.
Fases: LISTO -> ESPACIO -> GOLPE -> (espera) -> RETRAYENDO (el motor regresa la rueda, la viga jala la compuerta
       hacia abajo) -> LISTO.
Teclas: ESPACIO golpear | A retraer ya | R reiniciar | P pausa | flechas arriba/abajo: k | ESC salir
Uso:  python propuesta_negra.py          (ventana)
      python propuesta_negra.py --auto   (sin ventana: golpea solo, guarda CSV, gráfica y capturas)
"""
import argparse
import csv
import math
import os

import matplotlib
import pymunk
from pymunk import Vec2d

from compuerta import DEG, caja
from params import P, PN


class PropuestaNegra:
    NOMBRE = "propuesta_negra"

    def __init__(self, p, pn):
        self.p, self.n = dict(p), dict(pn)
        self.reiniciar()

    # ------------------------------------------------------------------ construcción
    def reiniciar(self):
        p, n = self.p, self.n
        self.space = pymunk.Space()
        self.space.gravity = (0, -p["gravedad"])
        self.space.iterations = p["iteraciones"]
        est = self.space.static_body
        self.t, self.t_lib, self.t_fin = 0.0, None, None
        self.liberado = self.guardado = self.ciclo_completo = False
        self.filas, self.archivos, self.avisos = [], "", []
        sin_choque = pymunk.ShapeFilter(mask=0)

        # --- Compuerta ---
        L, e, m, mc = p["compuerta_largo"], p["compuerta_espesor"], p["compuerta_masa"], p["carga_punta_masa"]
        M = m + mc
        cg = Vec2d((m * L / 2 + mc * L) / M, 0)
        I0 = pymunk.moment_for_poly(m, caja(0, L, -e / 2, e / 2)) + mc * L * L
        self.compuerta = pymunk.Body(M, I0 - M * cg.length_squared)
        self.compuerta.center_of_gravity = cg
        a0 = p["angulo_cerrado"] * DEG
        self.compuerta.angle = a0
        self.compuerta.position = p["bisagra"]
        forma = pymunk.Poly(self.compuerta, caja(0, L, -e / 2, e / 2))
        forma.filter = sin_choque
        self.space.add(self.compuerta, forma, pymunk.PivotJoint(est, self.compuerta, p["bisagra"]))
        self.space.add(pymunk.DampedRotarySpring(est, self.compuerta, 0, 0, p["friccion_bisagra"]))
        self.space.add(pymunk.RotaryLimitJoint(est, self.compuerta, a0 - 0.005, p["angulo_abierto"] * DEG))

        # --- Rueda con motor ---
        zx0, zx1, zy0, zy1 = p["zona_mecanismo"]
        R, rp = n["rueda_radio"], n["pasador_radio"]
        self.C = Vec2d(n["rueda_x"], zy0 + R + 0.002)
        self.rueda = pymunk.Body(n["rueda_masa"], 0.5 * n["rueda_masa"] * R * R)
        self.rueda.position = self.C
        self.psi_a = n["angulo_armado"] * DEG
        self.rueda.angle = self.psi_a
        self.space.add(self.rueda, pymunk.PivotJoint(est, self.rueda, self.C))
        self.pin_local = (rp, 0.0)
        self.k_t = n["k"] * R * R                                        # resorte de torsión equivalente
        self.theta0 = n["extension_armado"] / R                          # giro enrollado al armar
        self.psi_rest = self.psi_a + self.theta0
        self.resorte = pymunk.DampedRotarySpring(est, self.rueda, self.psi_rest, self.k_t, n["amortiguamiento"])
        self.space.add(self.resorte)
        self.motor = pymunk.SimpleMotor(est, self.rueda, n["motor_velocidad"] / n["reduccion"])
        self.motor.max_force = 0.0                                       # apagado hasta retraer
        self.space.add(self.motor)
        self.seguro = pymunk.RotaryLimitJoint(est, self.rueda, -20.0, self.psi_a)
        self.space.add(self.seguro)

        # --- Viga atada a la punta de la compuerta, con ranura para el pasador ---
        T0 = self.compuerta.local_to_world((L, 0))
        P0 = self.rueda.local_to_world(self.pin_local)
        beta = (T0 - P0).angle
        sa, sb = 0.01, 0.01 + n["ranura_largo"]
        u = Vec2d(1, 0).rotated(beta)
        origen = P0 - sa * u
        self.Lr = (T0 - origen).length
        mr, tr = n["viga_masa"], n["viga_espesor"]
        self.viga = pymunk.Body(mr, pymunk.moment_for_box(mr, (self.Lr, tr)))
        self.viga.center_of_gravity = (self.Lr / 2, 0)
        self.viga.angle = beta
        self.viga.position = origen
        self.space.add(self.viga)
        self.articulacion = pymunk.PivotJoint(self.viga, self.compuerta, (self.Lr, 0), (L, 0))
        self.ranura = pymunk.GrooveJoint(self.viga, self.rueda, (sa, 0), (sb, 0), self.pin_local)
        self.space.add(self.articulacion, self.ranura)
        self.sa, self.sb = sa, sb

        self.fase = "LISTO"
        self.max_omega = self.max_punta = self.max_angulo = 0.0
        self.max_angulo = self.compuerta.angle / DEG
        self.F_pico, self.F_suma, self.F_n = 0.0, 0.0, 0
        self.E_lib = 0.0

        # --- Avisos de zona ---
        if self.C.x - R < zx0:
            self.avisos.append("la rueda se sale de la zona por la izquierda")
        if 2 * R > zy1 - zy0 + 1e-6:
            self.avisos.append("la rueda no cabe en la altura de la zona")
        ymin = min(origen.y, T0.y, P0.y) - tr / 2
        if ymin < zy0:
            self.avisos.append("la viga queda por debajo de la zona")

    # ------------------------------------------------------------------ mediciones
    def punta(self):
        return self.compuerta.local_to_world((self.p["compuerta_largo"], 0))

    def vel_punta(self):
        return self.compuerta.velocity_at_local_point((self.p["compuerta_largo"], 0)).length

    def energia(self):
        th = max(0.0, self.psi_rest - self.rueda.angle)
        return 0.5 * self.k_t * th * th

    def par_resorte(self):
        return self.k_t * max(0.0, self.psi_rest - self.rueda.angle)

    def fuerza_viga(self):
        return abs(self.articulacion.impulse) / self.p["dt"]

    # ------------------------------------------------------------------ control
    def disparar(self):
        if self.fase != "LISTO":
            return
        self.E_lib = self.energia()
        self.space.remove(self.seguro)
        self.fase, self.liberado, self.t_lib = "GOLPE", True, self.t
        self.max_omega = self.max_punta = 0.0
        self.max_angulo = self.compuerta.angle / DEG
        self.F_pico, self.F_suma, self.F_n = 0.0, 0.0, 0

    soltar = disparar

    def rearmar(self):
        if self.fase != "GOLPE":
            return
        self.motor.max_force = self.n["motor_torque"] * self.n["reduccion"]
        self.fase = "RETRAYENDO"

    def cambiar_k(self, s):
        self.n["k"] = max(10.0, self.n["k"] + s * 50.0)
        self.k_t = self.n["k"] * self.n["rueda_radio"] ** 2
        self.resorte.stiffness = self.k_t

    # ------------------------------------------------------------------ física
    def paso(self):
        p, dt = self.p, self.p["dt"]
        # el elástico solo tira: si la rueda pasó su ángulo de reposo, no ejerce par
        self.resorte.stiffness = self.k_t if self.rueda.angle < self.psi_rest else 0.0
        if self.fase == "RETRAYENDO" and self.rueda.angle <= self.psi_a + 0.01:
            self.motor.max_force = 0.0
            self.space.add(self.seguro)                  # queda trabada = armada otra vez
            self.fase = "LISTO"
            if self.liberado and not self.ciclo_completo:
                self.ciclo_completo, self.t_fin = True, self.t
        elif self.fase == "GOLPE" and self.t - self.t_lib >= self.n["espera_rearmado"]:
            self.rearmar()
        self.space.step(dt)
        self.t += dt
        c = self.compuerta
        vp, F = self.vel_punta(), self.fuerza_viga()
        if self.fase == "GOLPE" and c.angle / DEG < p["angulo_abierto"] - 0.5 and F > 1.0:
            self.F_pico = max(self.F_pico, F)
            self.F_suma += F
            self.F_n += 1
        if self.liberado:
            self.max_omega = max(self.max_omega, abs(c.angular_velocity))
            self.max_punta = max(self.max_punta, vp)
            self.max_angulo = max(self.max_angulo, c.angle / DEG)
        self.filas.append(dict(
            t=round(self.t, 6), fase=self.fase, angulo_deg=c.angle / DEG, omega=c.angular_velocity, vel_punta=vp,
            angulo_rueda_deg=self.rueda.angle / DEG, omega_rueda=self.rueda.angular_velocity,
            fuerza_viga=F, par_resorte=self.par_resorte(), energia_elastico=self.energia(),
            energia_cinetica_compuerta=c.kinetic_energy, energia_cinetica_rueda=self.rueda.kinetic_energy))

    @property
    def terminada(self):
        return self.ciclo_completo and self.t - self.t_fin >= 0.3

    def F_media(self):
        return self.F_suma / self.F_n if self.F_n else 0.0

    def resumen(self):
        return (f"ángulo máx {self.max_angulo:.1f}° (techo {self.p['angulo_abierto']:.0f}°) | ω máx {self.max_omega:.1f} rad/s | "
                f"v punta máx {self.max_punta:.2f} m/s | E almacenada {self.E_lib:.2f} J (k={self.n['k']:.0f}) | "
                f"fuerza de la viga media {self.F_media()/9.81:.1f} kgf, pico {self.F_pico/9.81:.0f} kgf")

    def guardar(self):
        import matplotlib.pyplot as plt
        self.guardado = True
        os.makedirs(self.p["carpeta_salida"], exist_ok=True)
        base = os.path.join(self.p["carpeta_salida"], self.NOMBRE)      # sobrescribe el último resultado
        with open(base + ".csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(self.filas[0].keys()))
            w.writeheader()
            w.writerows(self.filas)
        col = lambda k: [f[k] for f in self.filas]
        fig, ax = plt.subplots(4, 1, sharex=True, figsize=(9, 11))
        series = [("ángulo [°]", [("angulo_deg", "compuerta"), ("angulo_rueda_deg", "rueda")]),
                  ("velocidad", [("omega", "ω compuerta [rad/s]"), ("vel_punta", "punta compuerta [m/s]"),
                                 ("omega_rueda", "ω rueda [rad/s]")]),
                  ("fuerza de la viga [N]", [("fuerza_viga", "empuje / tiro de la viga")]),
                  ("energía [J]", [("energia_elastico", "elástico"), ("energia_cinetica_compuerta", "cinética compuerta"),
                                   ("energia_cinetica_rueda", "cinética rueda")])]
        for a, (yl, ss) in zip(ax, series):
            for c, lg in ss:
                a.plot(col("t"), col(c), label=lg)
            if self.t_lib is not None:
                a.axvline(self.t_lib, color="gray", ls="--", lw=1)
            a.set_ylabel(yl)
            a.grid(alpha=0.3)
            a.legend(loc="best", fontsize=8)
        ax[-1].set_xlabel("tiempo [s]   (línea punteada = golpe)")
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
            f"PROPUESTA NEGRA   fase: {self.fase}   t = {self.t:6.3f} s",
            f"k = {self.n['k']:6.1f} N/m   par del elástico = {self.par_resorte():5.2f} N·m   (flechas: k)",
            f"ángulo        = {c.angle/DEG:8.2f} °    (máx {self.max_angulo:6.2f}, techo {self.p['angulo_abierto']:.0f})",
            f"ω             = {c.angular_velocity:8.2f} rad/s   (máx {self.max_omega:6.2f})",
            f"vel. punta    = {self.vel_punta():8.3f} m/s     (máx {self.max_punta:6.3f})",
            f"fuerza viga   = {self.fuerza_viga()/9.81:8.1f} kgf     (media {self.F_media()/9.81:5.1f}, pico {self.F_pico/9.81:5.0f})",
            f"E almacenada  = {self.energia():8.3f} J       (al golpear: {self.E_lib:.3f} J)",
            ("AVISO: " + self.avisos[0]) if self.avisos else (f"archivos: {self.archivos}" if self.archivos else ""),
        ]


# ---------------------------------------------------------------------- visor y bucle
def dibujar(pg, pan, fuente, sim):
    p, n = sim.p, sim.n
    esc, org = p["escala"], p["origen_px"]
    s = lambda q: (int(org[0] + q[0] * esc), int(org[1] - q[1] * esc))
    Hh = p["ventana"][1]
    pan.fill((250, 250, 250))
    zx0, zx1, zy0, zy1 = p["zona_mecanismo"]
    a, b = s((zx0, zy1)), s((zx1, zy0))
    pg.draw.rect(pan, (225, 170, 225), (a[0], a[1], b[0] - a[0], b[1] - a[1]))        # zona del mecanismo

    c = sim.compuerta
    pts = [s(c.local_to_world(v)) for v in
           caja(0, p["compuerta_largo"], -p["compuerta_espesor"] / 2, p["compuerta_espesor"] / 2)]
    pg.draw.polygon(pan, (120, 170, 220), pts)
    pg.draw.polygon(pan, (30, 60, 110), pts, 2)
    if p["carga_punta_masa"] > 0:
        pg.draw.circle(pan, (90, 90, 90), s(sim.punta()), 5)
    # viga con su ranura
    v = sim.viga
    pg.draw.line(pan, (230, 150, 90), s(v.local_to_world((0, 0))), s(v.local_to_world((sim.Lr, 0))),
                 max(3, int(n["viga_espesor"] * esc)))
    pg.draw.line(pan, (120, 60, 10), s(v.local_to_world((sim.sa, 0))), s(v.local_to_world((sim.sb, 0))), 2)
    # rueda, pasador y arco del elástico enrollado
    cc = s(sim.C)
    pg.draw.circle(pan, (230, 200, 120), cc, int(n["rueda_radio"] * esc))
    pg.draw.circle(pan, (120, 80, 10), cc, int(n["rueda_radio"] * esc), 2)
    pin = sim.rueda.local_to_world(sim.pin_local)
    pg.draw.line(pan, (120, 80, 10), cc, s(pin), 2)
    pg.draw.circle(pan, (200, 30, 30), s(pin), 4)
    th = max(0.0, sim.psi_rest - sim.rueda.angle)
    if th > 0.02:
        r_arc = n["rueda_radio"] * 0.8
        puntos = [s(sim.C + Vec2d(r_arc, 0).rotated(sim.rueda.angle + th * i / 30)) for i in range(31)]
        pg.draw.lines(pan, (200, 40, 40), False, puntos, 3)
    pg.draw.circle(pan, (200, 30, 30), s(p["bisagra"]), 5)
    for i, linea in enumerate(sim.hud()):
        pan.blit(fuente.render(linea, True, (20, 20, 20)), (10, Hh - 215 + 18 * i))
    pan.blit(fuente.render("ESPACIO golpear | A retraer | R reiniciar | P pausa | flechas arriba/abajo: k", True, (90, 90, 90)),
             (10, Hh - 24))
    pg.display.flip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", action="store_true")
    auto = ap.parse_args().auto
    if auto:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        matplotlib.use("Agg")
    import pygame
    pygame.init()
    pan = pygame.display.set_mode(P["ventana"])
    pygame.display.set_caption("Propuesta negra")
    fuente = pygame.font.SysFont("monospace", 15)
    sim = PropuestaNegra(P, PN)
    for a in sim.avisos:
        print("AVISO:", a)

    if auto:
        os.makedirs(P["carpeta_salida"], exist_ok=True)
        fotos = [0.01, 0.03, 0.08]
        while not sim.terminada and sim.t < 20:
            if sim.fase == "LISTO" and sim.t >= 0.2 and not sim.liberado:
                dibujar(pygame, pan, fuente, sim)
                pygame.image.save(pan, os.path.join(P["carpeta_salida"], "negra_antes.png"))
                sim.disparar()
            sim.paso()
            if sim.liberado and fotos and sim.t - sim.t_lib > fotos[0]:
                dibujar(pygame, pan, fuente, sim)
                pygame.image.save(pan, os.path.join(P["carpeta_salida"], f"negra_despues{len(fotos)}.png"))
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
