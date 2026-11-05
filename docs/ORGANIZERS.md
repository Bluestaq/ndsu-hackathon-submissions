# Organizer runbook

Everything here is done by Bluestaq organizers with write access. Participants never need it.

## Before the event

1. **Event details.** Edit `site/event.json` with the date, kickoff time, room, and lock time, then merge. The site updates automatically.
2. **Lock time.** Set the repository variable `SUBMISSION_LOCK_UTC` (ISO 8601, for example `2026-12-05T22:00:00Z`) in Settings → Secrets and variables → Actions → Variables. Optionally set `SUBMISSION_GRACE_MINUTES` (default 10).
3. **Answer key.** Confirm the repository secret `ANSWER_KEY_JSON` exists. It holds the evaluation answer key and is never committed.
4. **Dataset.** Confirm the draft release **Straight Rows dataset** has `StraightRows_Student_Package.zip` attached, and that its checksum matches `starter/DATASET_SHA256`.
5. **Recommended protections.** Protect `main`: require pull requests and the **Tests** check, and restrict who can push.

## Kickoff (hour 0)

- Publish the draft release. `starter/scripts/get_data.py` and the "latest release" download link start working immediately.

## Lock (hour 22)

- Participants open one pull request each. The **Submission check** validates format without running participant code.
- Review each pull request. Merge those that pass and touch only `submissions/<handle>/submission.json`. Note any marked late.
- Never merge a pull request that changes anything outside the participant's own folder.

## Scoring and results

1. After all valid submissions are merged, run **Actions → Score submissions → Run workflow** and type `score`.
2. The workflow scores every merged submission with the answer key secret and opens a **Publish diagnostic results** pull request that updates `results/results.json`.
3. Review it, then merge. The results page updates automatically.
4. The results page shows the automated diagnostic only. The winner is decided by the judges with the 100-point rubric and announced separately.

## Privacy

Submissions identify participants only by GitHub username and an optional display name. If anyone adds an email address, student ID, or other personal details, close the pull request and ask them to resubmit. Personal details stay with University Programs.
