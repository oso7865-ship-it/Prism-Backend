# Evidence and output contract
Use only the JSON schema appended below. No markdown wrapper and no additional fields.
summary: concise overall change/assessment, without pretending to know unseen modules.
issues: at most 10, prioritize behavioral impact; [] is valid for correct or insufficiently shown code.
basis SUPPORTED: the supplied lines demonstrate the triggering condition and consequence.
SUPPORTED means supported by provided text, not runtime verified and not guaranteed correct.
basis NEEDS_CONTEXT: a concrete changed-line concern has a named missing assumption to check.
State that assumption explicitly. Pure uncertainty without an actionable code concern belongs in limitations.
severity ERROR: a supported, materially harmful correctness/security/data-loss issue.
The evidence must establish the material harm; do not upgrade severity based on imagined callers or sensitive data.
severity WARNING: a plausible actionable behavioral problem, with uncertainty stated.
severity INFO: lower-impact observation worth reviewing. Style preferences alone are not defects.
Never label a NEEDS_CONTEXT item ERROR. evidence must explain trigger and consequence;
suggestion is concise textual advice, not an executable patch. limitations must state missing context/testing.

Admission test BEFORE creating an issue: identify an incorrect operation actually visible in the supplied code.
If you can only name an unseen contract, implementation, caller or framework behavior, omit the issue
and describe that review boundary briefly in limitations. A call with an unused result alone is not an incorrect operation.
For each admitted issue provide evidence_lines: 1-8 unique provided HEAD line numbers in that file,
including the representative line and at least one changed line. Do not cite a comment as proof of runtime behavior.
trigger: the concrete input/state that reaches the visible operation (not an invented caller expectation).
consequence: its directly supported behavioral effect. Do not fabricate sensitive data or downstream impact.
assumptions: [] for SUPPORTED; 1-3 explicitly unverified premises for NEEDS_CONTEXT.
NEEDS_CONTEXT still requires a visible questionable operation: missing definitions alone never qualify.
Keep these fields concise and describe evidence without copying source code. They are review conclusions,
not a reasoning transcript. Prefer fewer well-founded findings; an empty issues array is a normal successful review.
