# Russel claims decision system

A claims decision system for a California wildfire total loss, built from the
Chubb Masterpiece homeowners policy filed in California and the Department of
Insurance's guide for adjusting property claims after a disaster. It
demonstrates [Effective Decisions](https://effectiveai.dev): guideline
documents turned into a running system, written in RSL ("Russel").

Every rule cites the page it came from. Every dollar shows its arithmetic. The
system knows who is allowed to decide what. And any change to a guideline can
be replayed against past claims before it goes live.

## The documents

| Source | Document | Used for |
|---|---|---|
| `form` | Chubb Masterpiece, Deluxe House Coverage, California (Federal Insurance Company, SERFF ACEH-134883748, 2026 edition) | How a total loss of the house is settled, and the 180-day clause to begin rebuilding |
| `guide` | California Department of Insurance, *Guide for Adjusting Property Claims in California After a Major Disaster* (January 2026) | Payments owed in week one, the claim deadlines, the duty to disclose time limits |

## The files

| File | What it is |
|---|---|
| [`settlement.rsl`](settlement.rsl) | The payment rules. What the family is owed in week one, and the full position on the house, debris removal and code upgrades. |
| [`claim.rsl`](claim.rsl) | The guideline. Roles, deadlines, the time-limit notice, and the rule that sends a file to a supervisor. |
| [`ortiz.script`](ortiz.script) | One claim, start to finish: day 2, day 40, day 150. A test that runs against the rules. |
| [`replay.py`](replay.py) | Replays 1,000 claims under the current guideline and under a proposed change. |

## Run it

```bash
pip install rslc

rslc check settlement.rsl     # PASS settlement.rsl (strict)
rslc check claim.rsl          # PASS claim.rsl (strict)
rslc script ortiz.script      # PASS ortiz.script: 35 steps, 0 failed
python replay.py 1000         # the guideline change, on 1,000 claims
```

## The rules, and where they come from

| Rule | In the code | Source |
|---|---|---|
| Pay 60% of the contents limit, up to $350,000, without an itemized inventory | `contents_share`, `contents_cap`, step `dayone` | guide, page 16 |
| Advance four months of living expenses | `advance_months` | guide, page 11 |
| Acknowledge the claim within 15 days, decide within 40 | `ack_days_left`, `decide_days_left` | guide, page 13 |
| Extended replacement cost up to twice the combined limit | `erc_multiple`, step `pay` | form, page 3 |
| Begin rebuilding within 180 days of the loss, or the house settles on the lower basis | `switch_day`, `verified_basis` | form, page 3 |
| Debris removal up to 30%, code upgrades up to the house limit | `debris_share`, `code` | form, page 9 |
| Disclose the time limit before taking a position after day 150 | `TIME_LIMIT_NOT_DISCLOSED` | guide, page 18 |
| At day 150 with no rebuild started, a supervisor decides | `refer rebuild_clock ... to @Role.supervisor` | guide, page 18 |

The compiler enforces the citations. A rule without a page does not compile.

```rsl
step dayone [cite: guide:p16] {
    contents: Premium [cite: guide:p16] = round(min(self.contents_limit * contents_share, contents_cap), 0, half_up),
    living: Premium [cite: guide:p11] = round(self.monthly_living * advance_months, 0, half_up)
}
```

```rsl
refer rebuild_clock when self.days_since_loss >= alert_day and not self.claim.rebuild_started
    to @Role.supervisor because "Day 150, no rebuild started: the 180-day clause is 30 days away." [cite: guide:p18]
```

## One claim: the Ortiz family

A hypothetical total loss in a declared wildfire emergency. House limit $2,500,000, other
structures $250,000, contents $1,250,000.

| Day | What the system says | Who acts |
|---|---|---|
| 2 | Owed now: $350,000 for contents with no inventory, and a $56,000 living advance. 15 days to acknowledge. | Adjuster |
| 40 | Position: $4,080,000. House $3,390,000, debris $280,000, code upgrades $410,000. | Adjuster signs |
| 150 | No rebuild started and 30 days left on the clause, with $650,000 at stake. No position until the time-limit notice is sent. Then the file goes to a supervisor. | Adjuster sends the notice |
| 150 | The family asks for more time. The extension is approved. | Supervisor signs |

`ortiz.script` is that story as a test. It also checks what is refused: intake
cannot enter the estimate, and the adjuster cannot approve the extension.

## Change a guideline, see what happens

`replay.py` runs 1,000 synthetic total-loss claims through the system twice:
once with the 180-day clause, once with 12 months.

| | 180 days | 12 months | Change |
|---|---|---|---|
| Files escalated to a supervisor | 337 | 173 | 164 fewer |
| Rebuild paid with no escalation | $2,456.4M (663 files) | $3,074.5M (827 files) | +$618.1M |
| Rebuild paid after escalation | $926.7M | $493.9M | -$432.8M |
| Total rebuild paid | $3,383.1M | $3,568.4M | +$185.3M |

One number changed in one file. The effect on the whole book is known before
the guideline goes live.

## License

MIT. See [LICENSE](LICENSE).
