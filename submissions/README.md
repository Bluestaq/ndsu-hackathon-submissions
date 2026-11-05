# Submitting your solution

Submit before the deadline, when code and results lock (hour 24).

**Deadline: Saturday, November 14, 2026 at 4:00 pm Central Time (Fargo, ND) — 22:00 UTC.** Pull requests opened or changed after the deadline are not accepted.

## Before you submit

- Build in your own GitHub repository, and keep it **private** until you submit.
- Its README must give exact setup and run commands, pinned dependencies, and the command that regenerates your `submission.json`.
- Validate early and often:

  ```bash
  python starter/submission/validate_submission.py path/to/submission.json
  ```

## Submitting (before the deadline)

1. **Make your solution repository public.** (Settings → General → Danger Zone → Change visibility.)
2. **Fork** `Bluestaq/ndsu-hackathon-submissions` (the Fork button, top right).
3. In your fork, **add exactly one file**: `submissions/<your-github-username>/submission.json`.

   With Git:

   ```bash
   git clone https://github.com/<your-github-username>/ndsu-hackathon-submissions.git
   cd ndsu-hackathon-submissions
   git switch -c submission
   mkdir -p submissions/<your-github-username>
   cp /path/to/your/submission.json submissions/<your-github-username>/submission.json
   python starter/submission/validate_submission.py submissions/<your-github-username>/submission.json
   git add submissions/<your-github-username>/submission.json
   git commit -m "Straight Rows submission: <your-github-username>"
   git push -u origin submission
   ```

   In the browser: in your fork, choose **Add file → Create new file**. Type `submissions/<your-github-username>/submission.json` as the name, paste your JSON, and commit to a new branch.

4. **Open a pull request** to `Bluestaq/ndsu-hackathon-submissions` `main`, and complete the checklist.
5. Wait for the **Submission check** to finish. If it fails, read the job summary, fix the file, and push again to the same branch **before the deadline**. Any push after 4:00 pm Central makes the submission late.

## What the check verifies

- The pull request changes only `submissions/<your-github-username>/submission.json`.
- `participant.github_handle` matches your GitHub username, and `repository_url` is a **public** repository you own.
- The file passes the starter validator: identifiers, timestamps, confidence and evidence.
- No email address or student ID is present.
- The pull request was opened, and last changed, before the deadline.

It checks **format only**. It never runs your code, and it does not score you. Scoring runs once, after the lock.

## submission.json

```json
{
  "participant": {"github_handle": "your-github-username", "display_name": "Optional name for the results page"},
  "repository_url": "https://github.com/your-github-username/your-solution-repo",
  "detections": [
    {
      "start": "2026-05-06T10:15:00+00:00", "end": "2026-05-06T10:55:00+00:00",
      "tractors": ["T1", "T2"], "class": "JAMMING", "action": "HALT_AND_REPORT",
      "confidence": 0.8,
      "evidence": ["C/N0 fell on T1 and T2 together while S4 stayed quiet", "RFI report near the field at 10:22"]
    }
  ]
}
```

`display_name` is optional. If you include it, it appears on the results page next to your GitHub username.
