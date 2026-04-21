from packs.orchestrator.router import route_for_confidence


def test_route_thresholds():
    assert route_for_confidence(0.9).tier == "T0"
    assert route_for_confidence(0.7).tier == "T1"
    assert route_for_confidence(0.2).tier == "T1"

