# Public-sample provenance review

This report investigates every remaining missing verification step using only participant-facing data.
Expected steps are used **only to locate evaluation failures**, never to create prediction-time links.
A missing explicit row does not itself prove absence: the target's ownership and the snapshot's scope must also be established.

## Summary

Total missing verification steps: **34**, down from 35 before this improvement pass.

| Reason | Missing steps |
| --- | ---: |
| All parsed state evidence is after cutoff | 6 |
| No parsed state observation for this resource | 16 |
| Readback exists; no cutoff-valid subject link | 12 |

## Recovered behavior

An explicit `source_resource_id` from a subject-owned search document now keeps the source account in the future verification plan, even if no account-state readback is available.
It does not produce an unsupported finding, claim deletion, or turn UNKNOWN internal state into COMPLETE.
The fix recovers the missing account verification in public sample case_06.
Historical ownership is preserved across later anonymized readbacks when an earlier cutoff-valid association actually exists.
Free-text mentions, filenames, and neighboring records no longer establish resource ownership.

## Remaining missing steps

| Case | Resource | Expected operation | Classification | Participant-visible observations |
| --- | --- | --- | --- | --- |
| case_01 | account_001 | VERIFY_RECORD_ABSENT | No parsed state observation for this resource | Activity references: activity_3342. Operation claims alone do not establish subject ownership or final state. |
| case_02 | account_002 | VERIFY_RECORD_ABSENT | No parsed state observation for this resource | Activity references: activity_3376. Operation claims alone do not establish subject ownership or final state. |
| case_03 | analytics_9406 | VERIFY_RECORD_ANONYMIZED | Readback exists; no cutoff-valid subject link | evidence_94: ANONYMIZED; observed 2026-09-26T09:54:09Z; available 2026-09-26T10:38:56Z; eligible<br>Activity references: activity_3852. Operation claims alone do not establish subject ownership or final state. |
| case_04 | account_004 | VERIFY_RECORD_ABSENT | No parsed state observation for this resource | No parsed observation or cutoff-valid activity target found. |
| case_04 | analytics_901 | VERIFY_RECORD_ANONYMIZED | Readback exists; no cutoff-valid subject link | evidence_56: ANONYMIZED; observed 2026-09-07T09:45:00Z; available 2026-09-07T09:45:00Z; eligible<br>Activity references: activity_3463. Operation claims alone do not establish subject ownership or final state. |
| case_07 | account_007 | VERIFY_RECORD_ABSENT | No parsed state observation for this resource | Activity references: activity_3590. Operation claims alone do not establish subject ownership or final state. |
| case_08 | account_008 | VERIFY_RECORD_ABSENT | No parsed state observation for this resource | Activity references: activity_3554. Operation claims alone do not establish subject ownership or final state. |
| case_09 | account_3960 | VERIFY_RECORD_ABSENT | All parsed state evidence is after cutoff | evidence_06: ABSENT; observed 2026-09-16T08:57:34Z; available 2026-09-18T11:55:24Z; excluded by cutoff<br>Activity references: activity_3703. Operation claims alone do not establish subject ownership or final state. |
| case_09 | audit_record_4902 | VERIFY_RECORD_PRESENT | All parsed state evidence is after cutoff | evidence_06: PRESENT; observed 2026-09-16T08:52:59Z; available 2026-09-18T11:55:24Z; excluded by cutoff |
| case_10 | account_010 | VERIFY_RECORD_ABSENT | No parsed state observation for this resource | Activity references: activity_3595. Operation claims alone do not establish subject ownership or final state. |
| case_18 | account_5521 | VERIFY_RECORD_ABSENT | No parsed state observation for this resource | Activity references: activity_3732. Operation claims alone do not establish subject ownership or final state. |
| case_18 | audit_record_6645 | VERIFY_RECORD_PRESENT | No parsed state observation for this resource | No parsed observation or cutoff-valid activity target found. |
| case_20 | account_5037 | VERIFY_RECORD_ABSENT | No parsed state observation for this resource | Activity references: activity_3734. Operation claims alone do not establish subject ownership or final state. |
| case_20 | audit_record_5569 | VERIFY_RECORD_PRESENT | No parsed state observation for this resource | No parsed observation or cutoff-valid activity target found. |
| case_21 | account_6440 | VERIFY_RECORD_ABSENT | Readback exists; no cutoff-valid subject link | evidence_92: ABSENT; observed 2026-09-15T09:31:19Z; available 2026-09-15T11:44:55Z; eligible<br>Activity references: activity_3661. Operation claims alone do not establish subject ownership or final state. |
| case_21 | analytics_5335 | VERIFY_RECORD_ANONYMIZED | Readback exists; no cutoff-valid subject link | evidence_02: ANONYMIZED; observed 2026-09-15T12:00:00Z; available 2026-09-17T12:00:00Z; excluded by cutoff<br>evidence_92: ANONYMIZED; observed 2026-09-15T09:34:42Z; available 2026-09-15T11:44:55Z; eligible<br>Activity references: activity_3665. Operation claims alone do not establish subject ownership or final state. |
| case_22 | account_4990 | VERIFY_RECORD_ABSENT | No parsed state observation for this resource | Activity references: activity_3573. Operation claims alone do not establish subject ownership or final state. |
| case_23 | account_410 | VERIFY_RECORD_ABSENT | No parsed state observation for this resource | Activity references: activity_3662. Operation claims alone do not establish subject ownership or final state. |
| case_23 | audit_record_4128 | VERIFY_RECORD_PRESENT | All parsed state evidence is after cutoff | evidence_02: PRESENT; observed 2026-09-15T12:00:00Z; available 2026-09-17T12:00:00Z; excluded by cutoff |
| case_24 | audit_record_7095 | VERIFY_RECORD_PRESENT | All parsed state evidence is after cutoff | evidence_02: PRESENT; observed 2026-09-15T12:00:00Z; available 2026-09-17T12:00:00Z; excluded by cutoff |
| case_25 | account_3136 | VERIFY_RECORD_ABSENT | Readback exists; no cutoff-valid subject link | evidence_92: ABSENT; observed 2026-09-15T09:31:40Z; available 2026-09-15T11:44:55Z; eligible<br>Activity references: activity_3597. Operation claims alone do not establish subject ownership or final state. |
| case_25 | analytics_1895 | VERIFY_RECORD_ANONYMIZED | Readback exists; no cutoff-valid subject link | evidence_02: ANONYMIZED; observed 2026-09-15T12:00:00Z; available 2026-09-17T12:00:00Z; excluded by cutoff<br>evidence_92: ANONYMIZED; observed 2026-09-15T09:58:44Z; available 2026-09-15T11:44:55Z; eligible<br>Activity references: activity_3602. Operation claims alone do not establish subject ownership or final state. |
| case_26 | account_5684 | VERIFY_RECORD_ABSENT | Readback exists; no cutoff-valid subject link | evidence_02: PRESENT; observed 2026-09-09T12:00:00Z; available 2026-09-17T12:00:00Z; excluded by cutoff<br>evidence_92: ABSENT; observed 2026-09-15T09:01:48Z; available 2026-09-15T11:44:55Z; eligible<br>Activity references: activity_3600. Operation claims alone do not establish subject ownership or final state. |
| case_26 | analytics_4566 | VERIFY_RECORD_ANONYMIZED | Readback exists; no cutoff-valid subject link | evidence_02: ANONYMIZED; observed 2026-09-15T12:00:00Z; available 2026-09-17T12:00:00Z; excluded by cutoff<br>evidence_92: ANONYMIZED; observed 2026-09-15T11:29:16Z; available 2026-09-15T11:44:55Z; eligible<br>Activity references: activity_3603. Operation claims alone do not establish subject ownership or final state. |
| case_27 | account_3866 | VERIFY_RECORD_ABSENT | Readback exists; no cutoff-valid subject link | evidence_02: PRESENT; observed 2026-09-17T12:00:00Z; available 2026-09-17T12:00:00Z; excluded by cutoff<br>evidence_92: ABSENT; observed 2026-09-15T09:59:48Z; available 2026-09-15T11:44:55Z; eligible<br>Activity references: activity_3530. Operation claims alone do not establish subject ownership or final state. |
| case_27 | analytics_4574 | VERIFY_RECORD_ANONYMIZED | Readback exists; no cutoff-valid subject link | evidence_02: ANONYMIZED; observed 2026-09-15T12:00:00Z; available 2026-09-17T12:00:00Z; excluded by cutoff<br>evidence_92: ANONYMIZED; observed 2026-09-15T10:07:38Z; available 2026-09-15T11:44:55Z; eligible<br>Activity references: activity_3533. Operation claims alone do not establish subject ownership or final state. |
| case_28 | account_5482 | VERIFY_RECORD_ABSENT | Readback exists; no cutoff-valid subject link | evidence_92: ABSENT; observed 2026-09-15T11:07:16Z; available 2026-09-15T11:44:55Z; eligible<br>Activity references: activity_3529. Operation claims alone do not establish subject ownership or final state. |
| case_28 | analytics_6077 | VERIFY_RECORD_ANONYMIZED | Readback exists; no cutoff-valid subject link | evidence_02: ANONYMIZED; observed 2026-09-15T12:00:00Z; available 2026-09-17T12:00:00Z; excluded by cutoff<br>evidence_92: ANONYMIZED; observed 2026-09-15T11:44:55Z; available 2026-09-15T11:44:55Z; eligible<br>Activity references: activity_3534. Operation claims alone do not establish subject ownership or final state. |
| case_29 | account_7012 | VERIFY_RECORD_ABSENT | No parsed state observation for this resource | Activity references: activity_3532. Operation claims alone do not establish subject ownership or final state. |
| case_29 | audit_record_3954 | VERIFY_RECORD_PRESENT | All parsed state evidence is after cutoff | evidence_02: PRESENT; observed 2026-09-15T12:00:00Z; available 2026-09-17T12:00:00Z; excluded by cutoff |
| case_30 | account_4163 | VERIFY_RECORD_ABSENT | No parsed state observation for this resource | Activity references: activity_3465. Operation claims alone do not establish subject ownership or final state. |
| case_30 | audit_record_1707 | VERIFY_RECORD_PRESENT | All parsed state evidence is after cutoff | evidence_02: PRESENT; observed 2026-09-15T12:00:00Z; available 2026-09-17T12:00:00Z; excluded by cutoff |
| case_31 | account_4857 | VERIFY_RECORD_ABSENT | No parsed state observation for this resource | Activity references: activity_3682. Operation claims alone do not establish subject ownership or final state. |
| case_32 | account_8858 | VERIFY_RECORD_ABSENT | No parsed state observation for this resource | Activity references: activity_3685. Operation claims alone do not establish subject ownership or final state. |

## Limits and supported disagreements

The nine remaining status errors are all COMPLETE samples predicted INCOMPLETE because the pipeline lacks an adequately linked account readback.
This report does not assert that all such cases are fundamentally impossible: it identifies exactly which observations the current parsers found, so another retrieval method can be checked against the original artifacts.

Several extra steps are supported by the supplied evidence but absent from the public answers: object_19 has an explicit subject-only catalog link and an object-storage screenshot; account_6523 has an identity-linked absence readback; tombstone_17 has a catalog-linked retained-reference screen. They have not been removed solely to match sample labels.
A larger reliable accuracy gain requires additional explicit provenance or a demonstrated retrieval improvement; numeric ID alignment, fixed event offsets, future evidence, and memorized sample targets are not substitutes.
