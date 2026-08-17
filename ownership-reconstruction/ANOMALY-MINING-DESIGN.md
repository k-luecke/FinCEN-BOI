# Anomaly-mining design (leads engine)

Status: **design, not yet built.** Scheduled after DOJ challenge-aware
recovery lands (cross-source overlap is what most detectors need).
Anomalies produce **leads for document review, never accusations**; the
hypothesis is that consequential information is public but structurally
obscure — no individual piece hidden, the connection simply hard to see.

## Detectors

1. **Public-record contradictions** — two independent sources make
   incompatible ownership/control claims about the same entity during
   overlapping periods.
2. **Unexplained disappearance** — a repeatedly disclosed relationship
   vanishes without an observed sale, merger, dissolution, rename,
   threshold change, or successor.
3. **Cross-agency convergence** — the same person/entity/network
   independently appears in SEC, DOJ, Treasury/OFAC, banking-regulator,
   Congressional, or court material.
4. **Role migration** — the same person moves owner → officer →
   manager → related entity across a connected group, especially where
   the entities themselves change names.
5. **Circular structures** — ownership/control cycles (A→B→C→A).
6. **Ownership/control discontinuities** — A owns X → B owns X → A
   owns X, or rapid changes over short intervals.
7. **Shell-network topology** — many entities sharing few controllers,
   agents, addresses, or counterparties. Shared addresses alone stay
   weak; combinations of independent signals become interesting.
8. **Financial-flow / ownership intersection** — do named
   senders/recipients in flow observations intersect the ownership
   graph? The underlying document must establish the transaction.
9. **Enforcement before/after** — publicly disclosed structure before
   an enforcement event vs after.
10. **Repeatedly amended ownership** — unusually frequent 13D/G
    amendments where percentages, group membership, or control
    language materially changes.
11. **Disclosure lag** — valid_from/event_date vs
    source_date/publication_date outliers (accounting for filing
    rules and amendment conventions).
12. **Orphan intermediaries** — entities existing almost entirely to
    connect a person to another company/property/account, with little
    independent footprint in the corpus.
13. **Historical-name joins** — once state corporate records arrive:
    current name ← former name ← earlier filing ← subsidiary ← person,
    reconnecting records keyword search would never associate.

## Scoring: REVIEW_PRIORITY (never a suspicion score)

Positive: cross-agency sources · independent documents · explicit
ownership/control assertions · temporal inconsistency · unexplained
structural change · financial-flow intersection · enforcement
intersection · historical-name connection · high network centrality.

Negative: same-document repetition · same-agency repetition ·
unresolved identity · weak relationship type · obvious corporate
succession · known reporting-rule explanation.

## Self-disproof requirement

Every generated lead must contain both sides: *why this is unusual*
AND *plausible ordinary explanations to eliminate first*. A
disappearing beneficial owner is auto-checked against later 13D/G
amendments, acquisitions, renames, dissolutions, threshold changes,
and entity-resolution candidates before it may surface. Only
unexplained cases survive.

## Calibration set

The BMO succession (Bank of Montreal → Bankmont 1996–1998 → Nesbitt
Burns 1999–2003 → BMO Nesbitt Burns 2003–2012, then disappearance)
should initially trigger disappearance/discontinuity detectors and
then be **downgraded automatically** because subsequent records
explain the succession. That behavior is the acceptance test before
trusting the system on less obvious cases.

## Order of evidence

Let the evidence determine which networks are unusual rather than
starting from a name and searching for something incriminating —
this reduces confirmation bias and is the condition under which a
surviving lead means something.
