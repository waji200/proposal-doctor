# Proposal Doctor

A Claude plugin for freelancers who send Upwork proposals and hear nothing back.

Most advice about proposals is about wording. Most proposals are lost before the client reads a word: the job was dead, the bid went in hours late, or the profile didn't match what the client searched for. Proposal Doctor checks a proposal in the order a client meets it:

1. **The job.** Is the client real, active and hiring, and can you win this one?
2. **The card.** Clients see a sorted list of cards and the first couple of lines of each letter. Does yours earn the click?
3. **The letter.** Does it show you read the post, name the hard part, give a first step, prove it with one checkable thing, and end with an easy question?
4. **The voice.** Does it read like you, or like the pile of templated and machine-written bids the client is skimming past?

It finds the gate where your proposals are dying and fixes that one first.

## What you can ask it

- "I've sent 20 proposals this month, one view, no replies. What am I doing wrong?" It reads your numbers and tells you whether the problem is job selection, timing, your profile or the letter.
- "Should I bid on this?" with a job post pasted in. You get bid, bid with boost, or skip, a score out of 16, and the reason.
- "Write a proposal for this job." It asks for your own rough take on the job first, so the letter carries what you know and sounds like you, then drafts the letter and the screening answers.
- "Is this proposal any good?" with your draft. You get what the client sees before clicking, scores, the top three fixes and a rewrite that keeps your facts.
- "Make this sound less like ChatGPT." It removes stock phrases and machine-writing habits, and tells you if the real problem is fit rather than wording.

## What's inside

```
skills/proposal-doctor/
  SKILL.md                     the workflow Claude follows
  references/
    how-clients-see-proposals.md   ranking, preview, boosts, timing, with how far to trust each claim
    job-gate.md                    hard skips and an 8-question bid-or-skip score
    writing-the-proposal.md        building the letter and screening answers, with worked examples
    fit-checklist.md               25 checks: does it answer this client's problem?
    human-voice.md                 what reads as machine-written and what to write instead
    funnel-diagnosis.md            finding where your proposals are lost
    sources.md                     every source, with its caveats
  scripts/
    proposal_lint.py           checks one letter (preview, job terms, swap test, stock phrases, tells)
    funnel_audit.py            reads your past proposals and names the biggest leak
  assets/
    proof-bank-template.md     your reusable facts, so nothing gets invented
evals/                         three test cases for claude plugin eval
```

## Install

**Claude Code**

```
claude plugin marketplace add waji200/proposal-doctor
claude plugin install proposal-doctor@waji200-plugins
```

Or inside a session: `/plugin marketplace add waji200/proposal-doctor`, then `/plugin install proposal-doctor@waji200-plugins`.

**Claude apps (claude.ai, desktop):** once the listing is approved it will be in the Claude directory under Customize, Skills.

## Using the scripts on their own

Both need Python 3.8 or later and nothing else.

```
python skills/proposal-doctor/scripts/proposal_lint.py --proposal letter.txt --job job.txt
python skills/proposal-doctor/scripts/proposal_lint.py --proposal letter.txt --job job.txt --answers answers.txt --json
python skills/proposal-doctor/scripts/funnel_audit.py my_proposals.json
```

`funnel_audit.py` takes a JSON list or CSV of past proposals. Every field is optional; the docstring at the top of the file lists them.

## What it runs, reads and sends

- The plugin has no connector, no server and no network code of its own. It collects no data and stores nothing.
- If you've added your own Upwork connector to Claude, the skill may use it, when you ask, to read your past proposals and job posts for a diagnosis or a bid check. It submits a proposal or spends Connects through that connector only after showing you the exact text and cost and getting your yes. That data passes between Claude and Upwork under your connector; the plugin sends it nowhere else.
- The two scripts run on your machine. They read only the files you pass them, write nothing, and make no network requests.
- If you ask, Claude can save your proof bank as a file in your own working folder.

[Privacy](PRIVACY.md) has the details.

## What it won't do

- Invent experience. Every claim in a letter comes from what you tell it or from your proof bank.
- Help disguise text you haven't read. The voice check removes generic and machine-written phrasing from a letter you stand behind. It refuses fake typos, forced slang and "I'm not an AI" lines.
- Promise results. The scores are checklists for spotting problems, not predictions of a reply. Neither script is an AI detector.

## Where the advice comes from

Upwork's own help and resource pages, vendor datasets on reply rates (large but correlational, from companies that sell bidding tools), freelancer and client accounts, and Wikipedia's catalogue of AI-writing signs. `skills/proposal-doctor/references/sources.md` lists each source with what it was used for and how far to trust it.

## Testing

```
claude plugin validate . --strict
claude plugin eval .
```

`claude plugin eval` runs the three cases in `evals/` with and without the plugin. These are real model runs and are billed to your account.

## Support

Open an issue at https://github.com/waji200/proposal-doctor/issues for bugs, wrong advice or security problems. Pull requests are welcome, especially new stock phrases for the lint and corrections to the sources.

## Disclaimer

Not affiliated with, endorsed by or sponsored by Upwork Inc. "Upwork" and "Connects" are used only to describe what the plugin helps with.

## License

MIT. See `LICENSE`.
