from agent.memory.event_store import EventStore, MissionEvent


def test_event_store_starts_empty():
    store = EventStore()

    assert store.count() == 0
    assert store.get_all() == []
    assert store.get_latest() is None


def test_event_can_be_recorded():
    store = EventStore()

    event = store.record(
        step_id="S001",
        activity="CHECK_EQUIPMENT",
        detected_object="experiment_controller",
        confidence=0.57,
        status="DEVIATION",
        deviation="WRONG_OBJECT",
        guidance="Wrong object detected.",
    )

    assert isinstance(event, MissionEvent)
    assert event.step_id == "S001"
    assert event.activity == "CHECK_EQUIPMENT"
    assert event.detected_object == "experiment_controller"
    assert event.confidence == 0.57
    assert event.status == "DEVIATION"
    assert event.deviation == "WRONG_OBJECT"


def test_events_are_kept_in_chronological_order():
    store = EventStore()

    store.record(
        step_id="S001",
        activity="CHECK_EQUIPMENT",
        detected_object="experiment_container",
        confidence=0.91,
        status="CORRECT",
    )

    store.record(
        step_id="S002",
        activity="RETRIEVE_SAMPLE",
        detected_object="wrong_object",
        confidence=0.88,
        status="DEVIATION",
        deviation="WRONG_OBJECT",
        guidance="Select the biological sample.",
    )

    events = store.get_all()

    assert len(events) == 2
    assert events[0].step_id == "S001"
    assert events[1].step_id == "S002"


def test_latest_event():
    store = EventStore()

    store.record(
        step_id="S001",
        activity="CHECK_EQUIPMENT",
        detected_object="experiment_container",
        confidence=0.91,
        status="CORRECT",
    )

    store.record(
        step_id="S002",
        activity="RETRIEVE_SAMPLE",
        detected_object=None,
        confidence=0.20,
        status="UNCERTAIN",
        deviation="LOW_CONFIDENCE",
    )

    latest = store.get_latest()

    assert latest is not None
    assert latest.step_id == "S002"
    assert latest.status == "UNCERTAIN"


def test_clear_removes_events():
    store = EventStore()

    store.record(
        step_id="S001",
        activity="CHECK_EQUIPMENT",
        detected_object="experiment_container",
        confidence=0.91,
        status="CORRECT",
    )

    assert store.count() == 1

    store.clear()

    assert store.count() == 0
    assert store.get_latest() is None


def test_history_is_bounded_but_lifetime_counts_are_preserved():
    store = EventStore(max_events=2)
    for status in ("CORRECT", "DEVIATION", "UNCERTAIN"):
        store.record(
            step_id="S001",
            activity="CHECK_EQUIPMENT",
            detected_object=None,
            confidence=None,
            status=status,
        )

    assert len(store.get_all()) == 2
    assert store.count() == 3
    assert store.get_counts() == {"CORRECT": 1, "DEVIATION": 1, "UNCERTAIN": 1}