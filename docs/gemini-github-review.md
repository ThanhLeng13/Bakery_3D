# Gemini GitHub PR Review

This repository includes a GitHub Actions workflow that runs Gemini on pull requests and posts a code review back to GitHub.

## Setup

1. Create a Gemini API key in Google AI Studio.
2. Open the GitHub repository: `Settings` > `Secrets and variables` > `Actions`.
3. Add a repository secret:
   - Name: `GEMINI_API_KEY`
   - Value: your Gemini API key
4. Optional: add a repository variable named `GEMINI_MODEL`.
   - Default: `gemini-2.5-pro`

## Usage

- Gemini runs automatically when a pull request is opened, reopened, marked ready for review, or updated.
- For safety, automatic reviews only run for pull requests from branches in this repository, not forks.
- To review manually, go to `Actions` > `Gemini PR Review` > `Run workflow`, then enter the PR number.
- You can add an optional focus such as `security`, `performance`, or `API contract`.

## Notes

- The workflow uses `google-github-actions/run-gemini-cli` with the official Gemini CLI code review extension.
- Gemini can read the PR diff and post review comments through the GitHub token granted to the workflow.
- Keep the API key only in GitHub Secrets. Do not commit it to the repository.
