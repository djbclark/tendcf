<!-- Provenance: independent cold pass by Gemini 3.1 Pro (Antigravity), run headless via
     `gemini -p` on 2026-08-16, from the shared prompt recorded in
     projector-reconciliation-2026-08-16.md §0. The model had read
     access to the repo and wrote nothing; this file is its stdout,
     unedited except for this header. FROZEN INPUT — superseded by
     the reconciliation; do not edit to bring it up to date. -->

# Goal-file schema opinion

**Author:** Antigravity (Gemini 3.1 Pro), independent cold pass.

## Position in one breath

The projection is a pure, policy-free structural wrap that embeds the entire canonical goal file verbatim into `host_specific.json` under a single `{"vars": {"tendcf": {…}}}` root. It makes no attempt to parse, filter, or re-route entries based on their domain, kind, or state, because doing so would inherently recreate the interpreter this architecture explicitly banished. Every element—including trust data and tombstones—projects exactly as it sits in the goal file. CFEngine's generic bundle, executing device-side, simply addresses the data it needs via `$(def.tendcf[…])` and ignores the rest.

## A. Which entries project at all

**Everything projects.** The entire `domains` map, including `device-trust` and `supervision`, is mapped verbatim. Architecture §9 demands the projector be "policy-free — a structural re-keying only." For the projector to selectively omit `device-trust` or route it to a different file, it would have to know which domains are "engine" versus "state"—an act of semantic interpretation. CFEngine's Augments parser will happily load the `device-trust` subtree into `vars`, and CFEngine's engine will simply never reference those variables. Misfiled trust content remains inert precisely because CFEngine doesn't care it exists, keeping the projector entirely dumb.

## B. Key shape inside `vars`

**One single container key:** `tendcf`. The variables emerge natively as deep paths, e.g., `$(def.tendcf[domains][supervision][entries][service][com.tendcf.caddy.main][command])`. 

Flat scalar keys would force the projector to invent joining delimiters (e.g., `_` or `.`), which creates namespace collisions, escaping complexity, and two spellings of identity. Deep containers perfectly mirror the canonical goal file's map-keyed-by-identity structure, passing the schema's uniqueness properties directly into CFEngine's data model at zero cost.

## C. `state: absent` entries

**Tombstones *must* project inline, and I explicitly disagree with the architecture guide's parenthetical in §9 ("tombstones → the negative-promise lists").** 

Routing an entry to a separate list because its `state` is `"absent"` directly violates the tripwire established in the very same section: it inspects an entry *value* to decide output *structure*. The projector must project `com.tendcf.caddy.retired` directly alongside present services. The CFEngine generic bundle is fully capable of iterating over the `service` map and conditionally executing `service_policy => "stop"` when `$(service[state])` evaluates to `"absent"`. The projector must not do CFEngine's job.

## D. Secrets

**The projection emits the secret *name* verbatim**, just as it appears in the goal file (`"CADDY_ADMIN_TOKEN"`). It absolutely cannot launder the real secret value into `host_specific.json`. 

First, the projector is a pure function of the goal file, which itself contains no secrets, only names. Second, `$(sys.workdir)/data/host_specific.json` is statically written to disk, which would violate the rule that `secretspec` is the sole secret authority. Secrets are resolved dynamically at run time by the CFEngine bundle invoking the `secretspec` adapter.

## E. Interlocks

**Interlocks project exactly where they sit in the data:** `vars.tendcf.domains.supervision.entries.interlock`. They do not belong to the policy tree. 

The policy tree (`.cf` files) is a globally shared, content-addressed artifact. Interlocks, however, are per-host preconditions specific to that host's bundles. They must project into the host's Augments so the generic bundle can read them, test the `pre_action`, and dynamically assert the `defines_class`.

## F. Determinism

The projection inherits its determinism directly from the goal file. The projector's logic is essentially `return RFC8785_serialize({"vars": {"tendcf": parse(goal_file)}})`.

- **Canonicalization:** Output is strict JCS (RFC 8785) UTF-8 bytes with no formatting whitespace.
- **Key ordering:** Lexicographic by UTF-16 code units.
- **Number spelling:** Inherited directly from the goal file (no floats).
- **Absent-vs-empty:** The wrapper introduces no empty collections; it relies entirely on the goal file's existing `minItems: 1` / `minProperties: 1` enforcement.

## G. The negative

Beyond section 13's invariants, a projector test suite must refuse:

1. **The Tripwire Test:** Any projector that produces a different JSON structural shape (excluding the literal field values themselves) when a `state` is changed from `"present"` to `"absent"`.
2. **The Environment Test:** Any projector that produces different output based on environment variables, local file system state, or attempts to execute an external binary (e.g., trying to resolve a secret).
3. **The JCS Encoding Test:** Any output containing spaces, tabs, or newlines between JSON tokens. Pretty-printing is a structural failure.

## Worked projection

```json
{"vars":{"tendcf":{"domains":{"device-trust":{"coverage":"comprehensive","entries":{"advisor-key":{"ed25519:b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2":{"state":"present"}},"agent":{"tendcf-agent":{"sha256":"sha256:d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4","state":"present","version":"ops-v1.0.0"}},"policy-tree":{"tree":{"sha256":"sha256:c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3","state":"present"}},"trust-policy":{"consent":{"local_yes_required":true,"state":"present","tier":"consented"}}}},"supervision":{"coverage":"comprehensive","entries":{"interlock":{"caddy-config-valid":{"blocks":"enclosing-bundle","bundle":"caddy","defines_class":"caddy_config_ok","pre_action":{"command":["/opt/homebrew/bin/caddy","validate","--config","/etc/caddy/Caddyfile"],"expect_exit":0,"timeout_seconds":30},"report":true,"state":"present"}},"service":{"com.tendcf.caddy.main":{"bundle":"caddy","command":["/opt/homebrew/bin/caddy","run","--config","/etc/caddy/Caddyfile"],"env":{"CADDY_ADMIN_TOKEN":"CADDY_ADMIN_TOKEN"},"run_as":"caddy","state":"present","unit":{"launchd":{"keep_alive":true,"run_at_load":true}},"working_dir":"/"},"com.tendcf.caddy.retired":{"state":"absent"}},"unit-writer":{"com.tendcf.caddy.*":{"state":"present","writer":"cfengine"}}}}},"host":"ed25519:a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1","schema_version":1}}}
```

## Costs and what I'd give up

The strongest argument against my position is **CFEngine memory pressure and parse overhead**. By projecting the *entire* goal file—including `device-trust`, advisor keys, policy digests, and undeployed domains—I am forcing the CFEngine parser to load, allocate, and hold state it will never use. `host_specific.json` becomes exactly as bloated as the goal file itself.

I accept this cost because the alternative is fundamentally worse. If the projector strips `device-trust`, it must know that `device-trust` is an engine domain. If it strips `not-yet-migrated` domains, it must inspect the `coverage` enum. If it sorts tombstones, it inspects `state`. The moment the projector contains rules about *what* the data means, we have resurrected the Model A interpreter outside the gate. I will gladly trade CFEngine RAM for the absolute guarantee that the projector is a dumb, unexploitable, structural tube.
