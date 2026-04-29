# Ranking de repartidores — Comparativa: Weights vs. Listwise + Plackett–Luce

**Contexto:** Grupo Sazón recibe ~200 candidaturas/semana para repartidores en 45 locales (España + México). El cuello de botella no es decir *quién pasa*, es decir *a quién llamar primero hoy* dentro de los aptos. Este documento muestra el mismo problema resuelto con dos enfoques, paso a paso, con prompts incluidos.

> Documentos de referencia: [`FDE_Technical_Assignment.md`](./FDE_Technical_Assignment.md) · [`2026.eacl-demo.24_ES.md`](./2026.eacl-demo.24_ES.md)

---

## 0. Setup común a los dos enfoques

### 0.1 Vacante
- Rol: **Repartidor (delivery driver)**
- Ciudad: **Guadalajara, MX**
- Urgencia operativa: **alta** — faltan **6 turnos noche** y **3 turnos fin de semana** en los próximos 5 días.

### 0.2 Filtros duros (deterministas, idénticos en ambos enfoques)
Se descartan automáticamente los candidatos que no cumplan:

- `licencia_conducir = sí`
- `ciudad ∈ zonas_servicio`
- `consentimiento_datos = sí`

Tras esto, supón que pasan **8 candidatos aptos**:

| ID | Exp. años | Plataformas | Disponibilidad | Inicio | Confiabilidad | Notas |
| --- | ---: | --- | --- | --- | --- | --- |
| A | 5 | Uber Eats, Rappi | solo noche | 10 días | alta | Quiere noches estrictas |
| B | 2 | DiDi Food, Rappi | flexible | 1 día | alta | Disponible fines de semana |
| C | 3 | Uber Eats | tarde / noche | 2 días | media-alta | 1 ausencia justificada hace 8 meses |
| D | 4 | Glovo, Rappi | flexible | 3 días | alta | Tiene moto propia |
| E | 0 | — | mañana | 7 días | sin datos | Primer empleo |
| F | 1 | Uber Eats | flexible | 1 día | media | Cambió de plataforma 2 veces |
| G | 6 | Glovo, Stuart | tarde | 14 días | alta | Solicita salario superior |
| H | 2 | DiDi Food | noche / fin de semana | 2 días | alta | Recomendado por empleado actual |

El objetivo: **ordenar estos 8** para llamar primero a los más críticos esta semana.

---

## 1. Enfoque 1 — Weights (fórmula fija de scoring)

### 1.1 Paso a paso

#### Paso 1: Definir features y pesos
El equipo (o el LLM en una sola pasada) propone una fórmula:

```
score = 0.40·experiencia
      + 0.25·disponibilidad
      + 0.20·rapidez_inicio
      + 0.10·confiabilidad
      + 0.05·match_plataforma
```

Cada feature se normaliza a [0, 1] con reglas simples:

| Feature | Regla de normalización |
| --- | --- |
| `experiencia` | `min(años / 5, 1.0)` |
| `disponibilidad` | flexible=1.0; tarde+noche=0.8; solo noche=0.6; solo mañana=0.4 |
| `rapidez_inicio` | 1 día=1.0; 2-3=0.85; 4-7=0.6; 8-14=0.3 |
| `confiabilidad` | alta=1.0; media-alta=0.8; media=0.6; sin datos=0.5 |
| `match_plataforma` | conoce ≥ 1 plataforma del listado canónico → 1.0; otra → 0.5 |

#### Paso 2: (Opcional) prompt al LLM para sugerir pesos

```text
SYSTEM
Eres un experto en operaciones de delivery. Dado el contexto de la vacante,
propón pesos numéricos (suman 1.0) para 5 features de scoring.
Devuelve SOLO JSON.

USER
Vacante: Repartidor en Guadalajara.
Urgencia: alta — faltan turnos noche y fin de semana en 5 días.
Features disponibles: experiencia, disponibilidad, rapidez_inicio, confiabilidad, match_plataforma.

Formato:
{
  "weights": {
    "experiencia": 0.0,
    "disponibilidad": 0.0,
    "rapidez_inicio": 0.0,
    "confiabilidad": 0.0,
    "match_plataforma": 0.0
  },
  "rationale": "una frase corta"
}
```

