# 🚀 Quick Start: Google Cloud Deployment

**Deploy your Food Price Anomaly Detection app in 5 minutes**

---

## ✅ Prerequisites Checklist

- [ ] GitHub account (you have this ✓)
- [ ] Google account
- [ ] Internet connection

That's it! No credit card needed initially.

---

## 🎯 5-Minute Deployment Steps

### Step 1️⃣: Create Google Cloud Account (2 min)

1. Go to https://cloud.google.com
2. Click **"Get started for free"**
3. Sign in with your Google account
4. Follow the registration steps
5. ✅ You get $300 free credits (optional)

**Note:** You DON'T need to add a credit card to try the free tier!

---

### Step 2️⃣: Install Google Cloud SDK (2 min)

**Windows:**
- Download: https://dl.google.com/dl/cloud/sdk/windows/google-cloud-sdk-installer.exe
- Run the installer
- Select "Run gcloud init"

**macOS:**
```bash
brew install --cask google-cloud-sdk
gcloud init
```

**Linux:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

---

### Step 3️⃣: Deploy with One Command (1 min)

#### **Windows PowerShell:**

```powershell
cd d:\Dessertation
.\deploy-gcloud.ps1 -ProjectId "my-project-id"
```

#### **macOS/Linux:**

```bash
cd ~/d/Dessertation
chmod +x deploy-gcloud.sh
./deploy-gcloud.sh my-project-id
```

**Replace `my-project-id` with your actual Google Cloud Project ID**
(You can see it in Google Cloud Console)

---

### Step 4️⃣: Wait for Deployment ⏳

The script will:
1. ✅ Check your gcloud setup
2. ✅ Enable required APIs
3. ✅ Build Docker image
4. ✅ Push to Container Registry
5. ✅ Deploy to Cloud Run
6. ✅ Get your live URL

---

### Step 5️⃣: Access Your App 🎉

**You'll get a URL like:**
```
https://food-price-anomaly-xxxxx-uc.a.run.app
```

**Open it in your browser to see your app live!**

---

## 🎮 Test the Deployment

```bash
# View logs in real-time
gcloud run services logs read food-price-anomaly --region us-central1 --limit 50 --follow

# Check service status
gcloud run services describe food-price-anomaly --region us-central1

# Get the live URL
gcloud run services describe food-price-anomaly \
  --region us-central1 \
  --format 'value(status.url)'
```

---

## 💰 Free Tier Details

✅ **What's Included (No Cost):**
- 2 million requests/month
- 360,000 GB-seconds of compute
- 180,000 vCPU-seconds
- 1 GB egress/month

⚠️ **Beyond Free Tier:**
- Still very cheap: ~$0.01 per 1000 requests
- Auto-scales with traffic

---

## 🔗 Next Steps

1. **Copy the deployment URL** from the output
2. **Share it** - Your app is now public!
3. **Test it** - Upload some data and see anomalies detected
4. **Monitor** - Check Google Cloud Console for usage

---

## 🆘 Troubleshooting

### Error: "Project not found"
```
Solution: Make sure PROJECT_ID matches your Google Cloud Project ID
View it in: https://console.cloud.google.com/projectselector
```

### Error: "Permission denied"
```
Solution: Run: gcloud auth login
Then accept the permission prompt
```

### Error: "API not enabled"
```
Solution: The script handles this automatically
If it fails, run: gcloud services enable run.googleapis.com
```

### Deployment stuck on "Building..."
```
This is normal! Building takes 2-3 minutes
Check progress: https://console.cloud.google.com/cloud-build/builds
```

---

## 📚 Full Documentation

For advanced configuration, scaling, and troubleshooting:
👉 **Read:** [GOOGLE_CLOUD_DEPLOYMENT.md](GOOGLE_CLOUD_DEPLOYMENT.md)

---

## ✨ You're Done!

Your app is now:
- ✅ Deployed globally
- ✅ Auto-scaling
- ✅ HTTPS secured
- ✅ Monitored 24/7
- ✅ Under $20/month (if you exceed free tier)

**Congratulations! 🎉**

---

**Questions?** Check the [full Google Cloud guide](GOOGLE_CLOUD_DEPLOYMENT.md) or [GitHub Issues](https://github.com/lucasWAFULA/Dissertation/issues)
