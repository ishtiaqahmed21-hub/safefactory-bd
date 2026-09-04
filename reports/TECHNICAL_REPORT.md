# SafeFactory BD — Technical Report

**An ISO 45001-aligned HSE management and site risk intelligence system for Bangladeshi food and dairy manufacturing**

Ishtiaq Ahmed
Industrial and Production Engineering, Islamic University of Technology
September 2026

---

## Contents

1. [Executive summary](#1-executive-summary)
2. [Problem statement](#2-problem-statement)
3. [System architecture](#3-system-architecture)
4. [The risk engine](#4-the-risk-engine)
5. [The hazard register](#5-the-hazard-register)
6. [Permit to Work and Lockout–Tagout](#6-permit-to-work-and-lockouttagout)
7. [Incident classification and performance metrics](#7-incident-classification-and-performance-metrics)
8. [The compliance matrix](#8-the-compliance-matrix)
9. [Data provenance and integrity screening](#9-data-provenance-and-integrity-screening)
10. [Ambient exposure analysis](#10-ambient-exposure-analysis)
11. [The Composite Site HSE Risk Index](#11-the-composite-site-hse-risk-index)
12. [Verification and testing](#12-verification-and-testing)
13. [Limitations](#13-limitations)
14. [Implementation roadmap](#14-implementation-roadmap)
15. [References](#15-references)

---

## 1. Executive summary

Bangladesh recorded between 802 and 1,190 workplace deaths in 2025, depending on
which monitor you read, and 27,059 fires. The Department of Inspection for
Factories and Establishments has fewer than 500 staff, of whom 231 are labour
inspectors, for the whole country. A study of the post-Accord period found that
93% of factories had constituted a safety committee and concluded that the
failure point was not formation but *functionality*.

Those four facts define the problem this project addresses. External enforcement
capacity is thin and will remain thin. Formal compliance is widespread and
substantially hollow. The binding constraint on worker safety in Bangladeshi
manufacturing is therefore the **internal capability of the plant's own HSE
function** — its ability to find its own hazards, control its own permits,
measure its own performance honestly, and know where its own numbers stop being
trustworthy.

SafeFactory BD is a working system for exactly that. It contains:

- a **36-hazard risk register** for a dairy and snack-food plant, scored on a 5×5
  matrix with a fatality-escalation rule and hierarchy-of-controls scoring, and
  reported in three states — inherent, current and target;
- a **Permit to Work system** covering seven permit classes that automatically
  detects expired, self-issued, ungas-tested and unclosed permits;
- **Lockout–Tagout** isolation logic across eight energy types that refuses to
  sign off an electrical-only isolation on plant holding stored energy;
- an **incident system** computing LTIFR, TRIR, DART and severity rate on their
  correct and separately-named bases, with a reporting-health check, a 5-Why
  blame detector and a bow-tie gap detector;
- a **35-requirement compliance matrix** mapping every ISO 45001:2018 clause group
  to the Bangladeshi instrument that makes it a legal duty, with named evidence
  and weighted conformity scoring;
- a **Composite Site HSE Risk Index** screening industrial locations on ambient
  air burden, industrial density, worker concentration and emergency access, with
  weight and radius sensitivity analysis;
- **exposure analytics** on 1.05 million hourly air-quality records, ending in a
  work-adjustment calendar rather than a chart;
- an **automated data-integrity screen** that found two defects in the published
  source dataset and now blocks any finding that fails it.

**The three findings that matter most:**

**First**, separating what a plant *has* from what it *plans* changes the picture
entirely. The register's residual scores show zero hazards at High or Critical —
the target state. Crediting only the controls actually installed shows **26 of 36
hazards at High or Critical today**. The second number is the honest one, and it
is the number a plant should be managed against.

**Second**, the source air-quality dataset contains a 26-year Dhaka series through
which a striking trend can be fitted: +2.55 µg/m³ per year. It is an artefact. The
2000–2021 segment rises monotonically every single year (monotone fraction 1.00,
R² 0.994) and then steps down by 68 µg/m³. The pipeline now detects this
automatically and refuses to report the trend. The same screen found that three
pairs of the thirty named cities carry byte-identical hourly series, leaving 27
independent locations, not 30.

**Third**, the exposure analysis produces a designable control rather than an
observation. At the Dhaka reference point, 435 of 1,207 valid days (36%) sit at or
above AQI 150, concentrated sharply in the dry season — January at 98.2 µg/m³ mean
PM2.5 against July at 14.4. A protocol firing on a third of days in a predictable
window is one a plant can run. Had the number come out at 80%, the correct
conclusion would have been the opposite.

---

## 2. Problem statement

### 2.1 The national picture

| Indicator | 2024 | 2025 | Source |
|---|---|---|---|
| Workplace deaths (SRS) | 758 | **802** | Safety and Rights Society |
| Workplace accidents (SRS) | 639 | **713** | Safety and Rights Society |
| Workplace deaths (OSHE) | — | **1,190** | OSHE Foundation |
| Fire incidents | 26,659 | **27,059** | Fire Service and Civil Defence |
| Fire deaths (civilian) | 140 | **85** | Fire Service and Civil Defence |

The two fatality counts for 2025 must never be summed or used interchangeably.
SRS compiles from 15 national and 11 local newspapers; OSHE uses a different
methodology and scope, and attributes 84% of incidents to the informal sector.
Both under-count, because both depend on an event being reported. Any benchmark
quoted from either must name which one it came from — a discipline this project
enforces by storing the source organisation and URL against every statistic.

Sector breakdown of the 802 SRS deaths:

| Sector | Deaths | Share |
|---|---|---|
| Transport | 385 | 48.0% |
| Service (workshops, gas, electricity) | 145 | 18.1% |
| Construction | 120 | 15.0% |
| Agriculture | 94 | 11.7% |
| Factories | 58 | 7.2% |

Two things follow directly. Transport is the largest single killer, which is why
this register treats yard traffic and vehicle movement (HZ-VEH-01, HZ-MHE-01) as
Critical inherent hazards rather than as housekeeping. And the "factories" figure
of 58 is small relative to the national total but is the directly comparable
number for a food and dairy plant.

Fire causation, from 27,059 FSCD incidents:

| Cause | Incidents | Share |
|---|---|---|
| Electrical short circuit | 9,392 | 34.71% |
| Burning cigarettes | 4,269 | 15.78% |
| Stoves | 2,909 | 10.75% |
| Gas cylinder leak | 920 | 3.40% |
| Gas supply line leak | 562 | 2.08% |
| Gas cylinder explosion | 121 | 0.45% |
| Chemical incidents | 38 | 0.14% |

Electrical short circuit is the single largest ignition source nationally by a
wide margin. That is the empirical basis for HZ-ELE-02 in this register —
uncontrolled temporary wiring — being scored at 16 inherent, and for the electrical
requirements CM-15 and CM-17 in the compliance matrix being rated Critical. It is
not a judgement call; it is what a third of the country's fires actually start
from.

### 2.2 The regulatory constraint

| Figure | Value | Source |
|---|---|---|
| DIFE total staff | fewer than 500 | DIFE Annual Report 2021 via CPD/FES |
| DIFE labour inspectors | 231 | DIFE Annual Report 2021 via CPD/FES |
| Factories with a constituted safety committee | 93% | CPD/FES post-Accord study |

231 inspectors cannot police a national industrial base. The CPD/FES study's
finding — near-universal committee formation alongside a functionality failure —
is the key structural insight: the paper exists, the practice does not. This is
why HZ-ORG-02 in the register addresses committee *functionality* specifically
(quarterly minutes to BLR Schedule IV(3), worker-nominated representatives, a
tracked action register) rather than committee existence, and why CM-05 in the
compliance matrix asks for four sets of minutes per year rather than a
constitution letter.

### 2.3 Why a dairy and snack plant

The reference operation is a Bangladeshi dairy nutrition and snack manufacturer
operating since 1992, with a head office in Tejgaon Industrial Area, Dhaka, and
two factories — one at Vulta, Rupganj, Narayanganj, and one at Jangalipara,
Gazipur. Its published product range spans instant full-cream and non-fat milk
powders, butter oil, instant and stick noodles, ramen, chowmein, chips, crackers,
wafers, biscuits and cookies.

That range is unusually demanding from an HSE standpoint, because it stacks four
distinct high-consequence hazard families in one plant:

1. **Combustible dust.** Milk powder handling generates dust clouds in blender
   headspaces and extraction ducting, with deflagration and secondary-explosion
   potential.
2. **Hot oil.** Continuous frying lines for noodles and snacks operate at
   140–180 °C, with fire spread through grease-laden extraction ductwork.
3. **Ammonia refrigeration.** Dairy cold chain typically runs on anhydrous
   ammonia — acutely toxic above an IDLH of 300 ppm and flammable between 15% and
   28% by volume in air.
4. **Fired plant.** Gas-fired tunnel ovens and steam boilers, each with its own
   explosion and pressure-release mechanisms.

A register built for a garment factory does not cover any of these. This one does.

---

## 3. System architecture

```
data/raw/ ──────────┐
                    ├──> scripts/build_dataset.py ──> data/processed/ (37 tables)
data/reference/ ────┘                │                        │
                                     │                        │
                          src/safefactory/quality.py          │
                          (screens before anything            │
                           downstream is computed)            │
                                                              v
                                                        app/ (8 pages)
                                                        reports/
```

The design rules are deliberate and each exists to prevent a specific failure:

**Every threshold lives in `config.py`.** Likelihood and severity descriptors,
band boundaries, the fatality escalation floor, hierarchy weights, permit validity
limits, gas-test acceptance criteria, occupational exposure limits, ambient
standards, index weights — all in one file. An auditor can read the rules the
system runs on without reading code.

**Nothing downstream reads a raw file.** Every figure in the dashboard and this
report is one hop from `build_dataset.py`, so provenance is traceable by
inspection.

**Screening runs before analysis, not after.** `quality.run_all()` is called
before any trend is computed, because the screen decides whether a trend may be
computed at all.

**Reference data is CSV, not code.** The hazard register, compliance matrix,
national statistics and site coordinates are all editable spreadsheets. A safety
officer can extend the register without touching Python.

---

## 4. The risk engine

### 4.1 The matrix

Risk score is likelihood × severity on a 5×5 matrix, giving 1–25.

**Likelihood**

| Level | Label | Definition |
|---|---|---|
| 1 | Rare | Not expected to occur in the life of the plant (<1 in 25 years) |
| 2 | Unlikely | Could occur at some time (once in 10–25 years) |
| 3 | Possible | Might occur at some time (once in 2–10 years) |
| 4 | Likely | Will probably occur in most circumstances (once a year) |
| 5 | Almost certain | Expected to occur in most circumstances (several times a year) |

**Severity**

| Level | Label | Definition |
|---|---|---|
| 1 | Negligible | No treatment or first aid only; no lost time; no environmental effect |
| 2 | Minor | Medical treatment case; up to 3 days lost; contained on-site release |
| 3 | Moderate | Lost-time injury; reversible health effect; reportable release |
| 4 | Major | Permanent disability or single serious injury; major release; regulatory action |
| 5 | Catastrophic | Single or multiple fatality; irreversible health effect; licence at risk |

**Bands**

| Score | Band | Required response | Max review interval |
|---|---|---|---|
| 1–4 | Low | Acceptable. Monitor and maintain existing controls. | 12 months |
| 5–9 | Medium | Tolerable if ALARP. Documented action plan required. | 6 months |
| 10–15 | High | Not acceptable as-is. Additional controls within 30 days. | 3 months |
| 16–25 | Critical | Unacceptable. Stop or restrict the activity until controls are in place. | 1 month |

### 4.2 The fatality escalation rule

A credible fatality scenario (severity 5) assessed at likelihood 3 or above is
forced to at least High, whatever the arithmetic gives.

This exists to block a specific and common HIRA failure: scoring a fatal hazard as
tolerable because it is judged unlikely. A confined-space entry that kills is not
a Medium risk because it happens rarely.

The rule has a deliberate floor. At likelihood 1 or 2, severity 5 is *not*
escalated — a fatality genuinely judged rare is allowed to sit where the
arithmetic puts it. Without that floor the rule would sweep every conceivable
fatal scenario into High and the register would stop discriminating. Both the
firing and the non-firing of the rule are covered by unit tests.

### 4.3 Hierarchy-of-controls scoring

ISO 45001 clause 8.1.2 requires the hierarchy of controls to be applied. Most
registers assert this and then list PPE. This system scores it.

| Level | Weight |
|---|---|
| Elimination | 5 |
| Substitution | 4 |
| Engineering | 3 |
| Administrative | 2 |
| PPE | 1 |

A control plan's effectiveness is the mean weight of the levels it names,
normalised to 0–1. `Engineering + Administrative` scores 0.5; `PPE` alone scores
0.2; `Elimination` scores 1.0.

The diagnostic that matters is the **combination of a high residual risk with a
low-effectiveness plan**. That pairing is the clearest available signal that a
control was written for the audit file rather than for the hazard. In this
register, **16 hazards** combine a residual score of 6 or more with a plan resting
mainly on administrative measures or PPE:

| Hazard | Control plan | Effectiveness | Residual |
|---|---|---|---|
| HZ-RFG-01 Ammonia release | Engineering + Administrative | 0.50 | 8 |
| HZ-RFG-02 Ammonia line breaking | Administrative | 0.40 | 8 |
| HZ-HGT-01 Work at height | Engineering + Administrative | 0.50 | 8 |
| HZ-ELE-01 LV/HV switching | Engineering + Administrative | 0.50 | 8 |
| HZ-MHE-01 Forklift/pedestrian | Engineering + Administrative | 0.50 | 8 |
| HZ-CON-01 Contractor management | Administrative | 0.40 | 8 |

These are the first candidates for an engineering solution, and this is precisely
the list that a conventional register — which reports a single residual number and
stops — cannot produce.

### 4.4 Three-state reporting

The most consequential design decision in the whole system.

A conventional register scores each hazard twice: inherent, and residual after
controls. The residual score silently assumes every control listed is in place.
It usually is not. The register then describes an intention rather than a plant,
and the gap is invisible.

This register carries a `control_status` per hazard — Implemented, In progress, or
Proposed — and computes a third score that credits the plan only to the extent it
exists: fully when Implemented, half when In progress, not at all when Proposed.

| Band | Inherent (no controls) | **Current (what is installed)** | Target (full plan in place) |
|---|---|---|---|
| Low | 0 | **4** | 16 |
| Medium | 4 | **6** | 20 |
| High | 20 | **17** | 0 |
| Critical | 12 | **9** | 0 |

The target column is what a conventional register would report. The current
column is the truth: **26 hazards at High or Critical today**. The distance
between the two columns is the implementation programme, and it is worth 246 risk
points across 31 hazards.

---

## 5. The hazard register

36 hazards across 18 areas. Distribution by category:

| Category | Hazards | Mean inherent | Mean residual | Mean reduction |
|---|---|---|---|---|
| Energy | 1 | 20.00 | 8.00 | 60.0% |
| Mechanical | 3 | 17.33 | 7.33 | 56.7% |
| Fire/Explosion | 5 | 16.00 | 6.40 | 60.0% |
| Electrical | 2 | 15.50 | 7.00 | 54.6% |
| Chemical | 3 | 15.33 | 6.00 | 60.8% |
| Confined Space | 2 | 15.00 | 4.00 | 73.3% |
| Organisational | 8 | 14.38 | 5.50 | 61.5% |
| Physical | 8 | 12.25 | 4.75 | 60.9% |
| Environmental | 3 | 11.00 | 5.33 | 51.9% |
| Ergonomic | 1 | 8.00 | 4.00 | 50.0% |

Highest-exposure areas by total residual risk:

| Area | Hazards | Mean inherent | Total residual |
|---|---|---|---|
| Whole Site | 14 | 14.86 | 80 |
| Powder Blending & Packing | 3 | 11.67 | 18 |
| Refrigeration Plant | 2 | 20.00 | 16 |
| Noodle & Snack Frying Line | 2 | 15.50 | 14 |
| Substation & MCC Rooms | 1 | 15.00 | 8 |
| Yard & Transport | 1 | 20.00 | 8 |
| Warehouse & Yard | 1 | 20.00 | 8 |
| Boiler House | 2 | 12.50 | 8 |

Total residual risk is summed rather than averaged, so an area carrying many
moderate hazards is not hidden behind an area carrying one severe one. The
Refrigeration Plant's mean inherent score of 20.00 — the joint highest on site —
reflects that both its hazards are credible fatality scenarios at likelihood 4.

### 5.1 Four worked hazards

**HZ-RFG-01 — Anhydrous ammonia release, refrigeration plant.** Inherent 4×5=20,
Critical. Existing controls: plant-room ventilation, an annual pressure-vessel
certificate, an operator on shift. Target 2×4=8.

The consequence statement is quantified rather than adjectival: acute inhalation
injury and chemical burns, fatality above the IDLH of **300 ppm**, and a
potentially flammable atmosphere between **15% and 28% by volume in air**. Those
figures come from NIOSH, and they are what determine the control set: fixed
detection alarming at the NIOSH REL of 25 ppm and tripping at 300 ppm, interlocked
to emergency ventilation and compressor shutdown; two SCBA sets plus four
full-face ammonia respirators at the plant-room entrance; deluge shower and eye
wash within 10 m; an ammonia-specific emergency plan with wind-direction assembly
points.

Legal basis: BLR 60 and 62 (pressure plant certificate), BLA 62 (precautions
against fire and dangerous fumes), BLA 78A (training). ISO 45001 clauses 8.2 and
6.1.2.

Its bow-tie model, on the dashboard's Incidents page, exposes two unbarriered
lines: **corrosion under insulation has no preventive barrier**, and **flammable
atmosphere has no mitigative barrier**. Corrosion under insulation is the failure
mode least likely to be found by a visual walk-round, which is exactly why it
needs a named inspection programme rather than an assumption.

**HZ-PWD-01 — Milk-powder dust deflagration.** Inherent 3×5=15, High. Existing
controls: dust extraction at the tipping point, housekeeping by sweeping. Target
2×4=8.

The control set is built on a dust hazard analysis to NFPA 61: earthing and bonding
continuity testing of all conductive plant, EX-rated fittings and dust-tight
luminaires in the classified zone, explosion venting or suppression on the blender
and cyclone, a **ban on compressed-air blow-down** replaced by certified vacuum
cleaning, and monthly dust-layer inspection above false ceilings and on beams.

The compressed-air ban is the substitution step and the reason this hazard's plan
scores `Engineering + Substitution` rather than `Engineering` alone. Blowing dust
down with an air line is the standard shortcut and it converts a settled layer
into precisely the suspended cloud that deflagrates. The secondary-explosion
mechanism — a primary event lifting settled dust from beams and ceiling voids —
is why the inspection covers surfaces nobody normally looks at.

**HZ-FRY-01 — Hot-oil fire, continuous fryer at 140–180 °C.** Inherent 3×5=15,
High. Target 2×4=8.

Controls: a high-temperature cut-out **independent of the control thermostat**
(a single sensor serving both control and protection is a single point of
failure), automatic wet-chemical Class F suppression over the fryer and inside the
canopy with fuel and gas auto-shutoff, scheduled duct degreasing with records, and
an explicit **ban on water-based extinguishers in the area**. That last control is
the one most often missing: applying water to burning oil produces a violent steam
explosion, and a well-meaning extinguisher in the wrong place is a hazard rather
than a control.

**HZ-ELE-02 — Uncontrolled temporary wiring.** Inherent 4×4=16, Critical. Target
2×3=6.

This hazard is in the register because of the national data, not because of a site
observation. Electrical short circuit caused 9,392 of 27,059 fires in 2025 —
34.71%, the largest single ignition source in the country. In a plant that also
has a dust-classified zone, temporary wiring is an ignition source sitting inside
a combustible atmosphere.

Controls: a ban on permanent use of temporary wiring with a 30-day maximum permit,
a monthly electrical-safety walk with a photographic non-conformance register,
RCD/ELCB protection on all portable-tool circuits tested six-monthly, and portable
appliance testing with pass labels.

### 5.2 Statutory coverage

Every one of the 36 hazards cites at least one statutory provision — enforced by a
unit test. The most-cited instruments:

| Provision | Hazards citing |
|---|---|
| BLA 62 (precautions against fire and dangerous fumes) | 17 |
| BLA 79c (health check, dangerous operations) | 6 |
| BLR 68 (dangerous operations) | 6 |
| BNBC 2020 Part 4 (fire protection) | 5 |
| BLA 78A (training and PPE) | 4 |
| BLR 63 (excessive weights) | 4 |
| Fire Prevention and Extinction Act 2003 ss. 4 & 8 | 3 |
| BLA 61 (fencing of machinery) | 3 |

BLA 62 carrying 17 of 36 hazards is itself a finding: the primary statutory hook
for factory safety in Bangladesh is a single broadly-drafted section. That is
convenient for a compliance register and a weakness in the legislation, because a
broad duty is harder to enforce specifically than a prescriptive one — which is
part of why the BNBC and the Fire Prevention and Extinction Act do so much of the
real work in practice.

---

## 6. Permit to Work and Lockout–Tagout

### 6.1 The design principle

The value of a permit system is not the form. It is that an expired permit, a
missing gas test, an absent standby person or an unclosed fire watch can be found
*without reading every sheet in the file*. A paper system makes each of those
invisible at scale. Detection is the whole product.

### 6.2 Permit classes and their rules

| Permit type | Max validity | Gas test | Fire watch after | Standby |
|---|---|---|---|---|
| Hot Work | 12 h | Yes | 60 min | Yes |
| Confined Space Entry | 8 h | Yes | — | Yes |
| Work at Height | 12 h | No | — | Yes |
| Electrical Work | 12 h | No | — | Yes |
| Line Breaking | 8 h | Yes | — | Yes |
| Excavation | 24 h | Yes | — | No |
| General Maintenance | 24 h | No | — | No |

Two rules apply to every class:

- **The issuer and the acceptor must be different people.** A self-issued permit
  has had no independent check, and the whole control reduces to one person's
  judgement on their own work.
- **Confined space entry, line breaking and electrical work must record at least
  one energy isolation.** A permit for those activities with an empty isolation
  list is not a control document.

### 6.3 Gas-test acceptance criteria

| Parameter | Acceptable range | Basis |
|---|---|---|
| Oxygen | 19.5% – 23.5% | Standard entry criterion |
| LEL | 0 – 10% | Standard hot-work and entry criterion |
| Carbon monoxide | 0 – 25 ppm | NIOSH REL TWA |
| Hydrogen sulphide | 0 – 10 ppm | Standard |
| Ammonia | 0 – 25 ppm | NIOSH REL TWA |

The oxygen criterion is two-sided. Enrichment above 23.5% is a fire hazard, not a
safe atmosphere, and a system that only checks for deficiency will pass a
dangerously enriched space. That behaviour is unit-tested.

A gas test with no readings recorded returns **fail**, not pass. An absent
measurement is not evidence of a safe atmosphere.

### 6.4 The worked audit

The dashboard ships a six-permit register in which each of the five failure modes
appears once, so the detection logic can be seen working:

| Permit | Type | Finding |
|---|---|---|
| PTW-2026-041 | Hot Work | Compliant |
| PTW-2026-042 | Confined Space Entry | **No energy isolations recorded** |
| PTW-2026-043 | Work at Height | **Self-issued** and **no standby person** |
| PTW-2026-044 | Line Breaking | **Expired 25 h ago, never closed out** |
| PTW-2026-045 | Hot Work | **Closed without the 60-minute fire watch** |
| PTW-2026-046 | Electrical Work | Compliant |

Compliance rate 33%, six findings. Each finding names the rule broken rather than
reporting that the permit "failed", so the issuer knows what to fix.

PTW-2026-042 is the one that would kill someone. A confined-space permit with a
clean gas test, a named attendant and no isolation on the agitator drive is a
permit that authorises entry into a vessel whose agitator can still start.

### 6.5 Lockout–Tagout

Isolation is modelled across eight energy types: electrical, mechanical,
hydraulic, pneumatic, thermal, chemical, gravity and stored (spring, capacitor,
pressure).

Each isolation point must be locked, tagged, verified at zero energy by try-out,
and attributed to a named person. **Try-out** means attempting to start the
equipment through its normal controls after isolation and then returning the
control to off. A lock without a try-out is an assumption, not an isolation.

The system additionally refuses to sign off an isolation covering **electrical
energy alone** on plant that may hold stored pressure, gravity, thermal or
chemical energy. This is the classic fatal gap: the breaker is locked, the fitter
opens the machine, and the hopper contents, the trapped ammonia or the residual
steam does the killing. Four worked isolation sheets ship with the system —
ammonia compressor, powder blender, fryer line, silo agitator — each covering
three or four energy types.

---

## 7. Incident classification and performance metrics

### 7.1 Classification

Seven classes in ascending severity: Near Miss, First Aid Case, Medical Treatment
Case, Restricted Work Case, Lost Time Injury, Permanent Disability, Fatality. An
unrecognised class is rejected at load rather than silently bucketed.

**Recordable** (for TRIR): Medical Treatment Case and above.
**DART** (days away, restricted or transferred): Restricted Work Case and above.

Fatalities and permanent total disabilities are charged **6,000 days** under the
long-standing ANSI Z16.1 convention. This is applied automatically and declared
explicitly, because a severity rate quoted without stating its fatality charge is
not a comparable number.

### 7.2 The metrics, and the error they prevent

| Metric | Formula | Base | Convention |
|---|---|---|---|
| LTIFR | LTIs × 1,000,000 ÷ hours worked | 1,000,000 h | ILO |
| Severity rate | days lost × 1,000,000 ÷ hours worked | 1,000,000 h | ILO |
| TRIR | recordables × 200,000 ÷ hours worked | 200,000 h | OSHA |
| DART rate | DART cases × 200,000 ÷ hours worked | 200,000 h | OSHA |
| Incidence rate | cases × 1,000 ÷ average workers | 1,000 workers | ILO |

**The two bases are not interchangeable, and mixing them is the most common error
in factory HSE reporting.** A TRIR of 6.3 and an LTIFR of 6.3 describe completely
different levels of performance, because one is per 200,000 hours and the other
per 1,000,000. Quoting a number computed on one base against a benchmark set on
the other produces a five-fold error in either direction.

Every function in this system names its own base in its return key —
`LTIFR_per_1M_hours`, `TRIR_per_200k_hours` — and a unit test asserts that the two
never return the same value for the same inputs. That test exists specifically to
catch a future refactor that accidentally unifies them.

### 7.3 Reporting health

The observed ratio of near misses to recordables is reported as a measure of the
*reporting system*, not of the hazard. A plant recording few near misses per
recordable is almost certainly under-reporting rather than unusually safe.

On the demonstration register the ratio is 7.7 near misses per recordable. Below
roughly 10:1, under-reporting should be the working assumption, and the correct
response is to invest in the reporting channel rather than to celebrate the
apparent absence of hazards.

Falling near-miss volume is treated as a warning signal, not an improvement. It is
the leading indicator worth defending, which is why HZ-ORG-01 sets near-miss
reporting as a positive KPI with a published just-culture policy rather than a
penalty.

### 7.4 Investigation tools

**Five Why with a blame detector.** An analysis terminating in an individual —
"the operator was careless", "failed to follow the procedure" — has stopped at the
immediate cause and will not prevent recurrence. The system flags terminal
statements containing blame language and tells the investigator to keep going:
*what in the system allowed, required or rewarded that behaviour?* Depth below
five levels is also flagged.

The worked example runs from "operator sustained scald burns while draining the
fryer" through to "the interlock was never specified because the line was
commissioned without a pre-start safety review" — which lands on HZ-ORG-04,
management of change, and produces a control that protects everyone doing that
task rather than a warning to one person.

**Bow-tie with gap detection.** A bow-tie is worth drawing for one reason: it makes
an unbarriered line visible. The model returns an explicit `gaps` list naming every
threat with no preventive barrier and every consequence with no mitigative
barrier. On the ammonia model that is three lines out of nine, found in seconds.

---

## 8. The compliance matrix

### 8.1 Why both halves are needed

An ISO gap analysis that does not name the Bangladeshi legal instrument behind
each clause is an academic exercise — it tells a plant it is non-conformant
without telling it what it is exposed to. A legal register that does not map to a
management-system clause cannot be audited systematically. The matrix is both, in
one table: **clause → statute → evidence → verification method → frequency →
criticality**.

35 requirements across six ISO 45001 clause groups.

### 8.2 Conformity scoring

| Status | Score |
|---|---|
| Conforms | 1.0 |
| Minor NC | 0.6 |
| Major NC | 0.2 |
| Not Conform | 0.0 |
| Not Started | 0.0 |
| Not Applicable | excluded from the calculation |

Criticality weights: Critical 3.0, High 2.0, Medium 1.0, Low 0.5.

The weighting is deliberately steep. A Critical non-conformance cannot be averaged
away by a long list of conformities, which is what an unweighted percentage
allows. *Not Applicable* is excluded rather than scored zero — a requirement that
does not apply should not depress a score, and a system that scores it zero
punishes a plant for not having a hazard.

### 8.3 The Critical requirements

Fifteen requirements are rated Critical. Each carries a statutory duty as well as a
clause obligation, so each is an enforcement exposure and not only a certification
one:

| ID | Requirement | Statute |
|---|---|---|
| CM-04 | Safety Committee where 50+ workers, 50:50 parity, 6–12 members | BLA s. 90A; BLR r. 81, 84 |
| CM-05 | Committee meets at least quarterly | BLR Schedule IV(3) |
| CM-06 | Systematic HIRA covering routine and non-routine activities | BLA ss. 61–62; BLR r. 68 |
| CM-09 | Competence appropriate to hazards, with certification | BLA s. 78A |
| CM-13 | Hierarchy of controls applied; dangerous parts securely fenced | BLA ss. 61, 63 |
| CM-14 | Valid certificates for lifting machinery and pressure plant | BLR r. 60, 62 |
| CM-15 | Valid electrical system certification | BLR r. 58 |
| CM-16 | Permit to Work across hot work, entry, height, electrical, line breaking | BLA ss. 62, 78A |
| CM-17 | LOTO on all energy isolation during maintenance and cleaning | BLA s. 62 |
| CM-20 | Contractor pre-qualification, induction, method statements | BLA ss. 62, 150 |
| CM-21 | Fire licence valid; escape routes unobstructed; alarm functional | BLA ss. 62, 89; FPEA 2003 ss. 4, 8 |
| CM-22 | Documented emergency plan and periodic scenario drills | BLA s. 62; BNBC 2020 Part 4 |
| CM-29 | Statutory accident notification; investigation with root causes | BLA s. 80; BLR r. 73, Sch. IV(2) |
| CM-31 | Structural adequacy certified and maintained | BLA ss. 88, 326; BNBC Parts 3, 6 |
| CM-32 | Valid ECC; effluent and emissions within standards | ECA 1995; ECR 1997 |

CM-04 and CM-05 sit together deliberately. Formation and functionality are scored
as separate requirements because the CPD/FES finding — 93% formation, failing
functionality — shows they come apart in practice. A matrix that scored only
"has a safety committee" would rate the national picture at 93% conformant, which
is the exact illusion this project exists to dispel.

### 8.4 Where the gaps usually are

The dashboard ships a starting profile representing a plausible mid-maturity
Bangladeshi food plant, and its shape is itself informative. Statutory
*certificates* — boiler, electrical, structural, fire licence, ECC — are typically
in place, because they are externally demanded and periodically inspected. The
gaps cluster in the requirements nobody comes to check: the legal register
(CM-07), management of change (CM-19), compliance evaluation (CM-26), internal
audit (CM-27) and demonstrated continual improvement (CM-30) — all rated *Not
Started* in the profile. LOTO (CM-17) is the standout Critical gap, because it is
a behaviour rather than a document and cannot be satisfied by a certificate on a
wall.

---

## 9. Data provenance and integrity screening

### 9.1 Datasets

| Dataset | Content | Size | Used for |
|---|---|---|---|
| National hourly air quality | PM2.5, PM10, CO, NO₂, SO₂, O₃, AQI by city point | 1,048,551 rows, 30 named cities, 2000–2025 | Exposure analysis; air component of the site index |
| Open industrial facility registry | Geocoded apparel and textile facilities with reported worker counts | 2,123 facilities, 968 with worker data | Industrial density and worker concentration; neighbour profiles |
| City reference points | Named populated places with coordinates | 103 places | Emergency-access proxy |
| BBS Labour Force Survey 2022; QLFS 2015-16, 2023 | National labour statistics including the OSH module | Full report text | Workforce context; OSH module design |
| CPD / FES post-Accord study | Institutional analysis of DIFE, RSC, RCC, Nirapon | Full report text | Regulatory capacity; the committee functionality finding |

The row count of 1,048,551 is itself a warning: it is one short of the classic
spreadsheet row limit of 1,048,576 minus a header. The source dataset is described
as covering 103 cities; the delivered file covers 30, and the city names run
alphabetically from Azimpur to Gaurnadi. The file has been **truncated at a
spreadsheet row limit**, and every analysis in this project is scoped accordingly
rather than presented as national coverage.

### 9.2 Defect 1 — duplicate series presented as separate cities

| City A | City B | Overlap hours | Identical fraction | Separation |
|---|---|---|---|---|
| Azimpur | Dhaka | 28,968 | 1.0000 | 3.11 km |
| Barisāl | Gaurnadi | 9,783 | 1.0000 | 33.44 km |
| Dohār | Farīdpur | 28,992 | 1.0000 | 30.79 km |

Three pairs of the thirty named cities carry byte-identical hourly records,
leaving **27 independent series, not 30**.

The dataset is a gridded product: city points falling in the same model cell share
one series. A 3.11 km pair is unsurprising. Two pairs over 30 km apart tell you
the grid is coarse, which materially limits how finely the data can discriminate
between nearby industrial locations — directly relevant to the site index, where
a factory 15 km from its nearest named monitor may be characterised by a cell
whose centre is somewhere else entirely.

Treating all 30 as independent would inflate the apparent sample and let one grid
cell vote three times in any cross-city ranking. Detection is automated in
`quality.find_duplicate_series()`.

### 9.3 Defect 2 — a synthetic segment in the long Dhaka record

The published Dhaka annual mean PM2.5, as delivered:

| Year | Mean PM2.5 | Year | Mean PM2.5 | Year | Mean PM2.5 |
|---|---|---|---|---|---|
| 2000 | 39.6 | 2009 | 82.2 | 2018 | 138.2 |
| 2001 | 43.7 | 2010 | 87.6 | 2019 | 145.2 |
| 2002 | 47.6 | 2011 | 93.2 | 2020 | 152.1 |
| 2003 | 51.9 | 2012 | 99.7 | 2021 | 158.5 |
| 2004 | 56.8 | 2013 | 105.3 | **2022** | **118.5** |
| 2005 | 61.4 | 2014 | 111.6 | **2023** | **50.2** |
| 2006 | 66.4 | 2015 | 118.2 | **2024** | **47.7** |
| 2007 | 71.5 | 2016 | 124.7 | **2025** | **47.7** |
| 2008 | 76.6 | 2017 | 131.5 | | |

Fitting a linear trend across all 26 years returns **+2.55 µg/m³ per year**, R²
0.269. That is a striking, publishable-looking result about air quality in one of
the world's most polluted cities. It is also entirely an artefact.

Segment statistics after splitting at discontinuities greater than 25 µg/m³:

| Segment | Years | Mean | Std dev | Coefficient of variation |
|---|---|---|---|---|
| 2000–2021 | 22 | 93.80 | 37.24 | 0.40 |
| 2022 | 1 | 118.50 | — | — |
| 2023–2025 | 3 | 48.53 | 1.44 | 0.03 |

Back-fill screen by segment:

| Segment | Years | Monotone fraction | Linear R² | Screened | Synthetic |
|---|---|---|---|---|---|
| 2000–2021 | 22 | **1.000** | **0.994** | Yes | **Yes** |
| 2022 | 1 | — | — | No | — |
| 2023–2025 | 3 | — | — | No | — |

The 2000–2021 segment rises in **every single year** — 21 of 21 consecutive
year-pairs in the same direction — and a straight line explains 99.4% of its
variance. Real ambient particulate records do not behave that way. They carry
strong, irregular year-to-year variation driven by monsoon onset and duration,
wind direction, and brick-kiln season length. A near-perfect monotone ramp is the
signature of interpolated or modelled back-fill, and a trend fitted through it
measures the interpolation rather than the air.

The build output:

```
segment 2000-2021 (22 yr): monotone=1.0, R2=0.994, screened=True, synthetic=True
segment 2022-2022 (1 yr):  screened=False
segment 2023-2025 (3 yr):  screened=False
REJECTED: no segment both passes the screen and is long enough.
          No long-run trend will be reported from this dataset.
```

Two design points are worth stating.

**The screen must segment first.** Running the monotonicity test on the whole
26-year series returns a monotone fraction of 0.84 and an R² of 0.27, which reads
as "no problem" — the real, noisy tail statistically hides the synthetic head.
There is a unit test asserting exactly this: that the whole-series test misses the
defect and the segmented test catches it.

**A short segment is not a clean segment.** The 2023–2025 segment passes no
screen; it is simply too short to screen. The system marks it `screened=False` and
excludes it from trend claims rather than treating absence of evidence as evidence
of soundness.

### 9.4 The consequence for every downstream figure

Both defects force the same restriction, and it must apply to *all* analytics, not
only the cross-city ones. An early version of this pipeline correctly restricted
the cross-city comparison to a common window but left the seasonal, diurnal and
shift profiles on the full record. Those profiles then inherited the synthetic
segment and reported Dhaka shift exposure at 105.1 µg/m³ — roughly **twice** the
measured value of 42.0. The bug was caught by cross-reading the two tables against
each other and is recorded here because it is the realistic failure mode: not
missing the defect, but failing to propagate the fix.

The analysis window is therefore **2022-08-05 to 2025-11-23**, across the 29
cities whose records extend to the end of the file. It is written into the output
tables so it travels with the numbers. Every figure in section 10 and every air
figure in section 11 uses it.

### 9.5 Completeness

Carbon dioxide is missing for 73.8% of records and is not used anywhere in this
system. Small negative values appear in the nitrogen dioxide and ozone columns —
consistent with a modelled product rather than an instrument reading, and a
further indication that this is a reanalysis output rather than a monitoring
network.

---

## 10. Ambient exposure analysis

### 10.1 Why an HSE function should care

Most factory HSE work treats the "E" in HSE as effluent and stack emissions —
things the regulator asks about. Ambient air is the exposure every outdoor worker
takes all shift, every shift, and it is the load drawn into every fresh-air intake
on site. It is also measurable, which makes it one of the few chronic exposures a
plant can quantify without buying instruments.

### 10.2 Dhaka reference exposure, screened window

| Year | Valid days | Mean PM2.5 | Days over WHO 24-h | Days over BD 24-h | × WHO annual guideline |
|---|---|---|---|---|---|
| 2022 | 149 | 49.35 | 124 (83.2%) | 43 (28.9%) | 9.9 |
| 2023 | 365 | 50.23 | 305 (83.6%) | 101 (27.7%) | 10.0 |
| 2024 | 366 | 47.68 | 308 (84.2%) | 113 (30.9%) | 9.5 |
| 2025 | 327 | 47.70 | 285 (87.2%) | 86 (26.3%) | 9.5 |

Mean PM2.5 sits at roughly **ten times the WHO annual guideline of 5 µg/m³** and
about **three times the Bangladesh national annual standard of 15 µg/m³**. Between
83% and 87% of valid days exceed the WHO 24-hour guideline of 15 µg/m³.

Share of hours by US EPA AQI category:

| Good | Moderate | Unhealthy for Sensitive Groups | Unhealthy | Very Unhealthy | Hazardous |
|---|---|---|---|---|---|
| 10.3% | 31.7% | 20.6% | 35.9% | 1.5% | 0.0% |

**58.0% of all hours are at "Unhealthy for Sensitive Groups" or worse.** For a
plant whose gatehouse, loading bay and yard are staffed continuously, that is a
chronic exposure with no engineering control currently applied — which is
HZ-ENV-03 in the register, and the only hazard whose residual band remains Medium
rather than Low because ambient air cannot be engineered away, only shielded
against.

### 10.3 Seasonal profile

| Month | Mean PM2.5 | Month | Mean PM2.5 |
|---|---|---|---|
| January | **98.2** | July | **14.4** |
| February | 80.8 | August | 20.6 |
| March | 58.1 | September | 26.0 |
| April | 46.3 | October | 48.6 |
| May | 35.7 | November | 66.1 |
| June | 26.2 | December | 75.9 |

A **6.8-fold** swing between the July monsoon minimum and the January dry-season
maximum. This is the shape that makes scheduling a real control: heavy outdoor
work, external contractor projects and non-urgent yard tasks have a genuine
low-exposure window from June to September.

### 10.4 Shift exposure

| Shift | Mean PM2.5 | 95th percentile | × WHO 24-h guideline |
|---|---|---|---|
| A (06–14) | 42.0 | 93.4 | 2.80 |
| B (14–22) | 57.0 | 133.6 | 3.80 |
| C (22–06) | 46.9 | 118.5 | 3.13 |

Shift B carries the highest exposure, 36% above shift A. That difference is large
enough to justify rotating outdoor assignments between shifts — but it is also
small relative to the seasonal swing, which tells you where the effort belongs:
**seasonal scheduling buys more than shift rotation**, by roughly a factor of
five.

### 10.5 From data to control

At AQI 150 as the trigger, **435 of 1,207 valid days (36.0%)** would fire an
outdoor-work adjustment protocol, concentrated in the dry season.

That figure is the point of the whole exercise. A protocol firing on a third of
days within a predictable window is one a plant can actually run: shift the
movable work out of the peak months, and let the administrative trigger handle the
residue. Had the calculation returned 80% of days, the honest conclusion would
have been the opposite — that a day-by-day administrative trigger is theatre, and
the budget belongs in engineering controls instead: an enclosed and positively
pressurised gatehouse and loading office, and filtered fresh-air intakes sited
away from stack downwash.

Running this calculation *before* writing the procedure is the difference between
a control that works and one that is ignored by week three. It is also the
difference between an analytics project and an HSE project.

---

## 11. The Composite Site HSE Risk Index

### 11.1 Purpose and honest positioning

The index answers a question an HSE function is regularly asked and usually has to
answer by opinion: *is this location a higher- or lower-risk place to operate, and
why?*

It is a **screening tool**. It ranks locations relative to each other. It is not
an absolute measure of harm, and it is never a substitute for a site survey.

### 11.2 Components and weights

| Component | Weight | Measure | Rationale |
|---|---|---|---|
| Ambient air burden | 0.30 | Mean PM2.5 at the nearest monitored grid point, screened window | Chronic exposure of outdoor and yard staff; the load drawn into every air intake. Measured, not assumed. |
| Industrial density | 0.25 | Registered facilities within 10 km | A fire, release or explosion next door becomes your emergency. Also proxies approach-route congestion. |
| Worker concentration | 0.25 | Reported workers at those facilities | Population inside the same response envelope; determines how fast district emergency capacity saturates. |
| Emergency access | 0.20 | Distance to the nearest significant urban centre | Transparent proxy for fire-service and trauma-care response time. |

Each component is min–max normalised to 0–100 across the candidate set, oriented
so that higher always means more risk, then weighted. Bands: Low below 25,
Moderate 25–50, Elevated 50–75, High 75 and above.

### 11.3 Results

| Rank | Site | Plants ≤10 km | Workers ≤10 km | Mean PM2.5 | To urban centre | Index | Band | Dominant driver |
|---|---|---|---|---|---|---|---|---|
| 1 | Ashulia Industrial Belt | 715 | 558,418 | 48.66 | 7.1 km | **86.1** | High | Industrial density |
| 2 | DEPZ Savar | 353 | 282,766 | 48.66 | 14.5 km | **71.3** | Elevated | Emergency access |
| 3 | **NZDP Factory 2 — Jangalipara, Gazipur** | 340 | 278,412 | 48.66 | 12.2 km | **67.5** | Elevated | Ambient air |
| 4 | Tongi Industrial Area | 484 | 314,219 | 48.66 | 0.0 km | **57.3** | Elevated | Ambient air |
| 5 | **NZDP Factory 1 — Vulta, Rupganj** | 48 | 56,197 | 48.66 | 13.2 km | **48.7** | Moderate | Emergency access |
| 6 | NZDP Head Office — Tejgaon | 171 | 143,158 | 48.66 | 3.7 km | **43.8** | Moderate | Ambient air |
| 7 | Narayanganj Town Industrial | 148 | 98,327 | 48.66 | 0.0 km | **35.9** | Moderate | Ambient air |
| 8 | Bogura Industrial Area | 3 | 1,501 | 51.84 | 0.0 km | **30.2** | Moderate | Ambient air |
| 9 | Dinajpur Agro Belt | 0 | 0 | 49.27 | 0.0 km | **27.0** | Moderate | Ambient air |
| 10 | Chattogram Industrial Area | 245 | 184,150 | 27.72 | 0.0 km | **19.1** | Low | Industrial density |
| 11 | Cumilla Industrial Area | 9 | 4,330 | 38.94 | 0.0 km | **15.7** | Low | Ambient air |
| 12 | Sylhet Industrial Area | 1 | 0 | 25.75 | 0.0 km | **0.0** | Low | Industrial density |

**The two operating sites differ substantially — 67.5 against 48.7 — and for
reasons that translate directly into different HSE plans.**

Factory 2 (Gazipur) sits inside a dense industrial cluster: 340 registered
facilities and roughly 278,000 workers within 10 km, with the nearest recorded
facility effectively adjacent. Its exposure is *external*: a neighbour's fire or
release, a saturated district emergency service, and a congested approach route
for responding appliances. Its plan needs mutual-aid arrangements, a joint
evacuation understanding with immediate neighbours, and a marked, kept-clear FSCD
access route with a turning circle.

Factory 1 (Narayanganj) is comparatively isolated — 48 facilities, 56,000 workers
— but 13.2 km from a significant urban centre. Its exposure is *internal and
temporal*: whatever happens on site, help is further away, so the site must be
more self-sufficient. Its plan needs stronger on-site first-aid and fire
capability, a written arrangement with a burn-capable hospital, and a dedicated
emergency vehicle held on site.

Chattogram at rank 10 is instructive: 245 facilities and 184,000 workers within
10 km, but a mean PM2.5 of 27.72 against Dhaka's 48.66, and zero distance to a
major urban centre. Its low score is driven by clean air relative to the Dhaka
basin and immediate emergency-service access — a genuinely different risk profile
rather than a scoring artefact.

### 11.4 Sensitivity to the weights

Five weighting schemes: the declared baseline, equal weights, and one scheme per
component dominating at 55%.

| Site | Baseline | Equal | Air-dom. | Density-dom. | Access-dom. | Rank range | Stable |
|---|---|---|---|---|---|---|---|
| Ashulia | 1 | 1 | 1 | 1 | 3 | 2 | No |
| DEPZ Savar | 2 | 2 | 2 | 2 | 1 | 1 | Yes |
| **NZDP Factory 2** | **3** | **3** | **3** | **3** | **2** | **1** | **Yes** |
| Tongi | 4 | 4 | 4 | 4 | 6 | 2 | No |
| **NZDP Factory 1** | **5** | **5** | **5** | **6** | **4** | **2** | **No** |
| NZDP Head Office | 6 | 6 | 6 | 5 | 5 | 1 | Yes |
| Narayanganj Town | 7 | 7 | 8 | 7 | 7 | 1 | Yes |
| Bogura | 8 | 8 | 7 | 9 | 8 | 2 | No |
| Dinajpur | 9 | 9 | 9 | 10 | 9 | 1 | Yes |
| Chattogram | 10 | 10 | 11 | 8 | 10 | 3 | No |
| Cumilla | 11 | 11 | 10 | 11 | 11 | 1 | Yes |
| Sylhet | 12 | 12 | 12 | 12 | 12 | 0 | Yes |

**Seven of twelve sites hold their rank to within one position across all five
schemes. Five do not.** The honest reading: the broad tiering is robust, and
individual adjacent positions are not.

Factory 2's rank 3 is stable and can be quoted. Factory 1 moves between ranks 4
and 6 and should be quoted as "mid-table, Moderate band" rather than as rank 5.
Chattogram's three-position range means its exact placement depends on what you
think matters most, and anyone using this index to choose between Chattogram and
Bogura should set the weights deliberately rather than accept the default.

This is what a sensitivity analysis is *for*. A composite index whose ranking
flips as soon as the weights move is not telling you much, and the only way to
know which case you are in is to run it. Reporting the result honestly — including
the five unstable sites — is more useful than a single confident ranking.

### 11.5 Sensitivity to the radius

| Site | 5 km | 10 km | 15 km | 25 km |
|---|---|---|---|---|
| **NZDP Factory 1** | 48.3 Moderate | 48.7 Moderate | 53.6 Elevated | 70.4 Elevated |
| **NZDP Factory 2** | 78.2 **High** | 67.5 Elevated | 79.5 **High** | 92.1 **High** |

Factory 2 is in the High band at three of the four radii, dipping to Elevated only
at 10 km. That is a real feature, not noise: at 5 km it has 131 facilities and
118,000 workers, which is extremely dense at that scale; the normalisation then
places it lower at 10 km because *other* sites in the comparison set grow faster
over that step.

The operational reading is simply that **Factory 2's neighbourhood is dense at
every scale examined**, and the choice of 10 km as the default understates it
slightly. Factory 1 crosses from Moderate to Elevated between 10 and 15 km, which
locates the edge of its sparse envelope — useful information for deciding how far
a mutual-aid arrangement needs to reach.

### 11.6 The neighbour profile

The density score becomes actionable through the named list. Within 10 km of
Factory 2 the registry holds 340 facilities; the profile lists the 25 nearest,
of which several sit at effectively zero recorded distance — Standard Styles
(packaging, 1,241 workers), Silver Washing and Dyeing (1,500), Apparel 21 (2,000)
and Yasin Knitex (5,000).

A wet-processing and dyeing operation next door is a specific hazard, not a
generic one: it means chemical storage, boiler plant and effluent handling inside
the same response envelope. That is the list a mutual-aid agreement, a joint
evacuation plan and a shared emergency-access route should cover, and it is
available in one query.

---

## 12. Verification and testing

87 unit tests, all passing. Every rate test states its expected value as a
hand-worked calculation in its own docstring, so a reviewer can confirm the
arithmetic without trusting the code.

| Area | Tests | What is verified |
|---|---|---|
| Risk scoring | 6 | Products, all band boundaries, fatality escalation firing *and* not firing, invalid input rejection, all 25 matrix cells |
| Risk register | 8 | Seed loads and scores; controls never increase risk; current risk bounded by inherent and target; Proposed earns zero credit; Implemented earns full credit; every hazard cites a statute; roadmap ordering |
| Injury rates | 9 | LTIFR, TRIR, DART, severity, incidence and average days lost against hand calculations; zero and negative hours rejected; the ILO and OSHA bases proven non-interchangeable |
| Incident register | 5 | Classification counts; all five KPIs against hand calculations; the 6,000-day fatality charge; unknown class rejected; Pareto cumulative reaches 100% |
| Investigation | 3 | 5-Why blame detection positive and negative; bow-tie identifies every unbarriered line |
| Gas testing | 5 | Acceptable atmosphere passes; low oxygen fails and names the parameter; **enriched oxygen also fails**; ammonia above the REL fails; **no readings is a failure, not a pass** |
| Permits | 11 | Complete permit valid; over-length, missing gas test, missing standby, self-issued, expired-unclosed, fire-watch-not-completed, confined-space-without-isolation all caught; unknown type and inverted dates rejected; register audit arithmetic; duplicate ID rejected |
| LOTO | 5 | Full isolation safe; **electrical-only isolation challenged**; unverified zero energy blocks work; empty procedure unsafe; unknown energy type rejected |
| Compliance | 8 | Matrix loads; untouched scores 0; full conformity scores 100; a Critical gap costs more than a Medium one; Not Applicable excluded rather than zeroed; unknown status and unknown ID rejected; every requirement names its evidence |
| Geometry | 4 | Haversine against the known Dhaka–Chattogram distance; zero distance; vectorised form; worker-range midpoint parsing |
| Site index | 7 | Index bounded 0–100 and banded; dense outranks sparse; weights must sum to 1; missing columns rejected; facility count monotone in radius; NaN worker counts do not break the sum; sensitivity reports stability |
| Quality screen | 8 | Identical series detected; distinct series not flagged; synthetic ramp flagged; realistic noisy series not flagged; short segments marked unscreened rather than clean; segmentation splits at the step; **whole-series screening proven to miss a spliced ramp**; impossible values found |
| Exposure | 8 | All AQI categories; short days flagged invalid; exceedance counts bounded by valid days and correctly nested; shift coverage sums to all hours; trigger percentages bounded; unknown city rejected; trend refuses short series |

Three tests are worth singling out, because each encodes a lesson rather than a
specification:

- `test_the_two_bases_are_not_interchangeable` asserts that LTIFR and TRIR never
  return the same value for the same inputs. It exists to catch a future refactor
  that accidentally unifies the ILO and OSHA bases — the error this system is most
  likely to reintroduce.
- `test_whole_series_screen_would_miss_a_spliced_ramp` asserts that the naive
  whole-series test *fails* to detect a synthetic head hidden by a noisy tail, and
  that the segmented screen catches it. It documents why the screen is built the
  way it is.
- `test_enriched_oxygen_also_fails` asserts that 24.5% oxygen is rejected. A
  system that only checks for deficiency will pass a dangerously enriched space.

Two genuine bugs were found by these tests during development, both worth
recording. `control_effectiveness("PPE")` returned 0.0 instead of 0.2, because
the input was title-cased and `"PPE".title()` is `"Ppe"`, which is not in the
hierarchy table — silently dropping PPE from every control plan that named it.
And `trend_slope` crashed when passed a frame without a `coverage_ok` column,
because `DataFrame.get("coverage_ok", True)` returns the boolean `True` rather
than a mask.

Beyond unit tests, the pipeline was run end to end and all eight dashboard pages
were rendered and inspected visually. Two layout defects (a chart title colliding
with its legend, and outside bar labels overflowing the plot area) and one
analytical defect (the profile tables still using the rejected pre-2022 segment,
section 9.4) were found that way and fixed. Screenshots are in `docs/`.

---

## 13. Limitations

An HSE professional who cannot say where their own numbers stop being trustworthy
is a liability. Each item below is something a reviewer is entitled to ask about,
and each is stated before being asked.

**The incident data is synthetic.** Generated, seeded and reproducible. It is
labelled as synthetic in the filename, in a column of the file itself, and on
every dashboard page that displays it. It exists so the system can be demonstrated
before a plant loads real records. No conclusion about any real plant's injury
performance can be drawn from it. The metric definitions, classification rules and
investigation logic are real and are what a live register would use.

**The risk assessment has not been validated on site.** It is built from the
company's published description of its operations combined with the standard
hazard profile of dairy and snack-food processing. It is a credible starting
register and a demonstration of method. It is not a site assessment. A real HIRA
requires a walk-through with the people who do the work, and several hazards here
would change or disappear once the plant is actually seen. The likelihood and
severity scores are the author's judgement, not measurements.

**Site coordinates are geocoded, not surveyed.** Both factory coordinates come
from the published postal address at sub-district level. Adequate to screen a
neighbourhood at a 10 km radius. Not adequate for a dispersion model, an
evacuation plan, or anything where being 2 km out matters.

**The air-quality data is a gridded model product, not station measurements.** Two
named cities 30 km apart return identical hourly values, which settles the
question. It is fit for comparing the relative ambient burden of locations and for
characterising the seasonal and diurnal shape of exposure. It is not a substitute
for a monitor at the site boundary, and no regulatory compliance claim should rest
on it. The pre-2022 Dhaka segment is excluded entirely.

**The delivered file is truncated.** 1,048,551 rows is one short of a spreadsheet
row limit, and the 30 cities present run alphabetically from Azimpur to Gaurnadi
against a documented 103. Nothing here is national coverage.

**The facility registry is partial and sector-skewed.** It covers apparel and
textile facilities, so it under-counts food, pharmaceutical, chemical and
engineering plants. Industrial density in the site index is therefore a **lower
bound**, and it is a better proxy inside the ready-made garment belt than outside
it. Worker counts are self-reported and present for only 968 of 2,123 sites;
ranges such as "1001–5000" are reduced to their midpoint.

**The emergency-access component is a proxy.** It measures distance to the nearest
significant urban centre. It does not know where fire stations are, what the roads
are like, or how long an ambulance actually takes.

**The index weights are a judgement.** They are declared in `config.py` and are
meant to be argued with. The sensitivity analysis exists so the argument can be
settled with evidence, and it found five of twelve sites unstable — reported
rather than buried.

**The national fatality statistics under-count and they disagree with each other.**
Both SRS and OSHE derive from reported events. They are the best national picture
available and should be used as an order of magnitude, not as a precise
denominator.

**Compliance scoring is a self-assessment tool.** The conformity index is only as
good as the honesty of the person setting each status. It structures and weights a
judgement. It does not replace a third-party audit and confers no certification.

---

## 14. Implementation roadmap

The register's roadmap ranks outstanding work by the risk points each control would
remove — a different and more useful order than raw risk score, because it targets
the largest available reduction rather than the largest number.

31 hazards have an open gap, worth 246 risk points in total.

**Immediate — the seven Critical hazards with no controls yet installed (12 points each)**

| Hazard | Area | Control still to buy |
|---|---|---|
| HZ-RFG-01 | Refrigeration Plant | Fixed NH₃ detection at 25/300 ppm interlocked to ventilation and shutdown; SCBA at the plant-room door; deluge shower; NH₃-specific ERP |
| HZ-RFG-02 | Refrigeration Plant | Written LOTO with line-breaking permit: pump-down, double block and bleed, nitrogen-purge verification |
| HZ-HOT-01 | Whole Site | Hot Work Permit with a documented 60-minute fire watch and 11 m clearance |
| HZ-HGT-01 | Whole Site | Work-at-Height Permit above 1.8 m; fixed guardrails and static lines on silo tops and roof routes; rescue-from-height plan |
| HZ-MHE-01 | Warehouse & Yard | Physically segregated pedestrian walkways; 10 km/h limit; annual racking integrity inspection |
| HZ-CON-01 | Whole Site | Contractor pre-qualification, inducted photo ID, approved method statements |
| HZ-VEH-01 | Yard & Transport | One-way yard traffic plan, fixed banksman positions, wheel chocks and driver key retention |

Four of these seven are permit-and-procedure controls that cost organisation
rather than capital, which makes them the fastest available risk reduction on the
site. HZ-RFG-01 is the one requiring real capital, and it is also the one whose
failure mode is a multiple fatality.

**Within 90 days** — the remaining High-band hazards, led by HZ-BLR-02 (boiler
internal entry, 11 points) and the confined-space programme; plus the Critical
compliance gaps, of which LOTO (CM-17) is the standout because it is a behaviour
and cannot be discharged by a certificate.

**Within 12 months** — the engineering controls for the 16 hazards currently
resting on administrative measures and PPE, an occupational hygiene baseline
survey (HZ-HYG-01: dust, noise, WBGT heat, ammonia and caustic mist), and the
management-system requirements the profile shows as Not Started: legal register,
management of change, compliance evaluation, internal audit, continual improvement.

**Improvements to the system itself**, in descending value:

1. Substitute the FSCD station list for the urban-centre proxy in the
   emergency-access component, converting it from a distance stand-in to a real
   response-time estimate.
2. Survey the two factory coordinates, which unlocks everything the current
   sub-district geocoding blocks.
3. Add the SRS annual reports, FSCD statistics and DIFE LIMS to the fetch pipeline
   for automatic benchmark refresh — the manifest in
   `data/reference/data_sources_manifest.csv` already describes them.
4. Broaden the facility registry beyond apparel and textiles, which would turn the
   industrial-density lower bound into an estimate.

---

## 15. References

### Statistics and reports

- Safety and Rights Society. *802 workers were killed in 713 workplace accidents
  across the country in 2025.* https://safetyandrights.org/
- Safety and Rights Society. *758 workers killed in workplace accidents across
  Bangladesh in 2024.*
  https://safetyandrights.org/758-workers-killed-in-workplace-accidents-across-bangladesh-in-2024/
- The Business Standard. *Fragile workplace safety in Bangladesh linked to 802
  deaths in 2025: Survey.*
  https://www.tbsnews.net/bangladesh/fragile-workplace-safety-bangladesh-linked-802-deaths-2025-survey-1323496
- OSHE Foundation, reported in *Health and Safety International*. *Workplace death
  toll hits 1,190 in Bangladesh in 2025.*
  https://www.healthandsafetyinternational.com/article/1944101/workplace-death-toll-hits-1190-bangladesh-2025-report-finds
- Fire Service and Civil Defence, reported in The Business Standard. *Over 27,000
  fires in 2025, 75 per day average.*
  https://www.tbsnews.net/bangladesh/over-27000-fires-2025-75-day-average-fire-service-report-1357271
- Fire Service and Civil Defence, reported in The Business Standard. *Country
  witnesses 26,659 fire incidents, 140 deaths in 2024.*
  https://www.tbsnews.net/bangladesh/country-witnesses-26659-fire-incidents-140-deaths-2024-fscd-1054826
- Centre for Policy Dialogue / Friedrich-Ebert-Stiftung. *Industrial Safety in the
  RMG Sector in the Post-Accord-Alliance Era.*
  https://bangladesh.fes.de/fileadmin/user_upload/Industrial-Safety-in-the-RMG-Sector-in-the-Post-Accord-Alliance-Era.pdf
- Bangladesh Bureau of Statistics. *Labour Force Survey 2022*; *Quarterly Labour
  Force Survey 2015-16* and *2023*.

### Regulatory and standards

- Bangladesh Labour Act 2006, as amended.
- Bangladesh Labour Rules 2015.
- Fire Prevention and Extinction Act 2003.
- Bangladesh National Building Code 2020.
- Environment Conservation Act 1995; Environment Conservation Rules 1997.
- ISO 45001:2018, *Occupational health and safety management systems*.
- DIFE. *Managing Health and Safety in the Workplace.*
  https://dife.portal.gov.bd/sites/default/files/files/dife.portal.gov.bd/publications/00084045_2bb2_4159_861b_1cc488c45881/5%20Managing%20Health%20and%20Safety%20in%20the%20work%20place_%20English%20V9.pdf
- DIFE. *Safety Committee.*
  https://dife.portal.gov.bd/sites/default/files/files/dife.portal.gov.bd/publications/006ad2dc_dd7b_46e3_a865_671a1d508b1e/4%20Safty%20Community_English%20V8.pdf

### Exposure limits and technical references

- NIOSH. *Ammonia — Immediately Dangerous to Life or Health Concentrations
  (IDLH).* IDLH 300 ppm; REL 25 ppm TWA, 35 ppm STEL; LEL 15%.
- OSHA. *Permissible Exposure Limits, Table Z-1.* Ammonia PEL 50 ppm TWA.
- OSHA. *Ammonia Refrigeration — Hazard Recognition.*
  https://www.osha.gov/ammonia-refrigeration/hazards
- NFPA 61, *Standard for the Prevention of Fires and Dust Explosions in
  Agricultural and Food Processing Facilities.*
- WHO. *Global Air Quality Guidelines*, 2021. PM2.5 5 µg/m³ annual, 15 µg/m³
  24-hour.
- ANSI Z16.1 — the 6,000-day standard charge for a fatality or permanent total
  disability.

### Datasets

- *Bangladesh AQI Dataset 2000–2025.* Mendeley Data.
  DOI [10.17632/9j447cynb9.2](https://data.mendeley.com/datasets/9j447cynb9/2)
- Open Supply Hub. Bangladesh facility export. https://opensupplyhub.org/

---

*Repository: `safefactory-bd`. Built with Python, pandas, Streamlit and Plotly.
87 unit tests. Licensed under MIT, with the scope note in `LICENSE`: this is a
decision-support tool and not a substitute for a competent person's assessment of
an actual workplace.*