Salida del LLM (ejemplo):

```json
{
  "weights": {
    "experiencia": 0.40,
    "disponibilidad": 0.25,
    "rapidez_inicio": 0.20,
    "confiabilidad": 0.10,
    "match_plataforma": 0.05
  },
  "rationale": "Se prioriza experiencia y disponibilidad para minimizar onboarding."
}
```

#### Paso 3: Calcular score por candidato

| ID | exp | disp | inicio | conf | match | **score** |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 1.00 | 0.60 | 0.30 | 1.00 | 1.00 | **0.760** |
| B | 0.40 | 1.00 | 1.00 | 1.00 | 1.00 | **0.760** |
| C | 0.60 | 0.80 | 0.85 | 0.80 | 1.00 | **0.740** |
| D | 0.80 | 1.00 | 0.85 | 1.00 | 1.00 | **0.892** |
| E | 0.00 | 0.40 | 0.60 | 0.50 | 0.50 | **0.295** |
| F | 0.20 | 1.00 | 1.00 | 0.60 | 1.00 | **0.640** |
| G | 1.00 | 0.80 | 0.30 | 1.00 | 1.00 | **0.810** |
| H | 0.40 | 0.80 | 0.85 | 1.00 | 1.00 | **0.680** |

#### Paso 4: Ordenar por score (descendente)

**Ranking weights:** `D > G > A ≈ B > C > H > F > E`

### 1.2 Problema visible
- **A y G** salen muy arriba aunque empiezan **en 10 y 14 días**. Esta semana no resuelven nada operativamente.
- **H** queda en 6º lugar a pesar de tener disponibilidad **noche + fin de semana**, justo lo que falta esta semana.
- **B** y **F** (los que empiezan mañana) quedan empatados o por debajo de gente que empieza en 2 semanas.

La fórmula congela una visión genérica del rol y **no refleja la urgencia real** de la semana.

### 1.3 Costo y trazabilidad
- **1 llamada al LLM** (opcional, solo para sugerir pesos).
- Trazabilidad: alta — todo cálculo es visible.
- Pero la **decisión** está atrapada en pesos arbitrarios.

---

## 2. Enfoque 2 — Listwise + Plackett–Luce

### 2.1 Paso a paso

#### Paso 1: Generar subconjuntos (mini-torneos) de tamaño K=3

Round-robin parcial cubriendo a todos los candidatos al menos 2 veces:

- T1: {A, B, C}
- T2: {D, E, F}
- T3: {G, H, A}
- T4: {B, D, G}
- T5: {C, F, H}
- T6: {A, D, H}
- T7: {B, G, E}
- T8: {C, D, B}

#### Paso 2: Prompt listwise para el LLM (idéntico para todos los torneos)

```text
SYSTEM
Eres evaluador de candidatos para Grupo Sazón (rol: repartidor).

Evalúa COMPARATIVAMENTE (listwise) un grupo de candidatos.
NO los evalúes uno por uno de forma aislada.
Razonas internamente paso a paso, pero entregas SOLO el orden final.

Rúbrica (en este orden de importancia):
1) Cobertura operativa inmediata (inicio + disponibilidad real para los turnos críticos).
2) Confiabilidad (historial, ausencias, estabilidad).
3) Experiencia relevante en reparto (años + plataformas).
4) Comunicación y resolución básica de incidencias.
5) Riesgo operativo (señales de abandono, restricciones fuertes).

Reglas:
- No inventes datos. Si falta info, trátalo como neutral.
- No uses atributos personales no laborales (nombre, género, edad, nacionalidad).
- Considera el contexto operativo provisto.
- Devuelve SOLO JSON con esta forma:
  {
    "ranking": ["ID1","ID2","ID3"],
    "confidence": 0.00
  }
- Sin explicaciones, sin texto extra.
```

```text
USER
Contexto operativo:
- Ciudad: Guadalajara
- Urgencia: alta
- Turnos críticos esta semana: noche, fin_de_semana
- Ventana de inicio ideal: 0-3 días

Candidatos:
[
  {"id":"A","exp_years":5,"platforms":["Uber Eats","Rappi"],"availability":"solo_noche","start":"10_dias","reliability":"alta"},
  {"id":"B","exp_years":2,"platforms":["DiDi Food","Rappi"],"availability":"flexible","start":"1_dia","reliability":"alta"},
  {"id":"C","exp_years":3,"platforms":["Uber Eats"],"availability":"tarde_noche","start":"2_dias","reliability":"media_alta"}
]
```

