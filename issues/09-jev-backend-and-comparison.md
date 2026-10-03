# 09 — Jev classifier backend and comparison

**What to build:** A user can switch the live-flag classifier from Nemotron Lightning to Jev (TypeSafe AI's System One classifier) through config. Both backends return the same decision shape: yes/no plus confidence. A comparison script runs both backends on one labeled set of duplicate and non-duplicate pairs. It reports latency, cost, and accuracy. The results go into the hackathon feedback section.

This ticket is the lowest priority. Skip it if time runs short. Nemotron stays the default either way.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] Config selects the backend; Nemotron is the default.
- [ ] With Jev selected, ticket 07's edit-time tests pass with a scripted Jev fake.
- [ ] A missing Jev API key falls back to Nemotron with a single warning, and the hook still exits 0.
- [ ] The comparison script prints a table of median latency, cost per 1,000 decisions, and accuracy for both backends on at least 50 labeled pairs.
- [ ] The comparison results are saved in a file that the README can link to.
