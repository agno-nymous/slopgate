# 74 — The default install fails for compiled repos

## Summary

- **Goal:** Know which repos the default install cannot build, and why, and give the maintainer a ready `setup` line for each kind.
- **Checkable finish condition:** For each of the 10 instances below, the Comments give the cause and a `setup` line that makes `pytest --collect-only` pass, or the reason that none exists.
- **Evidence:** Before: ticket 67 `install` stage of 2026-10-21. The default install fails on 10 of 28 instances: `psf__requests-1963`, `scikit-learn-10297`, `-10508`, `-11040`, `matplotlib-18869`, `-22711`, `-23299`, `astropy-6938`, `-12907`, `-14182`. After: the same stage with the `setup` lines.
- **Constraints:** Do not add a model agent. Ticket 67 measured an install agent: it proved 0 of 72 attempts. A person writes the install instructions, and the README says how.

**Blocked by:** 67

**Status:** ready-for-agent

**Type:** research.

## Context

The causes in the 2026-10-21 `install` report: C extensions with no wheel for the date (matplotlib freetype, astropy, scikit-learn on Python 3.6), and Python 3.6 `develop` failures. The image has no compiler. `apt-get install -y build-essential` takes 24 s (ticket 67 stage 0).

## Design

1. For each instance, run the failing install by hand in ConTree and read the real error.
2. Test two `setup` lines: with `apt-get install -y build-essential`, and with `pip install --only-binary :all:` for the C packages.
3. Measure whether `uv` instead of `pip` (A/B on the 18 instances that build) changes the time or the success.

## Acceptance

- [ ] The Comments list the cause of each of the 10 failures.
- [ ] The Comments give the A/B time of uv and pip on the 18 instances that build.
- [ ] The README names the best `setup` line for compiled repos.
