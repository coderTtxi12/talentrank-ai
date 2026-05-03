"""Bulk synthetic data for local QA: candidates, chats, and sentiment rows.

Builds realistic **Spanish** screening transcripts and post-screening outcomes as if
the screening agent and (when applicable) the sentiment worker had already run—
**without** calling OpenAI or writing listwise/ranking tables.

HTTP access is gated by ``ALLOW_SIMULATION_SEED``. Seeded rows are marked via
``captured_data.simulation_batch`` and ``@mock.orbio.test`` emails; use
:func:`purge_simulation_seed_data` to tear down.
"""

from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple, cast

from sqlalchemy import delete, text
from sqlalchemy.engine import CursorResult

from sqlalchemy.orm import Session

from app.models.database import (
    Availability,
    Candidate,
    CandidateStatus,
    Channel,
    Conversation,
    ConversationStatus,
    Language,
    Message,
    MessageRole,
    PreferredSchedule,
    RankingResult,
    Sentiment,
    SentimentResult,
)
from app.workers.sentiment_analysis.grupo_sazon_coverage_cities import (
    COVERAGE_CITIES_MEXICO,
    COVERAGE_CITIES_SPAIN,
)

MODEL_LABEL = "simulation/screening-seed-v1"

# Cities outside coverage (not listed in GRUPO_SAZON_PUBLIC_INFO_ES.txt).
OUT_OF_COVERAGE_CITIES: Tuple[str, ...] = (
    "Logroño, La Rioja",
    "Pachuca de Soto, Hidalgo",
    "Rio Verde, San Luis Potosi",
    "Uruapan, Michoacan",
    "Parla, Madrid periferia sur",
)

FIRST_NAMES_ES = (
    "Marcos", "Laura", "Diego", "Carmen", "Álvaro", "Lucía", "Pablo", "Elena",
    "Hugo", "Marta", "Sergio", "Andrea", "Iván", "Paula", "Rubén", "Cristina",
    "Javier", "Sara", "Miguel", "Natalia", "Rafael", "Isabel", "Fernando",
    "Beatriz", "Alberto",
)
LAST_NAMES_ES = (
    "García", "Martínez", "López", "Sánchez", "González", "Pérez", "Hernández",
    "Jiménez", "Ruiz", "Díaz", "Moreno", "Muñoz", "Álvarez", "Romero", "Torres",
    "Gutiérrez", "Serrano", "Ramos", "Blanco", "Suárez", "Castro", "Ortega",
    "Rubio", "Márquez", "Delgado",
)

FIRST_NAMES_MX = (
    "José Luis", "María Fernanda", "Carlos", "Guadalupe", "Luis", "Ana",
    "Fernando", "Daniela", "Ricardo", "Valentina", "Jorge", "Camila",
    "Alejandro", "Ximena", "Roberto", "Paola", "Manuel", "Adriana",
    "Francisco", "Sofía", "Óscar", "Monica", "Eduardo", "Gabriela", "Héctor",
)
LAST_NAMES_MX = (
    "Hernández", "García", "Martínez", "López", "González", "Pérez", "Rodríguez",
    "Sánchez", "Ramírez", "Flores", "Rivera", "Gómez", "Díaz", "Torres",
    "Morales", "Cruz", "Reyes", "Ortiz", "Castillo", "Vargas", "Jiménez",
    "Ramos", "Medina", "Ruiz", "Castro",
)

ASSISTANT_INTRO_ES = (
    "Hola, soy el asistente de Grupo Sazón. Gracias por tu interés en el puesto "
    "de repartidor/a. Te haré unas preguntas breves sobre tu disponibilidad, "
    "licencia y zona."
)
ASSISTANT_INTRO_MX = (
    "¡Hola! Soy el asistente de Grupo Sazón México para repartidores. "
    "Vamos a revisar algunos datos operativos: licencia, ciudad y plataformas."
)
MONTHS_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _pick_start_date(rng: random.Random, today: date) -> date:
    """Roughly 5 days to ~12 weeks from today; occasionally longer if negotiating notice."""
    if rng.random() < 0.18:
        days = rng.randint(21, 55)
    elif rng.random() < 0.1:
        days = rng.randint(56, 95)
    else:
        days = rng.randint(5, 20)
    return today + timedelta(days=days)


