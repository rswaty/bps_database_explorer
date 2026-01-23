# Sharing Guide - BPS Database Explorer

## Option 1: Streamlit Cloud (Recommended - Easiest for Non-Technical Users)

Streamlit Cloud is free and makes your app accessible via a web link that anyone can use.

### Steps to Deploy:

1. **Create a GitHub account** (if you don't have one)
   - Go to https://github.com
   - Sign up for a free account

2. **Create a new GitHub repository**
   - Click the "+" icon → "New repository"
   - Name it something like `bps-database-explorer`
   - Make it **Public** (required for free Streamlit Cloud)
   - Don't initialize with README (we already have files)

3. **Push your code to GitHub** (one-time setup):
   ```bash
   cd /home/rswaty/Documents/bps_database_play
   git init
   git add .
   git commit -m "Initial commit - BPS Database Explorer"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/bps-database-explorer.git
   git push -u origin main
   ```
   (Replace YOUR_USERNAME with your GitHub username)

4. **Deploy to Streamlit Cloud**:
   - Go to https://share.streamlit.io
   - Sign in with your GitHub account
   - Click "New app"
   - Select your repository: `bps-database-explorer`
   - Main file path: `app.py`
   - Click "Deploy!"
   - Wait 2-3 minutes for deployment

5. **Share the link**:
   - Once deployed, you'll get a URL like: `https://bps-database-explorer.streamlit.app`
   - Share this link with your colleagues - they can just click and use it!

### Advantages:
- ✅ Free
- ✅ No installation needed for users
- ✅ Works on any device with a web browser
- ✅ Automatically updates when you push changes
- ✅ No server management

---

## Option 2: Local Network Sharing (For Same Office/Network)

If everyone is on the same network, you can run it locally and share your computer's IP address.

### Steps:

1. **Find your IP address**:
   ```bash
   hostname -I
   ```
   (You'll get something like `192.168.1.100`)

2. **Run the app**:
   ```bash
   cd /home/rswaty/Documents/bps_database_play
   source venv/bin/activate
   streamlit run app.py --server.address 0.0.0.0
   ```

3. **Share the link**:
   - Tell colleagues to go to: `http://YOUR_IP:8501`
   - Example: `http://192.168.1.100:8501`

### Important Notes:
- ⚠️ Your computer must stay on and connected to the network
- ⚠️ Firewall may block connections (you may need to allow port 8501)
- ⚠️ Only works on the same network

---

## Option 3: Package for Easy Installation

Create a simple installer package for colleagues.

### Create a setup script:

1. **Create `setup_and_run.sh`** (already created below)
2. **Share the entire folder** (via USB, shared drive, etc.)
3. **Colleagues run**: `./setup_and_run.sh`

---

## Option 4: Docker Container (For Technical Users)

If your colleagues are comfortable with Docker, this is a good option.

---

## Quick Start for Colleagues (If Using Streamlit Cloud)

Once you share the Streamlit Cloud link, your colleagues just need to:

1. **Click the link** (works in any web browser)
2. **Use the search box** to find models
3. **Click "Download Document"** to get the Word files

No installation, no setup, no technical knowledge needed!

---

## Troubleshooting

### If Streamlit Cloud deployment fails:
- Make sure `requirements.txt` includes all dependencies
- Check that `app.py` is in the root directory
- Ensure the database file is included (or use a cloud database)

### If local sharing doesn't work:
- Check firewall settings
- Make sure you're on the same network
- Try `streamlit run app.py --server.address 0.0.0.0 --server.port 8501`
