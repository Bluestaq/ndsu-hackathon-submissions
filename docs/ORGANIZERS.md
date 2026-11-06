# Organizer runbook

Everything here is done by Bluestaq organizers with write access. Participants never need it.

## Before the event

1. **Event details.** Edit `site/event.json` with the date, kickoff time, room, and lock time, then merge. The site updates automatically.
2. **Lock time.** The repository variable `SUBMISSION_LOCK_UTC` is `2026-11-14T22:00:00Z` (Saturday, November 14, 2026, 4:00 pm CST in Fargo), and `SUBMISSION_GRACE_MINUTES` is `0`. Change them in Settings → Secrets and variables → Actions → Variables.
3. **Answer key.** Confirm the repository secret `ANSWER_KEY_JSON` exists. It holds the evaluation answer key and is never committed.
4. **Dataset.** Confirm the draft release **Straight Rows dataset** has `StraightRows_Student_Package.zip` attached, and that its checksum matches `starter/DATASET_SHA256`.
5. **Branch protection.** `main` requires a pull request and a passing **Tests** check, applies to administrators, and blocks force pushes and deletion. Organizers merge submission pull requests; no approving review is required.
6. **Fork pull request approval.** In Settings → Actions → General, set "Approval for running fork pull request workflows from contributors" to **Require approval for first-time contributors who are new to GitHub**. With the stricter setting every student is a first-time contributor, so no check runs until an organizer approves it. Students with brand-new accounts still need approval: watch for "Approve and run" in the last hour.

## Kickoff (Friday, Nov 13, 4:00 pm CT · hour 0)

- Publish the draft release. `starter/scripts/get_data.py` and the "latest release" download link start working immediately.

## Deadline (Saturday, Nov 14, 4:00 pm CT · hour 24)

- Participants open one pull request each. The **Submission check** validates format without running participant code.
- Review each pull request. Merge those that pass and touch only `submissions/<handle>/submission.json`. Do not merge late submissions. The check fails any pull request opened, pushed to, or reopened after the deadline. Editing a title or ticking the checklist does not re-run it.
- The scorer is the backstop. It dates each merged pull request's final commit by the first Actions run GitHub created for it, which cannot be backdated, and excludes any entry opened or changed after the deadline even if its check shows green.
- Never merge a pull request that changes anything outside the participant's own folder.

## Scoring and results

1. After all valid submissions are merged, run **Actions → Score submissions → Run workflow** and type `score`.
2. The workflow scores every merged submission with the answer key secret and pushes a `results/run-<id>` branch with the updated `results/results.json`. (Organization policy does not let Actions open pull requests.)
3. Open the run's job summary, choose **Open the results pull request**, review it, and merge. The results page updates automatically.
4. The results page shows the automated diagnostic only. The winner is decided by the judges with the 100-point rubric and announced separately.

## Privacy

Submissions identify participants only by GitHub username and an optional display name. If anyone adds an email address, student ID, or other personal details, close the pull request and ask them to resubmit. Personal details stay with University Programs.
