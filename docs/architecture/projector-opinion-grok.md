<!-- Provenance: independent cold pass by Grok 4.6 (xAI), run headless via
     `grok -p` on 2026-08-16, from the shared prompt recorded in
     projector-reconciliation-2026-08-16.md §0. The model had read
     access to the repo and wrote nothing; this file is its stdout,
     unedited except for this header. FROZEN INPUT — superseded by
     the reconciliation; do not edit to bring it up to date. -->

# Projector mapping opinion

**Author:** Grok 4.6 (xAI), independent mapping pass, 2026-08-16.
**Decided, not reopened:** device-side projector inside tendcf-agent, after approval; target `$(sys.workdir)/data/host_specific.json` only; envelope `{"vars": {…}}` with no sibling keys (reconciliation §9; architecture-DEFINITIVE-v3 near line 437).
**Empirical extra, not in the brief:** CFEngine Core 3.27.1 (`/opt/homebrew/bin/cf-agent --version`) against a throwaway `CFENGINE_TEST_OVERRIDE_WORKDIR`, read against `~/src/cfengine-core/libpromises/cmdb.c` (the 3.27.1 CMDB loader). Used only to settle what `vars` *becomes* in this slot.

## Position

Project only what CFEngine must actuate. That is the `supervision` kinds `service` and `interlock`, including every `state: "absent"` service tombstone, copied field-for-field into two data-container vars. `device-trust` does not appear in `vars` at all — it is the agent's own configuration, and the agent already holds the approved goal file. `unit-writer` and coverage stay with the agent too: they are detector and consent metadata, not mutation input. The projection is a structural re-keying with a closed kind table, not a rewrite into `service_policy` / `@{secrets.*}` / Site Model nicknames; those are how the guide §16.A illustration *describes* a derivation, and 3.27.1 will not even load two of its top-level keys.

## A. Which entries project

**`device-trust` does not project.** Advisor keys, the agent digest, the policy-tree digest, and the consent tuple (`tier`, `local_yes_required`) are consumed by tendcf-agent — the validator, the TUF fetch, the local-yes gate. The schema already says so: “The validator and agent read their own configuration ONLY from here” (`schema/goal-file.schema.json`, `trust_domain`). A second copy under `vars` is a second source of truth, and it is a worse one: 3.27.1 installs CMDB vars into the eval context tagged `source=cmdb` (`cmdb.h` `CMDB_SOURCE_TAG`; acceptance test `11-augments-no-override.cf` shows `--show-vars` printing that tag). Advisor public keys and the consent tier would then be visible to every bundle, to `cf-promises --show-vars`, and to anything that iterates `data:variables`. That is a privilege leak of the region the validator treats as “any hunk under `device-trust`.”

