# Straight Rows Hackathon — Student Package

**Bluestaq University Programs, in partnership with North Dakota State University**

Read `docs/Bluestaq_NDSU_Straight_Rows_Hackathon_Official.pdf` first. It is the
**official event guide**. This package is released at kickoff for an
individual competition with a 24-hour build, from Friday, November 13 at 4:00 pm
CT to Saturday, November 14 at 4:00 pm CT. Submissions close at 4:00 pm Saturday
(hour 24); demos and judging follow. Participation is restricted to NDSU undergraduate students
who are U.S. citizens. Any language, internet resources, and AI coding assistants
are allowed; collaboration between competitors is prohibited.

> “My tractor is drifting. Is it the Sun, an adversary, or my own hardware?”

Build a working system that detects degraded precision guidance, attributes its
cause using farm telemetry and Space Domain Awareness (SDA) context, and
recommends actions with evidence an operator can check. Causes can overlap.

## Quickstart

Use Python 3.11 or newer. From this package's root:

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python submission/baseline.py --data data --output submission.json \
  --github-handle YOUR_GITHUB_USERNAME \
  --repo-url https://github.com/YOUR_GITHUB_USERNAME/YOUR_SOLUTION_REPO
python submission/validate_submission.py submission.json
```

Use your real GitHub username and the private repository where you are
building your solution. **Submissions are public: never put your email address
or student ID in `submission.json`.** The validator rejects them, along with
template placeholders. A valid baseline is
only a starting point: improve its detections, recommendations, confidence, and
evidence. Validation checks format, not correctness.

For the optional interactive notebook:

```bash
python -m pip install "jupyterlab>=4,<5"
cd notebooks
jupyter lab starter_notebook.ipynb
```

The notebook loads all feeds, plots development episodes, and calls the same
baseline script. It intentionally ignores S4, RFI reports, advisories, and
multipath. The baseline identifies six of the eight evaluation episodes in the
organizer benchmark; detailed private results are withheld from competitors.

## Package contents

```text
README.md
requirements.txt
docs/Bluestaq_NDSU_Straight_Rows_Hackathon_Official.pdf
data/farm/tractor_telemetry.csv.gz
data/sda/sgi_indices.json
data/sda/scintillation_series.json
data/sda/constellation_advisories.json
data/sda/rfi_reports.json
data/labels/train_episodes.json
notebooks/starter_notebook.ipynb
submission/baseline.py
submission/submission_template.json
submission/validate_submission.py
```

## Simulated timeline

Scenario epoch: **2026-05-04T00:00:00Z**. These are simulated dates,
not the actual event dates.

- Development: hours 0–48, with 12 labeled episodes.
- Evaluation: **2026-05-06T00:00:00Z through 2026-05-07T00:00:00Z**, with
  eight unlabeled episodes. Only this window is scored.
- Three machines work approximately 06:00–22:00 local time
  (11:00Z–03:00Z) and park overnight.
- Scored guidance episodes concern working tractors. Poor reception while
  parked alone is not a scored guidance event.
- Retrospective processing of the full evaluation window is allowed. Episode
  onset accuracy is not a measurement of online detection latency.

## Farm telemetry

The compressed CSV has **777,600 rows**: 72 hours × 3 tractors × 1 Hz.

| Column | Meaning |
|---|---|
| `ts` | UTC timestamp |
| `tractor_id` | `T1`, `T2`, or `T3` |
| `lat`, `lon` | Reported GNSS position; can be displaced during spoofing |
| `speed_mps` | 4.5 while working, 0 while parked |
| `cross_track_error_m` | Deviation from the intended line, supplied by a separate simulated guidance monitor |
| `num_sats` | Satellites used in the navigation solution |
| `mean_cn0_dbhz` | Mean carrier-to-noise ratio across tracked satellites |
| `min_cn0_dbhz` | Weakest tracked signal; individual satellite measurements are not supplied |
| `fix_state` | `RTK_FIXED`, `RTK_FLOAT`, `DGPS`, `AUTONOMOUS`, or `NO_FIX` |
| `base_link_ok` | Whether the RTK correction link is available |

The guidance monitor is an idealized simulated measurement, not a claim that a
real GNSS receiver independently knows its true cross-track error. Reported
position is not trusted ground truth. Real deployments would need independent
position or inertial checks.

## SDA feeds

- `sgi_indices.json`: three-hourly **Kp** and hourly **Dst**. The synthetic
  storm profile is inspired by public measurements of the May 2024 Gannon
  storm; it is not an exact archival replay.
- `scintillation_series.json`: a 15-minute regional **S4** proxy, lagging Kp.
  Compare it with actual farm impact rather than assuming identical timing.
- `constellation_advisories.json`: routine maintenance and storm advisories.
- `rfi_reports.json`: reports with uncertain locations and 10–30-minute delays.
  Some interference events have no report; reports can be false alarms. An
  uncertainty ellipse and a nearby timestamp are corroboration, not proof.

All data is synthetic and unclassified. No live accounts, external API credits,
physical equipment, or RF transmission are required.

## Classes and expected actions

| Class | Expected action |
|---|---|
| `SPACE_WEATHER` | `HALT_OR_DEGRADED_MODE` |
| `JAMMING` | `HALT_AND_REPORT` |
| `SPOOFING` | `HALT_CROSSCHECK_AND_REPORT` |
| `EQUIPMENT_FAULT` | `SERVICE_MACHINE_OTHERS_CONTINUE` |
| `MULTIPATH` | `CONTINUE_FALSE_ALARM` |

Do not force one class per timestamp: a machine fault or interference can
coincide with a regional storm. Use a separate detection for each distinct cause.

## Deliverables and judging

Submit by **hour 24 (Saturday, November 14, 4:00 pm CT)**:

1. `submission.json`, following the template and passing the validator.
2. A repository link with source, pinned dependencies, exact reproduction
   commands, approach, limitations, and additional data that would help.
3. A five-minute working demo followed by three minutes of Q&A.

No separate technical memo is required. You must understand and defend your
solution, including code produced with AI assistance.

| Event criterion | Points |
|---|---:|
| Technical execution | 30 |
| Mission relevance and decision quality | 25 |
| Innovation and research depth | 20 |
| Assurance and rigor | 15 |
| Demo and communication | 10 |

The automated diagnostic is supporting evidence for judges, not an extra
40-point event component. Its matching thresholds, onset credit, false-positive
rules, and recurrent-multipath exemption are published on page 4 of the PDF.
Ties use mission relevance and decision quality, then technical execution.

## Submitting by the deadline

**Deadline: Saturday, November 14, 2026, 4:00 pm Central Time.** Pull requests
opened or changed after the deadline are not accepted.

1. Build in your own GitHub repository and keep it private until you submit.
2. Before the deadline, make your repository public.
3. Fork [Bluestaq/ndsu-hackathon-submissions](https://github.com/Bluestaq/ndsu-hackathon-submissions) and add exactly one file:
   `submissions/<your-github-username>/submission.json`.
4. Open a pull request. Its opening time is your submission time. A check
   validates the file's format only; it never runs your code.

Full step-by-step instructions, the agenda and results are at
<https://bluestaq.github.io/ndsu-hackathon-submissions/>.

Registered participants receive the confirmed date, room, and kickoff time from
**universityprograms@bluestaq.com**. One winner receives **both a paid summer internship at Bluestaq headquarters
in Colorado Springs and a full one-year scholarship that pays tuition**. The internship is subject
to standard internship eligibility and hiring requirements.
