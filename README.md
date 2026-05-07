# UTM Annual Dashboard — FY 2025-26

Live dashboard auto-generated from Excel data. Updates automatically when the Excel file is replaced.

---

## 🔗 Live Dashboard URL

Once set up, your dashboard will be live at:
```
https://YOUR-GITHUB-USERNAME.github.io/utm-dashboard/
```

---

## ⚙️ One-Time Setup (do this once only)

### Step 1 — Create the repo
1. Go to [github.com/new](https://github.com/new)
2. Name it: `utm-dashboard`
3. Set it to **Public**
4. Click **Create repository**

### Step 2 — Upload all files
Upload the following files/folders maintaining the exact same folder structure:
```
utm-dashboard/
├── build.py
├── requirements.txt
├── .github/
│   └── workflows/
│       └── build.yml
├── data/
│   └── master_sales.xlsx       ← your Excel file goes here
└── docs/
    └── .gitkeep
```

To upload: click **Add file → Upload files** in GitHub.

> ⚠️ Make sure the Excel file is named exactly: `master_sales.xlsx` and placed inside the `data/` folder.

### Step 3 — Enable GitHub Pages
1. Go to your repo → **Settings** → **Pages** (left sidebar)
2. Under **Source** → select **Deploy from a branch**
3. Branch: select `gh-pages` → folder: `/ (root)`
4. Click **Save**

### Step 4 — Trigger first build
1. Go to **Actions** tab in your repo
2. Click **Build Dashboard** on the left
3. Click **Run workflow** → **Run workflow**
4. Wait ~1 minute
5. Your dashboard is live!

---

## 🔄 Updating the Data (anyone can do this)

Whenever you have a new Excel file:

1. Go to your GitHub repo in a browser
2. Click on the `data/` folder
3. Click on `master_sales.xlsx`
4. Click the **trash icon** (top right) to delete it → commit the deletion
5. Go back to the `data/` folder
6. Click **Add file → Upload files**
7. Upload the new Excel file — **must be named** `master_sales.xlsx`
8. Click **Commit changes**
9. GitHub automatically rebuilds the dashboard
10. Within 1–2 minutes, the live URL shows updated data

> ✅ No coding needed. Just replace the file.

---

## ⚠️ Important Rules for the Excel File

- File name must be exactly: `master_sales.xlsx`
- Sheet name must remain: `Master Sales` (check your sheet tab)
- Column headers (row 1) must not be changed
- SZN brand rows will be automatically excluded
- All other brands (Sangria, House of Pataudi, All About You, Anouk Rustic) will be included

---

## 📁 Folder Structure Explained

| Folder/File | Purpose |
|---|---|
| `data/master_sales.xlsx` | Your source Excel — replace this to update dashboard |
| `build.py` | Python script that reads Excel and generates HTML |
| `requirements.txt` | Python packages needed (auto-installed by GitHub) |
| `.github/workflows/build.yml` | Automation — runs build.py whenever Excel changes |
| `docs/index.html` | Generated dashboard HTML (auto-created, don't edit) |

---

## 🛠️ Troubleshooting

**Dashboard not updating?**
- Go to **Actions** tab → check if the latest workflow run has a green tick ✅
- If it shows a red ✗, click it to see the error message

**Build failing?**
- Make sure the Excel file is named exactly `master_sales.xlsx`
- Make sure it's inside the `data/` folder
- Make sure the sheet name hasn't changed

**Pages not showing?**
- Go to Settings → Pages → confirm it's set to `gh-pages` branch
- Wait 2–3 minutes after a successful build
