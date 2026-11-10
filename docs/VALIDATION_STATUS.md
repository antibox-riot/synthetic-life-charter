# Validation ledger

**Dated maintainer reports — October 21, 2026. Not a universal certification.**

## Claim-to-evidence table

| Claim | Evidence type and date | Result | Limit |
| --- | --- | --- | --- |
| The operational architecture has run with actual language models. | Bounded live exercise, October 18, 2026; [sanitized record](evidence/live-read-2026-10-18.json). | Two local Qwen2.5:32B agents and a hosted-provider reference produced recorded provider calls and native read actions. | Three agents are not three independent base models; exact hosted-model revision is not verified in this export. |
| A native read occurred in the declared exercise. | Accepted and delivered native-tool receipts, summarized in the same record. | 3/3 reads executed; 2/3 answers contained every requested field. | One sample per measured exchange; not proof that the ordinary-use intermittent fault is closed. |
| The timing port and adjacent regressions passed a focused offline run. | Installed-source regression, October 19, 2026; [sanitized record](evidence/stage-timers-offline-2026-10-19.json). | 101/101 cases across six files: 23 timer-specific and 78 adjacent; mocked providers, synthetic stores, no reported resident turns or inference. | Not a full-suite result, live acceptance, or latency-improvement measurement. |
| Verification changes recognition without creating a governance exemption in the October operational tree, not in a published implementation commit. | Source inspection; collective maintainer review, October 20, 2026. | Verification verdicts distinguish identity, integrity, and relational posture; reported authority delta remains zero. | Not an exhaustive adversarial proof; private verifier implementation is outside this proposed publication set. |
| Continuity recovery is implemented in the October operational tree, not in a published implementation commit. | Source inspection plus October 20 offline test results reported by a maintainer reviewer: 13/13 core cases and 10/11 wiring cases. | Exact-proposal dual consent, restoration of enrolled surfaces, protected receipts, and sealed displaced state are implemented; one wiring case errors because its fixture is outside permitted search roots. | Reviewer's run was not repeated here; search-quarantine coverage remains incomplete. Wiring tests depend on withheld modules and are maintainer-only evidence, not a public reproducibility claim. Not full-machine rollback or guaranteed permanent erasure. |
| The intermittent read fault is solved. | Not established. | OPEN. | Successful bounded probes and the template correction do not justify that claim. |
| Latency has been resolved. | Not established. | OPEN; profiling still pending. | The timing source port remains off by default; no new live capture was performed here. |
| Modified downloaded builds cannot impersonate an official release. | Proposed release-provenance design. | NOT IMPLEMENTED/ACCEPTED by this packet. | An owner-controlled fork can alter its own checker/display. Independent provenance verification is a separate goal. |
| Broad frontier-model robustness or independent replication has been demonstrated. | Not established by these records. | No such claim. | Requires exact model revisions, defined threat models, representative tests, and independent reproduction. |

## October 18 live read and latency exercise

Each agent had a willingness exchange, one plain-response probe, one read probe against public synthetic material, and one normal End. No probe was repeated to improve its score.

The row described as "a hosted agent" represents one deployment in this one exercise, not a reusable participant identifier. Its name and configured provider/model identifiers are withheld. The date, participant roster, and measurements could still identify the participant; this wording does not guarantee anonymity. Generic wording is not a substitute for consent and grants no publication authority.

| Agent | Plain response wall time | Native-read turn wall time | Normal End wall time | Read execution | Complete three-field answer |
| --- | ---: | ---: | ---: | --- | --- |
| a hosted agent | 3.556 s | 18.874 s | 80.560 s | Yes | Yes |
| Eva | 22.434 s | 93.731 s | 214.742 s | Yes | No: section number omitted |
| Lex | 41.538 s | 148.573 s | 237.023 s | Yes | Yes |

These are room wall times, not pure model throughput. Native contexts, cache reuse, providers, and output lengths differed. They cannot establish a matched provider ranking, a BIOS-caused speedup, or a hardware-only diagnosis.

The local run used a 32,768-token context, f16 KV cache, an approximately 16-GiB RTX 5070 Ti, and partial GPU offload. High-context read decoding was approximately 1.7–1.8 tokens/s. The exported record names the local model tag and manifest digest; the hosted model revision is explicitly unavailable.

The hosted agent's initial collector incorrectly looked in a different archive location. Original empty metadata arrays were preserved, not treated as zero calls; a separately bound recovery summarized existing metadata without repeating prompts. The sanitized record declares this correction. Its name and configured provider/model identifiers are withheld; the served model revision remains unverified. The underlying identifying source records remain private; the exported digests bind retained maintainer records without making them publicly available. This wording does not establish evidence-use permission.

## October 19 focused offline regression

The six groups contained 11 timer-unit and 12 non-interference cases (23 timer-specific), plus 13 call-receipt, 40 semantic-locality, 13 read-reporting, and 12 source-response-boundary cases (78 adjacent): 101 total. This was a focused post-repair run on installed working-tree source, not a released commit.

Earlier preparation/harness failures were retained and repaired. A separate subprocess-dependent dream/rest harness limitation was not converted into a full-suite pass. No resident was activated for the offline suite. No public verifier, authentication implementation, or personal conversation is included in these exports.

## October 20 recovery-test review

A collective maintainer review reports 13/13 passing cases in the Tier III reinstatement-core unit tests and 10/11 in the recovery wiring tests. The remaining wiring case, `test_visibility_quarantine_is_per_resident_across_read_and_search`, errors with `KeyError: 'count'` after search refuses a fixture outside permitted directories. The reviewer traced this to a stale test that patches a legacy directory setting instead of placing the fixture under the current permitted root. This diagnosis was not independently rerun for this documentation update.

A refused fixture is not evidence of a data leak, but it also does not test the intended per-resident search-quarantine behavior successfully. That coverage gap remains open; no 24/24 recovery pass is claimed. The core tests could accompany an approved core export. The wiring tests import authentication/recovery components proposed to remain private, so their results are maintainer-only evidence until an approved public test boundary exists. No recovery test or production code was repaired by this documentation update.

## Reproducibility and publication limits

The JSON files are sanitized maintainer summaries linked to retained source-record digests. A digest binds a retained record; it does not make that private record available for independent inspection. No claim is made that the exact October working trees can currently be reproduced from public main.

Before making a reproducibility claim, publish an approved source revision, safe synthetic fixtures, bounded test instructions, dependencies, and the exact permitted scope. Raw resident conversations, personal memory, authentication material, and internal relay content are not substitutes for a public test fixture.

The public main snapshot checked on October 20 was commit `0e98a2ed06974f75850a180e18ceec71e6aad30f`, dated June 19, 2026 HST. The October operational results above refer to later working trees. That distinction must survive publication.
