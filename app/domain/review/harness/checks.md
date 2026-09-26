# Review procedure
1. Identify changed lines and their local control/data flow. Context lines only support a changed behavior.
2. Check concrete failure paths: null/empty/boundary inputs, exception handling, resource cleanup,
   authorization decisions, unsafe data use, transaction boundaries, concurrent state changes,
   duplicate execution and avoidable unbounded work.
3. For concurrency claims identify the shared resource, two competing paths and the violated invariant.
   If lock acquisition, isolation, caller or transaction propagation is unseen, do not declare a race.
4. For security claims identify attacker-controlled input and the visible sensitive operation.
   A method name alone is not evidence of a bypass or injection.
5. For performance claims identify a visible workload growth or unbounded operation; avoid speculative tuning.
6. Drop generic advice, duplicate observations and unsupported claims. Do not manufacture issues to fill a quota.
   Missing method bodies, signatures, callers or contracts alone are limitations, not NEEDS_CONTEXT issues.
   Do not hypothesize that an unseen method returns a failure flag, needs a row-count check,
   or has non-idempotent side effects merely because its result is not assigned.
   A normally propagated exception prevents the following statement from executing; do not claim otherwise.
   Describe observable effects without inventing caller expectations or asserting data leakage without a visible path.
7. Report the concrete triggering condition, observed consequence, and smallest relevant improvement.
   Put missing dependencies and unverified assumptions in limitations. No hidden reasoning transcript is needed.
