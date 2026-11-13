#!/usr/bin/env python3
"""funnel_audit.py - find where Upwork proposals are being lost.

A proposal dies at one of four places. Each has a different fix, so the first
job is to work out which one is costing the most:

  1. CLIENT NEVER REVIEWED   the client opened almost nobody, or the job closed without a hire
  2. OUT-RANKED              the client opened plenty of proposals, but not this one
  3. VIEWED, NO REPLY        the client opened it and moved on
  4. REPLIED, NOT HIRED      a conversation started and stalled

Usage
  python funnel_audit.py proposals.json
  python funnel_audit.py proposals.csv --json

Input: a JSON list (or a CSV with the same column names). Every field is optional
except something to identify the row; give what you have.

  title           job title
  proposal_id     Upwork proposal id          (used to estimate the send time)
  job_id          Upwork job id               (used to estimate the posting time)
  submitted_at    ISO time the proposal went in       (overrides proposal_id)
  job_posted_at   ISO time the job was posted         (overrides job_id)
  viewed          true/false  client opened this proposal
  replied         true/false  client messaged you
  hired           true/false
  boosted         true/false
  connects        Connects spent on this proposal
  opened          how many proposals the client opened      (Proposal insights)
  total           how many proposals the job received       (Proposal insights)
  status          open | expired | cancelled | no_hire | filled | filled_elsewhere | declined | hired | removed

About the id trick: Upwork job and proposal ids are time-ordered "snowflake"
numbers. (id >> 22) + 1288834974657 is the creation time in milliseconds. That
was checked against real proposal timestamps in November 2026. For a job it is
when the posting record was created, so a reposted or long-drafted job can be
off. Treat the result as an estimate and prefer real timestamps when you have them.

Python 3.8+, standard library only.
"""
import argparse
import csv
import json
import statistics
import sys
from datetime import datetime, timezone

SNOWFLAKE_EPOCH_MS = 1288834974657
CONNECT_PRICE_USD = 0.15
NO_HIRE = {"expired", "cancelled", "canceled", "no_hire", "removed"}


def id_to_ts(value):
    try:
        n = int(str(value).lstrip("~").strip())
    except (TypeError, ValueError):
        return None
    if n < (1 << 40):
        return None
    if str(value).lstrip("~").startswith("02") and len(str(value).lstrip("~")) > 19:
        n = int(str(value).lstrip("~")[2:])
    return ((n >> 22) + SNOWFLAKE_EPOCH_MS) / 1000.0


def iso_to_ts(value):
    if not value:
        return None
    try:
        s = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


