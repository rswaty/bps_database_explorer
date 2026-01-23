# Deployment Checklist

## Before Sharing with Colleagues

### ✅ Files to Include

Make sure these files are in your project:
- [x] `app.py` - Main application file
- [x] `requirements.txt` - Python dependencies
- [x] `bps_database.db` - Database file (IMPORTANT!)
- [x] `all_bps_docs/` - Document folder with all .docx files
- [x] `README.md` - Project documentation
- [x] `USER_GUIDE.md` - Guide for end users

### For Streamlit Cloud Deployment

1. **Create `.streamlit/config.toml`** (already created ✓)
2. **Ensure database is included** - The database file should be committed to git
3. **Check file sizes**:
   - Database: Should be fine (SQLite databases are usually small)
   - Documents: If `all_bps_docs/` is very large (>100MB), consider:
     - Using Git LFS (Large File Storage)
     - Or hosting documents separately

### Quick Test Before Sharing

1. **Test locally first**:
   ```bash
   source venv/bin/activate
   streamlit run app.py
   ```
   - Search for a model
   - Try downloading a document
   - Make sure everything works

2. **Check file paths**:
   - Make sure `bps_database.db` is in the same directory as `app.py`
   - Make sure `all_bps_docs/` folder exists and has documents

---

## Sharing Options Summary

| Option | Best For | Difficulty | Cost |
|--------|----------|------------|------|
| **Streamlit Cloud** | Sharing with many people, anywhere | Easy | Free |
| **Local Network** | Same office/network | Easy | Free |
| **Setup Script** | Sharing files directly | Medium | Free |
| **Docker** | Technical users | Hard | Free |

**Recommendation**: Use **Streamlit Cloud** - it's the easiest for non-technical users!

---

## Step-by-Step: Streamlit Cloud Deployment

### 1. Prepare Your Repository

```bash
# Make sure .gitignore allows the database
# Check that bps_database.db is not ignored
git status
```

### 2. Create GitHub Repository

- Go to https://github.com/new
- Repository name: `bps-database-explorer`
- Make it **Public** (required for free tier)
- Click "Create repository"

### 3. Push Your Code

```bash
cd /home/rswaty/Documents/bps_database_play

# Initialize git if not already done
git init

# Add all files (including database)
git add .

# Commit
git commit -m "BPS Database Explorer - Ready for deployment"

# Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/bps-database-explorer.git

# Push
git branch -M main
git push -u origin main
```

### 4. Deploy to Streamlit Cloud

- Go to https://share.streamlit.io
- Sign in with GitHub
- Click "New app"
- Repository: Select `bps-database-explorer`
- Branch: `main`
- Main file path: `app.py`
- Click "Deploy!"

### 5. Share the Link

Once deployed (takes 2-3 minutes), you'll get a URL like:
`https://bps-database-explorer.streamlit.app`

**Share this link with your colleagues!** They can use it immediately.

---

## Troubleshooting Deployment

### Database File Too Large?

If your database is very large:
- Streamlit Cloud has a 1GB limit per app
- Consider compressing the database
- Or use a cloud database (PostgreSQL, etc.)

### Documents Folder Too Large?

If `all_bps_docs/` is very large:
- Use Git LFS for large files
- Or host documents on a file server and link to them
- Or use a cloud storage service (S3, Google Drive, etc.)

### App Won't Deploy?

- Check `requirements.txt` has all dependencies
- Make sure `app.py` is in the root directory
- Check the deployment logs in Streamlit Cloud dashboard
- Verify database file is included in the repository

---

## After Deployment

### Updating the App

When you make changes:
1. Update your code locally
2. Test it works
3. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Updated search functionality"
   git push
   ```
4. Streamlit Cloud automatically redeploys!

### Monitoring Usage

- Streamlit Cloud dashboard shows:
  - Number of users
  - App performance
  - Error logs

---

## Need Help?

- Streamlit Cloud docs: https://docs.streamlit.io/streamlit-cloud
- Streamlit Community: https://discuss.streamlit.io
