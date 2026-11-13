# Funnel diagnosis: why proposals get no views or no replies

"My proposals aren't working" has at least four different causes with four different fixes.
Rewriting letters only fixes one of them. Find the leak first.

## Get the numbers

For the last 20 to 40 proposals collect, per proposal:

- when the job was posted and when the proposal was sent
- viewed or not, replied or not, hired or not
- how many proposals the job got and how many the client opened (Proposal insights, on
  Freelancer Plus)
- how the job ended: still open, hired, expired, cancelled
- Connects spent, boosted or not
- the job's main skill, and whether it matches the freelancer's profile title

If an Upwork connector is available, its read-only proposal tools return most of this:
list the proposals in each status (submitted, archived, declined, hired), then fetch each
one for its insights. Otherwise ask the freelancer to copy the figures from "My proposals"
and each job page.

Save the rows as JSON or CSV and run:

    python scripts/funnel_audit.py proposals.json

Posting and sending times can be estimated from the ids alone. Upwork job and proposal ids
are time-ordered: `(id >> 22) + 1288834974657` is the creation time in milliseconds. The
script does this when no timestamp is given. Treat it as an estimate; a reposted job can be
off.

## The four leaks

### 1. The client never reviewed

**Sign:** the client opened under about 5% of proposals, or the job expired or was cancelled.

**Meaning:** the letter was never in play. This is the most common leak and the one people
least suspect, because every unviewed proposal feels like a writing failure.

**Fix:** job selection. Apply the hard skips and scoring in `job-gate.md`. Favour clients
with a hiring history, verified payment and recent activity. Stop bidding on posts that are
vague, duplicated or days old.

### 2. Out-ranked

**Sign:** the client opened a healthy share of proposals (15% or more) but not this one.

**Meaning:** the card lost on position or at a glance. Work through these in order:

1. **Timing.** Compare views for proposals sent inside an hour with those sent later. If the
   late ones are never viewed, set up saved searches and alerts and bid early or not at all.
2. **Profile match.** Does the profile title say what the job asks for? If bids are spread
   across several specialties, most of them sort low. Narrow the bidding to what the title
   says, or rewrite the title and top skills around the work being chased.
3. **The field.** If rivals average many times the freelancer's earnings and job count,
   Best match favours them. Move to smaller scopes, intermediate-level posts and fresher
   jobs, where a thinner history competes.
4. **Bid position.** A bid far below the range reads as junior on an expert post; far above
   reads as not having read it.
5. **The preview.** Read the first 150 characters of each unviewed proposal on their own.
   If they open with the freelancer, a greeting or an echo of the brief, fix that.
6. **Boost.** Worth testing only once 1 to 5 are right, on exact-fit jobs with real value.

### 3. Viewed, no reply

**Sign:** the client opened the proposal and messaged someone else or nobody.

**Meaning:** the opening worked; the letter did not close. Score the viewed proposals with
`fit-checklist.md`. The usual causes: proof that is a name with nothing to look at, a full
plan that leaves nothing to ask, self-undermining lines, a price outside the range, or no
question at the end.

### 4. Replies, no hire

**Sign:** conversations start and stall.

**Meaning:** the proposals are fine. Look at reply speed (answer within the hour when
possible), whether the first reply moves to a concrete scope and price, and whether the
first milestone is small enough to say yes to.

## Yardsticks

Rough figures from vendor studies, useful only for orientation:

- an established freelancer: 20 to 40% of proposals viewed, 10 to 20% answered
- agency pipelines: about 7% answered on average, about 13% for the top quarter
- a new or thin profile on crowded jobs: 1 to 3% won is normal

A view rate under 15% almost always means leak 1 or 2, not the wording.

## Reporting the diagnosis

Lead with the biggest leak and the evidence for it, then the next one. For each, give the
one or two changes that address it. Be direct about what the data cannot show:

- under about 20 proposals in a bucket, call it a pattern, not a rate
- "not viewed" is a snapshot; recent proposals may still be opened
- opened counts cover organic proposals and refresh with a delay

End with a short operating rule the freelancer can follow from tomorrow (for example:
"bid only inside the first hour, only on jobs whose main skill is in your title, at most
five a week, boost none until the view rate passes 25%"), and a date to re-run the audit.
