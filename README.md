# romanslaap.nl

The website and every resume PDF are generated from one file: `data/career.yaml`.

```
data/career.yaml      all career facts (roles, bullets + tags, skills, education, ...)
resumes/*.yaml        one small config per resume variant
templates/            site.html.j2 (website), resume.html.j2 (PDF layout)
static/               images and CNAME, copied as-is
build.py              renders _site/ (website) and dist/resumes/ (HTML + PDF per variant)
```

## Build locally

```sh
pip install -r requirements.txt
python -m playwright install chromium
python build.py                       # or --no-pdf for a quick site-only build
python -m http.server -d _site 8000   # preview at http://localhost:8000
```

## Common changes

- **Change a fact**: edit `data/career.yaml`. Website and all resumes pick it up.
- **New job**: add an entry to `experience` (top = newest). Give each bullet one or more `tags`.
  `site: false` on a bullet keeps it off the website (for resume-only rewordings).
- **New resume variant**: copy `resumes/fde.yaml`, change `output`, `headline`, `tags`, limits.
- **Skills**: define each skill once under `skills:` in `career.yaml` (id, label, group), and list
  the ids a position used in its `used:`. The build fails on unknown ids and on skills no position uses.
  The website shows every skill; a resume shows only skills used by the roles on it.
- **Tailor for a posting**: adjust a variant's `tags` order, `max_bullets_per_position`,
  `exclude_positions`, `skill_groups` (which groups, in which order; `{label: ..., groups: [...]}` merges several
  groups into one line) or `exclude_skills`.
  Variants only select and reorder facts; wording lives in `career.yaml`. Other variant keys:
  `max_tech_per_position` (length of each role's "Tech:" line), `skill_labels` (resume-only label per skill id), `availability`,
  `certifications` (names to keep) and `position_notes` (an extra line under a position).
- **Resume-only layout**: `client_of: <position id>` nests a position under that one as a
  client project; `resume_merge` on an experience entry collapses its positions into one
  entry with its own `title`, `company` and `date`. The website ignores both.
- **Which PDF the site's Resume button serves**: `site.resume` in `career.yaml`.

The build fails on unknown tags, position ids, skills or skill groups, and warns when a PDF
exceeds the variant's `max_pages`.

## Deploy

Pushing to `main` runs `.github/workflows/deploy.yml`: it builds everything, deploys `_site/`
to GitHub Pages, and attaches all resume PDFs (including unpublished variants) to the run
as a downloadable `resumes` artifact.
