# Mictlantecuhtli · Sistema de propulsión frontal

Simulación física 2D (Pymunk + Pygame) de cuatro mecanismos para levantar de golpe la compuerta delantera de un robot de combate. Proyecto integrador del grupo 931-M, TESCI.

> **Estado:** los resultados salen de una simulación con valores de ejemplo. Sirven para **comparar propuestas entre sí**, no son mediciones del robot real. Los parámetros marcados con `# <-- CAMBIAR` en `params.py` hay que reemplazarlos por medidas reales.

---

## Índice

1. [Resumen](#1-resumen)
2. [Estructura del repositorio](#2-estructura-del-repositorio)
3. [Instalación y ejecución](#3-instalación-y-ejecución)
4. [Convenciones](#4-convenciones)
5. [Objetivo y restricciones geométricas](#5-objetivo-y-restricciones-geométricas)
6. [Parámetros](#6-parámetros)
7. [Modelo físico común](#7-modelo-físico-común)
8. [Propuesta 1 · Palanca con elástico y cuerda](#8-propuesta-1--palanca-con-elástico-y-cuerda)
9. [Propuesta 2 · Volante de inercia](#9-propuesta-2--volante-de-inercia)
10. [Propuesta 3 · Elástico con leva de caracol](#10-propuesta-3--elástico-con-leva-de-caracol)
11. [Propuesta del equipo · Rueda con ranura (ariete)](#11-propuesta-del-equipo--rueda-con-ranura-ariete)
12. [Resultados de referencia](#12-resultados-de-referencia)
13. [Salidas: CSV, gráficas y capturas](#13-salidas-csv-gráficas-y-capturas)
14. [Métricas: cómo se calculan](#14-métricas-cómo-se-calculan)
15. [Lecciones técnicas y errores comunes](#15-lecciones-técnicas-y-errores-comunes)
16. [Limitaciones del modelo](#16-limitaciones-del-modelo)
17. [Página web](#17-página-web)
18. [Pendientes](#18-pendientes)

---

## 1. Resumen

El robot lleva al frente una **compuerta** de 25 cm articulada por su parte alta, que en reposo cuelga a -45° con la punta hacia el piso. Al dispararse debe girar hacia arriba lo más rápido posible para levantar al oponente. Después debe volver a cerrarse.

Todo el mecanismo tiene que caber en una franja de unos 54 × 12 cm a la izquierda y por debajo de la bisagra. Arriba, abajo y a la derecha de la compuerta no puede haber piezas.

Se simularon cuatro soluciones, con la misma compuerta y el mismo espacio:

| # | Mecanismo | Fuente de energía | Archivo | Comando |
|---|---|---|---|---|
| 1 | Palanca de una bisagra, cuerda y motor | Elástico | `compuerta.py` | `--propuesta 1` |
| 2 | Volante de inercia, embrague y biela | Energía cinética | `compuerta.py` | `--propuesta 2` |
| 3 | Palanca con leva de caracol | Elástico | `compuerta.py` | `--propuesta 3` |
| 4 | Rueda con ranura (ariete), viga atada a la compuerta | Elástico enrollado | `propuesta_negra.py` | — |

## 2. Estructura del repositorio

```
.
├── compuerta.py            # propuestas 1, 2 y 3 (clases Compuerta, CompuertaVolante, CompuertaLeva) + visor + bucle
├── propuesta_negra.py      # propuesta del equipo (clase PropuestaNegra) + visor + bucle
├── params.py               # todos los parámetros: diccionario P (propuestas 1-3) y PN (propuesta del equipo)
├── requirements.txt        # dependencias
├── salidas/                # resultados: CSV, gráficas y capturas (se sobrescriben en cada corrida)
├── iconos/                 # icono simplificado del emblema (SVG y PNG 16 a 512 px)
├── web/                    # generador de la página web del proyecto
│   ├── extract.py          # corre las 4 simulaciones, extrae series, métricas y esquemas SVG
│   ├── build.py            # arma pagina.html a partir de template.html y los datos
│   ├── template.html       # plantilla (HTML, CSS y JS de las gráficas)
│   └── *.txt               # logo e icono en base64
├── Mictlantecuhtli.png     # emblema del equipo (fondo transparente)
├── Mictlantecuhtli.jpg     # emblema del equipo (fondo blanco)
└── ProyectoIntegradorMictlantecuhtli.pdf   # documento de referencia
```

Las clases de `compuerta.py` comparten una base (`Compuerta`) que construye la compuerta, la palanca y los topes. Cada propuesta sobrescribe solo su accionamiento.

| Método | Qué hace |
|---|---|
| `_accionamiento()` | Crea la fuente de energía y el seguro |
| `_antes_paso()` | Máquina de estados y control; se llama antes de cada subpaso |
| `disparar()` / `rearmar()` | Acciones del usuario (ESPACIO y A) |
| `hud_accionamiento()` | Línea de datos del accionamiento en pantalla |
| `dibujar_accionamiento()` | Dibujo de la fuente de energía |
| `energia()`, `tension()`, `extension()` | Medición de la energía almacenada y de la fuerza |

## 3. Instalación y ejecución

Probado con Python 3.14, pymunk 7.3.1, pygame-ce 2.5.8 y matplotlib 3.11.2.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Se usa **pygame-ce** y no `pygame` porque, con Python 3.14, el paquete `pygame` 2.6.1 se instala sin soporte de fuentes.

```bash
.venv/bin/python compuerta.py --propuesta 1     # palanca, elástico y cuerda (por defecto)
.venv/bin/python compuerta.py --propuesta 2     # volante de inercia
.venv/bin/python compuerta.py --propuesta 3     # elástico con leva
.venv/bin/python propuesta_negra.py             # rueda con ranura (ariete)
.venv/bin/python compuerta.py --propuesta 2 --auto   # sin ventana: dispara solo y guarda todo
```

**Controles** (con ventana):

| Tecla | Acción |
|---|---|
| ESPACIO | Dispara (en la propuesta 2 espera la fase de enganche) |
| A | Rearma ya (propuestas 1 y de equipo; en las demás el rearmado es automático) |
| R | Reinicia la simulación con los parámetros actuales |
| P | Pausa |
| ↑ / ↓ | Sube o baja la rigidez `k` (100 N/m por pulsación en 1 y 3, 50 N/m en la de equipo). En la propuesta 2 cambia la velocidad del volante en 25 rad/s |
| ESC | Sale y guarda si hubo disparo |

Con `--auto` se usa el controlador de video `dummy`: no abre ventana. Dispara solo a los 0.2 s (o cuando la propuesta llega a `LISTO`), corre hasta terminar el ciclo y guarda el CSV, la gráfica y unas capturas.

## 4. Convenciones

- **Unidades:** SI. Metros, kilogramos, segundos, newtons, N·m. Los ángulos en los parámetros van en **grados** y en el código se pasan a radianes con `DEG = π/180`.
- **Ejes:** x hacia la derecha, y hacia **arriba** (Pymunk). El dibujo invierte y.
- **Ángulos:** 0° apunta a +x; positivo es antihorario.
- **Origen del mundo:** la bisagra de la compuerta, en `(0, 0)`.
- **Compuerta:** `angulo_cerrado = -45°` (cuelga hacia abajo y a la derecha). Abre hacia 0° y +14°.
- **Cuerpos con origen en la bisagra:** la compuerta y la palanca tienen el origen del cuerpo en su bisagra, y el centro de gravedad se declara aparte con `center_of_gravity`.
- **Idioma:** comentarios, nombres de parámetros y mensajes en español.

## 5. Objetivo y restricciones geométricas

La zona permitida sale de un boceto de referencia. La escala se obtiene de la compuerta: en la imagen mide `hypot(110, 115) ≈ 159 px`, que corresponden a `LARGO_COMPUERTA_M = 0.25 m`.

```
s = 0.25 / 159.14 ≈ 1.571 mm/px           (hx, hy) = (330, 175) px es la bisagra en el boceto
x_min = (17  − 330) · s = −0.492 m          y_min = −(300 − 175) · s = −0.196 m
x_max = (363 − 330) · s = +0.052 m          y_max = −(224 − 175) · s = −0.077 m
techo_y = (175 − 135) · s = +0.063 m        (franja prohibida arriba)
```

Consecuencias que condicionan todo el diseño:

1. **Contacto cerca de la bisagra.** Como nada puede ir a la derecha de `x_max = 0.052 m`, cualquier pieza que empuje la compuerta por debajo toca a menos de 5 cm de la bisagra. Ahí casi no hay brazo de palanca.
2. **Apertura limitada.** Por el techo, la punta de la compuerta solo puede subir hasta `asin(0.063 / 0.25) ≈ 14.6°`, de modo que `angulo_abierto = 14°`. El recorrido total es de unos 59°.
3. **Carga estática.** El par que la compuerta (0.3 kg) con 0.3 kg en la punta ejerce sobre la bisagra a -45° es `(m·L/2 + mc·L)·g·cos45° = 0.78 N·m`.
4. **Largo útil.** El espacio a la izquierda mide 54 cm en el boceto; el máximo real indicado es 50 cm.

La escala se cambia en `LARGO_COMPUERTA_M` y la zona se reescala sola. Si se cambia el boceto, hay que actualizar `_hx`, `_hy` y los píxeles de `_zona`.

## 6. Parámetros

Todo está en `params.py`. Los valores son de ejemplo salvo la geometría de la zona.

### 6.1 Compuerta y simulación (`P`)

| Parámetro | Valor | Significado |
|---|---|---|
| `zona_mecanismo` | calculado | `(x_min, x_max, y_min, y_max)` en m |
| `techo_y` | 0.063 m | Límite superior permitido |
| `bisagra` | (0, 0) | Punto fijo de la compuerta |
| `compuerta_largo` | 0.25 m | Largo de la viga |
| `compuerta_espesor` | 0.012 m | Grosor |
| `compuerta_masa` | 0.30 kg | Masa de la viga |
| `carga_punta_masa` | 0.30 kg | Masa extra en la punta (lo que levanta) |
| `angulo_cerrado` / `angulo_abierto` | -45° / 14° | Topes (`RotaryLimitJoint`) |
| `friccion_bisagra` | 0.002 N·m·s/rad | Amortiguamiento viscoso de la bisagra |
| `friccion_contacto` | 0.5 | Fricción compuerta-palanca |
| `gravedad` | 9.81 m/s² | Hacia -y |
| `dt` | 1/4000 s | Subpaso de física |
| `iteraciones` | 30 | Iteraciones del solver de Pymunk |
| `t_extra_final` | 0.3 s | Tiempo que se sigue grabando al terminar el ciclo |
| `ventana`, `escala`, `origen_px` | (900, 700), 1000 px/m, (560, 190) | Visor |

### 6.2 Palanca, elástico y motor (propuestas 1 y 3)

| Parámetro | Valor | Significado |
|---|---|---|
| `palanca_pivote_y` | centro de la zona | Altura del pivote; la x se calcula para que la punta quede a `margen_derecho` del borde |
| `palanca_largo` | 0.25 m | Del pivote a la punta (puede llegar a ~0.45) |
| `palanca_espesor` | 0.015 m | Grosor |
| `palanca_masa` | 0.20 kg | 80 % en el brazo largo, 10 % en cada brazo corto |
| `punta_radio` | 0.010 m | Punta redondeada |
| `brazo_elastico` / `brazo_cuerda` | 0.055 m c/u | Brazos cortos: arriba (elástico) y abajo (cuerda) |
| `angulo_armado` / `angulo_max` | -10° / 55° | Topes de la palanca |
| `margen_derecho` | 0.003 m | Holgura de la punta respecto al borde derecho |
| `k` | 3400 N/m | Rigidez del elástico |
| `amortiguamiento` | 0.5 N·s/m | Amortiguamiento del elástico |
| `extension_armado` | 0.10 m | Estiramiento con la palanca armada |
| `ancla_elastico_x` | -0.33 m | Ancla fija del elástico |
| `tambor_x`, `radio_enrolle` | -0.40 m, 0.05 m | Tambor del motor |
| `reduccion` | 10 | Motorreductor |
| `motor_velocidad` | 60 rad/s | Del motor, antes de la reducción |
| `motor_torque` | 2.5 N·m | Del motor, antes de la reducción |
| `espera_rearmado` | 0.7 s | Pausa entre el golpe y el rearmado automático |

### 6.3 Propuesta 2 (volante)

| Parámetro | Valor | Significado |
|---|---|---|
| `volante_x`, `volante_radio` | -0.40 m, 0.055 m | Posición y tamaño; `2R` debe caber en la altura de la zona |
| `volante_masa` | 3.0 kg | Disco macizo, `I = ½ m R²` |
| `manivela_radio` | 0.018 m | Radio de la manivela; recorrido de la biela ≈ 2× |
| `volante_reduccion` | 5 | Engranes volante → manivela |
| `volante_velocidad` | 150 rad/s | Velocidad a la que el motor acelera el volante |
| `volante_torque` | 1.5 N·m | Solo acelera el volante |

### 6.4 Propuesta 3 (leva)

| Parámetro | Valor | Significado |
|---|---|---|
| `leva_velocidad` | 3 rad/s | Giro de la leva (ya con reducción) |
| `leva_caida` | 5.5 rad | Ángulo de la leva donde cae el escalón |
| `leva_angulo_tope` | 35° | Hasta dónde deja subir la leva a la palanca |
| `leva_x`, `leva_radio_min/max` | -0.10 m, 0.02, 0.055 m | Solo dibujo |

### 6.5 Propuesta del equipo (`PN`)

| Parámetro | Valor | Significado |
|---|---|---|
| `rueda_x`, `rueda_radio`, `rueda_masa` | -0.40 m, 0.058 m, 0.6 kg | Rueda con motor |
| `pasador_radio` | 0.055 m | Radio de giro del pasador |
| `angulo_armado` | -150° | Posición del pasador con el elástico armado |
| `ranura_largo` | 0.015 m | Juego libre de la ranura |
| `viga_masa`, `viga_espesor` | 0.15 kg, 0.01 m | Viga |
| `k` | 700 N/m | Elástico enrollado en la rueda |
| `amortiguamiento` | 0.05 N·m·s/rad | Del resorte de torsión equivalente |
| `extension_armado` | 0.13 m | Elástico enrollado al armar |
| `reduccion`, `motor_velocidad`, `motor_torque` | 10, 60 rad/s, 1.0 N·m | Motor para retraer |
| `espera_rearmado` | 1.0 s | Pausa entre el golpe y el rearmado |

## 7. Modelo físico común

### 7.1 Motor y paso de tiempo

- **Paso fijo `dt = 1/4000 s`.** El mecanismo es muy rígido y rápido: la punta de la palanca llega a más de 10 m/s y la compuerta mide 12 mm de espesor. Con `1/240` o `1/960` la palanca puede atravesar piezas y los resultados son falsos (por ejemplo, con `1/240` el volante no lograba abrir la compuerta).
- La ventana avanza la simulación con un acumulador a 60 fps: en cada cuadro se dan `16.67 ms / 0.25 ms ≈ 67` subpasos.

### 7.2 Cuerpos rígidos y su inercia

Ni `Body(mass, moment)` ni `shape.mass` calculan por sí solos la inercia de piezas compuestas. Para cada cuerpo se hace a mano:

```
M       = Σ mᵢ
cog     = Σ mᵢ · cᵢ / M                      (centro de gravedad, en coordenadas locales)
I₀      = Σ moment_for_poly(mᵢ, vértices_i)   (respecto al origen del cuerpo, que es la bisagra)
I_cog   = I₀ − M · |cog|²                      (teorema de Steiner; es lo que pide Pymunk)
body.center_of_gravity = cog
```

La compuerta es una sola viga más una **masa puntual** `mc` en la punta (`I₀ += mc·L²`). Los cuerpos que solo se trasladan (empujador, cuña) se crean con `moment = inf` para que no giren.

### 7.3 Compuerta

- `Body` con origen en la bisagra + `PivotJoint(static_body, compuerta)` + `DampedRotarySpring(rest 0, k 0, damping=friccion_bisagra)` para la fricción viscosa.
- Topes: `RotaryLimitJoint(static_body, compuerta, angulo_cerrado − 0.005 rad, angulo_abierto)`.
- La compuerta **no tiene retén** en el techo: rebota y cae por gravedad, y se cierra sola. En la palanca, el golpe la lanza y vuelve a apoyarse en ella.

### 7.4 Colisiones

Se usan `ShapeFilter` con categorías: la compuerta solo choca con la palanca. La palanca no choca con el tambor ni con el elástico. En la propuesta del equipo la compuerta no tiene colisiones (la viga la mueve por la articulación).

### 7.5 Elástico unilateral

Un elástico solo tira. Se modela con `DampedSpring`, pero en cada subpaso se hace:

```python
if extension > 0: spring.stiffness, spring.damping = k, c
else:             spring.stiffness = spring.damping = 0      # flojo: no empuja
```

Con `extension = distancia − largo_libre`. El `largo_libre` se calcula en la construcción para que el estiramiento inicial sea `extension_armado`.

### 7.6 Motor con cuerda

El motor y el tambor no se simulan como cuerpos. La cuerda es un `SlideJoint(palanca, mundo, anclaje_brazo, punto_del_tambor, 0, L_max)`:

- `L_max` se acorta a `radio_enrolle · motor_velocidad / reduccion` por segundo mientras se retrae.
- `max_force = motor_torque · reduccion / radio_enrolle` limita la fuerza de la cuerda al par del motor.
- **Importante:** un `SlideJoint` exactamente en su límite no ejerce impulso. Por eso se crea con `L_max = distancia_real − 0.5 mm`, así la cuerda ya está "tensa" y sostiene la palanca contra el elástico.
- La cuerda tensa cumple también la función de **seguro**. `disparar()` la quita del espacio.

### 7.7 Convención del `SimpleMotor`

En Chipmunk/Pymunk `SimpleMotor(a, b, rate)` impone `ω_b − ω_a = −rate`. Para que `b` gire en sentido antihorario (positivo) hay que pasar `rate` negativo. La propuesta 2 usa `-volante_velocidad` y la del equipo usa `+motor_velocidad/reduccion` (gira en sentido horario al retraer).

### 7.8 Máquinas de estados

| Propuesta | Estados |
|---|---|
| 1 | `LISTO` → (ESPACIO) `DISPARADO` → (espera) `REARMANDO` → `LISTO` |
| 2 | `ACELERANDO` → `LISTO` → (ESPACIO) `ENGANCHANDO` → `DISPARADO` → `ACELERANDO` → `LISTO` |
| 3 | `LISTO` → (ESPACIO) `GIRANDO` → `DISPARADO` → `LISTO` |
| Equipo | `LISTO` → (ESPACIO) `GOLPE` → (espera) `RETRAYENDO` → `LISTO` |

El ciclo termina cuando se vuelve a `LISTO` tras haber disparado. Se sigue grabando `t_extra_final` y se guardan CSV y gráfica (`terminada`).

## 8. Propuesta 1 · Palanca con elástico y cuerda

**Piezas (Pymunk):**

| Pieza del diseño | Objeto |
|---|---|
| Palanca (brazo largo + 2 brazos cortos) | `Body` con 3 `Poly` y un `Circle` en la punta |
| Bisagra de la palanca | `PivotJoint(mundo, palanca, piv)` |
| Topes de la palanca | `RotaryLimitJoint(mundo, palanca, angulo_armado − 0.03, angulo_max)` |
| Elástico | `DampedSpring(mundo, palanca)` en el brazo de arriba, unilateral |
| Cuerda y seguro | `SlideJoint(palanca, mundo)` en el brazo de abajo |
| Motor | solo el límite de fuerza de la cuerda y su velocidad |

**Cómo funciona:** el motor jala la cuerda y gira la palanca hacia abajo (armado), con el elástico estirado `extension_armado`. La cuerda tensa sostiene la palanca. Al soltarla, el elástico tira del brazo de arriba hacia la izquierda y la punta sube y golpea la compuerta. A los 0.7 s el motor vuelve a jalar la cuerda; la palanca baja y la compuerta se cierra.

**Ecuaciones (con los valores de ejemplo):**

```
F_elástico   = k · e₀                         = 3400 · 0.10          = 340 N
τ_palanca    ≈ F_elástico · c_arriba          = 340 · 0.055          ≈ 18.7 N·m
F_punta      ≈ τ_palanca / L_palanca          = 18.7 / 0.25          ≈ 75 N (7.5 kgf)
E_almacenada = ½ k e₀²                        = ½ · 3400 · 0.10²     = 17 J
F_cuerda     ≈ F_elástico · c_arriba/c_abajo  = 340 N               (c_arriba = c_abajo)
T_motor      ≥ F_cuerda · r / N               = 340 · 0.05 / 10      = 1.7 N·m  (< 2.5 N·m)
```

**Geometría de la palanca:** el pivote queda a la altura media de la zona. La coordenada x se calcula para que la punta armada (con su radio) quede a `margen_derecho` del borde derecho:

```
piv.x = x_max − margen_derecho − (L_palanca + r_punta) · cos(angulo_armado)
```

La palanca armada está a -10° para que la punta quede dentro de la zona. Al disparar sube hasta unos 25–30° hasta que la compuerta, ya en el techo, la detiene.

**Limitación física:** el contacto con la compuerta queda a ≈ 2–5 cm de la bisagra, así que la fuerza que se transmite es mucho menor que la de la punta de la palanca. Con la carga de ejemplo solo levanta bien unos 0.4 kg en la punta de la compuerta. Con 0.5 kg no llega al techo.

## 9. Propuesta 2 · Volante de inercia

**Idea:** guardar la energía como movimiento, sin elástico. Un motor pequeño acelera un volante; al disparar un embrague engancha una biela y el volante da una vuelta moviendo la palanca.

**Piezas (Pymunk):**

| Pieza del diseño | Objeto |
|---|---|
| Volante | `Body(m, I = ½ m R²)` + `PivotJoint` al mundo (sin forma: no choca) |
| Motor | `SimpleMotor(mundo, volante, −ω_obj)`; `max_force = volante_torque` |
| Manivela | `Body` pequeño concéntrico con el volante |
| Reducción | `GearJoint(volante, manivela, 0, N)` |
| Embrague | `PinJoint(manivela, palanca)` que se agrega y se quita |

**Detalles:**

- **Energía:** `E = ½ I ω² = ½ · 4.54·10⁻³ · 150² = 51 J`.
- **Reducción 5:1 (indispensable).** La compuerta con su carga, vista desde el punto de contacto, tiene una masa efectiva enorme comparada con el volante. Sin reducción el volante se frena, rebota y la biela se traba. Con `GearJoint` el volante gira N veces más rápido que la manivela, y su inercia "reflejada" en la manivela es `N² · I = 25 · 4.54·10⁻³ = 0.113 kg·m²`.
- **Semántica de `GearJoint`:** `GearJoint(a, b, fase, ratio)` impone `ω_b = ω_a / ratio`. Con `ratio = 1/N` la manivela giraba N veces **más rápido** (error que hubo que corregir); con `ratio = N` gira N veces más lento.
- **Enganche:** la manivela da vueltas todo el tiempo. Al presionar ESPACIO se espera a que el ángulo de la manivela cruce un múltiplo de 2π (el pasador está en el punto más lejano a la palanca, que coincide con la palanca armada) y se agrega el `PinJoint`. Al avanzar otros 2π se quita y el motor vuelve a acelerar el volante.
- **Motor desconectado:** mientras la biela está enganchada, `motor.max_force = 0`; solo trabaja el volante.
- **Recorrido y techo:** el recorrido del extremo inferior del brazo de la palanca es ≈ `2 · manivela_radio`. Con `manivela_radio = 0.018 m` la palanca llega a unos 29°. Si la biela exige más recorrido del que permite la compuerta ya en el techo, **el mecanismo se traba** (la biela empuja contra un tope). Se observó en pruebas con manivelas mayores antes de agregar la reducción. Es un mecanismo cinemático: no cede, así que el radio de la manivela debe ajustarse al recorrido de la palanca.
- **Punto muerto:** al engancharse la manivela está en punto muerto, donde la fuerza transmitida es muy grande para un desplazamiento mínimo.
- **Esfuerzos:** en el modelo rígido la biela soporta picos de 14 000 a 26 000 N.

## 10. Propuesta 3 · Elástico con leva de caracol

**Idea:** misma palanca y elástico que la propuesta 1, pero el rearmado y el seguro los hace una leva de caracol accionada por un motor lento. El perfil de la leva baja la palanca poco a poco (arma); al caer el escalón, el elástico dispara.

**Modelado.** El contacto leva-rodillo no se simula con colisiones (el caracol no es convexo y haría falta una descomposición en triángulos). En su lugar la leva es un **tope de ángulo que se mueve**: un `RotaryLimitJoint(mundo, palanca)` cuyo máximo depende del ángulo de la leva φ:

```
θ_leva(φ) = θ_tope − (θ_tope − θ_armado) · φ / φ_caída     para φ < φ_caída
θ_leva(φ) = θ_tope                                           para φ ≥ φ_caída (el escalón ya pasó)
```

con `φ_caída = 5.5 rad`, `θ_armado = -10°`, `θ_tope = 35°`. El motor mantiene la leva detenida en `φ_alto = φ_caída − 0.02`. Al disparar, φ avanza a `leva_velocidad`:

1. Al pasar `φ_caída` el límite salta a `θ_tope` y el elástico lanza la palanca (disparo).
2. La leva sigue; al completar la vuelta el límite vuelve a bajar y la palanca se baja contra el elástico.
3. Al llegar a `φ_alto + 2π` el motor se detiene (`LISTO`).

La fuerza que puede ejercer el tope se limita con `max_force = motor_torque · reduccion` (N·m).

**Pendiente de verificar:** para dar el recorrido necesario del brazo, `Δ = c_abajo · (sin 35° − sin(−10°)) ≈ 4 cm`, el perfil de la leva debe crecer 4 cm de radio. Con radio mínimo 2 cm el diámetro llega a unos 12 cm, que es toda la altura de la zona, y la palanca cruza esa zona. La leva está dibujada, pero **no se verificó que quepa físicamente**.

## 11. Propuesta del equipo · Rueda con ranura (ariete)

Réplica del boceto del equipo: una rueda con motor, una viga horizontal con ranura (con juego libre, el "ariete") atada a la punta de la compuerta, y el elástico enrollado en la rueda.

**Piezas (Pymunk):**

| Pieza del boceto | Objeto |
|---|---|
| Rueda con motor | `Body` (disco) + `PivotJoint` al mundo |
| Elástico enrollado | `DampedRotarySpring(mundo, rueda)` (unilateral) |
| Seguro | `RotaryLimitJoint(mundo, rueda, −20 rad, ψ_armado)`, temporal |
| Motor (retraer) | `SimpleMotor(mundo, rueda)` con `max_force = torque · reducción` |
| Viga | `Body` sin forma (no choca) |
| Ranura con juego | `GrooveJoint(viga, rueda, (sa, 0), (sb, 0), pasador_local)` |
| Viga atada a la compuerta | `PivotJoint(viga, compuerta, (Lr, 0), (L, 0))` |

**Resorte de torsión equivalente.** El elástico se enrolla en el borde de la rueda de radio `R`, así que una fuerza `F = k·x` produce un par `F·R` y un giro `x = R·θ`:

```
k_t     = k · R²                = 700 · 0.058²              = 2.355 N·m/rad
θ₀      = extensión_armado / R  = 0.13 / 0.058              = 2.24 rad (128°)
ψ_reposo= ψ_armado + θ₀
τ       = k_t · (ψ_reposo − ψ)  mientras ψ < ψ_reposo, 0 después (solo tira)
E       = ½ k_t · (ψ_reposo − ψ)² = ½ · 2.355 · 2.24²       = 5.9 J
```

**Ranura.** `GrooveJoint` constriñe el punto `pasador_local` de la rueda a deslizar por el segmento `(sa,0)–(sb,0)` de la viga (`sa = 0.01`, `sb = sa + ranura_largo`). Los extremos del segmento son las paredes de la ranura: **el pasador empuja la viga con la pared derecha (ariete) y la jala con la izquierda (retraer)**. La ranura se modeló recta, no en curva.

**Colocación de la viga.** Se calcula para que el pasador armado quede sobre el extremo izquierdo de la ranura y el otro extremo coincida con la punta de la compuerta cerrada:

```
β       = ángulo de (punta_compuerta − pasador_armado)
origen  = pasador − sa · (cos β, sin β)
Lr      = |punta_compuerta − origen|
```

**Recorrido del pasador.** Con `ψ_armado = −150°` el pasador avanza en x desde `−r_p cos 30°` hasta `+r_p` (a 0°): `Δx = r_p(1 + cos 30°) = 1.866 · 0.055 = 0.103 m`. Descontado el juego de 1.5 cm quedan ≈ 8.8 cm para mover la viga, suficientes para llevar la compuerta al techo.

**Limitación.** Empujar la punta en horizontal pierde palanca al acercarse a 0°: el par sobre la bisagra es `F · y_punta` y se anula cuando la punta llega a la altura de la bisagra. Con la carga de ejemplo la compuerta apenas llega al techo de 14°. Con `ranura_largo` mayor, `pasador_radio` menor o `k` menor puede no abrir del todo.

**Retraer y cerrar.** El motor gira la rueda de vuelta; el pasador recorre el juego y llega a la pared izquierda, jala la viga y baja la compuerta. Al llegar a `ψ_armado + 0.01 rad` se vuelve a poner el seguro.

## 12. Resultados de referencia

Todas las corridas parten de la compuerta de 0.3 kg con 0.3 kg de carga, con los valores de `params.py`. El tiempo cero es el disparo.

| Propuesta | Energía [J] | Abre a 14° [ms] | Velocidad pico punta [m/s] | ω máx. [rad/s] | Cierra [s] | Ciclo [s] |
|---|---|---|---|---|---|---|
| 1 · Palanca, elástico y cuerda | 17.1 | 184 | 1.8 | 7.1 | 0.86 | 0.94 |
| 2 · Volante de inercia | 51.0 | 109 | 7.0 | 27.9 | 0.32 | 0.31 |
| 3 · Elástico con leva | 16.9 | 192 | 1.7 | 6.9 | 0.97 | 2.09 |
| Equipo · Rueda con ranura | 5.9 | 93 | 3.7 | 14.8 | 0.37 | 1.85 |

Observaciones:

- La propuesta 2 tiene el pico de velocidad más alto, pero la compuerta tarda un poco más en llegar a 14° que con la del equipo: parte del recorrido de la palanca ocurre antes de tocar la compuerta.
- Las propuestas 1 y 3 son equivalentes en desempeño; la diferencia es el mecanismo de rearmado.
- La compuerta cierra cuando el motor rearma en las propuestas 1 y de equipo, cuando la leva baja la palanca en la 3, y por gravedad en la 2.
- Los picos de velocidad de la punta incluyen choques del modelo rígido.

**Carga máxima en la punta (propuesta 1):** abre hasta 14° con 0.3 y 0.4 kg; con 0.5 kg llega a unos 3° y con 0.6 kg ya no abre.

## 13. Salidas: CSV, gráficas y capturas

Cada corrida **sobrescribe** el último resultado, con nombres fijos, en `salidas/`:

| Archivo | Contenido |
|---|---|
| `propuesta1_elastico_cuerda.csv/.png` | Propuesta 1 |
| `propuesta2_volante.csv/.png` | Propuesta 2 |
| `propuesta3_leva.csv/.png` | Propuesta 3 |
| `propuesta_negra.csv/.png` | Propuesta del equipo |
| `antes.png`, `despues1..3.png` | Capturas de `--auto` de las propuestas 1-3 |
| `negra_antes.png`, `negra_despues1..3.png` | Capturas de `--auto` de la del equipo |

**Columnas del CSV (propuestas 1-3):** `t, fase, angulo_deg, omega, vel_punta, angulo_palanca_deg, vel_punta_palanca, altura_punta, fuerza_contacto, tension, energia_elastico, energia_cinetica_compuerta, energia_cinetica_palanca, k`.

**Columnas del CSV (equipo):** `t, fase, angulo_deg, omega, vel_punta, angulo_rueda_deg, omega_rueda, fuerza_viga, par_resorte, energia_elastico, energia_cinetica_compuerta, energia_cinetica_rueda`.

La columna `tension` es la fuerza del elástico en la propuesta 1/3 y la de la biela en la 2. `energia_elastico` es la energía almacenada (en la 2, la cinética del volante). La gráfica `.png` tiene cuatro paneles: ángulo, velocidad, fuerza y energía contra el tiempo, con una línea punteada en el disparo.

## 14. Métricas: cómo se calculan

| Métrica | Definición |
|---|---|
| **Energía almacenada** | `E_lib`, medida justo al disparar: `½ k x²` (elástico) o `½ I ω²` (volante, al engranar) |
| **Abre a 14°** | Tiempo desde el disparo hasta que el ángulo de la compuerta es ≥ 13.5° |
| **Velocidad pico de la punta** | Máximo de `|v|` del punto `(L, 0)` de la compuerta desde el disparo (incluye choques) |
| **ω máx.** | Máximo de `|ω|` de la compuerta desde el disparo |
| **Cierra** | Tiempo desde el disparo hasta que la compuerta vuelve a ≤ -44.5° tras haber estado abierta |
| **Ciclo** | Tiempo desde el disparo hasta `LISTO` otra vez |
| **Fuerza estática armada** | `|r × F|/L_palanca` con la tensión del elástico en la posición armada (propuestas 1 y 3) |
| **Fuerza de contacto media** | Promedio de `|impulso|/dt` palanca→compuerta mientras sube (ángulo < techo − 0.5°) y la fuerza > 1 N |
| **Fuerza de contacto pico** | Máximo de lo anterior; es un choque, **no** es la fuerza útil |

## 15. Lecciones técnicas y errores comunes

Cosas que fallaron durante el desarrollo y cómo se resolvieron.

1. **`body.mass` queda en 0.** Asignar `shape.mass` no calcula la masa del cuerpo en Pymunk 7. Hay que calcular masa, centro de gravedad e inercia a mano (sección 7.2).
2. **Signo del `SimpleMotor`.** `ω_b − ω_a = −rate`. Pasar `rate` positivo hacía girar al revés (la cuerda no se enrollaba y el motor la desenrollaba).
3. **`SlideJoint` en el límite no ejerce fuerza.** Si la cuerda se crea con `max` igual a la distancia, el elástico la arranca sin resistencia. Se resuelve con `max = distancia − 0.5 mm`.
4. **Cuerpos con `center_of_gravity` desplazado y juntas.** Una cuña con el centro de gravedad lejos del origen y un `GrooveJoint` en la punta giraba y se salía del riel. Se resolvió con `moment = inf` (no gira) y poniendo el origen en el centro de gravedad.
5. **Paso de tiempo.** `1/240` y `1/960` s dan resultados diferentes (y falsos) en los mecanismos rápidos; el volante con `1/240` parecía no abrir la compuerta. Se estabilizó con `1/4000`.
6. **Pendiente de la rampa (cuña descartada).** Con una cuña de más de ~40° la rampa choca con el extremo de la compuerta y se atora. Además necesitaba rieles. Se descartó a favor de la palanca de una sola bisagra.
7. **`GearJoint` invertido.** `ratio = 1/N` hace girar la manivela N veces más rápido que el volante. Para reducir hay que usar `ratio = N`.
8. **Biela rígida y techo.** En pruebas sin reducción, la palanca pedía subir más de lo que permite la compuerta ya en el techo y el volante se atoraba y rebotaba. El radio de la manivela debe ajustarse al recorrido de la palanca.
9. **Inercia reflejada.** Sin la reducción 5:1, el volante pesa muy poco frente a la compuerta cargada y se frena en el golpe.
10. **Dependencias.** `pygame` 2.6.1 con Python 3.14 se instala sin `pygame.font`. Se usa `pygame-ce`.

## 16. Limitaciones del modelo

- **2D y rígido.** No hay deformación, holguras reales ni vibración de las piezas.
- **Elástico lineal** y sin histéresis; en realidad una liga o resorte real tiene fatiga y una curva fuerza-estiramiento no lineal.
- **Motor ideal:** velocidad constante hasta su par máximo. No hay curva par-velocidad, corriente ni batería.
- **Choques sin rebote** (`elasticity = 0`) y con la fricción de los valores de ejemplo. Los picos de fuerza son muy sensibles a la rigidez numérica y no son confiables como valores absolutos.
- **Masas, dimensiones y carga** son de ejemplo, igual que la escala (se tomó de un boceto con la compuerta de 25 cm).
- **Leva (propuesta 3)** modelada de forma cinemática, no con contacto real.
- **Ranura** de la propuesta del equipo modelada recta.
- **Un solo robot:** no se simula al oponente; la carga en la punta lo representa de forma aproximada.
- **Sin protección:** los seguros mecánicos y los esfuerzos en piezas reales no se dimensionaron.

## 17. Página web

La página del proyecto se genera desde `web/`:

```bash
.venv/bin/python web/extract.py    # corre las 4 simulaciones y escribe web/data.json
.venv/bin/python web/build.py      # arma web/pagina.html con datos, gráficas y esquemas
```

- `extract.py` ejecuta cada propuesta hasta terminar un ciclo, guarda las series (muestreadas cada 1 ms), las métricas y dos esquemas SVG por propuesta (armado y apertura máxima), generados a partir de la geometría del propio modelo.
- `build.py` rellena `template.html` (los `__MARCADORES__`), incluidos el logo y el icono en base64, y escribe `pagina.html`.
- Las gráficas son SVG dibujados en el navegador con JavaScript puro: sin librerías externas, con valores al pasar el cursor.
- Tema claro y oscuro automáticos. Fuentes: Big Shoulders Display, IBM Plex Sans y IBM Plex Mono.
- Colores de las propuestas: azul, naranja, verde agua y amarillo, validados para daltonismo.
- Si se cambian los parámetros en `params.py`, hay que volver a correr `extract.py` y `build.py`; las cifras de las tarjetas y las gráficas se actualizan solas. Los textos fijos de la plantilla (por ejemplo "7.5 kgf" o "14 000 a 26 000 N") **no** se recalculan.

## 18. Pendientes

- [ ] Confirmar qué significa "6 kgf": empuje del mecanismo en el punto de contacto, o carga que la compuerta debe levantar. Con la carga actual la propuesta 1 levanta unos 0.4 kg en la punta.
- [ ] Reemplazar masas, dimensiones y carga de ejemplo por medidas reales del robot.
- [ ] Verificar físicamente que la leva de la propuesta 3 cabe junto a la palanca.
- [ ] Elegir propuesta comparando costo, facilidad de fabricación y seguridad.
- [ ] Medir un elástico real (curva fuerza-estiramiento) y un motor real (par, velocidad, reducción).
- [ ] Probar el golpe contra un robot rival real.
- [ ] Definir seguros mecánicos y un protocolo de manipulación para 17 J (elástico) o 51 J (volante).
- [ ] Modelar la ranura de la propuesta del equipo en curva.
- [ ] Dimensionar piezas (esfuerzos en la biela, pasadores y ejes) con las cargas reales.
