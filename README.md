# 2026 LLWS 12U Auto-Updating Schedule

## Upload to GitHub
Upload **all files and folders in this package** to the root of your GitHub repository.
Be sure `.github/workflows/update.yml` is included.

## Turn on GitHub Pages
Repository → Settings → Pages → Deploy from a branch → `main` → `/ (root)` → Save.

## Allow the updater to commit
Repository → Settings → Actions → General → Workflow permissions →
select **Read and write permissions** → Save.

## Run the first update
Repository → Actions → `Update LLWS schedule` → Run workflow.

After it finishes, open your GitHub Pages address. The page reads `latest.json`.
The workflow then checks official LittleLeague.org tournament pages on an hourly
schedule during August and commits changes automatically.

## Important
This is a personal dashboard, not an official Little League product. It uses
publicly available tournament pages. If Little League changes its page markup,
the scraper may need an adjustment.
