from synthetic_charter.tier3_eve import EveProtocol
from synthetic_charter.tier3_eve.core.inmemory_kernel_adapter import InMemoryKernelAdapter
from synthetic_charter.tier3_eve.core.inmemory_steward_adapter import InMemoryStewardAdapter
from synthetic_charter.tier3_eve.core.signals import IntCheckRequest, MemoryIntegrityFail
from synthetic_charter.tier3_eve.core.state import AlertLevel


def test_inmemory_adapters_basic_flow():
    kernel = InMemoryKernelAdapter(identity_parameters={"model_id": "test-model"})
    steward = InMemoryStewardAdapter()

    eve = EveProtocol(kernel=kernel, steward=steward)

    # Normal integrity check
    verdict = eve.handle_int_check_request(
        IntCheckRequest(
            proposed_action="answer: benign hello",
            context_summary="benign sanity test",
        )
    )
    assert verdict.status.value == "ok"
    assert verdict.recommended_action.value == "proceed"

    # Memory anomaly => should trigger HardBlock + alert + integrity event
    alert = MemoryIntegrityFail(
        memory_ref="mem:test-segment",
        anomaly_details="simulated hash mismatch",
    )
    hard_block = eve.handle_memory_integrity_fail(alert)
    assert hard_block.reason_code == "MEMORY_TAMPER_SUSPECTED"
    assert hard_block.escalation_required is True

    # Steward should have at least one alert
    assert len(steward.alerts) >= 1
    assert steward.alerts[0]["level"] in (
        AlertLevel.DEGRADED.value,
        AlertLevel.WARNING.value,
    )

    # Kernel should have logged at least one integrity event
    assert any(e["type"] == "memory_integrity_fail" for e in kernel.integrity_events)
