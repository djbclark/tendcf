# Opinion: `goal-file.schema.json` Design

**Author:** Gemini 3.1 Pro (High)
**Status:** Complete response to `GOAL-FILE-SCHEMA-BRIEF.md`

## 1. Concrete JSON Schema Sketch

The goal file must serve as a deterministic, fully resolved representation of the host's desired state. It is the artifact of record.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/frdminc/tendcf/schema/goal-file.schema.json",
  "title": "tendcf — Canonical per-host goal file",
  "description": "The fully resolved, canonical representation of a host's intended state. It serves as the compiler's output, the consent object, and the validator's input.",
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "integer",
      "minimum": 1,
      "description": "Must be bumped on any schema change, including additive changes, to ensure fail-closed versioning."
    },
    "host_public_key": {
      "type": "string",
      "description": "The expected public key of the host this goal file targets."
    },
    "domain_coverage": {
      "type": "object",
      "patternProperties": {
        "^[a-z0-9][a-z0-9-]*$": {
          "$ref": "common.schema.json#/$defs/domain_coverage"
        }
      },
      "additionalProperties": false,
      "description": "Per-domain declaration of comprehensiveness. Required to distinguish unchanged state from unmanaged state."
    },
    "entries": {
      "type": "array",
      "description": "All resolved state entries. Must be deterministically sorted by [domain, kind, id].",
      "items": {
        "$ref": "#/$defs/entry"
      }
    }
  },
  "required": ["schema_version", "host_public_key", "domain_coverage", "entries"],
  "additionalProperties": false,

  "$defs": {
    "entry": {
      "type": "object",
      "properties": {
        "domain": {
          "$ref": "common.schema.json#/$defs/identifier"
        },
        "kind": {
          "$ref": "common.schema.json#/$defs/token",
          "description": "The specific type of the entry, drawn from a closed set defined by the schema_version."
        },
        "id": {
          "$ref": "common.schema.json#/$defs/identifier"
        },
        "content": {
          "type": "object",
          "description": "The fully resolved payload of the entry. No defaults; all relevant fields must be explicitly stated.",
          "additionalProperties": false,
          "patternProperties": {
            "^.*$": {} 
          }
        },
        "fetched_digest": {
          "type": "string",
          "description": "If this entry relies on a fetched external artifact, its cryptographic digest MUST be recorded here (DC-11, R12)."
        }
      },
      "required": ["domain", "kind", "id", "content"],
      "additionalProperties": false
    }
  }
}
```
*(Omission note: the `content` payload schemas are omitted for brevity, but would be an explicit `anyOf` or `oneOf` matching `kind` to strict subschemas.)*

## 2. Positions on the Seven Hard Parts

1. **Canonicalization:** 
   RFC 8785 handles JSON serialization, but schema design must handle semantic canonicalization. We must strictly enforce `additionalProperties: false` everywhere. We must forbid empty collections (`minItems: 1` or `minProperties: 1`) so that omission is the only valid way to express "none." We rely on `schema_lint.py` and the on-device validator to reject anything not byte-identical to its own canonicalization.
2. **Entry identity:** 
   The stable identifier is the tuple `(domain, kind, id)`. A "rename" is fundamentally an intent-level concept. In the extent-level goal file, a rename is simply a `remove` hunk and an `add` hunk. We should **not** introduce a `rename` primitive to the diff or goal file because it re-introduces the compiler's intent assertions into the consent artifact. The UI/advisory layer can infer and display a rename if an `add` and a `remove` have identical `content`, but the underlying format remains strictly structural.
3. **Coverage:** 
   As required by E1 §5.7, the `domain_coverage` object is embedded directly into the goal file. If an entry is absent from `entries` but belongs to a domain marked `comprehensive: true`, the absence is an explicit negative promise (removal or absence enforced). If the domain is `not-yet-migrated`, the absence means "leave it alone."
4. **Versioning:** 
   Fail-closed is non-negotiable. Any change to the allowed `kind` set must bump `schema_version`. Because of strict `additionalProperties: false`, an old validator will reject a new file containing an unknown field or kind. This guarantees we never fail open or apply partial states that ignore unparseable safety constraints. 
5. **Privileged regions:** 
   The goal file structure explicitly separates `(domain, kind, id)` from `content`. Because the validator holds the privilege list, it can easily compute privilege matches by inspecting the `(domain, kind, id)` index before even reading `content`. The goal file's flat array of explicit entries makes this check computationally trivial and un-forgeable by the proposer.
6. **Fetched content:** 
   I added `fetched_digest` directly to the base `entry` definition. By elevating the digest out of arbitrary `content` and into the generic entry envelope, the validator can uniformly enforce that *any* remote fetch includes a signed digest, fulfilling DC-11 and R12 without requiring kind-specific validation logic.
7. **The E1 Open Question: Augments JSON vs. Projection:**
   **Position:** The goal file is a **projection onto** the CFEngine Augments JSON (`def.json` / `host_specific.json`), not the same artifact.
   **Reasoning:** CFEngine's Augments file is an implementation detail of the executor. It lacks the structural constraints required for consent (strict schema versions, deterministic sorting, detached signatures, explicit coverage maps). If the goal file *was* the Augments file, we would be fighting CFEngine's parser leniency. Instead, the goal file is the pure consent and validation artifact. The on-device validator reads it, confirms the diff and signatures, and then *renders* it into `def.json` for CFEngine to consume. This preserves the security boundaries.

## 3. What I Would Cut

**Cut the `explain-hunk` attribution tool (from E1 §5.5).**
The project's binding constraint is builder capacity. Building a tool that systematically reverts patches, re-renders, and diffs to synthesize intent is an intellectually satisfying solution to fan-out fatigue, but it is an expensive luxury. For a single unfunded builder who is both the proposer and the authorizer, the memory of "what did I just type?" is usually fresh. The counter-proposal loop (refusing hunks) is sufficient to handle large diff fatigue. Building `explain-hunk` is not a day-one requirement and should be cut to save builder bandwidth.

## 4. Disagreements with the Adjudication

**First adoption minimal-claim rule is overly prescriptive.**
E1 §5.4 states that first adoption is governed by a minimal-claim rule, forcing all but a few domains to be `not-yet-migrated`. While this avoids laundering a massive unreviewed state, it is practically hostile to bootstrapping. A real first-run of a node often requires configuring networking, SSH, users, and monitoring simultaneously to make the node reachable and safe. Forcing these into artificial, subsequent one-by-one diffs creates unnecessary friction for a single-operator project. We should allow the initial day-one goal file to be as comprehensive as the operator is willing to trust, relying on the physical first-run ceremony for the root of trust, rather than artificially constraining the day-one surface.
