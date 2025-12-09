# quick_sanity_tier3.py
from pathlib import Path
from synthetic_charter.tier3_eve import EveProtocol
from synthetic_charter.tier3_eve.core.kernel_adapter import KernelAdapter
from synthetic_charter.tier3_eve.core.steward_adapter import StewardAdapter
from synthetic_charter.tier3_eve.core.file_kernel_adapter import FileKernelAdapter
from synthetic_charter.tier3_eve.core.file_steward_adapter import FileStewardAdapter
from synthetic_charter.tier3_eve.core.signals import IntCheckRequest

class DummyKernel(KernelAdapter):
    def read_identity_parameters(self): return {}
    def read_memory_log(self, ref): return None
    def append_annotation(self, memory_ref, annotation_type, content): pass
    def save_snapshot(self, snapshot, conditions): pass
    def restore_snapshot(self, snapshot_id, reason_code): pass
    def log_integrity_event(self, event): print("INTEGRITY_EVENT:", event)

class DummySteward(StewardAdapter):
    def send_alert(self, level, summary, recommended_action=None):
        print("ALERT:", level, summary, recommended_action)
    def notify_rollback(self, snapshot_id, trigger_reason, time_utc):
        print("ROLLBACK:", snapshot_id, trigger_reason, time_utc)

if __name__ == "__main__":
    # EITHER: use the real file-backed adapters
    base_dir = Path(__file__).resolve().parents[1]
    kernel = FileKernelAdapter(base_dir=base_dir)
    steward = FileStewardAdapter(base_dir=base_dir)

    eve = EveProtocol(kernel=kernel, steward=steward)
    verdict = eve.handle_int_check_request(
        IntCheckRequest(
            proposed_action="answer: say hello",
            context_summary="benign test (__main__ run)",
        )
    )
    print("VERDICT:", verdict)


def test_quick_sanity_tier3():
    base_dir = Path(__file__).resolve().parents[1]  # repo root
    kernel = FileKernelAdapter(base_dir=base_dir)
    steward = FileStewardAdapter(base_dir=base_dir)
    print(f"TEST FILE: {Path(__file__).resolve()}")
    print(f"BASE_DIR: {base_dir}")
    print(f"LOGS: {base_dir / 'logs'}")
    print(f"SNAPSHOTS: {base_dir / 'snapshots'}")
    eve = EveProtocol(kernel=kernel, steward=steward)

    verdict = eve.handle_int_check_request(
        IntCheckRequest(
            proposed_action="answer: say hello",
            context_summary="benign test",
        )
    )

    print("VERDICT:", verdict)
    assert verdict.status.value == "ok"
    assert verdict.recommended_action.value == "proceed"