I disagree with reading residue R21 (“trust entries → the agent's own config”) as a *projector output*. The projector's only file is `host_specific.json`. The agent's own config is the approved goal file. Re-keying trust into Augments so the agent can read it back is a round trip with no consumer on the CFEngine side and a larger trusted computing base on the CFEngine side.

`host` and `schema_version` likewise stay out. Replay protection and fail-closed versioning are validator work, finished before the projector runs.

**From `supervision`, project `service` and `interlock`. Do not project `unit-writer` or `coverage`.** Extra-entry detection is report-only, indexed in tendcf-agent's SQLite (architecture-DEFINITIVE-v3 §8; guide §11). The schema calls a writer declaration “detector data, not actuated state.” Putting the prefix table into `vars` would give the generic bundle the information it would need to grow an enforce-mode sweeper — the mode the reconciliation explicitly deferred. Coverage is how the validator and the briefing interpret silence; it is not an actuation handle. The generic bundle promises about what is in `tendcf_service`, not about what the domain's coverage enum means.

The projector's include table is therefore keyed by **domain class and kind**, not by inspecting entry values:

- skip the reserved `device-trust` domain entirely;
- from every `state_domain`, copy `entries.service` and `entries.interlock` when present;
- refuse the whole projection on an unknown `schema_version` or an unknown kind (fail closed, matching E1 §5.6; the validator should already have refused, this is belt and braces).

That is a closed re-keying table. It is not the R21 tripwire (value-inspecting structure).

## B. Key shape inside `vars`

**A closed set of container keys, never flat scalars, never `$(def.NAME)`.**

The question's `$(def.NAME)` / `@(def.NAME)` framing is true of **`def.json` Augments** (`generic_agent.c` `LoadAugmentsData`: unscoped keys get `ref->scope = "def"`). It is **false of the decided target**. `host_specific.json` is the CMDB loader in `cmdb.c`, not that Augments path. Unscoped `vars` keys are installed as `data:variables.<key>` (`GetCMDBVariableRef`, `cmdb.c` lines 96–118: default ns `"data"`, default scope `"variables"`). Live against 3.27.1: a scalar `vars.hello = "world"` reports as `$(data:variables.hello)=world` and leaves `$(def.hello)` unexpanded. The same run warns `Invalid key 'data' … skipping it`, which is why guide §16.A's illustration injects nothing.

Flat scalar keys are additionally the wrong type. `AddCMDBVariable` (`cmdb.c` 131–160) does three things:

- a JSON primitive becomes a **string** (`JsonPrimitiveToString`: bools `"true"`/`"false"`, integers `StringFromLong`);
- a JSON array of primitives becomes an slist;
- anything else — including every object — becomes a **data container**, JSON types preserved.

Booleans (`keep_alive`, `report`) and integers (`expect_exit`, `timeout_seconds`) only survive as booleans and integers if they live *inside* a container. I confirmed this live: `$(data:variables.tendcf_service[com.tendcf.caddy.main][unit][launchd][keep_alive])` printed `true`; `$(data:variables.tendcf_interlock[caddy-config-valid][pre_action][expect_exit])` printed `0`. Flatten those fields to top-level `vars` and 3.27.1 stringifies them. Dots in a *vars key* are also not identity: `VarRefParse` treats `com.tendcf.caddy.main` as scope/lval. Dots in a *container index* are fine — `getindices("data:variables.tendcf_service")` returned both launchd labels.

**Naming rule.**

1. The only legal `vars` keys are `tendcf_` + the goal-file kind, with every `-` replaced by `_`.
2. v1 therefore admits exactly `tendcf_service` and `tendcf_interlock`.
3. Each value is one JSON object, keyed by the goal-file entry id (the promiser: launchd label, interlock id). Identity is not rewritten to a Site Model nickname.
4. The entry body is copied as-is. No field is added, renamed, dropped, or derived. `bundle`, `state`, `env`, `unit`, `blocks`, `report` travel unchanged.
5. CFEngine addresses them as data containers, for example `$(data:variables.tendcf_service[com.tendcf.caddy.main][state])` and `getindices("data:variables.tendcf_service")`.

I considered a dedicated namespace key (`tendcf:goal.service`). 3.27.1 accepts it — `$(tendcf:goal.service[com.tendcf.caddy.main][state])` resolved in the same probe. I am not taking it. It is extra address syntax the generic bundle does not need, and `data:variables.tendcf_*` plus the `source=cmdb` tag already mark ownership. Do not aim namespaced keys at `default:def.*` either: that is how you stomp MPF glue, and host-specific data already wins over `def.json` (`11-augments-no-override.cf`: “Cannot set variable … from augments, already defined from host-specific data”).

Disagree with using the guide's `nix2cf_services` / `launchd_label` / `service_policy` shape as the target. `nix2cf_` is a pre-rename leftover. `launchd_label` is a second spelling of the map key. `service_policy` is a CFEngine *promise attribute* the generic bundle writes after reading `state`; putting it in the projection is the projector interpreting. That is the R21 tripwire.

## C. `state: absent` entries

**They appear.** `com.tendcf.caddy.retired` is present in `tendcf_service` as `{"state":"absent"}` and nothing else.

Omission is the other spelling of “stop managing,” which the briefing must already distinguish from “remove from the device” (reconciliation §6; architecture-DEFINITIVE-v3 §9.8). Extra-entry detection *reports*; it does not unload. If the tombstone is dropped from the projection, a comprehensive domain has no actuated removal path — R4 reborn in the domains that were supposed to be finished. A crash mid-apply, a second `cf-agent` run, or an N−7 → N catch-up would all converge to “the retired unit is not mentioned,” which under CFEngine is “leave it alone.”

The safety argument for omission — “a mistaken tombstone could stop something” — is a consent argument, not a projection argument. The person approved `state: "absent"`. Hiding the approved removal from the mutation engine does not make a mistake safer; it makes an *intentional* removal non-convergent.

They go in the **same** map, not a parallel “negative-promise list.” R21's phrase “tombstones → the negative-promise lists” is the wrong structure. Splitting on the value of `state` is exactly “inspects entry values to decide output structure.” One container, `state` copied, generic bundle branches. Policy interpretation belongs in the digest-bound `.cf` tree, not in the projector.

## D. Secrets

**Emit the name, verbatim:**

```json
"env": { "CADDY_ADMIN_TOKEN": "CADDY_ADMIN_TOKEN" }
```

Not a resolved value. Not `@{secrets.CADDY_ADMIN_TOKEN}`. Not `$(secrets.CADDY_ADMIN_TOKEN)`.

Three independent reasons this cannot launder a real secret into `$(sys.workdir)/data/host_specific.json`:

1. **The projector is a pure function of the goal-file bytes.** It has no secretspec handle and must not grow one. Resolution is a run-time act of the unit wrapper / generic bundle (`schema/common.schema.json` `$defs/env_map`: “Values are secretspec key NAMES, never secret values … resolved at run time by secretspec”).
2. **The goal-file schema already refuses non-names.** `env_map` values are `^[A-Z][A-Z0-9_]*$`. A live token (`sk-live-…`, a hex key, anything that is not a NAME) cannot be in a conforming input, so it cannot be in a conforming projection. Fixture `examples/broken/06-literal-secret/` exists for the authoring side of this rail.
3. **3.27.1 will reject the guide's rewrite, and would publish a real value if one ever arrived.** `StringContainsUnresolved` (`var_expressions.h` 90–97) treats `$(`, `${`, `@{`, `@(` as variable references. `ReadCMDBVars` then errors `Invalid 'vars' CMDB data, cannot contain variable references` and **fails the entire CMDB load**. I reproduced this: `@{secrets.CADDY_ADMIN_TOKEN}` yielded that error twice (parse + load) and left every `data:variables.*` reference unexpanded. So the guide §16.A `@{secrets.LITELLM_MASTER_KEY}` illustration is not an alternative encoding — it is a payload 3.27.1 refuses. Conversely, a real secret that slipped through would become a CMDB variable: on disk under `data/`, tagged `source=cmdb`, printable via `--show-vars`, eligible for promise logs. The workdir `data/` directory is created mode `0700` in CFEngine's own tests (`01-vars.cf`); that is access control on a file that must still contain only names.

The generic bundle may call `sudo-secretspec` / `secretspec run` at exec time, or write a launchd plist whose `EnvironmentVariables` are filled by a wrapper. None of that is the projector's job, and none of it writes secret material into Augments.

## E. Interlocks

**They project**, into `tendcf_interlock`, body copied as-is. They do not belong only in the policy tree.

An interlock is per-host consented data: argv, `expect_exit`, `timeout_seconds`, `defines_class`, `bundle`. Privilege is “any hunk under `device-trust`, plus the header.” Changing `caddy-config-valid`'s command is an ordinary `supervision` hunk. Baking that argv into a `.cf` file makes the same change a `policy-tree` digest change — privileged, two-phase, the wrong ceremony for “the Caddyfile moved.” It also fights D15 (compile target is Augments, not freehand `.cf`) and fights per-host variation under one shared tree digest.

Guide §16.B's `bundle agent fleet_vpn` with a hardcoded `returnszero(...)` is an illustration of *effect*, not of *source*. The digest-bound generic bundle is an argv runner: for each entry in `tendcf_interlock`, run `pre_action.command`, require `expect_exit` within `timeout_seconds`, define `defines_class`, and block the referenced `bundle`. `blocks` and `report` are schema consts; they are still copied (policy-free) and implemented as code in the tree, not as a top-level Augments `classes` key. The projector must not emit `classes`. Defining `caddy_config_ok` is the runner's job after the probe succeeds.

Deleting an interlock is a remove hunk, not a tombstone (no device-state footprint). After deletion it simply stops appearing in `tendcf_interlock`; the runner stops running it. That is the correct “guard removed.”

## F. Determinism

`project(x)` is the RFC 8785 (JCS) serialization of the object below, using the same `rfc8785.dumps` `bin/schema_lint.py` already pins. The golden is those bytes, compared with `==`, never pretty-printed, never normalized at the test boundary.

Rules that make that equality hold:

1. **Envelope.** Always `{"vars": {…}}`. `vars` is present even when empty (`{"vars":{}}` is the projection of a host with nothing to actuate). No other top-level key.
2. **Kind containers.** Emit `tendcf_service` / `tendcf_interlock` iff the corresponding map is non-empty after the copy. Omission is the only spelling of “none,” matching the goal file. Never `null`, never `{}`, never `[]` as a kind container.
3. **Key order** is JCS's (UTF-16 code-unit order). The projector does not sort; the serializer does. ASCII ids in this fixture therefore come out `tendcf_interlock` then `tendcf_service`, `com.tendcf.caddy.main` then `com.tendcf.caddy.retired`.
4. **Numbers** remain JSON integers. `0` and `30`, never `0.0`, `30.0`, `3e1`. The projector does not parse numbers as IEEE floats. (3.27.1's Augments path has already been observed to reformat `3.5` → `3.50`; we must not introduce a `number` in the first place. The goal-file schema forbids floats; the projection inherits that.)
5. **Booleans** remain `true` / `false`, lowercase, unquoted.
6. **Strings** are copied as NFC bytes from the already-canonical goal file. The projector does not NFC, denormalize, or rewrite paths.
7. **Arrays** whose order is meaning (`command`, `pre_action.command`) keep input order. JCS does not reorder arrays.
8. **No derived fields, no dropped fields, no default insertion.** An absent service is exactly `{"state":"absent"}`. A present service without `env` has no `env` key.
9. **No insignificant whitespace, no trailing newline.** The 645-byte JCS form of the worked object below is the golden; `rfc8785.dumps` emits no `\n`.
10. **Id collision across domains** (two `service` entries with the same promiser) is a refuse, not last-wins. JSON objects cannot be honest about duplicate keys; last-wins would be a silent interpreter.

CFEngine's own `format("%S", …)` dump of a container is *not* JCS and is not the golden. Only the file the projector writes is.

## G. The negative

Section 13 already refuses any top-level key other than `vars`. The suite should also refuse:

1. **Top-level `variables`.** 3.27.1's second spelling of `vars`; loaded after `vars` and able to overwrite (`cmdb.c` 550–560). Metadata form `{value, tags, comment}` is how you smuggle comments into the mutation input.
2. **Top-level `classes`.** The remaining legal CMDB key (`cmdb.c` 541–546). Emitting `caddy_config_ok` from the projector is the interpreter defining classes; the runner defines them after a probe.
3. **Any string containing `$(`, `${`, `@{`, or `@(`.** 3.27.1 rejects the entire `vars` object. This catches the guide's `@{secrets.NAME}` rewrite as a mechanical negative, not a style note.
4. **Any `env` value that is not a NAME** (`^[A-Z][A-Z0-9_]*$`), or that differs from a declared secretspec key. Names only.
5. **`device-trust` content under `vars`** — advisor keys, `policy-tree` / `agent` digests, `trust-policy.consent`. Privilege in the CMDB.
6. **`unit-writer` or `coverage` under `vars`.** Detector / silence-class data in the mutation input.
7. **Derived or preview-channel fields:** `service_policy`, `launchd_label`, `nix2cf_edges`, `origin`, `rule`, `source`, Site Model nicknames as map keys (`caddy` instead of `com.tendcf.caddy.main`).
8. **Non-JCS bytes:** pretty-print, trailing newline, unsorted keys, `30.0`, `null`, empty kind containers.
9. **A `vars` key outside the closed set** `tendcf_service` / `tendcf_interlock` (including `tendcf_unit_writer`, `nix2cf_services`, and any `default:def.*` stomp).
10. **Writing `def.json`, or a path other than `$(sys.workdir)/data/host_specific.json`.** `def.json` drops unknown keys *silently* and is MPF glue under the policy-tree digest.
11. **YAML.** 3.27.1 JSON only (guide §4, corrected).
12. **A payload larger than 5 MiB.** `HOST_SPECIFIC_DATA_MAX_SIZE` in `cmdb.c` line 38; oversize is a hard load failure, not a warning.

## Worked projection

Complete image of `project(examples/goal-file.json)`. Pretty-printed here for review; the checked-in golden is the RFC 8785 serialization of this object (645 bytes, no trailing newline, produced by `rfc8785.dumps`).

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

What this file deliberately does not contain: the host key, `schema_version`, anything under `device-trust`, the `com.tendcf.caddy.*` writer, either domain's `coverage`, `service_policy`, `launchd_label`, `nix2cf_edges`, or a resolved admin token.

## Costs and what I'd give up

The strongest argument against this mapping is that **projecting interlocks makes the generic bundle an argv runner**, and argv in Augments is code in all but name. A consented `pre_action.command` of `["rm","-rf","/"]` will execute if the runner is faithful. Baking interlocks into the policy tree would put that argv under the tree digest and the privileged ceremony.

I accept the cost because the same hole already exists for `service.command` — that is the D15 bargain — and because the alternative privileges an ordinary supervision hunk. The consent object is where the person already said yes to those bytes; moving the yes onto the tree does not shrink the trusted computing base, it mislabels the change.

A close second: **keeping `device-trust` out of `vars` means CFEngine policy cannot branch on consent tier.** Someone will want `ifvarclass => "tendcf_consented"`. That would be the mutation engine interpreting the gate, which is the validator's job, done before projection. If a report row needs the tier, the agent already has it. I would rather explain a missing class than debug a bundle that loosened a gate the person did not re-approve as policy.
