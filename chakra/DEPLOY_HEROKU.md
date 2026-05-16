# DEPLOY CHAKRA V2 BACKEND TO HEROKU

## What You're Deploying
- Flask Python backend (app.py)
- All dependencies (requirements.txt)
- Heroku configuration (Procfile, runtime.txt)

## Prerequisites
- GitHub account: ✅ lovidocmaster
- Heroku account: Create one (free tier available)

---

## STEP 1: CREATE HEROKU ACCOUNT (5 minutes)

1. Go to https://www.heroku.com
2. Click "Sign up" (top right)
3. Fill in:
   - Email: Use your email
   - Password: Create a strong password
   - Company: Your Name
   - Language: Python
4. Click "Create free account"
5. Verify your email (check inbox, click link)
6. You're done with Heroku signup

---

## STEP 2: PUSH DEPLOYMENT FILES TO GITHUB (5 minutes)

These files need to be in your GitHub repo so Heroku can find them:
- `Procfile` - tells Heroku how to run your app
- `requirements.txt` - Python packages to install
- `runtime.txt` - Python version
- `app.py` - Flask backend
- `.gitignore` - prevents .env from being uploaded

**Actions:**

On your PC, open terminal and navigate to your project:
```bash
cd C:\Users\cmalo\OneDrive\Desktop\project-chakra
# or wherever your GitHub repo is cloned locally
```

Copy these files into your local repo folder:
- `Procfile` (from the files I created)
- `requirements.txt`
- `runtime.txt`
- `app.py`
- `.gitignore`

Then commit and push:
```bash
git add Procfile requirements.txt runtime.txt app.py .gitignore
git commit -m "Add Heroku deployment files and Flask backend"
git push origin main
```

Wait 1-2 minutes, then verify on GitHub.com that the files are there.

---

## STEP 3: DEPLOY ON HEROKU (10 minutes)

1. Log in to Heroku: https://dashboard.heroku.com
2. Click "New" button (top right)
3. Select "Create new app"
4. Fill in:
   - **App name:** `chakra-trading-backend` (or `chakra-backend-[yourname]`)
   - **Region:** United States
5. Click "Create app"
6. Wait for the app to be created (1 minute)

You'll see a new page with your app dashboard.

---

## STEP 4: CONNECT GITHUB TO HEROKU (5 minutes)

On your Heroku app page:

1. Scroll down to **"Deployment method"** section
2. Click **"Connect to GitHub"**
3. Click "Sign in with GitHub" if prompted
4. GitHub will ask for permission → Click "Authorize heroku"
5. You're back on Heroku
6. In the **"Connect to GitHub"** section, search for: `project-chakra`
7. Click "Connect" next to your repo
8. Enable **"Automatic deploys"** (so it auto-updates when you push to main)
9. Click "Deploy Branch" to deploy the current code

**Wait 3-5 minutes** while Heroku builds your app.

You'll see logs scrolling. When done, it will say: "Your app was successfully deployed"

---

## STEP 5: GET YOUR PUBLIC URL (1 minute)

At the top of your Heroku app page, you'll see a button that says:
**"Open app"** or shows a URL like: `https://chakra-trading-backend.herokuapp.com`

**COPY THIS URL** - you'll need it in the next step.

---

## STEP 6: VERIFY IT'S WORKING (2 minutes)

Test your backend endpoint:

1. Copy your URL (e.g., `https://chakra-trading-backend.herokuapp.com`)
2. Open your browser and go to:
   ```
   https://chakra-trading-backend.herokuapp.com/api/system/status
   ```
3. You should see JSON response:
   ```json
   {
     "status": "operational",
     "timestamp": "2026-05-16T...",
     "backend_version": "v15_chakra",
     ...
   }
   ```

If you see this → ✅ **BACKEND IS LIVE**

If you see error → Check Heroku logs:
- Click "More" button (top right of Heroku dashboard)
- Select "View logs"
- Look for errors

---

## STEP 7: UPDATE DASHBOARD TO USE LIVE BACKEND (5 minutes)

Now your Next.js dashboard needs to talk to your Heroku backend.

1. Open: `C:\Users\cmalo\chakra-v2\lib\api\client.ts`
2. Find this line:
   ```typescript
   const API_BASE_URL = "http://localhost:5000";
   ```
3. Replace it with your Heroku URL:
   ```typescript
   const API_BASE_URL = "https://chakra-trading-backend.herokuapp.com";
   ```
4. Save the file
5. Commit and push:
   ```bash
   cd C:\Users\cmalo\chakra-v2
   git add lib/api/client.ts
   git commit -m "Update backend URL to production Heroku"
   git push origin main
   ```

Vercel will automatically redeploy your dashboard within 1-2 minutes.

---

## STEP 8: TEST END-TO-END (5 minutes)

1. Open your Vercel dashboard: https://project-name.vercel.app
2. Wait for Vercel to show "✓ Deployment successful"
3. Open dashboard in browser
4. Check browser console (F12 → Console tab) for any API errors
5. You should see:
   - Account metrics loading
   - System status showing "operational"
   - Agents list populated
   - System logs visible

---

## TROUBLESHOOTING

**Dashboard won't connect to backend?**
- Check the URL in `lib/api/client.ts` is correct
- Open your browser DevTools (F12)
- Go to "Network" tab
- Try to load a page
- Look for failed API calls
- If URL shows "localhost" → You didn't update the config

**Heroku shows "Application Error"?**
- Click "More" → "View logs" on Heroku dashboard
- Look for Python errors
- Check that all files (Procfile, app.py, requirements.txt) are in repo
- Make sure you pushed to GitHub

**Heroku says "no Procfile found"?**
- Ensure Procfile is in the root of your repo (not in a subfolder)
- Commit and push again
- Click "Redeploy branch" on Heroku

---

## WHAT'S NEXT

Once backend is live and dashboard is connected:

1. **Start the trading system**
   - Run `v15_chakra.py` on your local machine
   - It will connect to your Heroku backend
   - Dashboard will show live data

2. **Monitor paper trading**
   - Open your Vercel dashboard
   - Watch trades execute in real-time
   - Check OANDA account balance

3. **Enable features**
   - Telegram alerts will trigger
   - System logs will show agent decisions
   - Charts will update with new data

---

## IMPORTANT NOTES

- **Free tier limits:** Heroku free apps sleep after 30 minutes of no traffic
  - Your dashboard keeps it awake (no problem)
  - If you need 24/7, upgrade to Hobby tier ($7/month)

- **Environment variables:** Your .env file is NOT uploaded to Heroku
  - For now, the Flask app works without secrets
  - Once you need OANDA/Supabase on the backend, add them via Heroku settings

- **Auto-redeploy:** When you push code to main, Heroku auto-redeploys
  - Takes 2-3 minutes
  - You'll see it in deployment history

---

Done! Your backend is now live. 🚀
