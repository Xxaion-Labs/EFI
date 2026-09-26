# EFI Public Release / Patent Boundary Policy

**Launch cut: September 26, 2026**

This is an operational publication rule, not a legal claim chart.

## Release classes

| Class | Meaning | Public action |
|---|---|---|
| **FILED-SUPPORTED** | The public technical relation is supported by filed disclosure to the extent documented in the filed technical envelope. | Publish. |
| **FILED-OVERLAP / SUPPORT-UNVERIFIED** | Likely related to filed subject matter, but exact priority support has not been checked. | Publish only without claiming an earlier priority date. |
| **POST-FILING PUBLIC DISCLOSURE** | Genuinely later technical matter intentionally disclosed by the inventor after the provisional filings. | Timestamp the disclosure. Treat any later patent filing as a separate support/priority question. |
| **FILE-FIRST** | New matter for which foreign or other pre-disclosure rights matter. | Do not publish until the desired filing is made. |
| **PROOF-OPEN** | Architecture may be disclosed, but a capability claim is not yet proved. | Publish architecture and the exact proof boundary, not an inflated capability claim. |

## Current filing anchors

- U.S. Provisional Patent Application No. **64/101,611**, filed **June 29, 2026**.
- U.S. Provisional Patent Application No. **64/154,781**, filed **September 14, 2026**.

The current public technical spine is mapped in [docs/FILED-TECHNICAL-ENVELOPE.md](docs/FILED-TECHNICAL-ENVELOPE.md).

## Post-filing rule

Public disclosure is evidence of what was made public and when. It is **not** a substitute for filing.

For genuinely new matter disclosed after the provisionals:

1. preserve the exact first-public commit/date;
2. never describe the matter as entitled to an earlier provisional date without support;
3. if relying on a U.S. inventor-disclosure grace period, file within the applicable statutory window;
4. remember that foreign novelty rules can be less forgiving;
5. if foreign rights materially matter, use **FILE-FIRST**.

## Provisional conversion clocks

The provisional applications have independent conversion/priority deadlines. Public release does not extend them.

The repository should therefore treat **June 29, 2027** and **September 14, 2027** as critical filing-calendar dates for the corresponding provisional subject matter under the ordinary 12-month provisional framework, subject to counsel and the actual filing strategy.

## Rights layer

Patent strategy and repository licensing are separate:

- patent filings protect eligible inventions only through patent law and only to the extent valid claims ultimately issue;
- copyright protects repository expression and code;
- the public-source license permits qualifying noncommercial use;
- commercial use requires a separate written commercial license;
- trademarks remain separately controlled.

## Publication log

The deliberate public repository launch occurred on **September 26, 2026**.

Future materially new technical disclosures should be recorded in [PUBLIC-DISCLOSURE.md](PUBLIC-DISCLOSURE.md) or an attached disclosure log with the public commit identifier and date.

---

**EFI™ · Xxaion Labs™ · PATENT PENDING**
