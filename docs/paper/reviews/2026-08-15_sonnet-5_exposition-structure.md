# Editorial and structural review — tendcf-architecture-guide.md

Reviewer: Sonnet 5, independent pass (no sub-agents used).
Target: `docs/paper/tendcf-architecture-guide.md` (964 lines, 19 sections), as of 2026-08-15.
Severity scale: **critical** (blocks trust/comprehension for most readers) · **major**
(meaningfully hurts the document) · **minor** (worth fixing, low stakes) · **nit** (optional
polish).

This is a findings report, not an edit pass. The file was not modified.

---

## 1. Opening (Section 1 and 2)

**Finding 1.1 — major.** Section 1 gestures at "why" in one paragraph but doesn't develop it
before the document moves to mechanism. The paragraph beginning "Most of the configuration will
be written by AI coding agents, not typed by a person" is the seed of the document's actual
thesis (later formalized in §9), but it's dropped as a single sentence among several other goals
(publishability, not-NixOS) with no signal that it's the load-bearing one. A first-time reader
has no way to know, on a first pass through §1, that this sentence is more important than the
Nix aside next to it.

**Finding 1.2 — major.** A reader who stops after §2 knows the layer names (tendcf,
site-shared, site-private, nix2cf, CFEngine, JSONL/SQLite) and the pipeline shape, but not *why*
it's shaped this way. §2 is a diagram plus terse annotations ("compile error," "never silent
last-wins") with almost no motivating prose — it reads as a reference card for someone who
already has the argument, not an introduction for someone who doesn't. The "why" (agents lack
global context, so local-knowledge designs are preferred) doesn't arrive until §9, roughly 40%
into the document. Contrast with §12's VPN-lockdown example or §13's ADB example, both of which
motivate a mechanism with a concrete failure *before* presenting the abstraction — §1–§2 do the
reverse.

**Finding 1.3 — minor.** §2 introduces "TUF-subset" in the diagram before TUF (The Update
Framework) is named or explained anywhere — that happens five sections later, in §7. A reader
working through the document linearly hits an unglossed acronym-plus-qualifier at the very
top.

**Finding 1.4 — minor.** §1's second paragraph ("A person whose computer is managed should be
able to read a proposed change in ordinary language and refuse it") is arguably the single most
persuasive sentence in the introduction — it's concrete, human-scale, and states the stakes. It
is one sentence in a five-sentence paragraph, no more emphasized than the sentences around it.
Consider whether this belongs closer to the top, ahead of the mixed-fleet/no-ops-staff framing.

---

## 2. Length and structure (19 sections; §10–§13 in particular)

**Finding 2.1 — major.** §10–§13 (ordering, extra entries, interlocks, peer actions) are four
mechanism sections back to back. Assessed individually:

- §10 (Ordering) and §11 (Extra entries) are clearly distinct problems — one is about sequencing,
  the other about completeness/drift detection — and each has enough independent content
  (three-level ambition ladder, self-doubt list, Bcfg2 comparison for §10; the two-reason opt-out
  scheme, the 0/2308 citation for §11) to earn a standalone section. Keep these separate.
