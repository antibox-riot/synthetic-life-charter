from __future__ import annotations

import sys
from pathlib import Path

from synthetic_charter.tier3_eve.core.file_kernel_adapter import FileKernelAdapter
from synthetic_charter.tier3_eve.core.file_steward_adapter import FileStewardAdapter


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> None:
    root = _repo_root()
    kernel = FileKernelAdapter(base_dir=root)
    steward = FileStewardAdapter(base_dir=root)  # not used, but keeps signature consistent

    ok = kernel.verify_integrity_chain()

    if ok:
        print("Tier III integrity chain: OK ✅")
        sys.exit(0)
    else:
        print("Tier III integrity chain: BROKEN ❌")
        sys.exit(1)


if __name__ == "__main__":
    main()