#### Paso 3: Resultados de los torneos (lo que devolvería el LLM)

| Torneo | Subconjunto | Salida del LLM (JSON) |
| --- | --- | --- |
| T1 | {A, B, C} | `{"ranking":["B","C","A"],"confidence":0.82}` |
| T2 | {D, E, F} | `{"ranking":["D","F","E"],"confidence":0.91}` |
| T3 | {G, H, A} | `{"ranking":["H","A","G"],"confidence":0.74}` |
| T4 | {B, D, G} | `{"ranking":["B","D","G"],"confidence":0.79}` |
| T5 | {C, F, H} | `{"ranking":["H","C","F"],"confidence":0.81}` |
| T6 | {A, D, H} | `{"ranking":["D","H","A"],"confidence":0.85}` |
| T7 | {B, G, E} | `{"ranking":["B","G","E"],"confidence":0.88}` |
| T8 | {C, D, B} | `{"ranking":["B","D","C"],"confidence":0.83}` |

Patrón visible: **B y D dominan**, **H aparece arriba en 2 de 3 torneos**, **A y G caen** porque "5 años" y "6 años" no compensan empezar en 10–14 días.

#### Paso 4: Agregar con Plackett–Luce

El modelo PL ajusta utilidades latentes \(u_i\) que **maximizan la verosimilitud** de los rankings observados:

\[
P(\pi) = \prod_{k=1}^{K} \frac{\exp(u_{\pi_k})}{\sum_{j=k}^{K} \exp(u_{\pi_j})}
\]

Para este conjunto de torneos, el ajuste produce (ejemplo):

| ID | utilidad \(u_i\) |
| ---: | ---: |
| B | 2.45 |
| D | 1.95 |
| H | 1.40 |
| C | 0.95 |
| F | 0.55 |
| G | 0.20 |
| A | 0.05 |
| E | -0.85 |

**Ranking PL:** `B > D > H > C > F > G > A > E`

#### Paso 5: Active learning para reducir incertidumbre

PL también devuelve la varianza posterior por candidato (Laplace approx.). Supón que la **frontera incierta** es entre `H` y `C` para top-3.

Lanzas un torneo dirigido:

- T9: {H, C, D} → `{"ranking":["D","H","C"],"confidence":0.80}`
- T10: {H, C, B} → `{"ranking":["B","H","C"],"confidence":0.78}`

Reajustas PL. La separación entre H y C se confirma. Top-3 estable: **B, D, H**.

### 2.2 Decisión final de negocio

- **Llamar HOY:** `B`, `D`, `H` (los 3 cubren turnos noche/fin de semana en ≤ 3 días)
- **Backup:** `C`, `F`
- **Mantener en cola más larga:** `G`, `A` (irrelevantes para esta semana, pero útiles más adelante)
- **Descartar suave:** `E` (sin experiencia ni urgencia)

### 2.3 Costo y trazabilidad
- **8 llamadas al LLM** en el round-robin inicial, **2 más** en active learning.
- Cada decisión cita: torneos donde apareció el candidato, utilidad PL, confianza, versión de rúbrica.
- Audit trail completo y defendible.

---

## 3. Comparativa lado a lado

| Aspecto | Weights | Listwise + PL |
| --- | --- | --- |
| **Top 3 final** | D, G, A | **B, D, H** |
| **¿Cubre los turnos críticos esta semana?** | No (G y A empiezan en 14 y 10 días) | **Sí** (los 3 inician en ≤ 3 días) |
| **Sensibilidad al contexto** | Baja — pesos fijos | **Alta** — el LLM ve la urgencia y la rúbrica |
| **Trade-offs entre dimensiones** | Lineales y ponderados a mano | **Capturados por comparación de grupo** |
| **Ruido de juicio único** | Inexistente (no hay LLM por candidato) | **Amortiguado** por agregación PL multi-torneo |
| **Auditabilidad** | Buena | **Buena** (utilidades + torneos + confianza) |
| **Extensibilidad a 200/semana** | Recalcular fórmula | **Active learning** reduce llamadas |
| **Coste LLM** | 0–1 llamada | 8–10 llamadas (escala sub-lineal con AL) |
| **Riesgo de mala decisión cuando contexto cambia** | **Alto** | Bajo |

