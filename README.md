# PaperFeed

PaperFeed is a minimal personal website that shows **new PubMed papers each day** for maxillofacial and related surgery topics.

It is designed to be simple:
- Static website (works on GitHub Pages)
- Daily GitHub Actions job fetches papers from PubMed
- Papers saved to `data/papers.json`
- Duplicate papers removed by PMID
- Only recent papers are shown (older ones are hidden)
- Newspaper-style layout with topic tabs for quick browsing

## Topics included
- maxillofacial surgery
- oral surgery
- facial reconstruction surgery
- orthognathic surgery
- facial trauma
- oral and maxillofacial infections
- cleft lip and palate surgery

## What is shown for each paper
- Title
- Authors
- Publication date (human-readable + ISO date when available)
- Structured abstract blocks: Objective/Aims, Study and Methods, Results, Conclusion
- Limitations (if detected in abstract sections)
- Figures link (opens the PubMed figures section)
- Link to PubMed

> Note: The script uses PubMed metadata/abstract. Full-text extraction is not guaranteed.

## How to deploy on GitHub Pages (step-by-step)
1. Create a GitHub repository (for example: `paperfeed`) and push this project to it.
2. Open your repository on GitHub.
3. Click **Settings** (top menu in the repository).
4. In the left sidebar, click **Pages**.
5. In **Build and deployment**:
   - **Source**: select **Deploy from a branch**
   - **Branch**: select your default branch (usually `main`)
   - **Folder**: select **/** (root)
6. Click **Save**.
7. Wait 1-2 minutes for GitHub Pages to build the site.
8. Refresh the **Pages** settings screen and click the published URL.

Your site URL format will be:
`https://<your-username>.github.io/<repo-name>/`

### First-time checks if the page does not open
1. Confirm files are in repo root: `index.html`, `app.js`, `style.css`, `data/papers.json`.
2. Confirm you selected **Deploy from a branch** + `main` + `/(root)`.
3. Go to the **Actions** tab and check for failed workflows.
4. If the site is still not available, wait a few more minutes and refresh.

### How to trigger today's data refresh manually
1. Open the repository **Actions** tab.
2. Click workflow **Daily PubMed Fetch**.
3. Click **Run workflow**.
4. After it finishes, refresh your website.

## Daily automation
GitHub Actions workflow (`.github/workflows/daily_fetch.yml`) runs every day and:
1. Fetches new papers from PubMed
2. Deduplicates papers by PMID
3. Keeps only recent papers (last 7 days)
4. Writes `data/papers.json`
5. Commits changes automatically

You can also run it manually from the **Actions** tab.

## Manual local run (optional)
```bash
python scripts/fetch_papers.py
```

## Customize
Open `scripts/fetch_papers.py` and edit:
- `TOPIC_QUERIES` to change topics
- `MAX_AGE_DAYS` to keep papers for longer/shorter period
- `MAX_RESULTS` to fetch more/less papers
