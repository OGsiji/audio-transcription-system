# Quick Deploy Guide

Get your Audio Transcription Service deployed in production in 15 minutes!

## Step 1: Cleanup (2 minutes)

```bash
# Clean up unnecessary files
./cleanup.sh

# Verify structure
ls -la
```

## Step 2: Choose Deployment Method

### Option A: Railway (Easiest - Recommended!)

**Perfect for:** Quick deployment, free tier available

```bash
# 1. Create GitHub repository
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/audio-transcription.git
git push -u origin main

# 2. Go to railway.app
# 3. Click "New Project" → "Deploy from GitHub"
# 4. Select your repository
# 5. Add environment variable: GEMINI_KEY=your_api_key
# 6. Deploy!
```

✅ **Done! Your API will be live at:** `https://yourapp.railway.app`

---

### Option B: Docker (Local or VPS)

**Perfect for:** Running on your own server/VPS

```bash
# 1. Build and run
docker-compose up -d

# 2. Check status
docker-compose logs -f

# 3. Test API
curl http://localhost:8000/
```

✅ **Done! API running at:** `http://localhost:8000`

---

### Option C: Google Cloud Run (Serverless)

**Perfect for:** Pay-per-use, auto-scaling

```bash
# 1. Build and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT/audio-transcription

# 2. Deploy
gcloud run deploy audio-transcription \
  --image gcr.io/YOUR_PROJECT/audio-transcription \
  --platform managed \
  --set-env-vars GEMINI_KEY=your_api_key \
  --allow-unauthenticated

# 3. Get URL
gcloud run services describe audio-transcription --format='value(status.url)'
```

✅ **Done! API is live!**

---

## Step 3: Test Your Deployment

```bash
# Health check
curl https://your-api-url.com/

# Check usage stats
curl https://your-api-url.com/usage

# Start a transcription
curl -X POST https://your-api-url.com/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "google_drive_link": "https://drive.google.com/drive/folders/YOUR_FOLDER_ID"
  }'
```

---

## Step 4: Frontend Deployment

### Quick Frontend with Vercel (5 minutes)

```bash
# 1. Create frontend directory
mkdir frontend
cd frontend
npx create-next-app@latest . --typescript --tailwind --app

# 2. Install dependencies
npm install axios

# 3. Create API client (see frontend-template/ for full code)

# 4. Deploy to Vercel
npm install -g vercel
vercel

# 5. Add environment variable in Vercel dashboard:
# NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

✅ **Done! Frontend live at:** `https://yourapp.vercel.app`

---

## Usage Monitoring

### Check Usage Stats

```bash
# Get current usage
curl https://your-api-url.com/usage

# Response:
{
  "tier": "free",
  "requests_today": 10,
  "daily_limit": 1500,
  "daily_usage_pct": 0.67,
  "total_cost_usd": 0.0
}
```

### Set API Tier

```bash
# Set to paid tier
curl -X POST https://your-api-url.com/usage/tier \
  -H "Content-Type: application/json" \
  -d '{"tier": "paid"}'
```

### Check Burn Rate

```bash
# Get cost estimates
curl https://your-api-url.com/usage/burn-rate

# Response:
{
  "daily_burn_rate_usd": 0.50,
  "monthly_estimate_usd": 15.00
}
```

---

## API Documentation

Once deployed, visit:
- **Swagger UI:** `https://your-api-url.com/docs`
- **ReDoc:** `https://your-api-url.com/redoc`

---

## Cost Estimates

### Free Tier
- Gemini API: 1,500 requests/day (FREE)
- Railway: $5 credit/month (FREE for light use)
- **Total: $0/month** for testing

### Paid Tier (Small Business)
- Gemini API: ~$10-20/month (500 files/day)
- Hosting: $5-20/month
- **Total: $15-40/month**

### Paid Tier (Medium Business)
- Gemini API: ~$50-100/month (2000 files/day)
- Hosting: $20-50/month
- **Total: $70-150/month**

---

## Monitoring & Maintenance

### View Logs

```bash
# Docker
docker-compose logs -f api

# Railway
# Check logs in Railway dashboard

# Google Cloud Run
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

### Backup Data

```bash
# Create backup
tar -czf backup-$(date +%Y-%m-%d).tar.gz \
  transcriptions/ \
  usage_data/

# Restore backup
tar -xzf backup-2025-11-26.tar.gz
```

---

## Troubleshooting

### API Not Starting
```bash
# Check environment variables
echo $GEMINI_KEY

# Verify FFmpeg installed
docker exec audio-transcription-api ffmpeg -version
```

### High Costs
```bash
# Check usage
curl https://your-api-url.com/usage

# Reset if needed (WARNING: clears history!)
curl -X POST https://your-api-url.com/usage/reset
```

### Slow Transcriptions
- Increase worker count in gunicorn
- Use larger instance (t3.medium instead of t3.small)
- Enable file chunking for large files

---

## Next Steps

1. ✅ Deploy backend (you just did this!)
2. ✅ Deploy frontend (optional but recommended)
3. ✅ Set up monitoring (usage tracking built-in!)
4. ✅ Configure alerts for high usage
5. ✅ Add custom domain (optional)

---

## Support

- **API Docs:** `/docs`
- **Usage Stats:** `/usage`
- **Health Check:** `/`

**You're ready to go! 🚀**