### El verdadero punto: ¿por qué difieren los rankings?
La fórmula de pesos premia **experiencia y disponibilidad nominal**.  
El listwise + PL premia **encaje operativo con la semana actual** porque el LLM ve la urgencia en el prompt y el modelo PL agrega múltiples comparaciones de grupo donde ese encaje aparece una y otra vez.

Cuando el contexto cambia (otra semana, otro turno crítico), **el flujo PL se adapta sin tocar fórmulas**. La fórmula de pesos requiere reescribir coeficientes cada vez.

---

## 4. Cuándo elegir cada uno

| Situación | Mejor opción |
| --- | --- |
| Filtros duros binarios (licencia, zona) | Reglas deterministas — no usar PL ni weights |
| Pool pequeño (< 10), criterios estables | Weights basta |
| Contexto operativo cambia semana a semana | **Listwise + PL** |
| Pool mediano-grande (50–500), trade-offs sutiles entre cualificados | **Listwise + PL** |
| Auditoría regulatoria fina (LL-144, EU AI Act) | Listwise + PL con `decision_trace` |
| Costo de LLM es restricción dura | Weights, o PL con menos torneos + AL agresivo |

### Recomendación para Grupo Sazón
**Híbrido en 3 capas:**

1. **Filtros duros** (deterministas) — descarta los que no cumplen mínimos.
2. **Score base con weights** — orden inicial barato sobre el pool grande.
3. **Listwise + PL solo en el top-N** (p. ej. los 30 mejores por score) — desempate fino donde sí importa la decisión de quién llamar primero.

Ese híbrido captura **~95% del beneficio de PL con ~20% del costo**.

---

## 5. Anexo — Esqueleto de implementación

```python
# Pseudocódigo — no es código de producción
def rank_candidates(candidates, context, k_subset=3, n_initial=8):
    apt = [c for c in candidates if hard_filters(c)]
    base_score = {c.id: weighted_score(c) for c in apt}

    top_pool = sorted(apt, key=lambda c: -base_score[c.id])[:30]

    subsets = round_robin_subsets(top_pool, k=k_subset, n=n_initial)
    tournaments = []
    for s in subsets:
        ranking = call_llm_listwise(s, context)
        tournaments.append(ranking)

    pl = fit_plackett_luce(tournaments, items=top_pool)

    while pl.has_uncertain_frontier():
        s = pl.next_informative_subset(k=k_subset)
        tournaments.append(call_llm_listwise(s, context))
        pl.refit(tournaments)

    return pl.global_ranking()
```

Componentes clave:
- `hard_filters` — deterministas, auditables.
- `weighted_score` — score barato del Enfoque 1, solo como pre-filtro.
- `call_llm_listwise` — el prompt de la sección 2.1 paso 2.
- `fit_plackett_luce` — librería estadística (p. ej. `choix`, `pyplackettluce` o implementación custom con MLE).
- `next_informative_subset` — acquisition function (MC-KG, posterior disagreement, KL-UCB) — ver sección 3.5 de [`2026.eacl-demo.24_ES.md`](./2026.eacl-demo.24_ES.md).

---

## 6. Para llevar

- **Ordenar pesos** funciona si los pesos son verdaderos y el contexto no cambia. En reclutamiento real, ninguna de las dos cosas se cumple.
- **Listwise + PL** convierte juicio del LLM en **inferencia estadística**: agrega muchas comparaciones ruidosas en utilidades latentes coherentes.
- **Active learning** hace el coste manejable: solo preguntas donde de verdad cambia la decisión.
- **El ranking ya no es una fórmula congelada, sino una inferencia adaptativa al contexto operativo de la semana.**

> Fuente metodológica: *Active Listwise Tournaments for Candidate Ranking* — ver [`2026.eacl-demo.24_ES.md`](./2026.eacl-demo.24_ES.md), secciones 3.5 y 4.1 (NDCG@K mejora sostenidamente con active learning; convergencia rápida tras ~10 iteraciones).