- §12 (Interlocks) and §13 (Peer actions) are each short (18 and 25 lines respectively — the
  shortest sections in the document apart from §15) and structurally similar: both open with a
  one-sentence problem statement, cite a Bcfg2 precedent as justification, and close with a
  design constraint the schema enforces. §12 is single-host ("do not do B unless this probe still
  succeeds"); §13 is cross-host ("a peer may act for you"). They're conceptually distinct, but
  thin enough, and similarly shaped enough, that presenting them as one section — something like
  "§12. Preconditions and peer actions: two escapes from pure ordering" — would read as complete
  rather than padded, and would shorten the four-in-a-row run to three.
- Recommendation: merge §12 and §13, or at minimum add a one-sentence bridge at the top of §13
  that explicitly contrasts it with §12 ("§12 was a single host waiting on itself; this is a host
  waiting on another host") so the back-to-back placement reads as intentional rather than as a
  list of leftover mechanisms.

**Finding 2.2 — minor.** §15 (Token discovery) is very short (19 lines) and is tightly coupled
to §10 (it exists to answer "how does an author find the name to write in `requires`," a question
§10 raises directly). Consider folding §15 into §10 as a subsection, or at least placing it
immediately after §10 rather than after §14 (Trust), which is thematically unrelated and
currently sits between them.

**Finding 2.3 — minor.** §14 (Per-device trust) is sandwiched between §13 (Peer actions) and §15
(Token discovery), neither of which it's strongly connected to — it interrupts the
ordering/completeness/discovery thread (§10, §11, §15) with a trust-model table. If §15 moves
next to §10 per 2.2, §14 could move later, e.g. directly before §16 (walkthroughs), since the
trust table is referenced by nothing in §16 either but at least wouldn't be splitting a related
pair.

**Finding 2.4 — nit.** §17 ("Where a different design is a better fit") is genuinely useful and
well-placed as a pressure-release valve before the status/roadmap sections, but its three bullets
are each a single dense paragraph-length sentence. Given the document's plain-language mandate,
these could be split into (claim) + (why) pairs rather than one compound sentence apiece — see
Finding 5.5.

**Finding 2.5 — minor.** No section count or "how to read this" note exists at the top. A
19-section, ~960-line document that says up front it's a "plain-language companion" would
benefit from one sentence in the frontmatter block pointing a busy reader to which sections are
load-bearing (§1, §9, §19) versus reference material they can skip (§16's walkthroughs, §18's
build-order table).

---

## 3. Closing (Section 19, nine open questions)

**Finding 3.1 — minor, leaning positive.** §19 does not oversell. If anything it undersells its
own confidence: Q9 explicitly entertains that "the schemas are defending the wrong wall" — a
direct admission that the document's central mechanism (§9–§15) might be solving the wrong
problem. Q3 concedes that without a dedicated staff role, the core completeness metric (§11)
"only ever rises" is a live possibility. This is unusually candid for a design document and
should be read as a strength, not a weakness — it signals the author is tracking the design's own
failure modes rather than defending it.

**Finding 3.2 — major.** The nine questions are unranked and unweighted. A reader deciding
whether to take the design seriously has no signal about which of the nine, if answered "no,"
would sink the whole approach versus which are minor calibration issues. Q1, Q2, and Q9 all
attack the foundational premise from different angles (is the mechanism unnecessary / is the
rule unproven / is the rule aimed at the wrong failure mode) — a reader could reasonably infer
these three are more load-bearing than, say, Q4 (domain granularity) or Q6 (querying reachable
devices), but the document doesn't say so. One sentence at the top or bottom of §19 ("1, 2, and 9
are the ones that would change the design if answered against it; the rest are calibration")
would let a reader triage.

**Finding 3.3 — minor.** The document's actual last word before Acknowledgements/Further
Reading is Q9 — the "wrong wall" admission — followed immediately by a short paragraph about
token discovery being a solved mechanism, not an open question. That paragraph reads as a
deliberate soft landing after Q9's harder note, which works, but it's easy to miss as the
intended closing beat since it's set off from the numbered list with no heading. Consider a
one-line explicit close to §19 (e.g., restating that this list is itself evidence the design is
being held to its own standard) rather than trailing off into the token-discovery aside.

**Finding 3.4 — nit.** Ending on Acknowledgements + Further Reading after nine open questions is
a reasonable, conventional close for a document in this register (it ends on credit and citation,
not on doubt) — no change needed, noted only because the review brief asked specifically about
"the right note to end on."

---

## 4. Accessibility of the argument (§9's placement relative to §10–§15)

**Finding 4.1 — major.** §9 sits immediately before the six sections it motivates (§10–§15),
which is structurally sound — a reader who just read §9 has the "local vs. global knowledge"
frame fresh when they hit ordering, extra entries, interlocks, peer actions, trust, and token
discovery. But §9 arrives *after* six sections (§3–§8: facts-in-layers, compiler, agent,
device record, signed plans, person's AI) that are themselves partly justified by the same
argument and are read without it. §9's own text retroactively admits this: "why conflict errors
carry a resolution, why 'show me device X' is first in the compiler" are both mechanisms from §4,
introduced there without the frame that explains them, and only tied back three sections later.
A reader forms an impression of §4's design choices as arbitrary engineering preferences, then
has to revise that impression once §9 supplies the reason. That's a real cost — not fatal, since
the revision is guided (§9 does the tying-back explicitly), but it means the document's central
argument is doing double duty as both a forward-looking frame for §10–§15 and a backward
retrofit for §3–§8.

**Finding 4.2 — major.** Recommendation: move a compressed version of §9's argument (the
block-quoted "local vs. global knowledge" and "machine-checkable vs. conventional" rules, without
the citation paragraph) to immediately after §2, before §3. Keep the full §9 — citations,
"working hypothesis, not a law," the Tratt/Liu/Kon/Nekrasov references — in place as the deeper
treatment, but forward-reference it from the earlier, shorter statement. This lets §3–§8 be read
*as* applications of the rule rather than requiring the reader to reconstruct that connection
later. If a full move is too disruptive, at minimum add one sentence to §1 or §2 explicitly
flagging that the design choices about to appear (conflict errors with resolutions, "show me
device X," schema-first) all follow from one rule that gets stated in full in §9.

**Finding 4.3 — minor.** §9's citation paragraph (Tratt, Liu et al. "Lost in the Middle," Kon et
al. IaC-Eval, Nekrasov et al.) is doing real argumentative work — it's the evidence for the
thesis — but it's compressed into one dense paragraph of academic references with no numbers or
findings stated inline (e.g., what IaC-Eval's actual first-try correctness rate was, or what
fraction of errors were "contextual reasoning failure"). A "plain-language companion" reader is
asked to trust "Benchmarks... find that first-try correctness... is low" without a number, which
undercuts the persuasive force the paragraph is clearly going for. Consider pulling one or two
concrete figures from the cited sources into the prose.

---

## 5. Prose (plain-language goal)

**Finding 5.1 — minor.** §4: "CFEngine's own `mergedata()` is not used for this." No gloss is
given for what `mergedata()` is or why a reader should care that it isn't used. For a reader who
doesn't already know CFEngine internals, this sentence conveys nothing beyond "we didn't use some
CFEngine thing" — it needs either a half-clause of explanation or should be cut as a detail for
implementers only (it may belong better in the implementer map document referenced in the
frontmatter, not the plain-language guide).

**Finding 5.2 — minor.** §13: "Stall is local. Idempotent." Two sentence fragments in a row,
the second with no stated subject. Requires rereading the preceding sentences to work out that
"idempotent" modifies the stall/retry behavior of the peer-action mechanism, not "stall" as a
noun. This is the single most compressed passage in the document — flag for expansion into a full
sentence.

**Finding 5.3 — minor.** §11: "Fleet-wide comprehensiveness on a machine that was never built
under it is not survivable." Grammatically ambiguous referent for "it" (comprehensiveness? the
mechanism? the fleet?) and "is not survivable" is a strong, almost personified claim about an
abstract property, applied to a "machine." Reads as compressed shorthand for something like "a
device that was never tracked under per-domain comprehensiveness from day one can't retroactively
be held to a fleet-wide comprehensive standard" — worth spelling out.

**Finding 5.4 — minor.** Register: the document as a whole holds a fairly consistent
dry-technical-with-occasional-vivid-metaphor voice ("brochure diagram," "severs every management
path," "the honest fix is") that works well for the stated plain-language goal. The exception is
§9's citation paragraph (Finding 4.3) and §17's three ceiling bullets (Finding 5.5), both of which
lurch into denser, more abstract, paper-register prose without a matching drop in information
density — i.e., they don't just use bigger words, they pack more independent claims per sentence
than the rest of the document does.

**Finding 5.5 — minor.** §17's three bullets are each one long compound-complex sentence pair
doing a lot of work: a general claim, a concrete threshold, and a named alternative architecture,
all in two sentences. Example: "Local-first reporting stops paying for itself once a fleet-wide
query becomes routine rather than exceptional. A JSONL record per device is free for as long as
'did host X converge' is the dominant question. Once 'did the rollout land everywhere' needs an
answer with bounded staleness often enough to matter, the honest fix is a central statistics
spine (the shape Bcfg2 already builds), not a federation layer retrofitted onto a local-first
design." Three sentences, three separate claims (a rule, a boundary condition, a named
alternative with a parenthetical citation) is dense for a document otherwise willing to use short
sentences. Not wrong, just harder going than the rest of the guide — a reader is likely to reread
each bullet once.

**Finding 5.6 — nit.** §2's opening diagram uses "TUF-subset" and "Augments" before either is
defined (Finding 1.3 covers TUF; "Augments" is at least defined two paragraphs later in the same
section's prose, which is better). Minor inconsistency in how much the diagram assumes versus how
much the prose immediately below it explains.

**Finding 5.7 — nit.** The phrase "confidently and plausibly" in §9 ("an agent will violate it
confidently and plausibly — which is worse than violating it obviously") is a strong, memorable
line and one of the clearest sentences in the document — flagged only as a positive example, no
change needed. Worth knowing what's working, not just what isn't.

**Finding 5.8 — minor.** Overall jargon-without-gloss count is modest but present: `def.json` /
`host_specific.json` (§4, shown as filenames with no explanation of what distinguishes them from
each other), "Promise Theory" (linked in §2 on first mention but not characterized in prose until
§5, two sections later — a reader who doesn't click the link carries an unexplained term for a
section and a half), and "ncf" (§5, §11 — glossed as "a vendored, stripped reference," which
tells the reader what it's *not* more than what it *is*).

---

## 6. Numeric claim verification

Both claims were checked against primary sources (PDFs fetched and text-extracted directly, not
via secondary summaries).

### Claim A — Bcfg2 booklet, §11 of the guide

> "Bcfg2's booklet records a first client run of `Total managed entries: 0 / Unmanaged entries:
> 2308`."

**Confirmed, exact match.** Source: Desai and Lueninghoener, *Configuration Management with
Bcfg2*, USENIX Short Topics in System Administration #19 (2008), retrieved from
`https://2459d6dc103cb5933875-c0245c5c937c5dedcca3f1764ecc9b2f.ssl.cf2.rackcdn.com/books/19_bcfg2.pdf`
(USENIX-hosted copy). Exact text from the extracted PDF, describing the client's first output:

```
Correct entries:             0
Incorrect entries:           0
Total managed entries:       0
Unmanaged entries:           2308
```

with the surrounding sentence: "At this point, the number of the goals ('Total managed entries')
is 0, so 0 correct entries are expected... The final number, unmanaged entries, are entries that
exist on the client (and can be detected), but were not included in goals. Over time, we will
reduce this number and increase the above three." This is the *first* run shown in the booklet;
a later passage in the same booklet (after `bcfg2-admin init`) shows a second run with `Total
managed entries: 1 / Unmanaged entries: 2308` — the guide's citation of the *first* run's figures
is accurate and matches the more dramatic (0 managed) illustration, not the immediately-following
one. No discrepancy found.

### Claim B — technical paper §7, Bcfg2 deployment figures

> "four months, one person, roughly three FTE of maintenance before and between a third and a
> half of an FTE after, across a division of about two hundred people."

**Confirmed, exact match.** Source: N. Desai, R. Bradshaw, et al., *A Case Study in Configuration
Management Tool Deployment*, LISA '05, retrieved as
`https://www.usenix.org/legacy/events/lisa05/tech/full_papers/desai/desai.pdf`. Extracted text:

- "Deploying Bcfg2 took approximately four months of work performed primarily by one person."
- "We estimate that before conversion three FTEs of time were spent on the maintenance of our
  workstation and server environment... After conversion, between one-third and one-half of an
  FTE is consumed by these activities."
- "The Mathematics and Computer Science Division of Argonne National Laboratory consists of
  nearly 200 researchers, programmers, students, and visitors."

All four figures (four months, one person, three FTE before, one-third-to-one-half FTE after,
~200-person division) match the paper's §7 citation precisely, including the "roughly" hedge on
three FTE (source says "We estimate... three FTEs," i.e., an estimate, which "roughly" fairly
represents) and "about two hundred" for "nearly 200."

**Note on source retrieval, not on the claim itself:** the first attempt to fetch the LISA '05
PDF via `usenix.org/legacy/publications/library/...` (the URL form linked in both the guide's §2
and the paper's Further Reading list) returned a 404 — that path appears to have been
reorganized. The working URL uses `usenix.org/legacy/events/lisa05/...` instead. This is a
citation-link-rot risk worth flagging separately from the content verification: the *numbers* are
correct, but if either document's hyperlink uses the `/legacy/publications/library/...` form
anywhere, that link may be dead. Spot-checked: the guide's §2 uses
`usenix.org/legacy/publications/library/proceedings/lisa05/tech/full_papers/desai/desai.pdf`
(the dead form); the guide's Further Reading list item 2 uses the same dead form. **Minor,
separate from the numeric-accuracy question:** consider updating both links to the
`/legacy/events/lisa05/...` form confirmed working above.
