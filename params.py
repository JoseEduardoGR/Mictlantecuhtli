"""
params.py -- Parámetros de la simulación de la compuerta (SI: m, kg, s, N/m, N·m).
Todo lo marcado con  # <-- CAMBIAR  es un valor de ejemplo: ajústalo a tu robot.
Ángulos en GRADOS (0° = hacia +x, positivo = antihorario, y hacia ARRIBA).
Origen del mundo = la bisagra de la compuerta.
"""
import math

# --- Escala tomada del boceto de referencia: la compuerta mide LARGO_COMPUERTA_M ---
LARGO_COMPUERTA_M = 0.25                  # m  <-- CAMBIAR (la zona del mecanismo se reescala con esto)
_s = LARGO_COMPUERTA_M / math.hypot(110, 115)   # metros por píxel del boceto (la compuerta mide ~159 px)
_hx, _hy = 330, 175                       # píxeles de la bisagra en el boceto
_zona = ((17 - _hx) * _s, (363 - _hx) * _s, -(300 - _hy) * _s, -(224 - _hy) * _s)   # x_min, x_max, y_min, y_max

P = {
    # --- Zona permitida (el rectángulo morado). Nada arriba, abajo ni a la derecha. ---
    "zona_mecanismo": _zona,              # sale de ~54 cm de largo x ~12 cm de alto; el largo máx. real es 50 cm  # <-- CAMBIAR
    "techo_y": (_hy - 135) * _s,          # m: arriba de esto es zona prohibida (franja roja superior)

    # --- Compuerta (viga con bisagra "Fija") ---
    "bisagra": (0.0, 0.0),
    "compuerta_largo": LARGO_COMPUERTA_M,
    "compuerta_espesor": 0.012,           # m
    "compuerta_masa": 0.30,               # kg                                              # <-- CAMBIAR
    "carga_punta_masa": 0.30,             # kg extra en la punta (lo que levanta; 0 = nada) # <-- CAMBIAR
    "angulo_cerrado": -45.0,              # grados, posición cerrada (descansa en su tope)
    "angulo_abierto": 14.0,               # grados, tope superior (techo del boceto)        # <-- CAMBIAR
    "friccion_bisagra": 0.002,            # N·m·s/rad
    "friccion_contacto": 0.5,

    # --- Palanca larga y horizontal (UNA sola bisagra, sin rieles): su punta levanta la compuerta desde abajo ---
    "palanca_pivote_y": (_zona[2] + _zona[3]) / 2,   # m, altura del pivote = centro de la zona
    "palanca_largo": 0.25,                # m, del pivote a la punta (puede llegar a ~0.45)  # <-- CAMBIAR
    "palanca_espesor": 0.015,             # m
    "palanca_masa": 0.20,                 # kg                                              # <-- CAMBIAR
    "punta_radio": 0.010,                 # m, punta redondeada
    "brazo_elastico": 0.055,              # m, brazo hacia ARRIBA donde tira el elástico (máx ~ mitad de la altura de la zona)  # <-- CAMBIAR
    "brazo_cuerda": 0.055,                # m, brazo hacia ABAJO donde tira la cuerda del motor (rearmado)
    "angulo_armado": -10.0,               # grados, palanca armada (punta baja)
    "angulo_max": 55.0,                   # grados, tope de la palanca tras el golpe
    "margen_derecho": 0.003,              # m que la punta armada queda antes del borde derecho de la zona

    # --- Elástico (tira del brazo superior hacia la izquierda; solo tira, nunca empuja) ---
    "k": 3400.0,                          # N/m rigidez (también con flechas arriba/abajo)   # <-- CAMBIAR
    "amortiguamiento": 0.5,               # N·s/m
    "extension_armado": 0.10,             # m de estiramiento con la palanca armada (F = k x, E = 1/2 k x^2)  # <-- CAMBIAR
    "ancla_elastico_x": -0.33,            # m, ancla fija del elástico (a la izquierda)      # <-- CAMBIAR

    # --- Motor + tambor (retrae la palanca con una cuerda que tira del brazo inferior) ---
    "tambor_x": -0.40,                    # m, centro del tambor (debe caber en la zona)
    "radio_enrolle": 0.05,                # m, radio del tambor (2 x radio debe ser menor que la altura de la zona)
    "reduccion": 10.0,                    # reducción del motorreductor (fuerza de cuerda = torque * reducción / radio)
    "motor_velocidad": 60.0,              # rad/s del motor al retraer (la cuerda va a radio*vel/reducción)  # <-- CAMBIAR
    "motor_torque": 2.5,                  # N·m del motor (antes de la reducción)             # <-- CAMBIAR
    "espera_rearmado": 0.7,               # s tras disparar antes de que el motor rearme (la compuerta cierra al rearmar)

    # ===================== PROPUESTA 2: volante de inercia + embrague + biela (SIN elástico) =====================
    "volante_x": -0.40,                   # m, centro del volante (a la izquierda de la palanca)
    "volante_radio": 0.055,               # m (2 x radio debe caber en la altura de la zona)
    "volante_masa": 3.0,                  # kg  (la energía guardada es 1/2 I w^2)           # <-- CAMBIAR
    "manivela_radio": 0.018,              # m, radio de la manivela (recorrido de la biela = 2 x esto)  # <-- CAMBIAR
    "volante_reduccion": 5.0,             # reducción volante -> manivela (la manivela gira N veces más lento)  # <-- CAMBIAR
    "volante_velocidad": 150.0,           # rad/s a los que el motor acelera el volante (flechas arriba/abajo)  # <-- CAMBIAR
    "volante_torque": 1.5,                # N·m del motor (solo acelera el volante; la velocidad aquí importa poco)  # <-- CAMBIAR

    # ===================== PROPUESTA 3: elástico + leva de caracol (sin cuerda ni seguro aparte) =====================
    "leva_velocidad": 3.0,                # rad/s de la leva (ya con reducción); arma lento, la velocidad aquí no importa
    "leva_caida": 5.5,                    # rad: ángulo de la leva donde cae el escalón (cerca de una vuelta = 6.28)
    "leva_angulo_tope": 35.0,             # grados: hasta dónde deja subir la leva a la palanca tras el golpe
    "leva_x": -0.10,                      # m, solo dibujo: centro de la leva
    "leva_radio_min": 0.020,              # m, solo dibujo
    "leva_radio_max": 0.055,              # m, solo dibujo

    # --- Simulación ---
    "gravedad": 9.81,                     # m/s^2
    "dt": 1 / 4000,                       # subpaso de física (mecanismo muy rápido: pasos grandes lo atraviesan)
    "iteraciones": 30,
    "paso_k": 100.0,                      # N/m por pulsación de flecha
    "t_extra_final": 0.3,                 # s que se sigue grabando tras terminar el rearmado
    "carpeta_salida": "salidas",
    "ventana": (900, 700),
    "escala": 1000,                       # px por metro
    "origen_px": (560, 190),              # px donde cae el (0,0) del mundo (la bisagra)
}


