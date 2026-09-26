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
