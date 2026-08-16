<!-- Provenance: independent cold pass by Grok 4.6 via Cursor, run headless via
     `cursor-agent -f -p` on 2026-08-16, from the shared prompt recorded in
     projector-reconciliation-2026-08-16.md §0. The model had read
     access to the repo and wrote nothing; this file is its stdout,
     unedited except for this header. FROZEN INPUT — superseded by
     the reconciliation; do not edit to bring it up to date. -->

# Goal-file projection mapping opinion

**Author:** Cursor Grok 4.6, independent mapping pass, 2026-08-16.
**Question:** the device-side projector’s *mapping* — which goal-file entries become `{"vars": {…}}`, under what names, and with what byte-stability rules.
**Binding inputs:** `examples/goal-file.json` (RFC 8785 bytes; inspected via `python3 -m json.tool`); `schema/goal-file.schema.json`; reconciliation 2026-08-15 §§9 and 13; guide §16.A (illustrative only); architecture-DEFINITIVE-v3 projector passage (~L437); CFEngine Core 3.27.1 (`/opt/homebrew/bin/cf-agent --version`) plus the 3.21/3.27 Augments reference.
**Already closed, not reopened:** device-side, inside tendcf-agent, after approval; target `$(sys.workdir)/data/host_specific.json` only; envelope `{"vars": {…}}` with no sibling keys.

This note does not edit any file. The worked projection is the falsifiable artifact.

---

The projector is a policy-free re-key of *actuated supervision entries* into two CFEngine-legal container variables, `tendcf_service` and `tendcf_interlock`. `device-trust` and `unit-writer` do not appear: the agent already consumed them from the goal file, and copying them into Augments would give the mutation engine a second, ignore-unknown-tolerant spelling of privileged and detector state. Tombstones project in the same map as live units, keyed by the same device-natural id, with `state` copied through — the generic bundle, not the projector, turns `absent` into a stop/unload. Secret *names* copy; secret *values* cannot, because the projector has no resolver and `env_map` cannot spell one. The golden is the RFC 8785 serialization of that object and nothing else.

## A. Which entries project

**Only `supervision.entries.service` and `supervision.entries.interlock`.** Nothing under `device-trust`. Nothing from `unit-writer`. Nothing from coverage declarations, `host`, or `schema_version`.

`device-trust` is the privileged region the validator and agent read *only from the goal file* (reconciliation §7: “trust content misfiled elsewhere is inert, not covert”). Projecting it into `vars` would make it *covert in the other direction*: cf-agent 3.27.1 would materialize advisor keys, the consent tier, the policy-tree digest, and the agent binary pin as CMDB-tagged runtime data, readable by every generic bundle. That is a second spelling of facts whose first spelling is the consent object, and it couples the mutation engine to the gate. The agent binary pin and the tree digest are consumed *before* projection (load the tree; know which projector ran). The consent tier and advisor keys are consumed *at* approval. None of them is a promiser CFEngine should converge.

I agree with reconciliation §9’s residue R21 destination — “trust entries → the agent’s own config” — and I tighten it: that config is **not** `host_specific.json`. The projector’s only file is `{"vars": {…}}`. Agent config is in-process state (or the agent’s own baseline reader). Stuffing trust under `vars` so it “has a home” is how privilege flags come back, wearing an Augments costume.

`unit-writer` is the same category error on the detector side. The schema is explicit: the *device* runs extra-entry detection and does not have the Site Model; the writer map is detector data, present-only, not actuated state. Extra-entry *reports* and does not remove (reconciliation §6, D16(d)). A generic bundle iterating `tendcf_service` already has the units it is allowed to write; it does not need the prefix registry to render them. Projecting the registry would invite a bundle to treat `com.tendcf.caddy.*` as a unit.

Coverage does not project because it has already done its job: a `deliberately-unmanaged` domain cannot carry entries, so there is nothing to re-key; a `not-yet-migrated` or `comprehensive` domain contributes exactly the entries it names. Silence vs description is a goal-file property. Repeating `coverage: comprehensive` inside `vars` would be a second spelling the generic bundle must not interpret.

