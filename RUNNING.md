# How to run SafeFactory BD

Five commands. Total time: about two minutes, most of it the first data build.

---

## 0. What you need

- **Python 3.10 or newer.** Check with `python --version` (on some systems it is
  `python3`). If you don't have it: [python.org/downloads](https://www.python.org/downloads/)
  — on Windows, tick **"Add Python to PATH"** during install.
- About 300 MB of free disk.
- No internet needed after the packages install. Nothing is uploaded anywhere.

---

## 1. Open a terminal in the project folder

- **Windows:** open the `safefactory-bd` folder in File Explorer, click the address
  bar, type `cmd`, press Enter.
- **macOS:** right-click the folder → Services → New Terminal at Folder.
- **Linux:** `cd /path/to/safefactory-bd`

You are in the right place if `dir` (Windows) or `ls` (macOS/Linux) shows
`README.md`, `app`, `src` and `scripts`.

---

## 2. Install the packages

```bash
pip install -r requirements.txt
```

If `pip` is not found, use `python -m pip install -r requirements.txt`.

<details>
<summary>Optional but recommended: use a virtual environment</summary>

Keeps these packages separate from the rest of your system.

```bash
# create it
python -m venv .venv

# activate it
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# then install
pip install -r requirements.txt
```

Run `deactivate` when you're done. You need to activate it again in each new
terminal.
</details>

---

## 3. Check the raw data is in place

The project needs two files in `data/raw/`:

```
data/raw/bd_air_quality_hourly.csv.gz     ~22 MB
data/raw/osh_facilities_bd.csv            ~8 MB
```

If you downloaded the **ready-to-run** zip, they are already there — skip ahead.

If you cloned from GitHub, they are not committed (too large). Get them from:

| File | Source |
|---|---|
| `bd_air_quality_hourly.csv.gz` | Bangladesh AQI Dataset, Mendeley Data, DOI [10.17632/9j447cynb9.2](https://data.mendeley.com/datasets/9j447cynb9/2) |
| `osh_facilities_bd.csv` | [Open Supply Hub](https://opensupplyhub.org/), Bangladesh facility export |

Rename them to exactly the names above and drop them into `data/raw/`.

---

## 4. Build the data

```bash
python scripts/build_dataset.py
```

Takes about 30 seconds. It reads the 1.05-million-row air-quality file, runs the
integrity screen, and writes 37 tables into `data/processed/`.

**You should see the integrity screen reject the trend** — this is correct
behaviour, not an error:

```
3 duplicate city series found; 27 of 30 named cities are independent
segment 2000-2021 (22 yr): monotone=1.0, R2=0.994, screened=True, synthetic=True
REJECTED: no segment both passes the screen and is long enough.
          No long-run trend will be reported from this dataset.
```

Then generate the demonstration incident register:

```bash
python scripts/make_demo_incidents.py
```

---

## 5. Launch the dashboard

```bash
streamlit run app/Home.py
```

Your browser opens at `http://localhost:8501`. Eight pages in the left sidebar:

| Page | What to show someone first |
|---|---|
| **Home** | The three-state risk chart — inherent vs current vs target |
| **Risk Register** | The 5×5 matrix, then the control-quality scatter |
| **Permit to Work** | The live audit tab — 6 permits, 4 non-compliant, each finding named |
| **Incidents** | The 5-Why blame detector and the ammonia bow-tie gaps |
| **Site Risk Index** | The ranking, then "Does the ranking hold?" |
| **Exposure** | The work-adjustment calendar at the bottom |
| **Compliance** | Conformity by ISO clause |
| **Data & Method** | The two dataset defects, and the Limitations tab |

Press **Ctrl+C** in the terminal to stop it.

---

## Optional

**Run the tests** — 87 of them, about one second:

```bash
python -m pytest tests/ -v
```

**Regenerate the one-page PDF summary** (put your real repo URL in):

```bash
python scripts/make_onepager.py github.com/yourname/safefactory-bd
```

Output: `reports/SafeFactory_BD_One_Page_Summary.pdf`

---

## If something goes wrong

| Symptom | Fix |
|---|---|
| `python: command not found` | Try `python3` instead of `python` everywhere |
| `pip: command not found` | Use `python -m pip ...` |
| `streamlit: command not found` | Use `python -m streamlit run app/Home.py` |
| `Missing data/raw/bd_air_quality_hourly.csv.gz` | Step 3 — the file isn't there or is named differently |
| Dashboard says "Processed data not found" | You skipped step 4. Run `python scripts/build_dataset.py` |
| `ModuleNotFoundError: No module named 'safefactory'` | You're not in the project root. `cd` into `safefactory-bd` first |
| Port 8501 already in use | `streamlit run app/Home.py --server.port 8502` |
| Browser doesn't open | Paste `http://localhost:8501` in manually |

---

## Publishing it to GitHub

```bash
# the repo already has one commit; just point it at GitHub
gh repo create safefactory-bd --public --source=. --push
```

No `gh` CLI? Create an empty repo on github.com, then:

```bash
git remote add origin https://github.com/yourname/safefactory-bd.git
git branch -M main
git push -u origin main
```

`data/raw/` and `data/processed/` are gitignored — the raw data is too large to
commit and the processed tables rebuild in 30 seconds.
