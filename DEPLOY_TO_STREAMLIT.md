# Deploy to Streamlit Cloud - Step by Step

Your code is now on GitHub! 🎉 Now let's deploy it so your colleagues can use it.

## Step 1: Go to Streamlit Cloud

Open your browser and go to:
**https://share.streamlit.io**

## Step 2: Sign In

- Click "Sign in" 
- Choose "Continue with GitHub"
- Authorize Streamlit Cloud to access your GitHub account

## Step 3: Create New App

- Click the **"New app"** button (usually in the top right or center)
- You'll see a form to configure your app

## Step 4: Configure Your App

Fill in the form:

- **Repository**: Select `rswaty/bps_database_explorer` from the dropdown
- **Branch**: Select `main`
- **Main file path**: Type `app.py`
- **App URL** (optional): You can customize this or leave default
  - Default will be: `bps-database-explorer` 
  - Full URL will be: `https://bps-database-explorer.streamlit.app`

## Step 5: Deploy!

- Click the **"Deploy!"** button
- Wait 2-3 minutes while Streamlit Cloud:
  - Clones your repository
  - Installs dependencies from `requirements.txt`
  - Starts your app

## Step 6: Get Your Shareable Link

Once deployment completes (you'll see "Your app is live!"), you'll get a URL like:
```
https://bps-database-explorer.streamlit.app
```

**This is the link to share with your colleagues!** 🎉

---

## What Happens Next?

- ✅ Your app is now accessible 24/7
- ✅ Anyone with the link can use it (no installation needed)
- ✅ Updates automatically when you push changes to GitHub

## Updating Your App

When you make changes:
1. Make your changes locally
2. Run: `git add . && git commit -m "Your update" && git push`
3. Streamlit Cloud automatically redeploys (takes 1-2 minutes)

---

## Troubleshooting

### If deployment fails:
- Check that `requirements.txt` has all dependencies
- Make sure `app.py` is in the root directory
- Check the deployment logs in Streamlit Cloud dashboard

### If the app doesn't work:
- Check the logs in Streamlit Cloud
- Make sure `bps_database.db` was pushed to GitHub
- Verify `all_bps_docs/` folder is in the repository

---

## Next Steps After Deployment

1. ✅ Test the app yourself
2. ✅ Share the link with colleagues
3. ✅ Send them the `USER_GUIDE.md` for instructions
