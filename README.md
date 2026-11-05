# Straight Rows Hackathon · Bluestaq × NDSU

**"My tractor is drifting. Is it the Sun, an adversary, or my own hardware?"**

Straight Rows is an individual, 24-hour challenge for NDSU undergraduates. You build software that detects degraded GPS guidance on a simulated three-tractor fleet near Casselton, North Dakota. It attributes the cause (space weather, jamming, spoofing, equipment fault, or multipath) using farm telemetry and Space Domain Awareness feeds, then recommends an action with evidence a person can check.

One winner receives **both a paid summer internship at Bluestaq headquarters in Colorado Springs and a full one-year scholarship that pays tuition.** Standard internship eligibility and hiring requirements apply to the internship.

**Event site:** <https://bluestaq.github.io/ndsu-hackathon-submissions/>: agenda, opening remarks, step-by-step instructions, and results.
**Official guide:** [starter/docs/Bluestaq_NDSU_Straight_Rows_Hackathon_Official.pdf](starter/docs/Bluestaq_NDSU_Straight_Rows_Hackathon_Official.pdf)

## Quick start

You need Python 3.11+, Git, and a GitHub account.

```bash
git clone https://github.com/Bluestaq/ndsu-hackathon-submissions.git
cd ndsu-hackathon-submissions
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r starter/requirements.txt
python starter/scripts/get_data.py                    # works once the dataset is released at kickoff
cd starter
python submission/baseline.py --data data --output submission.json \
  --github-handle YOUR_GITHUB_USERNAME \
  --repo-url https://github.com/YOUR_GITHUB_USERNAME/YOUR_SOLUTION_REPO
python submission/validate_submission.py submission.json
```

Build your solution in **your own private repository** (copy `starter/` into it). Keep it private until hour 22.

## Submitting at hour 22

1. Make your solution repository public.
2. Fork this repository and add **one file**: `submissions/<your-github-username>/submission.json`.
3. Open a pull request. Its opening time is your submission time.

An automatic check validates the file's format. It never runs your code. Full instructions are in [submissions/README.md](submissions/README.md) and on the event site.

> **Privacy:** submissions are public. Identify yourself only by GitHub username. Never put your email address or student ID in this repository. Bluestaq University Programs already has your registration details.

## What's in this repository

| Path | Contents |
|---|---|
| `starter/` | Official guide, starter notebook, baseline, validator, and template. The dataset downloads into `starter/data/` at kickoff. |
| `submissions/` | One folder per participant, added by pull request at hour 22. |
| `scoring/` | The published automated diagnostic (`score_submission.py`), the batch scorer, and tests. The answer key is not in this repository. |
| `results/` | `results.json`, published after scoring. |
| `site/` | The event website. |
| `docs/ORGANIZERS.md` | How organizers release data, lock submissions, score, and publish results. |

## Rules in brief

- Individual work. Collaboration between competitors and sharing solutions are prohibited.
- Any language, internet resources, and AI coding assistants are allowed. You must understand and defend what you submit.
- Code and results lock at hour 22. Demonstrations (five minutes plus three minutes of Q&A) and judging fill the final two hours.
- Judges score the 100-point rubric in the guide. The automated diagnostic is supporting evidence, not extra points.
- Open to NDSU undergraduate students who are U.S. citizens. All challenge data is synthetic and unclassified.

Questions: **universityprograms@bluestaq.com**

Code in this repository is licensed under the Apache License 2.0 (see [LICENSE](LICENSE)). The dataset and official guide are provided for the Straight Rows event.
