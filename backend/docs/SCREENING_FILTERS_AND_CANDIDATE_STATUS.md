# Screening Filters and Candidate Status

This document summarizes what the **first conversational agent** should collect, what is mandatory for the first hard filter, the filter phases, and candidate status definitions.

Based on:
- `FDE_Technical_Assignment.md`
- `Phase1_Conversation_Design.md`
- `Ranking_Repartidores_Listwise_vs_Weights.md`

---

## 1) Data the first conversational agent should capture

- `session_id` (conversation continuity key)
- `full_name`
- `consent` (data-processing consent)
- `drivers_license` (yes/no)
- `city`
- `zone` (if applicable)
- `availability` (`full_time` | `part_time` | `weekends`)
- `preferred_schedule` (`morning` | `afternoon` | `evening` | `flexible`)
- `experience_years`
- `platforms` (Glovo, Uber Eats, Rappi, DiDi, Stuart, etc.)
- `start_date`
- `language` (`es-ES` | `es-MX` | `en`, detected per turn)
- operational flags: `slot_uncertain`, `nudge_count`, `last_seen_at`

---

## 2) Mandatory data for the first hard filter

To pass the initial hard gate:

1. `consent = true`
2. `drivers_license = true`
3. `city` is within `service_areas`
4. `full_name` is present

If any of these fail, the candidate should not continue to normal qualification flow.

---

## 3) Non-mandatory data (still important)

These fields are not strict blockers for the first gate but are important for downstream prioritization:

- `zone` (optional in many cases)
- `preferred_schedule`
- `experience_years`
- `platforms`
- `start_date`
- optional reliability/context signals

Missing values may continue with uncertainty flags and human-review routing when needed.

---

## 4) Filter phases

### Phase 0 — Opening and consent
- Bot disclosure
- Capture `consent`
- Detect initial language

### Phase 1 — Hard filters (CP-1)
- Driver's license check
- Service-area check (city/zone)
- Outcome: pass, hard disqualify, or waitlist

### Phase 2 — Operational data capture
- Availability
- Preferred schedule
- Experience and platforms
- Start date

### Phase 3 — Validation and close (CP-2)
- Recap captured data
- Resolve ambiguous fields where possible
- Confirm final screening snapshot

### Phase 4 — Post-screening processing
- Enqueue sentiment job
- Enqueue ranking job
- Qualified candidates enter Listwise + Plackett-Luce prioritization

---

## 5) Candidate status definitions

- `new` — candidate record created, not yet progressed.
- `in_progress` — screening conversation active.
- `hard_disq` — failed hard filter (no license or outside coverage).
- `waitlist` — currently outside coverage but eligible for future openings.
- `soft_disq` — not a current fit (e.g., schedule/start-date mismatch), re-evaluable.
- `qualified` — passes hard filters and has required screening data.
- `qualified_flagged` — qualified with uncertainty/risk flags (e.g., `slot_uncertain`, frustration).
- `abandoned` — candidate stopped responding after re-engagement sequence.

---

## 6) Why this structure fits the project

- Keeps the first gate deterministic and auditable.
- Separates hard eligibility from ranking preference.
- Supports multilingual, messaging-first flow with partial/uncertain data handling.
- Produces clean status transitions for analytics and recruiter handoff.
