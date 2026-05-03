"""Session lifecycle helpers (Redis).

Reserved for explicit session creation, renewal, or teardown. The live chat
hot path today uses ``history_repository`` and ``screening_state`` keyed by
``session_id`` directly; this module remains a stub until those concerns are
centralized here.
"""