def _format_start_date_human(d: date) -> str:
    return f"{d.day} de {MONTHS_ES[d.month - 1]} de {d.year}"


def _pick_coverage_city(lang: Language, rng: random.Random) -> str:
    pool = COVERAGE_CITIES_SPAIN if lang == Language.ES_ES else COVERAGE_CITIES_MEXICO
    c = pool[rng.randrange(len(pool))]
    if lang == Language.ES_MX and rng.random() < 0.35:
        return f"{c}, México"
    if lang == Language.ES_ES and rng.random() < 0.25:
        return f"{c}, España"
    return c


def _build_turns(
    *,
    lang: Language,
    full_name: str,
    city_zone: str,
    has_license: bool,
    availability: Availability,
    preferred: PreferredSchedule,
    experience_years: int,
    platforms: List[str],
    start_date: date,
    rng: random.Random,
) -> List[Tuple[MessageRole, str]]:
    intro = ASSISTANT_INTRO_ES if lang == Language.ES_ES else ASSISTANT_INTRO_MX
    lic_text = (
        "Sí, tengo carnet de conducir en vigor."
        if has_license
        else "No dispongo de carnet de conducir para moto o coche."
    )
    plat_str = ", ".join(platforms) if platforms else "ninguna aún, pero puedo aprender"
    sched_label = {
        PreferredSchedule.MORNING: "Mañana",
        PreferredSchedule.AFTERNOON: "Tarde",
        PreferredSchedule.EVENING: "Noche",
        PreferredSchedule.FLEXIBLE: "Flexible",
    }[preferred]
    human_start = _format_start_date_human(start_date)
    start_user_phrase = rng.choice(
        [
            f"Mi idea es poder empezar el {human_start}.",
            f"Podría incorporarme el {human_start}, si os encaja.",
            f"Tengo disponible desde el {human_start}.",
            f"El {human_start} sería una fecha realista para mí.",
        ]
    )
    turns: List[Tuple[MessageRole, str]] = [
        (MessageRole.ASSISTANT, intro),
        (MessageRole.USER, "Hola, quiero aplicar al reparto."),
        (MessageRole.ASSISTANT, "¿Cómo te llamas completo?"),
        (MessageRole.USER, f"Me llamo {full_name}."),
        (MessageRole.ASSISTANT, "¿Tienes licencia de conducir vigente para trabajar en reparto?"),
        (MessageRole.USER, lic_text),
        (MessageRole.ASSISTANT, "¿En qué ciudad o zona vives?"),
        (MessageRole.USER, f"Vivo en {city_zone}."),
        (MessageRole.ASSISTANT, "¿Qué disponibilidad tienes: tiempo completo, parcial o fines de semana?"),
        (
            MessageRole.USER,
            "Tiempo completo"
            if availability == Availability.FULL_TIME
            else ("Fines de semana" if availability == Availability.WEEKENDS else "Parcial / tardes"),
        ),
        (MessageRole.ASSISTANT, "¿Prefieres turno mañana, tarde, noche o flexible?"),
        (MessageRole.USER, sched_label),
        (MessageRole.ASSISTANT, "¿Cuántos años de experiencia tienes en reparto o roles similares?"),
        (MessageRole.USER, f"Llevo alrededor de {experience_years} años, en parte con apps."),
        (MessageRole.ASSISTANT, "¿En qué plataformas has trabajado o conoces?"),
        (MessageRole.USER, f"He usado sobre todo {plat_str}."),
        (MessageRole.ASSISTANT, "Perfecto. ¿Podrías empezar en las próximas dos semanas?"),
        (
            MessageRole.USER,
            "Sí, puedo incorporarme con pocos días de margen."
            if rng.random() > 0.15
            else "Necesitaría al menos tres semanas por temas personales.",
        ),
        (
            MessageRole.ASSISTANT,
            "¿Qué fecha concreta podrías incorporarte? Necesitamos una referencia para planificar rutas.",
        ),
        (MessageRole.USER, start_user_phrase),
        (MessageRole.ASSISTANT, "Gracias, con esto cerramos el screening inicial. ¿Algo más que quieras contarnos?"),
        (
            MessageRole.USER,
            "Solo que tengo buena actitud en ventanas pico y me muevo bien en mi zona."
            if rng.random() > 0.3
            else "Nada más, quedo pendiente.",
        ),
        (MessageRole.ASSISTANT, "Recibido. Un equipo revisará tu perfil. ¡Que tengas buen día!"),
    ]
    return turns