# ===================== PROPUESTA NEGRA (propuesta_negra.py): rueda con ranura + viga-ariete atada a la compuerta =====================
# La rueda (motor) lleva un pasador que corre por una ranura de la viga (juego libre = "espacio en curva"). El elástico se
# enrolla en la rueda; al soltar, la rueda acelera, el pasador recorre el juego, golpea el fondo de la ranura (ariete) y
# empuja la viga. La viga está articulada a la punta de la compuerta: la empuja para abrir y la jala al retraer.
PN = {
    "rueda_x": -0.40,                 # m, centro de la rueda (a la izquierda; debe caber en la zona)    # <-- CAMBIAR
    "rueda_radio": 0.058,             # m (2 x radio debe caber en la altura de la zona)
    "rueda_masa": 0.6,                # kg                                                              # <-- CAMBIAR
    "pasador_radio": 0.055,           # m, radio de giro del pasador (da el recorrido de la viga)        # <-- CAMBIAR
    "angulo_armado": -150.0,          # grados: posición del pasador con el elástico armado (-90 = abajo)
    "ranura_largo": 0.015,            # m de juego libre en la ranura antes del golpe                    # <-- CAMBIAR
    "viga_masa": 0.15,                # kg                                                              # <-- CAMBIAR
    "viga_espesor": 0.01,             # m
    "k": 700.0,                       # N/m del elástico enrollado en la rueda (flechas arriba/abajo)    # <-- CAMBIAR
    "amortiguamiento": 0.05,          # N·m·s/rad del resorte de torsión equivalente
    "extension_armado": 0.13,         # m de elástico enrollado al armar (giro = extensión / radio)       # <-- CAMBIAR
    "reduccion": 10.0,                # reducción del motorreductor al retraer
    "motor_velocidad": 60.0,          # rad/s del motor al retraer
    "motor_torque": 1.0,              # N·m del motor (antes de la reducción)                            # <-- CAMBIAR
    "espera_rearmado": 1.0,           # s tras el golpe antes de retraer
}