**Disagreement with a loose reading of R21.** “Entries → the generic bundle’s containers” is not “every entry.” It is every entry the generic bundle *actuates*. Trust and writer declarations are not those.

## B. Key shape inside `vars`

**Two container keys, not flat scalars. Naming rule, not an example:**

1. The only legal `vars` members are `tendcf_<kind>`, where `<kind>` is a projected goal-file kind and every hyphen in the kind token is replaced by `_`. v1 therefore admits exactly `tendcf_service` and `tendcf_interlock`.
2. Each container is a JSON object whose keys are the goal-file entry ids, copied verbatim (dots, hyphens, and all).
3. Each value is the entry body, copied verbatim — same members, same types, no invented fields, no dropped consts.
4. No other `vars` key exists. No `tendcf_host`, no `tendcf_coverage`, no `nix2cf_*`.

Why containers, and why this spelling:

CFEngine 3.21/3.27 Augments `vars` keys may contain `.` and `:` as *namespace/bundle targeting* (`"MyBundle.MyVariable"`, `"MyNamespace:MyBundle.MyVariable"` — Augments reference, `vars` key, history 3.18.0). A flat key `com.tendcf.caddy.main` is therefore not a friendly name; it is a scope path. Unit ids *are* dotted launchd labels. Putting them at the `vars` top level would either mis-scope the variable or fail as an identifier. Hyphens are not CFEngine identifier characters; `tendcf-service` is not a legal `$(…NAME…)` token. The hyphen→underscore rewrite applies only to the closed kind enum (two ASCII tokens), never to entry ids.

Nested objects under a single `vars` key become one data container. Top-level arrays become slists; arrays *inside* a container stay JSON arrays (Augments `vars` examples: `"slist1": […]` at top level vs `"array1": {…}` as a container). `command` and `pre_action.command` are semantic arrays. They must remain nested so their type does not flip with depth.

The generic bundle iterates with `getindices()` / `$(container[$(id)])`. It must never expand a dotted unit id as a literal `$(container[com.tendcf.caddy.main])` path. That is a policy-tree convention, not a projector transform: canonifying ids into `com_tendcf_caddy_main` would be a second spelling of the promiser the schema just made identical to the launchd label.

**Disagreement with the brief’s `$(def.NAME)` shorthand, and with guide §16.A / Fable’s `nix2cf_services`.** `$(default:def.NAME)` is the *`def.json` `vars`* default (Augments reference). `host_specific.json` is a different slot: loaded first, tagged `source=cmdb`, and — on the 3.27.1 run already in this corpus (Grok schema opinion §8.5) — a `vars` object lands at `data:variables.<key>`. Official pages disagree with each other about `data:variables` vs `data:main` for the `variables` *key*; they do not clearly restate the `vars` key’s host_specific default. The projector therefore emits unqualified identifiers and lets 3.27.1’s host_specific default apply. Forcing `"default:def.tendcf_service"` would encode namespace policy in the projector and collide with MPF glue in `def` — the reason `def.json` was rejected as a per-host slot. The generic bundle binds to whatever namespace that default actually is; a JSON golden will not catch a bundle looking at `$(def.tendcf_service)` and seeing nothing. That is a policy-tree test, named so it is not forgotten.

Guide §16.A keys by Site Model nickname (`caddy`), invents `service_policy` and `launchd_label`, and prefixes `nix2cf_`. The schema dropped `launchd.label` because the id *is* the label. `nix2cf` is an optional tool fork (guide §4 / v3 tool-fork table), not the consent path. I reject that vocabulary.

## C. `state: absent` entries

**They appear.** `com.tendcf.caddy.retired` is present in `tendcf_service` as `{"state":"absent"}`.