def _availability_label(av: Availability) -> str:
    return {
        Availability.FULL_TIME: "tiempo completo",
        Availability.PART_TIME: "jornada parcial",
        Availability.WEEKENDS: "fines de semana",
    }[av]


def _schedule_label(pref: PreferredSchedule) -> str:
    return {
        PreferredSchedule.MORNING: "turno mañana",
        PreferredSchedule.AFTERNOON: "turno tarde",
        PreferredSchedule.EVENING: "turno noche",
        PreferredSchedule.FLEXIBLE: "horario flexible",
    }[pref]


def _reasoning_for_sentiment(
    sentiment: Sentiment,
    rng: random.Random,
    *,
    city_zone: str,
    human_start: str,
    lic_ok: bool,
    avail_label: str,
    sched_label: str,
    exp_years: int,
    plat_preview: str,
) -> str:
    """Texto tipo modelo: 2–4 frases, sin meta-referencias al seed."""
    lic_phrase = (
        "Confirma licencia en regla para reparto."
        if lic_ok
        else "En la charla declara no disponer de licencia; encaja con filtro duro si aplica."
    )
    city_short = city_zone.split(",")[0].strip()[:48]

    if sentiment == Sentiment.POSITIVE:
        opts = [
            (
                f"El tono es colaborativo y las respuestas son directas. {lic_phrase} "
                f"Indica vivir cerca de operación en «{city_short}» y una disponibilidad "
                f"de {avail_label} con preferencia de {sched_label}. "
                f"Propone incorporación el {human_start}, alineada con planificación típica de rutas."
            ),
            (
                f"Conversación fluida: explica ~{exp_years} años de experiencia y uso de {plat_preview}. "
                f"{lic_phrase} La fecha de alta {human_start} es plausible para onboarding. "
                f"No aparecen señales de frustración sostenida."
            ),
            (
                f"Perfil comunicativo y proactivo. Detalla ciudad/zona ({city_short}) y ventanas "
                f"en las que puede cubrir picos. {lic_phrase} Cierra con fecha concreta ({human_start}), "
                f"lo que facilita handoff a operaciones."
            ),
        ]
        return rng.choice(opts)

    if sentiment == Sentiment.NEUTRAL:
        opts = [
            (
                f"Interacción correcta pero con formulaciones genéricas en disponibilidad. {lic_phrase} "
                f"Menciona {city_short} y {human_start} como referencia de entrada. "
                f"Sin picos de hostilidad; conviene validar en llamada turno {sched_label}."
            ),
            (
                f"Responde lo solicitado sin profundizar en matices de cobertura. Experiencia declarada "
                f"~{exp_years} años y plataformas ({plat_preview}). {lic_phrase} "
                f"La fecha propuesta ({human_start}) es coherente con el guion del chat."
            ),
            (
                f"Tono plano, contestaciones breves. Aun así deja claros ciudad, {avail_label} y "
                f"preferencia {sched_label}. {lic_phrase} La incorporación el {human_start} queda explícita en el tramo final."
            ),
        ]
        return rng.choice(opts)

    if sentiment == Sentiment.CONFUSED:
        opts = [
            (
                f"Hay rebobinados sobre horarios y qué implica «{avail_label}» frente a picos de comida/cena. "
                f"{lic_phrase} A pesar de ello fija {human_start} y zona {city_short}; "
                f"la confusión parece operativa, no maliciosa."
            ),
            (
                f"Mezcla respuestas claras con dudas al cerrar (disponibilidad vs fecha). "
                f"{lic_phrase} Al final concreta entrada el {human_start}. "
                f"Recomendable aclarar franja {sched_label} antes de asignar ruta."
            ),
            (
                f"Pregunta implícitas sin responder del todo sobre turnos; el candidato insiste en "
                f"{plat_preview} y experiencia. {lic_phrase} Ciudad {city_short} y alta {human_start} sí quedan reflejados."
            ),
        ]
        return rng.choice(opts)

    # FRUSTRATED
    opts = [
        (
            f"Se percibe impaciencia al repetir preguntas de calendario y ciudad. {lic_phrase} "
            f"Aun así aporta {human_start} y {city_short}. "
            f"Valorar seguimiento humano breve antes de descartar: el perfil puede ser válido en pico."
        ),
        (
            f"El cierre del chat es algo cortante; podría haber fricción con coordinación en tienda. "
            f"{lic_phrase} Datos duros (zona, fecha {human_start}, {avail_label}) sí aparecen. "
            f"Experiencia declarada {exp_years} años."
        ),
        (
            f"Tono tenso cuando se pide concretar fecha; responde con {human_start} pero con formulación breve. "
            f"{lic_phrase} Interesa verificar motivación en {city_short} para estabilidad del turno {sched_label}."
        ),
    ]
    return rng.choice(opts)


