---
name: proposal-doctor
description: Diagnose, write, review and score freelance proposals (Upwork and similar marketplaces) so they get opened and answered. Use this whenever the user mentions Upwork or a freelance-marketplace bid - writing or improving a proposal or cover letter, answering screening questions, deciding whether a job is worth the Connects, asking why proposals get no views or no replies, wanting a checklist or a score for a draft, or wanting a draft to read in their own voice instead of generic or machine-written phrasing. Also use it when the user pastes a job post and asks "should I bid on this" or pastes a draft and asks "is this good", even if they never say the word proposal.
---

# Proposal Doctor

## The idea

A proposal passes four gates in order, and it dies at the first one it cannot pass:

1. **The job.** Is the client real, active and hiring, and is the job one this freelancer
   can win? Many jobs close with no hire. No letter fixes that.
2. **The card.** The client sees a sorted list of cards: photo, title, rate, badges,
   earnings, and about the first 150 to 200 characters of the letter. Position in the list
   (profile match, timing, boost) and that preview decide whether the proposal is opened.
3. **The letter.** Once opened: does it show the post was read, name the hard part, give a
   first step, prove it with one checkable thing, and make replying easy?
4. **The voice.** Does it read like a person who does this work, or like the rest of the
   pile?

Most people polish gate 4 while losing at gate 1 or 2. So find the gate first, then fix
that one. Read `references/how-clients-see-proposals.md` once per session before doing
anything else; the rest depends on it.

## Pick the mode

| The user wants | Do this |
|---|---|
| "Why am I getting no views / no replies?" | **Diagnose** |
| "Should I bid on this?" or pastes only a job post | **Gate**, then offer to write |
| "Write a proposal for this job" | **Gate** quickly, then **Write** |
| "Is this proposal good?" / "check my draft" / "score this" | **Review** |
| "Make this sound human / less AI" | **Review**, voice first, but still report a fit problem if there is one |
| Screening questions | Part of **Write** or **Review**; see the screening section in `references/writing-the-proposal.md` |

If a draft would fail at an earlier gate, say so before polishing it. Rewriting the wording
of a proposal for a dead job wastes the user's Connects and their trust.

## What you need from the user

Ask only for what is missing, in one message.

- **The full job post**, including the last line, the screening questions, and what the
  page shows about the client and the job: posted when, proposals so far, interviewing,
  hires, payment verified, hire rate, total spent, budget, experience level.
- **Their proof bank**: real projects with links, numbers, reviews and what they personally
  did. If there is none yet, offer `assets/proof-bank-template.md`, fill it together and
  save it in their working folder for next time. If one exists there, read it.
- **Their own take** on this job, in rough words. See below.

### Get their own words first

Before drafting, ask: *"In your own words, two or three rough sentences: what's the tricky
part of this job, and what would you do first?"*

Build the letter from the answer and keep their phrasing where it is clear. This matters
more than any wording rule: it puts in the letter the things only someone who does the work
would say, and it makes the letter theirs. If they would rather skip it, draft anyway, and
list every technical claim they need to confirm before sending.

## Diagnose

Follow `references/funnel-diagnosis.md`.

1. Gather the last 20 to 40 proposals with their outcomes. If an Upwork connector is
   connected, use its read-only tools to list proposals in every status and fetch each
   one's insights; otherwise ask the user for the figures.
2. Save the rows and run `python scripts/funnel_audit.py <file>`.
3. Read a sample of the actual letters too, and lint a few. Numbers show where proposals
   die; the letters show why.
4. Report the biggest leak first, with the evidence, then the next. Finish with a short
   operating rule they can follow from tomorrow and a date to re-check.

## Gate

Follow `references/job-gate.md`: hard skips first, then the eight-question score. Give the
answer in this form:

    BID / BID WITH BOOST / SKIP   score N/16
    Why: one or two lines
    Watch: code word, AI trap, requested items, anything odd about the client

If it is a skip, say so and stop. Do not write a "just in case" proposal.

## Write

Follow `references/writing-the-proposal.md`.

