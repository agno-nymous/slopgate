# 09 — Jev classifier backend and comparison

## Summary

- **Goal:** The user can switch the classifier of the live flag from Nemotron Lightning to Jev with a config setting. Example: set the backend to Jev, and the hook asks Jev "is this new function a copy of that one?" in place of Lightning.
- **Checkable finish condition:** The comparison script prints a table for both backends on at least 50 labeled pairs. The table shows median latency, cost per 1,000 decisions, and accuracy. The results are saved in a file.
- **Evidence:** Before: only Nemotron Lightning decides. After: the edit-time tests of ticket 07 pass with a scripted Jev fake, and the saved comparison file holds the measured latency, cost, and accuracy of both backends.
- **Constraints:** Nemotron stays the default. Both backends return the same decision shape: yes or no, plus a confidence value. When the Jev API key is missing, the gate falls back to Nemotron and prints one warning, and the hook still exits 0. This ticket has the lowest priority: skip it if time runs short.

**Blocked by:** 07

**Status:** ready-for-agent

## Details

Jev is the System One classifier of TypeSafe AI. The comparison script runs both backends on one labeled set of duplicate pairs and non-duplicate pairs. The results go into the hackathon feedback section.

- [ ] Config selects the backend. Nemotron is the default.
- [ ] When Jev is selected, the edit-time tests of ticket 07 pass with a scripted Jev fake.
- [ ] When the Jev API key is missing, the gate falls back to Nemotron and prints one warning. The hook still exits 0.
- [ ] The comparison script prints a table for both backends on at least 50 labeled pairs. The table shows median latency, cost per 1,000 decisions, and accuracy.
- [ ] The comparison results are saved in a file. The README can link to this file.

## Comments

- Jev facts from the planning handoff (do not research them again): The vendor is TypeSafe AI. The endpoint is `POST https://api.typesafe.ai/v1/systemone`. The model is `jev-latest`. Jev returns typed decisions with calibrated probabilities. Latency is 70 to 500 ms. Cost is $0.042 per 1M input tokens. Jev is API only. Payload shapes are at https://github.com/FrancoisChastel/jev-code