def _sentiment_bundle(
    idx: int,
    rng: random.Random,
    *,
    has_license: bool,
    city_zone: str,
    availability: Availability,
    preferred: PreferredSchedule,
    experience_years: int,
    platforms: List[str],
    start_date: date,
) -> Tuple[Sentiment, float, Dict[str, Any]]:
    cycle = (
        Sentiment.POSITIVE,
        Sentiment.NEUTRAL,
        Sentiment.CONFUSED,
        Sentiment.NEUTRAL,
        Sentiment.FRUSTRATED,
        Sentiment.POSITIVE,
        Sentiment.NEUTRAL,
    )
    sentiment = cycle[idx % len(cycle)]
    confidence = round(0.55 + rng.random() * 0.4, 3)
    tones = {
        Sentiment.POSITIVE: "cooperative",
        Sentiment.NEUTRAL: "neutral",
        Sentiment.CONFUSED: "neutral",
        Sentiment.FRUSTRATED: "frustrated",
    }
    engagement = rng.choice(["high", "medium", "medium", "low"])
    human_start = _format_start_date_human(start_date)
    start_iso = start_date.isoformat()
    avail_l = _availability_label(availability)
    sched_l = _schedule_label(preferred)
    plat_preview = ", ".join(platforms[:2]) if platforms else "apps de delivery"

    reasoning = _reasoning_for_sentiment(
        sentiment,
        rng,
        city_zone=city_zone,
        human_start=human_start,
        lic_ok=has_license,
        avail_label=avail_l,
        sched_label=sched_l,
        exp_years=experience_years,
        plat_preview=plat_preview,
    )

    notes = (
        "Candidato responde con claridad; tono adecuado para operación de pico."
        if sentiment == Sentiment.POSITIVE
        else (
            "Respuestas suficientes pero poco detalle en algunos matices operativos."
            if sentiment == Sentiment.NEUTRAL
            else (
                "Dudas o idas y vueltas en horarios; conviene una pasada de aclaración."
                if sentiment == Sentiment.CONFUSED
                else "Tono más tenso al final; datos clave igualmente presentes en el hilo."
            )
        )
    )
    summary = (
        f"Perfil colaborativo; confirma requisitos básicos y propone incorporación el {human_start}."
        if sentiment == Sentiment.POSITIVE
        else (
            f"Interacción estable; deja fijada fecha de inicio ({human_start}) y ciudad de referencia."
            if sentiment == Sentiment.NEUTRAL
            else (
                f"Mezcla de claridad y dudas en turnos; fecha de alta indicada: {human_start}."
                if sentiment == Sentiment.CONFUSED
                else f"Algo de fricción en el cierre; aun así concreta entrada hacia {human_start}."
            )
        )
    )

    evidence = [
        f"Menciona explícitamente la fecha de incorporación ({human_start}).",
        f"Declaración sobre zona o domicilio operativo: {city_zone[:120]}.",
        (
            "Indica disponibilidad y ventana horaria en la conversación."
            if sentiment != Sentiment.FRUSTRATED
            else "A pesar del tono, confirma disponibilidad y fecha en el mismo hilo."
        ),
    ]

    signals: Dict[str, Any] = {
        "tone": tones[sentiment],
        "engagement": engagement,
        "notes": notes,
        "reasoning": reasoning,
        "concerns": []
        if sentiment != Sentiment.FRUSTRATED
        else ["Posible fricción emocional en la recta final del screening"],
        "evidence": evidence,
        "post_conversation_summary": summary,
        "key_data_points": {
            "drivers_license": "yes" if has_license else "no",
            "city_zone": city_zone,
            "availability": availability.value,
            "preferred_schedule": preferred.value,
            "experience_years": experience_years,
            "platforms": platforms,
            "start_date": start_iso,
        },
    }
    return sentiment, confidence, signals