Reconciliation §6 already decided removal is a state, not an event, including in comprehensive domains: extra-entry detection reports and does not remove, so the tombstone is the only actuated removal path. A projector that omits `absent` entries re-opens R4 at the last possible moment. The negative promise would exist only in the goal file the mutation engine does not read. Crash, re-run, and N−7→N catch-up would all converge “not in the map” as “not my problem,” which is the meaning of *omission*, not of *absent*. The briefing already has to distinguish “stops being managed; the thing REMAINS” (bare deletion) from “will be stopped and unloaded” (tombstone). The projection must preserve that distinction or the ceremony is lying about what cf-agent will do on the second run.

The safety argument for omission — “absent means invisible, so we cannot accidentally stop something we only meant to forget” — is real and I reject it. Forgetting is bare deletion, a different hunk, a different briefing sentence. Hiding a tombstone to make actuation safer makes actuation *undefined*. The dangerous operation is dropping a tombstone (R19), and that remains a reviewed goal-file change, not a projector heuristic.

I also reject splitting tombstones into a sibling list (`tendcf_service_absent`). That inspects `state` to decide output *structure*, which is the R21 tripwire (v3 ~L455; reconciliation §9). One map, `state` as a field. The generic bundle builds the stop/unload promises at eval time. That is policy, digest-bound in the tree, which is the right place for it.

## D. Secrets

**The projection emits the name, as a name:**

```json
"env": { "CADDY_ADMIN_TOKEN": "CADDY_ADMIN_TOKEN" }
```

That is a copy of the goal-file member. It is not `@{secrets.CADDY_ADMIN_TOKEN}`, not an interpolated value, not an omitted key, not a resolved token.

`schema/common.schema.json` `$defs.env_map` (reused by the goal-file schema) constrains *both* the environment variable and its value to `^[A-Z][A-Z0-9_]*$`. A real secret value cannot pass that pattern. The projector is a JSON-to-JSON re-key with no `sudo-secretspec` client, no provider, and no environment of secret values — the same privilege boundary the sudo-secretspec skill already enforces for humans and agents. `host_specific.json` lives in `$(sys.workdir)/data/`, typically mode-accessible to cf-agent and anything that can read the workdir. A projector that resolved names would be the process that *wrote a secret onto disk next to policy*. That is the laundering path, and it is closed by construction: there is no call site.

Guide §16.A’s `@{secrets.LITELLM_MASTER_KEY}` is a second spelling and looks like resolution already happened. I reject it. Runtime resolution belongs to the unit writer / generic bundle at activation, via `sudo-secretspec`, and the value must never be written back into Augments.

If a proposer ever stuffed a high-entropy string into `env`, the *goal-file* schema refuses the file before approval. The projector is not a second validator of that; it is not a resolver either.

## E. Interlocks

**They project**, into `tendcf_interlock`, keyed by interlock id, body copied whole (`bundle`, `defines_class`, `blocks`, `report`, `pre_action`, `state`).

They do not belong *only* in the policy tree. The tree is a digest-bound, privileged `device-trust` artifact. Baking `caddy-config-valid` into `.cf` would make every guard edit a privileged tree-digest hunk — the wrong ceremony class for a Caddyfile validate. Interlocks are per-host intended state (the goal file already addresses them as `(supervision, interlock, id)`). The tree carries the generic runner (run `pre_action.command`, require `expect_exit`, define `defines_class`, block the enclosing bundle, report). The Augments file carries the instances.

`blocks` and `report` are schema consts. They still copy. Dropping consts because “the bundle knows” is a hidden default in the projection, the two-spellings defect the goal file exists to forbid. Grouping interlocks under their `bundle` key in the projector would inspect a value to decide structure (R21 again). The runner groups at eval time.

Present-only: there is no interlock tombstone in v1 (schema: no device-state footprint). Deleting one is a remove hunk; it disappears from `tendcf_interlock`. That is correct — a removed guard must not keep firing from a stale negative.

## F. Determinism

`project(x)` is a pure function of the approved goal-file bytes. Rules that make it byte-stable:

