Wake-up Call Service

A comprehensive Django application that allows users to schedule personalized wake-up calls with weather announcements using Twilio integration.

---

1. Key Features

- Multi-user Support: Each user can schedule multiple wake-up calls
- Phone Verification: Users must verify their phone numbers before scheduling calls
- Weather Integration: Calls include current weather based on user's zip code
- Multiple Contact Methods: Support for both phone calls and SMS messages
- Interactive Voice: Voice calls support DTMF input for call management
- REST API: External API endpoints for integration
- Admin Dashboard: User and admin roles with different permissions
- AWS Integration: CloudWatch logging and Fargate deployment ready
- Queue-based Processing: Async task processing with Celery and Redis

---

2. Technology Stack

Backend Services:
- Django 4.2 - Web framework
- Django REST Framework - API development
- Celery - Task queue and scheduling
- PostgreSQL - Database
- Redis - Cache and message broker

External Integrations:
- Twilio API - Phone calls and SMS
- OpenWeatherMap API - Weather data
- AWS CloudWatch - Logging and monitoring

---

3. Quick Start Guide

3.1 Prerequisites

Before starting, ensure you have:
- Python 3.11+
- PostgreSQL database
- Redis server
- (Optional) Twilio account for real calls
- (Optional) OpenWeatherMap API key for weather

3.2 Option 1: Automated Setup (Recommended)

Use our setup script for the easiest installation:

```bash
# Make setup script executable and run
chmod +x setup.sh
./setup.sh
```

This script will:
- Install PostgreSQL and Redis
- Create virtual environment
- Install Python dependencies
- Setup database and migrations
- Create admin user and demo data

3.3 Option 2: Manual Setup

Step 1: Clone and Setup Environment
```bash
git clone <repository-url>
cd wakeupcall

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Step 2: Configure Environment
```bash
cp env.example .env
# Edit .env with your configuration values
```

Step 3: Database Setup
```bash
# Install PostgreSQL and Redis (Ubuntu/Debian)
sudo apt install postgresql postgresql-contrib redis-server

# Start services
sudo systemctl start postgresql redis-server

# Create database and run migrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_data --count 30
```

Step 4: Start Application
```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker (for background tasks)
celery -A wakeupcall worker -l info

# Terminal 3: Celery beat scheduler (for scheduled calls)
celery -A wakeupcall beat -l info
```

3.4 Option 3: Docker Deployment

For containerized deployment:

```bash
docker-compose up --build
```

This starts all services:
- Django web application
- PostgreSQL database
- Redis cache
- Celery worker
- Celery beat scheduler

---

4. API Endpoints

4.1 Authentication Required

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/users/me/` | GET | Get current user profile |
| `/api/users/verify_phone/` | POST | Send phone verification code |
| `/api/users/verify_code/` | POST | Verify phone with code |
| `/api/wakeup-calls/` | GET/POST | List/Create wake-up calls |
| `/api/wakeup-calls/{id}/cancel/` | POST | Cancel wake-up call |
| `/api/wakeup-calls/{id}/reschedule/` | POST | Reschedule wake-up call |
| `/api/wakeup-calls/{id}/change_method/` | POST | Change contact method |

4.2 Webhook Endpoints (Public)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/calls/inbound-call/` | POST | Handle inbound Twilio calls |
| `/calls/sms-webhook/` | POST | Handle Twilio SMS replies |
| `/calls/call-status/` | POST | Handle Twilio call status updates |

---

5. Configuration

5.1 Required Environment Variables

Create a `.env` file with these settings:

```bash
# Django Settings
SECRET_KEY=your-secure-secret-key-here
DEBUG=True  # Set to False in production
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=wakeupcall
DB_USER=postgres
DB_PASSWORD=postgres_password
DB_HOST=localhost
DB_PORT=5432

# Twilio (Optional - for real calls)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_VERIFY_SERVICE_SID=your-verify-service-sid

# Weather API (Optional - for weather data)
WEATHER_API_KEY=1131d127f057fb12a2b44e49ec4af964

# Redis
REDIS_URL=redis://localhost:6379/0

# AWS (Optional - for CloudWatch logging)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
AWS_LOG_GROUP=wakeupcall-logs

# Base URL for webhooks
BASE_URL=http://localhost:8000
```

5.2 Service Configuration Notes

Development Mode: The application works without Twilio or Weather API credentials:
- Calls are logged but not sent (demo mode)
- Weather shows placeholder data
- All other features work normally

Production Mode: Configure real credentials for full functionality.

---

6. Usage Guide

6.1 User Workflow

1. Registration: Create account through web interface
2. Phone Verification: Verify phone number via SMS code
3. Profile Setup: Set zip code and preferred contact method
4. Schedule Calls: Create wake-up calls via web interface or API
5. Manage Calls: Cancel, reschedule, or change contact method

6.2 Admin Features

- User Management: Create and manage user accounts
- Call Monitoring: View all wake-up calls and system logs
- System Control: Access REST API endpoints and monitor status
- Analytics: Track call success rates and usage statistics

6.3 Demo Mode

The application includes demo data for testing:
- Admin Account: `admin` / `admin123`
- Demo Users: `demo_user_1` through `demo_user_10` / `demo123`
- Sample Calls: 30 pre-scheduled demo wake-up calls

Demo calls are marked as `is_demo=True` and won't make actual calls/texts but will log activity for testing.

---

7. Security Features

- Phone Verification: Required before scheduling calls
- CSRF Protection: Enabled on all forms
- Secure Storage: AWS Systems Manager for sensitive data
- Environment-based Config: Secure configuration management
- Non-root Containers: Secure Docker deployment

---

8. Monitoring & Logging

- Application Logs: Stream to AWS CloudWatch
- Call Tracking: Success/failure monitoring
- Performance Metrics: Celery task monitoring
- Health Checks: Container health monitoring

---

9. Testing

9.1 Access Points

- Main App: http://localhost:8000
- Admin Panel: http://localhost:8000/admin
- API Browser: http://localhost:8000/api/

9.2 Test Credentials

Admin Access:
- Username: `admin`
- Password: `admin123`

Demo Users:
- Usernames: `demo_user_1` through `demo_user_10`
- Password: `demo123` (all demo users)

9.3 Testing Scenarios

1. Basic User Flow: Login → Dashboard → Schedule Calls
2. Admin Workflow: Admin Panel → User Management → Call Monitoring
3. API Testing: Use API browser to test endpoints
4. Phone Verification: Test verification flow (UI only without Twilio)

---

10. AWS Fargate Deployment

10.1 Deployment Steps

1. Build and Push Image:
   ```bash
   cd aws-deployment
   ./deploy.sh
   ```

2. Configure AWS Resources:
   - ECS Cluster setup
   - RDS PostgreSQL instance
   - ElastiCache Redis cluster
   - Application Load Balancer
   - CloudWatch Log Groups

3. Secure Configuration:
   ```bash
   aws ssm put-parameter --name "/wakeupcall/twilio/account-sid" --value "your-sid" --type "SecureString"
   aws ssm put-parameter --name "/wakeupcall/twilio/auth-token" --value "your-token" --type "SecureString"
   ```

---

11. Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Test your changes thoroughly
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Submit a pull request

---

12. License

This project is created for demonstration and educational purposes.

---

13. Support

Need help? Here are the most common issues:

1. Database Connection Issues: Ensure PostgreSQL is running and credentials are correct
2. Redis Connection Issues: Check if Redis server is started
3. Twilio Errors: Verify API credentials and account status
4. Weather API Issues: Check API key validity and rate limits

For additional support, please check the troubleshooting section or create an issue in the repository.