def _hard_disq_slot_counts(count: int) -> tuple[int, int]:
    """How many synthetic rows get HARD_DISQ for license vs. city. Scales with ``count`` (e.g. 10 -> 2+2)."""

    if count < 1:
        return 0, 0
    n_lic = min(4, max(1, count // 5))
    n_city = min(4, max(1, count // 5))
    while n_lic + n_city > max(0, count - 1) and (n_lic > 0 or n_city > 0):
        if n_city > 0:
            n_city -= 1
        elif n_lic > 0:
            n_lic -= 1
    return n_lic, n_city


def seed_screening_simulation_batch(
    db: Session,
    *,
    count: int = 10,
) -> Dict[str, Any]:
    """Create ``count`` synthetic candidates with conversations.

    Every candidate has ``start_date``. Those in ``sentiment_analysis`` always get a
    ``SentimentResult`` (simulated post-worker). HARD_DISQ rows have no sentiment row.

    No listwise or ranking rows. Uses one DB transaction (caller should ``commit``).
    """

    if count < 1:
        raise ValueError("count must be >= 1")

    batch_id = uuid.uuid4().hex[:12]
    rng = random.Random(hash(batch_id) % (2**32))
    t0 = datetime.now(timezone.utc)
    candidate_ids: List[uuid.UUID] = []

    breakdown = {
        "hard_disq_no_license": 0,
        "hard_disq_city_out_of_coverage": 0,
        "sentiment_analysis_with_row": 0,
        "country_es": 0,
        "country_mx": 0,
    }

    today = _utc_today()
    n_lic_disq, n_city_disq = _hard_disq_slot_counts(count)

    for i in range(count):
        cid = uuid.uuid4()
        candidate_ids.append(cid)
        lang = Language.ES_ES if i % 2 == 0 else Language.ES_MX
        if lang == Language.ES_ES:
            breakdown["country_es"] += 1
            fn = FIRST_NAMES_ES[i % len(FIRST_NAMES_ES)]
            ln = LAST_NAMES_ES[(i * 3) % len(LAST_NAMES_ES)]
            tail = (int(batch_id, 16) % 10_000_000) + i * 97
            phone = f"+346{tail:08d}"
            if len(phone) > 15:
                phone = phone[:15]
        else:
            breakdown["country_mx"] += 1
            fn = FIRST_NAMES_MX[i % len(FIRST_NAMES_MX)]
            ln = LAST_NAMES_MX[(i * 3) % len(LAST_NAMES_MX)]
            tail = (int(batch_id[-10:], 16) % 10_000_000) + i * 131
            phone = f"+5255{tail:08d}"
            if len(phone) > 15:
                phone = phone[:15]

        full_name = f"{fn} {ln}"
        email = f"sim.{batch_id}.{i:03d}@mock.orbio.test"

        start_date = _pick_start_date(rng, today)

        # Hard requirements (aligned with phase-1 worker): license and city only.
        disq_mode = 0  # 0 none, 1 no license, 2 bad city
        if i < n_lic_disq:
            disq_mode = 1
            breakdown["hard_disq_no_license"] += 1
        elif i < n_lic_disq + n_city_disq:
            disq_mode = 2
            breakdown["hard_disq_city_out_of_coverage"] += 1

        if disq_mode == 1:
            has_license = False
            city_zone = _pick_coverage_city(lang, rng)
            status = CandidateStatus.HARD_DISQ
        elif disq_mode == 2:
            has_license = True
            city_zone = OUT_OF_COVERAGE_CITIES[i % len(OUT_OF_COVERAGE_CITIES)]
            status = CandidateStatus.HARD_DISQ
        else:
            has_license = True
            city_zone = _pick_coverage_city(lang, rng)
            status = CandidateStatus.SENTIMENT_ANALYSIS

        availability = rng.choice(
            [Availability.FULL_TIME, Availability.PART_TIME, Availability.WEEKENDS]
        )
        preferred = rng.choice(
            [
                PreferredSchedule.MORNING,
                PreferredSchedule.AFTERNOON,
                PreferredSchedule.EVENING,
                PreferredSchedule.FLEXIBLE,
            ]
        )
        experience_years = min(20, max(0, rng.randint(0, 8) + (i % 4)))
        platforms = rng.sample(
            ["Uber Eats", "Rappi", "DiDi Food", "just eat", "propia flota"],
            k=min(3, 1 + rng.randint(0, 2)),
        )

        cand = Candidate(
            id=cid,
            full_name=full_name,
            phone=phone[:40],
            email=email[:160],
            language=lang,
            drivers_license=has_license,
            city_zone=city_zone[:200],
            availability=availability,
            preferred_schedule=preferred,
            experience_years=experience_years,
            platforms=platforms,
            start_date=start_date,
            status=status,
            is_completed=True,
            slot_uncertain=(i % 13 == 0),
        )
        db.add(cand)

        session_token = f"sim-{batch_id}-{i:03d}-{uuid.uuid4().hex[:6]}"
        conv = Conversation(
            session_id=session_token[:80],
            candidate_id=cid,
            vacancy_id=None,
            channel=Channel.WEB_CHAT,
            language=lang,
            status=ConversationStatus.COMPLETED,
            captured_data={"simulation_batch": batch_id, "index": i},
            summary=f"Synthetic screening chat (batch {batch_id}, #{i}).",
            started_at=t0 - timedelta(minutes=45 + i, seconds=rng.randint(0, 59)),
            last_seen_at=t0 - timedelta(minutes=5 + i),
            ended_at=t0 - timedelta(minutes=2 + i),
        )
        db.add(conv)
        db.flush()

        turns = _build_turns(
            lang=lang,
            full_name=full_name,
            city_zone=city_zone,
            has_license=has_license,
            availability=availability,
            preferred=preferred,
            experience_years=experience_years,
            platforms=platforms,
            start_date=start_date,
            rng=rng,
        )
        for j, (role, content) in enumerate(turns):
            db.add(
                Message(
                    conversation_id=conv.id,
                    role=role,
                    content=content,
                    language=lang,
                    security_flagged=False,
                    created_at=conv.started_at + timedelta(seconds=20 * j + rng.randint(0, 8)),
                )
            )

        if status == CandidateStatus.SENTIMENT_ANALYSIS:
            sen, conf, signals = _sentiment_bundle(
                i,
                rng,
                has_license=has_license,
                city_zone=city_zone,
                availability=availability,
                preferred=preferred,
                experience_years=experience_years,
                platforms=platforms,
                start_date=start_date,
            )
            db.add(
                SentimentResult(
                    conversation_id=conv.id,
                    sentiment=sen,
                    confidence=conf,
                    signals=signals,
                    model_version=MODEL_LABEL,
                )
            )
            breakdown["sentiment_analysis_with_row"] += 1

    return {
        "batch_id": batch_id,
        "inserted_candidates": count,
        "candidate_ids": candidate_ids,
        "breakdown": breakdown,
    }


def purge_simulation_seed_data(db: Session) -> Dict[str, Any]:
    """Delete rows created by :func:`seed_screening_simulation_batch`.

    Matches conversations with ``captured_data.simulation_batch`` and/or candidates whose
    email ends with ``@mock.orbio.test``. Also removes ``ranking_results`` for those
    candidate ids so FKs do not block deletion.
    """

    rows = db.execute(
        text("SELECT id, candidate_id FROM conversations WHERE captured_data ? 'simulation_batch'")
    ).mappings().all()

    conv_uuids: List[uuid.UUID] = []
    cand_from_conv: List[uuid.UUID] = []
    for r in rows:
        conv_uuids_uuid = r["id"]
        if not isinstance(conv_uuids_uuid, uuid.UUID):
            conv_uuids_uuid = uuid.UUID(str(conv_uuids_uuid))
        conv_uuids.append(conv_uuids_uuid)
        cid = r["candidate_id"]
        if cid is not None:
            if not isinstance(cid, uuid.UUID):
                cid = uuid.UUID(str(cid))
            cand_from_conv.append(cid)

    erows = db.execute(
        text("SELECT id FROM candidates WHERE email LIKE '%@mock.orbio.test'")
    ).mappings().all()
    cand_email: List[uuid.UUID] = []
    for r in erows:
        x = r["id"]
        cand_email.append(x if isinstance(x, uuid.UUID) else uuid.UUID(str(x)))

    all_cand_ids = list({*cand_from_conv, *cand_email})

    deleted_rr = 0
    if all_cand_ids:
        res = cast(
            CursorResult[Any],
            db.execute(delete(RankingResult).where(RankingResult.candidate_id.in_(all_cand_ids))),
        )
        deleted_rr = res.rowcount or 0

    deleted_sr = deleted_msg = deleted_conv = 0
    if conv_uuids:
        res = cast(
            CursorResult[Any],
            db.execute(delete(SentimentResult).where(SentimentResult.conversation_id.in_(conv_uuids))),
        )
        deleted_sr = res.rowcount or 0
        res = cast(
            CursorResult[Any],
            db.execute(delete(Message).where(Message.conversation_id.in_(conv_uuids))),
        )
        deleted_msg = res.rowcount or 0
        res = cast(
            CursorResult[Any],
            db.execute(delete(Conversation).where(Conversation.id.in_(conv_uuids))),
        )
        deleted_conv = res.rowcount or 0

    deleted_cand = 0
    if all_cand_ids:
        res = cast(
            CursorResult[Any],
            db.execute(delete(Candidate).where(Candidate.id.in_(all_cand_ids))),
        )
        deleted_cand = res.rowcount or 0

    db.commit()
    return {
        "deleted_ranking_results": deleted_rr,
        "deleted_sentiment_results": deleted_sr,
        "deleted_messages": deleted_msg,
        "deleted_conversations": deleted_conv,
        "deleted_candidates": deleted_cand,
        "seed_conversations_matched": len(conv_uuids),
        "seed_candidates_matched": len(all_cand_ids),
    }
