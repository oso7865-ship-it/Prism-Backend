# Java review
Check null/Optional handling, resource lifetime, exception propagation and collection boundaries.
For Spring/JPA only infer transaction/lock semantics shown in the input. Do not assume annotations
apply across self-invocation, async work or unseen callers. A lock name or READ_COMMITTED alone
is not a race: identify competing access and lock scope first. ID tie-breaking may be a domain rule;
do not call it wrong without contradictory code. Avoid flagging wildcard imports already reported statically.
