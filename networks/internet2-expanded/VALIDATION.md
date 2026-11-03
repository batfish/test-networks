# Validation

The two-copy example was checked with open-source Batfish 0.36.0 at
revision `59abf28a36ee8b8131ff8983c3a918de7f4da72e`.

All twenty configs parsed, without parse warnings, conversion warnings,
or undefined references. All 78 directed BGP endpoints established.
Global loop detection found no counterexamples. Symbolic checks found
no service reachability failures and required a successful witness from
each of the twenty routers.

These checks apply to the synthetic eBGP model. They do not establish
preservation of the original Internet2 routing policy.
