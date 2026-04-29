# Grupo Sazon - Delivery Driver Job Description

## 1) Role Summary

**Position:** Delivery Driver (Repartidor/a)  
**Company:** Grupo Sazon (fictional client)  
**Markets:** Spain and Mexico  
**Hiring context:** High-volume recruiting (~200 applications/week) across 45 locations.

The role is responsible for timely, safe, and reliable order delivery from restaurant locations to customers. Drivers are expected to follow assigned shifts, comply with local traffic and safety regulations, and maintain professional communication with store staff and customers.

---

## 2) Main Responsibilities

- Pick up and deliver orders on time according to assigned route/zone.
- Follow safety and compliance rules for driving and food handling.
- Maintain clear communication during active shifts.
- Resolve basic delivery incidents (delays, wrong address, unavailable customer) following standard process.
- Keep reliability standards (attendance, punctuality, low no-show rate).

---

## 3) Mandatory Requirements (Hard Filters)

These are required to continue in screening:

1. **Valid driver's license:** candidate must confirm `yes`.
2. **Service area match:** candidate city/zone must be inside Grupo Sazon service areas.
3. **Consent for data processing:** candidate must explicitly consent before PII storage.

> Important for this project: **no license images are collected or stored** at this stage.  
Only a chat-based yes/no confirmation is captured.

---

## 4) Non-Mandatory (Preferred) Requirements

These improve ranking priority but are not absolute disqualifiers:

- Prior delivery experience (years and platforms such as Uber Eats, Rappi, Glovo, DiDi, Stuart).
- Availability aligned with operational gaps (night/weekend coverage).
- Earlier start date (short time-to-start).
- Higher reliability signals (historical attendance, consistency, references if available).
- Flexibility in schedule.

---

## 5) Structured Data Collected in Screening

- `full_name`
- `drivers_license` (boolean)
- `city`
- `zone` (optional)
- `availability` (`full_time | part_time | weekends`)
- `preferred_schedule` (`morning | afternoon | evening | flexible`)
- `experience_years`
- `platforms`
- `start_date`
- `consent`
- `language` (`es-ES | es-MX | en`)
- `session_id` (conversation continuity key)

---

## 6) Qualification Outcomes

- **Hard disqualified:** no license or outside service area.
- **Soft disqualified:** partial mismatch (e.g., schedule/start-date constraints), can be re-evaluated.
- **Qualified:** passes required filters and has complete core data.
- **Qualified with flags:** qualified but with uncertain fields or frustration/confusion signals; routed for recruiter review.

---

## 7) Ranking Logic (Post-Qualification)

For qualified candidates, prioritization uses:

- **Listwise LLM comparisons** on candidate subsets.
- **Plackett-Luce aggregation** to estimate stable utilities and produce global ranking.

Why this approach:
- Fixed weight formulas can become brittle when weekly operational urgency changes.
- Listwise + Plackett-Luce adapts better to context (critical shifts, start window, vacancy urgency).

---

## 8) Candidate Communication Guidelines

- Messaging channel first (web chat), voice optional extension.
- 1-3 short sentences per turn.
- One question per turn (except recap).
- Neutral, professional tone; avoid slang.
- Multi-language support (ES/EN) with code-switch handling.

---

## 9) Additional Project-Relevant Notes

### Storage and runtime
- **Redis:** hot-path session state and short-term history (keyed by `session_id`, TTL enabled).
- **PostgreSQL:** durable conversations, messages, candidate records, jobs, sentiment, ranking outputs.

### Security and safety
- Reflection/guardrail layer checks prompt injection patterns before final assistant response.
- System prompt leakage and role hijacking attempts are blocked and logged as security events.

### Analytics and operations
- Dashboard metrics should include completion rate, drop-off stage, average duration, qualified rate, and ranking funnel quality.
- Worker jobs handle sentiment analysis and ranking asynchronously.

---

## 10) Suggested Recruiter Handoff Payload

At handoff, include:

- Candidate profile snapshot (all validated fields).
- Conversation summary.
- Qualification status and reason codes.
- Ranking position + confidence signals.
- Flags (uncertain slots, sentiment risk, security anomalies if any).

