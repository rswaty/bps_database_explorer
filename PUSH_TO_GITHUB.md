# Push to GitHub - Step by Step

Once you have created the GitHub repository `bps_database_explorer`, follow these steps:

## Step 1: Initialize Git (if not already done)

```bash
cd /home/rswaty/Documents/bps_database_play
git init
```

## Step 2: Add All Files

```bash
git add .
```

This will add:
- ✅ `app.py` - Main application
- ✅ `bps_database.db` - Database file
- ✅ `all_bps_docs/` - Document folder
- ✅ `requirements.txt` - Dependencies
- ✅ All documentation files
- ✅ Configuration files

## Step 3: Make Initial Commit

```bash
git commit -m "Initial commit: BPS Database Explorer"
```

## Step 4: Add Remote Repository

Replace `YOUR_USERNAME` with your GitHub username:

```bash
git remote add origin https://github.com/YOUR_USERNAME/bps_database_explorer.git
```

Or if you're using SSH:
```bash
git remote add origin git@github.com:YOUR_USERNAME/bps_database_explorer.git
```

## Step 5: Push to GitHub

```bash
git branch -M main
git push -u origin main
```

You may be prompted for your GitHub username and password (or token).

## Step 6: Verify

Go to your GitHub repository page and verify all files are there:
- `app.py`
- `bps_database.db`
- `all_bps_docs/` folder
- `requirements.txt`
- Other documentation files

---

## Troubleshooting

### If you get "repository not found":
- Make sure you created the repository on GitHub first
- Check the repository name matches: `bps_database_explorer`
- Verify the URL is correct

### If you get authentication errors:
- GitHub no longer accepts passwords - you need a Personal Access Token
- Go to: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- Generate a new token with `repo` permissions
- Use the token as your password when pushing

### If files are too large:
- The database and documents should be fine
- If you get errors about large files, we can use Git LFS

---

## Next Steps After Pushing

Once your code is on GitHub, you can:
1. Deploy to Streamlit Cloud (see `DEPLOYMENT_CHECKLIST.md`)
2. Share the repository link with colleagues
3. Set up automatic deployments