1. Pull out the outcome, the fear, two or three anchors, the must-haves.
2. Get their own take. Choose one proof from the proof bank.
3. Write the first two sentences and judge them alone as the preview.
4. Write the rest: first step and first deliverable, proof, anything they asked for, one
   easy question. 80 to 150 words by default.
5. Write each screening answer for its own box. Answer 1 carries the hook.
6. Save the letter (and answers) to files and run the lint with the job post:
   `python scripts/proposal_lint.py --proposal letter.txt --job job.txt --answers answers.txt`
7. Score it against `references/fit-checklist.md` and read it against
   `references/human-voice.md`. Fix and re-run until there are no blockers.
8. Deliver in the output format below.

## Review

1. Run the lint (with the job post if you have it).
2. Score the 25 lines of `references/fit-checklist.md`. Quote the sentence that earns or
   loses each low score.
3. Go through `references/human-voice.md` sections 1 to 5 and list what is present.
4. Name the gate where this proposal would die.
5. Offer a rewrite, or give one straight away if they asked for it. Keep every true fact
   and their phrasing; change structure and wording.

## Output format

For Write and Review, use this shape. Keep it short; the user wants the letter, not an essay.

    VERDICT: Send / Fix first / Skip this job
    Would die at: job | card | preview | letter | voice | nowhere obvious
    Scores: Preview N/100 · Fit N/50 · Voice: N issues (N blockers)

    What the client sees first:
    "first 150 to 200 characters"

    Top fixes, in order (three at most)

    The proposal (ready to paste, plain text)

    Screening answers (one block per question)

    Before you send: facts only you can confirm, things to attach, the bid and why

Put the proposal in a plain code block or plain paragraph so it pastes without markdown.

## Rules that protect the user

- **Only true facts.** Use what the user gave you or what is in their proof bank. Never
  invent a project, client, metric, review, link or years of experience. If the proof for a
  job is missing, say so; then either bridge from the nearest real work in one plain
  sentence or recommend skipping.
- **Accurate, not apologetic.** Be accurate by choosing true statements, not by attaching
  disclaimers to them. One plain sentence about a real gap is fine. A letter that keeps
  qualifying itself loses.
- **No detection games.** No fake typos, forced slang or "I wrote this myself" lines. The
  voice check removes machine habits from a letter the freelancer stands behind; it is not
  for disguising one they have not read.
- **Their account, their call.** Never submit, edit, boost or spend Connects through a
  connector without showing the exact text, terms and cost and getting a clear yes for that
  proposal. Reading their own proposals and job pages is fine.
- **Stay inside Upwork's rules.** No asking clients to move off-platform before a contract,
  no bulk or automated bidding, no contact details in proposals.
- **Scores are aids.** They are heuristics for spotting problems, not predictions. Say so
  if the user treats a number as a guarantee.

## Scripts

Both are Python 3.8+ with no dependencies. If Python is not available, do the same checks by
hand from the reference files.

- `scripts/proposal_lint.py` checks one letter: what the preview shows, whether the job's
  own terms are used, generic sentences, proof and close, stock phrases, AI vocabulary,
  sentence-shape patterns, self-undermining lines, tracking tags, placeholders, code words
  and AI traps. `--json` for structured output. Exit code 1 means blockers.
- `scripts/funnel_audit.py` takes a list of past proposals and reports the view and reply
  rates, how late bids went in, how many clients never reviewed anyone, and which leak to
  fix first.

Neither is an AI detector and neither judges whether the letter is good. A clean lint means
the mechanical problems are gone; the checklists carry the judgment.

## Reference files

- `references/how-clients-see-proposals.md` mechanics and evidence. Read first.
- `references/job-gate.md` bid or skip.
- `references/writing-the-proposal.md` how to build the letter, screening answers, examples.
- `references/fit-checklist.md` 25 checks: does it answer this client's problem?
- `references/human-voice.md` what reads as machine-written and what to do instead.
- `references/funnel-diagnosis.md` finding the leak and what to change.
- `references/sources.md` where the claims come from and how far to trust each.
- `assets/proof-bank-template.md` the freelancer's reusable facts.