1. **Envelope.** Exactly `{"vars": <object>}`. No sibling keys, ever.
2. **Canonicalization.** The written file and the CI golden *are* the RFC 8785 (JCS) serialization of that object: UTF-16 code-unit member order, compact separators, no pretty-print whitespace, no trailing newline (same exemption as `examples/goal-file.json`, reconciliation §13). Python `json.dumps(…, sort_keys=True, separators=(',', ':'))` matches JCS for this ASCII-only v1 vocabulary; that equivalence is *not* the definition — JCS is. A pretty-printed twin is a negative, as with the goal file.
3. **Key set.** Emit `tendcf_<kind>` iff that kind’s map in the goal file is non-empty after the projectable-kind filter. Omit the container rather than emit `{}`. `vars` itself is always present: no projectable entries ⇒ `{"vars":{}}`. That is the one empty object the envelope requires; empty-vs-omitted is otherwise forbidden.
4. **Inner keys.** Goal-file entry ids, JCS-ordered (identity-keyed maps already are). No canonify, no sort override.
5. **Bodies.** Deep copy of present members only. Omitted goal-file keys stay omitted (`env` absent ⇒ no `"env":{}`). No `null`. No default insertion.
6. **Numbers.** JSON integers only, JCS integer spelling (`0`, `30`). `30.0` and `1e1` are negatives. The projector does not admit JSON `number` that is not an integer; it has nothing to reformat. 3.27.1 *will* load a float and display-reformat it (`3.5` → `3.50` — Grok schema opinion, empirical); that is why we never emit one.
7. **Booleans.** `true` / `false`, JCS spelling. Not `"true"`, not `1`.
8. **Arrays.** `command` / `pre_action.command` preserve input order. JCS does not sort arrays; neither do we. These are the only semantic arrays in the file.
9. **Strings.** Copied from the already-NFC, already-JCS goal file. No `$(sys.…)` expansion (Augments: sys expansion is a `def.json` behavior, not documented for `host_specific.json`; we do not rely on it).
10. **No Augments dual spellings.** Never `variables` (3.27.1: if both `vars` and `variables` set the same name, `variables` wins — Augments reference). Never `classes`, `inputs`, `augments` (`host_specific.json` does not support `augments`; 3.27.1 would warn-and-skip it). Never YAML.

The projector must not consult the diff, the previous projection, the clock, or the environment. Tombstones in the new file are sufficient (reconciliation §6).

## G. Further negatives

Section 13 already refuses any top-level key other than `vars`. Add these. Each is a distinct backdoor, not a restatement of that one.

| Negative | Why §13 does not already cover it |
| --- | --- |
| `variables` present *inside* `vars` as a nested key, or a second serialization that uses the `variables` Augments key at top level | Top-level `variables` is the §13 case; the *win-over-`vars`* dual spelling is the 3.27.1-specific hazard and wants its own fixture |
| Guide-shaped payload under `vars`: `nix2cf_services`, `nix2cf_edges`, `service_policy`, `launchd_label`, `@{secrets.…}` | All four are preview-channel residue; a `vars`-only envelope can still smuggle them |
| Any `vars` key outside `{tendcf_service, tendcf_interlock}` | Closed kind set; `tendcf_unit_writer`, `tendcf_advisor_key`, `tendcf_host`, `schema_version` are privilege/detector leaks |
| Deep copy of the goal file under `vars` (identity-under-Augments) | Envelope is legal; content is the consent object wearing a costume |
| Canonified or rewritten entry ids (`com_tendcf_caddy_main`, Site Model nickname `caddy`) | Second spelling of the promiser |
| `state: absent` service omitted, or present service missing `state` | C’s fork, as a fixture |
| Split containers (`tendcf_service` + `tendcf_service_absent`) | R21 tripwire, as a fixture |
| Float spelling of an integer (`30.0`, `15.0`) | Byte-class, matching goal-file fixture 48; Augments will load and reformat it |
| Empty container `{}` for a kind, or `"env": {}` | Empty-vs-omitted |
| `null` anywhere | Unrepresentable in the goal file; must stay unrepresentable here |
| Non-JCS bytes of an otherwise-legal object (pretty-print, trailing newline, reordered keys) | Same byte-class rule as the goal file; the golden *is* this test |
| Namespace-qualified `vars` keys (`default:def.tendcf_service`, `data:variables.tendcf_service`) | Encodes 3.27.1 scope policy in the projector; also uses `.`/`:` targeting |
| `env` value that does not match `^[A-Z][A-Z0-9_]*$`, or that differs from the goal-file member | Secret-laundering / mutation |

