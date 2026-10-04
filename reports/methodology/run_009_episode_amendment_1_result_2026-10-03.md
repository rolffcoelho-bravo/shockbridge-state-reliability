# Run 009 episode amendment 1 result

**Result date:** 2026-10-03
**Status:** pass; immutable v1 preserved
**Primary result changed:** no
**Transmission authorized:** no

The amendment reconstructed all 44 episode rows from the hash-bound Run 009 diagnostic CSV. Every original field and value matches the immutable v1 episode artifact exactly. The versioned artifact adds only `open_at_sample_end`.

One row is open at the sample boundary: the nonprimary leave-one-feature-out sensitivity omitting industrial production, using the 144-month rolling history and 6/6 persistence rule. It begins in November 2020, contains 55 breach months over a 60-month observed episode, and ends at the October 2025 sample boundary after only five stable months—one short of the required six-month recovery sequence.

All other 43 episode rows are explicitly closed. No full-panel primary episode is right-censored. No geometry metric, episode date, duration, breach count, classification, evidence claim, or decision changed. Original Run 009 v1 files were not overwritten.

Independent comparison confirms exact equality after removing the added field, and a repeat amendment execution is byte-identical.