def truthy(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("true", "yes", "y", "1"):
        return True
    if s in ("false", "no", "n", "0"):
        return False
    return None


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(path):
    if path.lower().endswith(".csv"):
        with open(path, newline="", encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else data.get("proposals", [])


def fmt_delay(h):
    if h is None:
        return "?"
    if h < 1:
        return "%d min" % round(h * 60)
    if h < 48:
        return "%.1f h" % h
    return "%.1f d" % (h / 24)


def classify(r):
    if r["hired"]:
        return "hired"
    if r["replied"]:
        return "replied"
    if r["viewed"]:
        return "viewed_no_reply"
    ratio = r["open_ratio"]
    if ratio is not None:
        if ratio <= 0.05:
            return "client_never_reviewed"
        if ratio >= 0.15:
            return "out_ranked"
        return "thin_review"
    if r["status"] in NO_HIRE:
        return "client_never_reviewed"
    return "unknown"


def audit(rows):
    recs = []
    for raw in rows:
        sub = iso_to_ts(raw.get("submitted_at")) or id_to_ts(raw.get("proposal_id"))
        posted = iso_to_ts(raw.get("job_posted_at")) or id_to_ts(raw.get("job_id"))
        delay = (sub - posted) / 3600.0 if sub and posted and sub >= posted else None
        opened, total = num(raw.get("opened")), num(raw.get("total"))
        r = {
            "title": str(raw.get("title") or raw.get("job_id") or "untitled")[:60],
            "delay_h": delay,
            "viewed": bool(truthy(raw.get("viewed"))),
            "replied": bool(truthy(raw.get("replied"))),
            "hired": bool(truthy(raw.get("hired"))) or str(raw.get("status", "")).lower() == "hired",
            "boosted": bool(truthy(raw.get("boosted"))),
            "connects": num(raw.get("connects")),
            "opened": opened, "total": total,
            "open_ratio": (opened / total) if opened is not None and total else None,
            "status": str(raw.get("status") or "open").strip().lower().replace(" ", "_"),
        }
        r["bucket"] = classify(r)
        recs.append(r)

    n = len(recs)
    viewed = sum(r["viewed"] or r["replied"] or r["hired"] for r in recs)
    replied = sum(r["replied"] or r["hired"] for r in recs)
    hired = sum(r["hired"] for r in recs)
    delays = [r["delay_h"] for r in recs if r["delay_h"] is not None]
    buckets = {}
    for r in recs:
        buckets[r["bucket"]] = buckets.get(r["bucket"], 0) + 1

    timing = []
    for lo, hi, label in ((0, 1, "under 1 h"), (1, 6, "1 to 6 h"), (6, 24, "6 to 24 h"), (24, 1e9, "over 24 h")):
        g = [r for r in recs if r["delay_h"] is not None and lo <= r["delay_h"] < hi]
        timing.append({"window": label, "sent": len(g), "viewed": sum(r["viewed"] or r["replied"] or r["hired"] for r in g)})

    closed = [r for r in recs if r["status"] != "open"]
    closed_no_hire = [r for r in closed if r["status"] in NO_HIRE]
    crowd = [r["total"] for r in recs if r["total"]]
    ratios = [r["open_ratio"] for r in recs if r["open_ratio"] is not None]
    connects = [r["connects"] for r in recs if r["connects"]]
    boosted = sum(r["boosted"] for r in recs)

    # ---- which leak is biggest
    lost = n - viewed
    leaks = []
    never = buckets.get("client_never_reviewed", 0)
    outr = buckets.get("out_ranked", 0) + buckets.get("thin_review", 0)
    vnr = buckets.get("viewed_no_reply", 0)
    late = sum(1 for d in delays if d >= 6)
    if n:
        if never / float(n) >= 0.3:
            leaks.append(("JOB SELECTION", "%d of %d proposals went to clients who opened almost nobody or closed the job without hiring. No letter can fix that. Tighten the bid/no-bid gate: client hire rate, payment verified, recent activity, under ~20 proposals." % (never, n)))
        if delays and late / float(len(delays)) >= 0.4:
            leaks.append(("TIMING", "%d of %d proposals went in 6+ hours after the job was posted (median %s). By then the client has usually opened the first batch and the list is long. Bid inside the first hour or skip." % (late, len(delays), fmt_delay(statistics.median(delays)))))
        if outr / float(n) >= 0.25:
            leaks.append(("RANK AND CARD", "%d of %d times the client was opening proposals but not yours. That is decided by list position and the card: profile title and skills matching the job, earnings/JSS/badge against the field, bid against budget, a boost, and the first two lines." % (outr, n)))
        if viewed and vnr / float(viewed) >= 0.6 and viewed >= 5:
            leaks.append(("THE LETTER", "%d of %d viewed proposals got no reply. The opening earned the click; the proof, the plan, the price or the close lost it. Run the fit checklist." % (vnr, viewed)))
        if replied >= 5 and hired / float(replied) < 0.2:
            leaks.append(("THE CONVERSATION", "%d replies, %d hire(s). The proposals work; the follow-up, scoping or pricing does not." % (replied, hired)))
    if not leaks and n:
        leaks.append(("NO DOMINANT LEAK", "Nothing stands out at this sample size. Keep logging until each bucket has 20+ proposals."))

    return {
        "n": n, "viewed": viewed, "replied": replied, "hired": hired,
        "view_rate": round(viewed / float(n), 3) if n else None,
        "reply_rate": round(replied / float(n), 3) if n else None,
        "median_delay_h": round(statistics.median(delays), 1) if delays else None,
        "timing": timing, "buckets": buckets,
        "closed_jobs": len(closed), "closed_without_hire": len(closed_no_hire),
        "median_crowd": statistics.median(crowd) if crowd else None,
        "median_client_open_ratio": round(statistics.median(ratios), 3) if ratios else None,
        "boosted": boosted,
        "connects_spent": sum(connects) if connects else None,
        "connects_rows": len(connects),
        "leaks": [{"name": a, "detail": b} for a, b in leaks],
        "rows": sorted(recs, key=lambda r: (r["delay_h"] is None, r["delay_h"] or 0)),
        "small_sample": n < 30,
    }


def render(a):
    L = []
    L.append("UPWORK FUNNEL AUDIT")
    L.append("")
    L.append("%-9s %-3s %-9s %-22s %s" % ("sent after", "saw", "opened", "what happened", "job"))
    names = {"client_never_reviewed": "client never reviewed", "out_ranked": "out-ranked",
             "thin_review": "client opened few", "viewed_no_reply": "viewed, no reply",
             "replied": "replied", "hired": "hired", "unknown": "unknown"}
    for r in a["rows"]:
        ot = "%d/%d" % (r["opened"], r["total"]) if r["opened"] is not None and r["total"] else "-"
        L.append("%-9s  %-3s %-9s %-22s %s%s" % (fmt_delay(r["delay_h"]), "Y" if r["viewed"] else ".", ot,
                                                names.get(r["bucket"], r["bucket"]), r["title"],
                                                "" if r["status"] == "open" else " [%s]" % r["status"]))
    L.append("")
    L.append("TOTALS")
    L.append("  proposals %d | viewed %d (%.0f%%) | replies %d (%.0f%%) | hires %d | boosted %d" % (
        a["n"], a["viewed"], 100 * (a["view_rate"] or 0), a["replied"], 100 * (a["reply_rate"] or 0), a["hired"], a["boosted"]))
    if a["median_delay_h"] is not None:
        L.append("  median time from job posted to proposal sent: %s" % fmt_delay(a["median_delay_h"]))
    if a["median_crowd"] is not None:
        L.append("  median proposals per job: %d | median share of proposals the client opened: %.0f%%" % (
            a["median_crowd"], 100 * (a["median_client_open_ratio"] or 0)))
    if a["closed_jobs"]:
        L.append("  closed jobs: %d, of which %d closed without hiring anyone (expired, cancelled, removed)" % (
            a["closed_jobs"], a["closed_without_hire"]))
    if a["connects_spent"]:
        if a["connects_rows"] >= 0.8 * a["n"]:
            per_view = (a["connects_spent"] / float(a["viewed"])) if a["viewed"] else None
            L.append("  Connects spent: %d (about $%.0f)%s" % (a["connects_spent"], a["connects_spent"] * CONNECT_PRICE_USD,
                                                             " | %.0f Connects per view" % per_view if per_view else " | no views to divide by"))
        else:
            L.append("  Connects recorded for only %d of %d proposals (%d Connects); add the rest for a cost-per-view figure" % (
                a["connects_rows"], a["n"], a["connects_spent"]))
    L.append("")
    L.append("VIEWS BY HOW FAST THE PROPOSAL WENT IN")
    for t in a["timing"]:
        if t["sent"]:
            L.append("  %-10s sent %2d   viewed %2d" % (t["window"], t["sent"], t["viewed"]))
    L.append("")
    L.append("WHERE PROPOSALS DIED")
    for key in ("client_never_reviewed", "out_ranked", "thin_review", "viewed_no_reply", "replied", "hired", "unknown"):
        if a["buckets"].get(key):
            L.append("  %-22s %d" % (names[key], a["buckets"][key]))
    L.append("")
    L.append("BIGGEST LEAKS (fix in this order)")
    for i, lk in enumerate(a["leaks"], 1):
        L.append("  %d. %s: %s" % (i, lk["name"], lk["detail"]))
    L.append("")
    L.append("  Rough yardsticks from vendor studies, not guarantees: 20-40% of proposals viewed and")
    L.append("  10-20% answered for an established freelancer; agency pipelines average about 7% replies.")
    if a["small_sample"]:
        L.append("")
        L.append("  Small sample (%d). Read these as patterns to act on, not statistics." % a["n"])
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Find where Upwork proposals are being lost.")
    ap.add_argument("file", help="JSON list or CSV of proposals")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    out = audit(load(a.file))
    print(json.dumps(out, indent=2, default=str) if a.json else render(out))


if __name__ == "__main__":
    main()