A projection that is schema-valid Augments and still fails these is the interesting failure. Parser leniency is the enemy; the suite should look like the goal-file negatives: refuse, never normalize.

---

## Worked projection

Complete object the projector emits for checked-in `examples/goal-file.json`. Keys are in JCS order. The CI golden is the RFC 8785 compact serialization of this object (no whitespace, no trailing newline), not this pretty-print.

```json
{
  "vars": {
    "tendcf_interlock": {
      "caddy-config-valid": {
        "blocks": "enclosing-bundle",
        "bundle": "caddy",
        "defines_class": "caddy_config_ok",
        "pre_action": {
          "command": [
            "/opt/homebrew/bin/caddy",
            "validate",
            "--config",
            "/etc/caddy/Caddyfile"
          ],
          "expect_exit": 0,
          "timeout_seconds": 30
        },
        "report": true,
        "state": "present"
      }
    },
    "tendcf_service": {
      "com.tendcf.caddy.main": {
        "bundle": "caddy",
        "command": [
          "/opt/homebrew/bin/caddy",
          "run",
          "--config",
          "/etc/caddy/Caddyfile"
        ],
        "env": {
          "CADDY_ADMIN_TOKEN": "CADDY_ADMIN_TOKEN"
        },
        "run_as": "caddy",
        "state": "present",
        "unit": {
          "launchd": {
            "keep_alive": true,
            "run_at_load": true
          }
        },
        "working_dir": "/"
      },
      "com.tendcf.caddy.retired": {
        "state": "absent"
      }
    }
  }
}
```

JCS bytes of the same object (the golden):

```json
{"vars":{"tendcf_interlock":{"caddy-config-valid":{"blocks":"enclosing-bundle","bundle":"caddy","defines_class":"caddy_config_ok","pre_action":{"command":["/opt/homebrew/bin/caddy","validate","--config","/etc/caddy/Caddyfile"],"expect_exit":0,"timeout_seconds":30},"report":true,"state":"present"}},"tendcf_service":{"com.tendcf.caddy.main":{"bundle":"caddy","command":["/opt/homebrew/bin/caddy","run","--config","/etc/caddy/Caddyfile"],"env":{"CADDY_ADMIN_TOKEN":"CADDY_ADMIN_TOKEN"},"run_as":"caddy","state":"present","unit":{"launchd":{"keep_alive":true,"run_at_load":true}},"working_dir":"/"},"com.tendcf.caddy.retired":{"state":"absent"}}}}
```

What is *not* in this file, on purpose: the entire `device-trust` domain, `unit-writer`, both `coverage` fields, `host`, `schema_version`, `service_policy`, `launchd_label`, `nix2cf_*`, edges, and any resolved secret.

## Costs and what I'd give up

The strongest argument against this position is that the generic bundle must now *interpret* `state` (and iterate dotted keys via `getindices()`), so the “policy-free projector” slogan has pushed a small interpreter into the digest-bound tree. A projector that emitted `service_policy: "start"|"stop"` and a slist of names-to-unload would match the guide’s illustration and the classical CFEngine services promise, and would let a thinner bundle exist. I accept the cost. Inventing `service_policy` is exactly the value-to-structure (or value-to-vocabulary) step R21 names as the interpreter returning *inside the agent binary*. The tree is already privileged, already reviewed as a digest, already the home of “what start/stop means on launchd.” The projector is the one component whose dumbness is a tripwire rather than a theorem; keeping it a copy-and-rename is the cheaper invariant to defend. If the bundle contract later needs a derived slist, derive it in `.cf` from this map — do not grow a second map in the golden.
