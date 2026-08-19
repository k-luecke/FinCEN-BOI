#!/usr/bin/env python3
"""
Recovery metrics and report.

Pure function of committed recovery state (challenge observations,
recovery links, queues) — safe to re-run anytime. Produces:

    recovery/unresolved-challenges.jsonl
    recovery/metrics.json
    RECOVERY-REPORT.md

Coverage semantics: requested-URL coverage and document-identity
coverage are reported separately. A challenged URL may remain
unresolved while its underlying document is fully preserved from an
official mirror — and a BOT_CHALLENGE capture is never counted as
ARCHIVED_CONTENT.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

DIRECT_RELATIONSHIPS = {"SAME_DOCUMENT", "OFFICIAL_MIRROR"}
ARCHIVE_RELATIONSHIP = "ARCHIVED_VERSION"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def coverage_state(observation: dict, links_by_url: dict) -> str:
    """Coverage state for one challenged URL."""
    url = observation["url"]
    links = links_by_url.get(url, [])
    best = None
    for link in links:
        if not link.get("retrieved_sha256"):
            continue
        if link["relationship"] in DIRECT_RELATIONSHIPS:
            return (
                "ARCHIVED_CONTENT"
                if link["relationship"] == "SAME_DOCUMENT"
                and link.get("alternate_url") == url
                else "RECOVERED_OFFICIAL_MIRROR"
            )
        if link["relationship"] == ARCHIVE_RELATIONSHIP:
            best = "RECOVERED_WEB_ARCHIVE"
    if best:
        return best
    status = observation.get("http_status")
    if status in (401, 403) and observation["classification"] == \
            "ERROR_RESPONSE":
        return "ACCESS_RESTRICTED"
    if observation["classification"] in (
        "BOT_CHALLENGE", "ACCESS_INTERSTITIAL", "APPLICATION_SHELL",
    ):
        return "UNRESOLVED_CHALLENGE"
    return "NON_CONTENT_TECHNICAL_RESPONSE"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recovery-dir", default="recovery")
    parser.add_argument("--acquisition-dir", default="acquisition")
    parser.add_argument("--report", default="RECOVERY-REPORT.md")
    args = parser.parse_args()

    recovery_dir = Path(args.recovery_dir)
    observations = load_jsonl(
        recovery_dir / "challenge-observations.jsonl"
    )
    identities = load_jsonl(recovery_dir / "document-identities.jsonl")
    links = load_jsonl(recovery_dir / "recovery-links.jsonl")

    links_by_url: dict[str, list[dict]] = defaultdict(list)
    for link in links:
        links_by_url[link["original_url"]].append(link)

    identity_by_id = {i["identity_id"]: i for i in identities}

    # -- per-URL coverage -------------------------------------------
    url_states: Counter = Counter()
    by_host: dict[str, Counter] = defaultdict(Counter)
    by_family: dict[str, Counter] = defaultdict(Counter)
    unresolved = []
    fingerprints: Counter = Counter()

    for obs in observations:
        state = coverage_state(obs, links_by_url)
        url_states[state] += 1
        from urllib.parse import urlparse
        host = (urlparse(obs["url"]).hostname or "").lower()
        by_host[host][state] += 1
        by_family[obs["source_family"]][state] += 1
        fingerprints[obs.get("fingerprint") or obs["classification"]] \
            += 1
        if state in ("UNRESOLVED_CHALLENGE",
                     "NON_CONTENT_TECHNICAL_RESPONSE",
                     "ACCESS_RESTRICTED"):
            unresolved.append({
                "url": obs["url"],
                "source_family": obs["source_family"],
                "tier": obs.get("tier"),
                "classification": obs["classification"],
                "coverage_state": state,
                "response_sha256": obs.get("response_sha256"),
                "retrieved_at": obs.get("retrieved_at"),
                "next_action": (
                    "access-limited; record the gap"
                    if state == "ACCESS_RESTRICTED"
                    else "alternate-source resolution / later "
                         "ordinary retry on low-frequency cadence"
                ),
            })

    # -- document-identity coverage ---------------------------------
    identity_states: Counter = Counter()
    obs_by_url = {o["url"]: o for o in observations}
    for identity in identities:
        url = identity["original_url"]
        obs = obs_by_url.get(url)
        state = coverage_state(obs, links_by_url) if obs else "UNKNOWN"
        identity_states[state] += 1

    tier_pending: dict[int, int] = defaultdict(int)
    for row in unresolved:
        tier_pending[row.get("tier") if row.get("tier") is not None
                     else 9] += 1

    relationship_counts = Counter(l["relationship"] for l in links)
    method_counts = Counter(l["discovery_method"].split(":")[0]
                            for l in links)

    metrics = {
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "challenge_observations": len(observations),
        "document_identities": len(identities),
        "identities_resolved": sum(
            1 for i in identities
            if i.get("identity_method") != "unresolved"
        ),
        "recovery_links": len(links),
        "recovery_links_by_relationship": dict(relationship_counts),
        "recovery_links_by_method": dict(method_counts),
        "requested_url_coverage": dict(url_states),
        "document_identity_coverage": dict(identity_states),
        "by_host": {h: dict(c) for h, c in sorted(by_host.items())},
        "by_family": {f: dict(c) for f, c in sorted(by_family.items())},
        "unresolved": len(unresolved),
        "unresolved_by_tier": {str(k): v for k, v in
                               sorted(tier_pending.items())},
        "top_fingerprints": dict(fingerprints.most_common(15)),
        "semantics_note": (
            "BOT_CHALLENGE / non-content captures are never counted "
            "as ARCHIVED_CONTENT. RECOVERED_* states preserve the "
            "distinction between original publisher and retrieval "
            "host; original challenge observations are retained."
        ),
    }

    atomic_write(
        recovery_dir / "metrics.json",
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
    )
    tmp_rows = sorted(unresolved,
                      key=lambda r: (r.get("tier") or 9, r["url"]))
    with (recovery_dir / "unresolved-challenges.tmp").open(
            "w", encoding="utf-8") as f:
        for row in tmp_rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(recovery_dir / "unresolved-challenges.tmp",
               recovery_dir / "unresolved-challenges.jsonl")

    # -- report ------------------------------------------------------
    def fmt_counter(counter: dict) -> str:
        return ", ".join(f"{k}: {v}" for k, v in
                         sorted(counter.items(),
                                key=lambda kv: -kv[1])) or "none"

    doj = by_family.get("doj", Counter())
    fr = by_family.get("federal_register", Counter())
    congress = by_family.get("congress", Counter())
    gao = by_family.get("gao", Counter())

    lines = [
        "# Recovery report — challenge-aware lawful recovery",
        "",
        f"Generated {metrics['generated_at']} from committed recovery "
        "state. No CAPTCHA solving, proxy/identity rotation, "
        "fingerprint spoofing, or rate-limit circumvention is used "
        "anywhere in this pipeline: challenged endpoints are routed "
        "around through lawful public representations, or recorded "
        "as unresolved.",
        "",
        "## 1. Challenge / non-content responses",
        "",
        f"- **{len(observations)}** challenge/non-content "
        "observations across the corpus (latest observation per URL).",
        f"- Requested-URL coverage states: "
        f"{fmt_counter(url_states)}",
        "",
        "## 2. Hosts generating them",
        "",
        "| Host | States |",
        "|------|--------|",
    ]
    for host, counter in sorted(by_host.items()):
        lines.append(f"| {host} | {fmt_counter(counter)} |")
    lines += [
        "",
        "## 3. Document identities",
        "",
        f"- {len(identities)} identities built; "
        f"{metrics['identities_resolved']} resolved via API metadata "
        "or URL-slug derivation.",
        f"- Document-identity coverage: "
        f"{fmt_counter(identity_states)}",
        "",
        "## 4–7. Recovery outcomes",
        "",
        f"- Same-agency recoveries (`SAME_DOCUMENT`): "
        f"{relationship_counts.get('SAME_DOCUMENT', 0)}",
        f"- Official government mirrors (`OFFICIAL_MIRROR`): "
        f"{relationship_counts.get('OFFICIAL_MIRROR', 0)}",
        f"- Public web archive (`ARCHIVED_VERSION`): "
        f"{relationship_counts.get('ARCHIVED_VERSION', 0)}",
        f"- Derived representations (API metadata records): "
        f"{relationship_counts.get('DERIVED_REPRESENTATION', 0)}",
        f"- Still unresolved: **{len(unresolved)}** "
        f"(by tier: {dict(sorted(tier_pending.items()))})",
        "",
        "## 8. Highest-value challenged collections",
        "",
        "Ranked by preservation tier of pending items — Tier 0 "
        "(FinCEN/BOI/CTA core) first, then Tier 1 (enforcement, "
        "oversight), then general agency content.",
        "",
        "## 9. DOJ",
        "",
        f"- DOJ URL states: {fmt_counter(doj)}",
        "",
        "## 10. Federal Register",
        "",
        f"- FR URL states: {fmt_counter(fr)}",
        "- Each recovered FR document links its page identity to the "
        "official GovInfo bytes "
        "(`FR_API_RECORD --REPRESENTS--> GOVINFO_DOCUMENT`); both "
        "identities preserved.",
        "",
        "## 11. Congress / GAO",
        "",
        f"- Congress: {fmt_counter(congress)}",
        f"- GAO: {fmt_counter(gao)}",
        "",
        "## 12. Challenge fingerprints observed",
        "",
    ]
    for fingerprint, count in fingerprints.most_common(15):
        lines.append(f"- `{fingerprint[:140]}` × {count}")
    lines += [
        "",
        "## 13. Most effective alternate routes",
        "",
    ]
    for method, count in method_counts.most_common():
        lines.append(f"- `{method}`: {count} links")
    lines += [
        "",
        "## 14. Access-limited gaps",
        "",
        f"- {url_states.get('ACCESS_RESTRICTED', 0)} URLs are "
        "access-restricted (401/403 without challenge markup). These "
        "are recorded as gaps and never evaded.",
        "",
        "## 15. Retry posture",
        "",
        "- Challenged endpoints: no immediate retry; small ordinary "
        "probe per run; direct retries wait a 7-day cadence and only "
        "resume when a probe shows the challenge lifted.",
        "- 429: Retry-After honored once, then the host is stopped "
        "for the run. 5xx/network: bounded exponential backoff. "
        "403: classified, never evaded. CAPTCHA: never automated.",
        "",
        "## Provenance rules",
        "",
        "- Every recovered object keeps original publisher vs "
        "retrieval host distinct (e.g. publisher DOJ, retrieval host "
        "web.archive.org, relationship ARCHIVED_VERSION).",
        "- Original challenge observations are preserved in "
        "`recovery/challenge-observations.jsonl` and the manifest; "
        "recovery never rewrites URL history.",
        "- Byte-identical official copies are EXACT_DUPLICATE; "
        "differing bytes with matching identity are "
        "SAME_DOCUMENT_DIFFERENT_REPRESENTATION; both provenance "
        "records are kept.",
        "",
    ]
    atomic_write(Path(args.report), "\n".join(lines))

    print(json.dumps(
        {k: v for k, v in metrics.items()
         if k in ("challenge_observations", "recovery_links",
                  "requested_url_coverage",
                  "document_identity_coverage", "unresolved")},
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
