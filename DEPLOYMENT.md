# Deployment Guide

This guide covers deploying the Brain Health Analysis System to various platforms.

## Mobile-Ready Features

✅ **Responsive Design** - Works on all screen sizes (mobile, tablet, desktop)
✅ **Touch-Friendly** - Optimized tap targets for touch devices
✅ **Fast Loading** - Optimized assets and caching
✅ **PWA Support** - Can be installed as a mobile app
✅ **Camera Access** - Works with mobile cameras for prescription photos
✅ **Offline-Ready** - Core functionality works offline

## Prerequisites

- Python 3.11+
- MySQL database
- Git

## Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Update the values:
- `DB_HOST` - Your database host
- `DB_USER` - Database username
- `DB_PASSWORD` - Database password
- `FLASK_SECRET_KEY` - Generate a secure random key
- `FLASK_ENV` - Set to `production` for deployment

## Deployment Options

### 1. Heroku Deployment

```bash
# Install Heroku CLI
# Login to Heroku
heroku login

# Create new app
heroku create your-app-name

# Add MySQL addon
heroku addons:create jawsdb:kitefin

# Get database credentials
heroku config:get JAWSDB_URL

# Set environment variables
heroku config:set FLASK_SECRET_KEY=your_secret_key
heroku config:set FLASK_ENV=production
heroku config:set DB_HOST=your_db_host
heroku config:set DB_USER=your_db_user
heroku config:set DB_PASSWORD=your_db_password
heroku config:set DB_NAME=your_db_name

# Deploy
git push heroku main

# Open app
heroku open
```

### 2. Railway Deployment

1. Go to [Railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Add MySQL database service
5. Set environment variables in Railway dashboard
6. Deploy automatically

### 3. Render Deployment

1. Go to [Render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd Doctors_prescription_patient_1&& gunicorn app:app`
5. Add MySQL database
6. Set environment variables
7. Deploy

### 4. DigitalOcean App Platform

1. Go to DigitalOcean App Platform
2. Create new app from GitHub
3. Add MySQL database
4. Configure environment variables
5. Deploy

### 5. AWS Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.11 healthcare-app

# Create environment
eb create healthcare-env

# Set environment variables
eb setenv FLASK_SECRET_KEY=your_key FLASK_ENV=production

# Deploy
eb deploy

# Open app
eb open
```

### 6. Google Cloud Run

```bash
# Build container
gcloud builds submit --tag gcr.io/PROJECT_ID/healthcare-app

# Deploy
gcloud run deploy healthcare-app \
  --image gcr.io/PROJECT_ID/healthcare-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### 7. VPS (Ubuntu/Debian)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3-pip python3-venv nginx mysql-server -y

# Clone repository
git clone https://github.com/ShashiBhat25/brain_health_analysis.git
cd brain_health_analysis

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Setup MySQL
sudo mysql_secure_installation
sudo mysql -e "CREATE DATABASE healthcare_system;"

# Configure environment
cp .env.example .env
nano .env  # Edit with your values

# Setup Gunicorn service
sudo nano /etc/systemd/system/healthcare.service
```

Add to service file:
```ini
[Unit]
Description=Healthcare AI Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/brain_health_analysis/Doctors_prescription_patient_1
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 app:app

[Install]
WantedBy=multi-user.target
```

```bash
# Start service
sudo systemctl start healthcare
sudo systemctl enable healthcare

# Configure Nginx
sudo nano /etc/nginx/sites-available/healthcare
```

Add to Nginx config:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /path/to/brain_health_analysis/Doctors_prescription_patient_1/static;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/healthcare /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Setup SSL (optional but recommended)
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

## Database Setup

After deployment, the database tables will be created automatically on first run.

To manually setup:
```bash
python Doctors_prescription_patient_1/app.py
```

## Post-Deployment Checklist

- [ ] Test on mobile devices (iOS and Android)
- [ ] Test on different browsers (Chrome, Safari, Firefox)
- [ ] Verify database connection
- [ ] Test file uploads
- [ ] Test camera functionality on mobile
- [ ] Check EEG analysis works
- [ ] Verify all user roles (Patient, Doctor, Caretaker)
- [ ] Test prescription creation and viewing
- [ ] Setup SSL certificate (HTTPS)
- [ ] Configure domain name
- [ ] Setup monitoring and logging
- [ ] Configure backups
- [ ] Test performance under load

## Mobile Testing

Test on these devices/browsers:
- iPhone (Safari)
- Android (Chrome)
- iPad (Safari)
- Android Tablet (Chrome)
- Desktop browsers (Chrome, Firefox, Safari, Edge)

## Performance Optimization

1. **Enable Gzip compression** in your web server
2. **Use CDN** for static assets
3. **Enable caching** for static files
4. **Optimize images** before upload
5. **Use connection pooling** for database
6. **Monitor with tools** like New Relic or DataDog

## Security Checklist

- [ ] Change default secret key
- [ ] Use strong database passwords
- [ ] Enable HTTPS/SSL
- [ ] Set secure session cookies
- [ ] Implement rate limiting
- [ ] Regular security updates
- [ ] Backup database regularly
- [ ] Monitor for suspicious activity

## Troubleshooting

### Database Connection Issues
```bash
# Check database credentials
# Verify database is running
# Check firewall rules
```

### File Upload Issues
```bash
# Check folder permissions
chmod 755 Doctors_prescription_patient_1/static/uploads/prescriptions
```

### Mobile Camera Not Working
- Ensure HTTPS is enabled (required for camera access)
- Check browser permissions

## Support

For issues or questions:
- GitHub Issues: https://github.com/ShashiBhat25/brain_health_analysis/issues
- Email: your-email@example.com

## License

This project is for educational and research purposes.
