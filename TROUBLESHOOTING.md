# Troubleshooting Streamlit Cloud Deployment

## Common Errors and Solutions

### Error: "Error running app"

This usually means there's an issue with the code or dependencies. Here's how to fix it:

#### 1. Check Streamlit Cloud Logs

In Streamlit Cloud dashboard:
- Click on your app
- Go to "Manage app" → "Logs"
- Look for the actual error message (it will tell you what's wrong)

#### 2. Common Issues:

**Missing Dependencies:**
- Make sure `requirements.txt` includes all packages
- Current requirements: `pandas` and `streamlit`

**Database File Not Found:**
- Verify `bps_database.db` is in the repository
- Check that it's not in `.gitignore`
- File should be in the root directory

**Path Issues:**
- Streamlit Cloud runs from the root directory
- Make sure paths use `Path(__file__).parent` (which we're already doing)

**File Size Limits:**
- GitHub: 100MB per file (our DB is 16MB, so OK)
- Streamlit Cloud: 1GB total app size
- If documents folder is too large, consider Git LFS

#### 3. Quick Fixes to Try:

**Update requirements.txt:**
Make sure it has exact versions:
```
pandas>=2.0.0
streamlit>=1.28.0
```

**Check File Structure:**
Your repo should have:
```
bps_database_explorer/
├── app.py
├── requirements.txt
├── bps_database.db
├── all_bps_docs/
└── .streamlit/
    └── config.toml
```

#### 4. Test Locally First:

Before deploying, test locally:
```bash
source venv/bin/activate
streamlit run app.py
```

If it works locally but not on Streamlit Cloud, check:
- File paths
- Environment differences
- Missing files

#### 5. View Detailed Error:

In Streamlit Cloud:
1. Go to your app dashboard
2. Click "Manage app"
3. Click "Logs" tab
4. Look for Python traceback/error messages
5. Share the error message for more specific help

---

## Next Steps

1. **Check the logs** in Streamlit Cloud dashboard
2. **Share the error message** - I can help fix it specifically
3. **Verify files are pushed** - Make sure database is in GitHub

---

## Push Updated Code

After fixing issues:

```bash
git add .
git commit -m "Fix deployment issues"
git push
```

Streamlit Cloud will automatically redeploy.
