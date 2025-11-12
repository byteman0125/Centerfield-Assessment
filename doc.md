## Wake-Up Call Platform Deep Dive

### Executive Summary
The Wake-Up Call Platform is a Django-based concierge that orchestrates automated calls or texts enriched with live weather context. Users schedule reminders through the web application, REST APIs, or optional IVR flows, while administrators monitor delivery health and compliance from dedicated dashboards. The blend of verified contact information, asynchronous execution, and channel flexibility makes the platform dependable for time-critical wake-ups.

| Dimension | Description |
|-----------|-------------|
| **Purpose** | Deliver reliable, personalized wake-up reminders that combine telephony and real-time weather data. |
| **Primary Users** | Individuals or teams who rely on scheduled alerts, along with administrators responsible for oversight and compliance. |
| **Value Proposition** | Couples strong operational guarantees (verification, retry-ready architecture) with rich context (weather, interaction controls) to build trust in the service. |

**Functional Capabilities**
| Capability | Summary |
|------------|---------|
| Multi-channel scheduling | Browser UI, REST endpoints, and inbound IVR for creating and managing reminders. |
| Verified contact enforcement | Twilio Verify workflow prevents calls/SMS until ownership is confirmed. |
| Weather-infused messaging | Voice and SMS notifications include current conditions based on the subscriber’s ZIP code. |
| Interactive controls | DTMF menu and SMS keywords allow recipients to cancel, reschedule, or change contact method in real time. |
| Role-aware dashboards | Distinct experiences for end users (personal schedules) and administrators (fleet-wide telemetry). |

**Nonfunctional Commitments**
| Commitment | Implementation |
|------------|----------------|
| Deployability | Containerized workload targeting AWS Fargate with accompanying infrastructure scripts. |
| Performance & resilience | Celery/Redis backbone ensures asynchronous execution even under load; demo mode isolates non-production traffic. |
| Observability | Structured logging streamed to CloudWatch, complemented by persistent `CallLog` and `InboundCall` records for auditing. |
| Security | Role-based access controls, admin-route middleware, secrets stored in AWS SSM, and verified phone numbers precondition scheduling. |

---

### Table of Contents
1. [Front-End Architecture & UI Walkthrough](#0-front-end-architecture--ui-walkthrough)
2. [Business Context & Objectives](#1-business-context--objectives)
3. [High-Level Architecture](#2-high-level-architecture)
4. [Domain Model](#3-domain-model)
5. [End-to-End Workflow](#4-end-to-end-workflow)
6. [Asynchronous Orchestration](#5-asynchronous-orchestration)
7. [Twilio & Weather Integrations](#6-twilio--weather-integrations)
8. [REST API Surface](#7-rest-api-surface-appsapiurlspy)
9. [Admin & UI Experience](#8-admin--ui-experience)
10. [Deployment & Operations](#9-deployment--operations)
11. [Demo & Testing Tooling](#10-demo--testing-tooling)
12. [Risks, Enhancements & Talking Points](#11-risks-enhancements--talking-points)
13. [Interview Game Plan](#12-interview-game-plan)
14. [Reference Commands](#13-reference-commands)

---

### 0. Front-End Architecture & UI Walkthrough

#### 0.1 Template & Asset Topology
- `templates/base.html`: shared Bootstrap shell (navigation, flash messages, script blocks) that loads `static/css/style.css` and `static/js/main.js`.
- `templates/core/home.html`: landing + contextual dashboard (hero CTA, scheduled-call cards, account status panel, marketing tiles for guests).
- `templates/core/dashboard.html`: scheduling cockpit with phone-verification modal, wake-up creation form, recent calls sidebar, and quick tips card.
- `templates/registration/login.html`: themed login page extending the base layout for consistent styling.
- `templates/admin/*.html`: rebranded Django admin entry points (logo, dashboard widgets).
- Static assets:
  - `static/css/style.css`: gradients, typography tweaks, card shadows, badge palettes.
  - `static/js/main.js`: reserved for global behaviors; page-specific scripts embedded within templates (e.g., dashboard modal logic).

#### 0.2 Text-Based UI Maps

**Home (Authenticated)**
```
+--------------------------------------------------------------------------------+
| Hero Banner                                                                    |
|  "Wake-up Call Service"    [Schedule New Call] [View My Calls]                 |
+--------------------------------------------------------------------------------+
| Left Column: Your Scheduled Calls                                              |
|  ├─ Card: [📞] Jul 20 06:30 AM • Phone +1 555-0000 • ZIP 10001 • Method CALL    |
|  ├─ Card: [💬] Jul 21 07:00 AM • Phone +1 555-1111 • ZIP 30301 • Method SMS     |
|  └─ ... (ordered soonest first)                                                |
| Right Column: Your Account Status                                              |
|  ├─ Total Scheduled Calls  [ 3 ]                                               |
|  ├─ Phone Verified        [✓ Verified] / [⚠ Not Verified]                      |
|  ├─ Weather Location      [10001 or "Not set"]                                 |
|  └─ Alert prompting verification when required                                 |
+--------------------------------------------------------------------------------+
```

**Home (Guest)**
```
+---------------------- HERO CTA -----------------------+
| Headline + tagline                                    |
| [Get Started Today] (login link)                      |
+------------------------------------------------------+
| "How It Works" feature cards:                         |
| 1) Phone Calls (interactive voice menus)              |
| 2) Text Messages (weather snapshot)                   |
| 3) Weather Updates (OpenWeatherMap feed)              |
+------------------------------------------------------+
| CTA Panel: [Login to Start] + demo credentials hint   |
+------------------------------------------------------+
```

**Dashboard**
```
+--------------------------------------------------------------------------------+
| Header: "Schedule Wake-up Calls"                             [Back to Home]   |
+--------------------------------------------------------------------------------+
| Verification Alert (visible if phone not verified)  → [Verify Phone Now]      |
+--------------------------------------------------------------------------------+
| Left Panel (8 cols)                                                            |
|  Card "Schedule New Wake-up Call"                                              |
|   ├─ DateTime picker (datetime-local)                                          |
|   ├─ Contact method select (📞 Call / 💬 SMS)                                   |
|   ├─ ZIP code input (prefilled via profile)                                    |
|   └─ [Schedule Wake-up Call] (POST /api/wakeup-calls/)                         |
|  Form disabled until verification completes; submit shows loading indicator.   |
|                                                                                |
| Right Panel (4 cols)                                                           |
|  Card "Recent Calls" → list with status badges                                 |
|  Card "Quick Tips" → bullet list of platform hints                             |
+--------------------------------------------------------------------------------+
| Modal "Verify Your Phone Number":                                              |
|  Step 1 → Enter phone (POST /api/users/verify_phone/)                          |
|  Step 2 → Enter 6-digit code (POST /api/users/verify_code/)                    |
|  Buttons show loading states; success triggers toast + reload.                 |
+--------------------------------------------------------------------------------+
```

#### 0.3 Interaction Mechanics
- Navbar adapts to role using `is_admin_user`; shows Admin Dashboard link only for admin profiles.
- Inline script in `dashboard.html` binds:
  - `handleWakeupSubmit` → validates fields, POSTs JSON to `/api/wakeup-calls/`, surfaces Bootstrap alert via `showNotification`, reloads on success.
  - `sendVerificationCode` / `verifyCode` / `resendCode` → fetch Twilio verification endpoints, toggle modal steps.
  - MutationObserver auto-focuses verification code input when second step becomes visible.
- Notification helper injects dismissible Bootstrap alerts at top of `.container`, auto-closes after five seconds.
- Templates use Django filters (`date`, `default`, `length`) to render friendly strings and fallbacks.

#### 0.4 Front-End Interaction Diagram
```
[Browser UI]
  ├─ GET /            → renders base.html + core/home.html
  ├─ GET /dashboard/  → renders base.html + core/dashboard.html (+ inline JS)
  ├─ POST /api/users/verify_phone/  (JSON)  ← sendVerificationCode()
  ├─ POST /api/users/verify_code/   (JSON)  ← verifyCode()
  └─ POST /api/wakeup-calls/        (JSON)  ← handleWakeupSubmit()

[Static Resources]
  ├─ /static/css/style.css
  └─ /static/js/main.js (extension point)

[Server Responses]
  ├─ HTML templates (session-auth protected)
  ├─ JSON payloads (success/error) for fetch requests
  └─ CSRF tokens embedded via Django template tags
```

> **Why it matters:** mastering the UI surface lets you narrate how verification, scheduling, and feedback loops feel to an end-user before diving into backend mechanics. The ASCII layouts double as interview-ready storyboards.

#### 0.5 Business Workflow & Integration Matrix

| Phase | Trigger / Actor | Business Logic & Responsibilities | Data Stores / Models | Async & External Comms |
|-------|-----------------|------------------------------------|----------------------|------------------------|
| **S1 Registration & Login** | User hits `/`, authenticates via `registration/login.html`. | Django auth checks credentials; `CustomLoginView` directs admins to `/admin/`, users to `/`. | `User`, `UserProfile` (ensured via seed or on-demand creation). | N/A |
| **S2 Phone Verification (Send)** | Dashboard modal `Verify Phone Now` → JS POST `/api/users/verify_phone/`. | `UserViewSet.verify_phone` validates number, stores on user, triggers `TwilioService.send_verification_code`. | `User.phone_number`, `PhoneVerification` (latest pending). | Twilio Verify API (SMS); logs via CloudWatch handler. |
| **S3 Phone Verification (Confirm)** | User submits code → POST `/api/users/verify_code/`. | `TwilioService.verify_code` checks OTP; on success, mark `User.is_phone_verified=True`. | `User.is_phone_verified`, optionally update `PhoneVerification.is_verified`. | Twilio Verify API approval response. |
| **S4 Schedule Wake-Up** | Dashboard form POST `/api/wakeup-calls/`. | `WakeUpCallSerializer` ensures future datetime + verified phone, auto-pulls `user.phone_number` if field omitted. | `WakeUpCall` (status `scheduled`, `is_demo` default False). | N/A |
| **S5 Register Task** | Django `post_save` signal for new `WakeUpCall`. | `schedule_wakeup_call` computes cron, creates/updates `CrontabSchedule` + one-off `PeriodicTask` referencing `execute_wakeup_call`. | `django_celery_beat_periodictask`, `django_celery_beat_crontabschedule`. | Celery Beat polls DB; no external service. |
| **S6 Queue Execution** | Celery Beat at runtime or sweep `schedule_recurring_wakeup_calls`. | Enqueue `execute_wakeup_call.delay`, logging number of calls scheduled. | Celery queue state (Redis). | Redis broker transmits task to workers. |
| **S7A Execute (Voice)** | Worker runs `execute_wakeup_call`, `contact_method=='call'`. | Fetch weather, create `CallLog(status='initiated')`, call Twilio, update log + `WakeUpCall.status` (`completed`/`failed`), set `last_executed`. | `CallLog`, `WakeUpCall`. | OpenWeatherMap REST; Twilio Voice REST. |
| **S7B Execute (SMS)** | Worker path when `contact_method=='sms'`. | Build message via `generate_sms_message`, send Twilio SMS, update log + call status. | Same as voice path. | Twilio Messaging REST. |
| **S8 TwiML Delivery** | Twilio requests `/calls/voice-response/<uuid>/`. | `VoiceResponseView` reloads wake-up, optional fresh weather, emits TwiML greeting + menu. | Read-only on `WakeUpCall`. | Twilio consumes TwiML (no DB writes). |
| **S9 User Interaction** | - Voice digits POST `/calls/handle-voice-input/`.<br>- SMS replies POST `/calls/sms-webhook/`. | Voice: adjust `WakeUpCall` status or contact method.<br>SMS: bulk cancel or toggle `UserProfile.preferred_contact_method`, respond via Twilio. | `WakeUpCall`, `UserProfile`. | Twilio webhooks (DTMF, inbound SMS). |
| **S10 Status Update** | Twilio POST `/calls/call-status/`. | Update `CallLog.status`, `CallLog.duration`; sync `InboundCall` status/duration when applicable. | `CallLog`, `InboundCall`. | Twilio status webhook. |
| **S11 Inbound Call (Optional)** | Caller dials Twilio number → `/calls/inbound-call/`. | Record `InboundCall`, associate user, read schedule, provide IVR options. | `InboundCall`, `WakeUpCall`. | Twilio Voice inbound webhook. |
| **S12 Admin Oversight** | Admin visits `/admin/`. | Middleware enforces role; admin site shows enhanced dashboards, aggregated stats via context processor. | `User`, `UserProfile`, `WakeUpCall`, `CallLog`, `InboundCall`, beat tables. | CloudWatch dashboards/logs for ops. |
| **S13 Demo Seeding** | `python manage.py seed_data`. | Creates admin/demo users, seeds wake-up calls flagged `is_demo=True` to avoid real Twilio charges while logging. | `User`, `UserProfile`, `WakeUpCall (demo)`. | Twilio omitted (demo short-circuit); log entries still generated. |

**Communication Topology**
- **Browser ↔ Django**: HTML templates + JSON API responses secured with session auth and CSRF tokens.
- **Django ↔ Celery**: Signals populate `django_celery_beat`; tasks queued via Redis, consumed by workers.
- **Django ↔ External APIs**: Twilio Verify/Voice/Messaging, OpenWeatherMap for weather, AWS CloudWatch for logging, AWS SSM Parameter Store for secrets.
- **Twilio ↔ Django**: Webhooks for voice response, DTMF menu, SMS inbound, and call status updates.
- **Observability**: Python logging routes to console (local) and CloudWatch (production); `CallLog`/`InboundCall` tables provide durable audit trails.

### 1. Business Context & Objectives
- **Primary value proposition**: dependable wake-up automation that personalizes reminders with live weather, reducing missed commitments for users in different time zones or travel windows.
- **Interaction matrix**:
  - Web UI for everyday users who want visual scheduling and dashboards.
  - REST API for mobile apps, integrations (e.g., fitness trackers) or enterprise partners.
  - Optional IVR so users can manage schedules from any phone even without data coverage.
- **Assurance requirements**:
  - Phone ownership verification via Twilio Verify prior to activating notifications (legal compliance + anti-spam).
  - Demo mode allowing interview walkthroughs without incurring Twilio charges while still exercising full stack paths.
- **Operational mandates**:
  - Container-first deployment targeting AWS Fargate for managed scaling and security.
  - Centralized logging (CloudWatch) and queue-based asynchronous execution (Celery + Redis) to decouple user actions from telephony workload spikes.
- **Stakeholder roles**:
  - Users manage personal wake-ups.
  - Admins oversee platform health, audit logs, respond to escalations.
  - SRE/DevOps maintain infrastructure, observability, and deployment pipeline.

> **Context snapshot:** start here when interviewers ask “what problem are you solving?”—these bullets translate directly into user stories and SLA guardrails.

---

### 2. High-Level Architecture

#### 2.1 Logical Layers
| Layer | Purpose | Primary Components |
|-------|---------|--------------------|
| **Presentation** | Capture user intent, render dashboards, and expose interactive controls. | Django templates (`core/home.html`, `core/dashboard.html`), Bootstrap UI, DRF browsable API. |
| **Application Services** | Orchestrate business workflows, enforce phone verification, and expose REST endpoints. | `apps.core`, `apps.calls`, `apps.api` viewsets, serializers, middleware. |
| **Domain & Scheduling** | Persist wake-up intents, log executions, and coordinate timed delivery. | `apps.calls.models`, `apps.scheduler.tasks`, `django_celery_beat` integration. |
| **Infrastructure** | Provide storage, queueing, telemetry, and third-party integrations. | PostgreSQL, Redis, Twilio APIs, OpenWeatherMap, AWS CloudWatch/SSM. |

#### 2.2 Component Responsibility Matrix
| Component | Key Responsibilities | Notable Interactions |
|-----------|----------------------|----------------------|
| `apps.core` | User authentication, profile preferences, admin access control. | Extends Django `User`, integrates Twilio Verify via `PhoneVerification`. |
| `apps.calls` | Twilio voice/SMS orchestration, webhook handlers, call logging. | Consumes `TwilioService`, writes to `CallLog`, responds to DTMF/SMS commands. |
| `apps.scheduler` | Celery tasks and signals that translate scheduled intents into timed jobs. | Registers one-off `django_celery_beat` tasks; enqueues `execute_wakeup_call`. |
| `apps.api` | REST endpoints for users, wake-up calls, and call logs. | DRF routers, serializers enforcing business rules (future date, verified phone). |
| External Services | Telephony delivery, weather data, monitoring, secret management. | Twilio Verify/Voice/Messaging, OpenWeatherMap, AWS CloudWatch & SSM. |

#### 2.3 Data Stores & Artifacts
| Store / Artifact | Contents | Usage |
|------------------|----------|-------|
| PostgreSQL | `User`, `UserProfile`, `WakeUpCall`, `CallLog`, `InboundCall` tables. | Source of truth for scheduling, verification status, and execution history. |
| Redis | Celery broker & result backend. | Buffers asynchronous tasks, enabling scale-out execution. |
| `django_celery_beat` tables | Periodic task definitions, crontab schedules. | Ensure wake-ups execute at precise times even after restarts. |
| CloudWatch Logs | Structured application and worker logs. | Operational traceability, troubleshooting, and audit evidence. |

#### 2.4 Integration Interfaces
| Direction | Interface | Notes |
|-----------|-----------|-------|
| Outbound | Twilio REST (Verify, Voice, Messaging) | Verification SMS, voice call initiation, SMS dispatch. |
| Outbound | OpenWeatherMap REST | Fetches current conditions per ZIP for inclusion in wake-ups. |
| Outbound | AWS SSM Parameter Store | Retrieves secrets (Twilio credentials, DB password) at runtime. |
| Inbound | Twilio Webhooks | Handles voice response XML, DTMF input, SMS replies, and status callbacks. |

#### 2.5 Deployment Topology
```
            +-------------------------------+
            |        Client Channels        |
            |  Web UI / REST / Inbound IVR  |
            +---------------+---------------+
                            |
                 HTTPS (UI & API requests)
                            |
          +-----------------v-----------------+
          |        Django Web / DRF API       |
          +-----------+------------+----------+
                      |            |
         ORM Access   |            |  Celery Dispatch
                      |            |
         +------------v--+     +---v-----------+
         |  PostgreSQL    |     |    Redis      |
         | (Domain Data)  |     | (Task Queue)  |
         +------------+---+     +------+--------+
                      |                |
         Read/Write Models             |  Asynchronous Jobs
                      |                |
         +------------v----------------+--------------+
         |         Celery Workers & Beat Scheduler    |
         +------------+-------------------------------+
                      |
      +---------------+--------------------------------------------+
      |           External Services via HTTPS                      |
      |  • Twilio Verify / Voice / Messaging                       |
      |  • OpenWeatherMap                                         |
      |  • AWS CloudWatch (logging) & SSM (secrets)               |
      +-----------------------------------------------------------+
```

This layered view highlights how presentation, application logic, and infrastructure collaborate, while the topology diagram captures runtime relationships between Django, Celery, data stores, and third-party services.

---

### 3. Domain Model
#### 3.1 Identity & Preferences (`apps/core/models.py`)
```7:62:apps/core/models.py
class User(AbstractUser):
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    is_phone_verified = models.BooleanField(default=False)

class UserProfile(models.Model):
    CONTACT_METHOD_CHOICES = [('call', 'Phone Call'), ('sms', 'Text Message')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    zip_code = models.CharField(max_length=10, blank=True)
    preferred_contact_method = models.CharField(max_length=4, choices=CONTACT_METHOD_CHOICES, default='call')
    timezone = models.CharField(max_length=50, default='America/New_York')
```
- `PhoneVerification` stores verification codes, status, timestamps for audit and throttling; supports multiple outstanding codes while retaining newest first via `ordering = ['-created_at']`.
- Design note: `timezone` stored at profile level because wake-up calls can continue using historical timezone even if user travels—future extension could snapshot timezone per call.

#### 3.2 Scheduling & Logging (`apps/calls/models.py`)
```9:119:apps/calls/models.py
class WakeUpCall(models.Model):
    scheduled_time = models.DateTimeField()
    contact_method = models.CharField(max_length=4, choices=CONTACT_METHOD_CHOICES)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='scheduled')
    is_demo = models.BooleanField(default=False)
    last_executed = models.DateTimeField(null=True, blank=True)
    next_execution = models.DateTimeField(null=True, blank=True)

class CallLog(models.Model):
    wakeup_call = models.ForeignKey(WakeUpCall, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES)
    twilio_sid = models.CharField(max_length=100, blank=True, null=True)
    weather_data = models.JSONField(null=True, blank=True)

class InboundCall(models.Model):
    twilio_call_sid = models.CharField(max_length=100, unique=True)
    from_number = models.CharField(max_length=17)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
```
- **Entity relationships (cardinality)**  
```
[User] 1───1 [UserProfile]
   │
   └───* [PhoneVerification]
   │
   └───* [WakeUpCall] 1───* [CallLog]
                  │
                  └───* [InboundCall] (calls into system)
```
- **Status lifecycle**:
  - `scheduled`: default state awaiting execution.
  - `active`: optional transitional state when execution is in progress (future multi-step flows).
  - `completed`: Twilio confirmed success or demo run finished.
  - `cancelled`: user or admin manually stopped future notifications.
  - `failed`: Twilio initiation error or internal exception.
- `is_demo` flag suppresses Twilio billing while logging behavior; used heavily in QA/staging to validate Celery pipelines without hitting telecom networks.
- `CallLog.weather_data` persists the spoken/text summary (temperature, description) for compliance and transparency, even if the API later returns different values.
- `InboundCall.recording_url` allows storing Twilio recording for quality assurance when voice input is enabled.

---

### 4. End-to-End Workflow

| Stage | Components | Details |
|-------|------------|---------|
| Registration | Django auth | Users register/login through UI; `UserProfile` holds role/preferences. |
| Phone Verification | `/api/users/verify_phone/` & `/verify_code/` | Twilio Verify sends SMS code; on approval `is_phone_verified` flips true. |
| Scheduling | `/api/wakeup-calls/` or UI | Serializer enforces verified phone + future datetime; auto-uses user phone if omitted. |
| Task Registration | `apps.scheduler.signals.schedule_wakeup_call` | `post_save` creates one-off `PeriodicTask` via `django_celery_beat`. |
| Async Execution | `apps.scheduler.tasks.execute_wakeup_call` | Fetch weather, log attempt, send Twilio call/SMS (demo mode logs only). |
| Voice Interaction | `VoiceResponseView`, `handle_voice_input` | TwiML provides wake-up + weather + DTMF menu (cancel/change method). |
| SMS Interaction | `generate_sms_message`, `handle_sms_webhook` | Outbound text includes weather; inbound STOP/CHANGE/METHOD adjust schedules/preferences. |
| Inbound Calls (Optional) | `handle_inbound_call` | IVR greets identified users, announces next wake-up, offers DTMF menu. |
| Status Tracking | `CallLog`, `call_status_webhook` | Twilio callbacks update call status/duration; admins & users review history. |

#### Sequence Walkthrough (Voice Call)
1. **User scheduling**: POST `/api/wakeup-calls/` with ISO timestamp → serializer validates phone verification, future time, persists `WakeUpCall`.
2. **Signal dispatch**: `post_save` registers `PeriodicTask` (one-off) plus Celery beat sweep ensures redundancy.
3. **Execution window**: Celery beat triggers `execute_wakeup_call` near scheduled time; task fetches latest record to account for last-minute edits.
4. **Weather lookup**: `WeatherService.get_weather_by_zip` queries OpenWeatherMap; if API fails, returns fallback string to ensure message continuity.
5. **Twilio call**: `TwilioService.make_call` hits Twilio REST API with callback URL pointing to `/calls/voice-response/<uuid>/`.
6. **TwiML response**: Twilio fetches voice response endpoint; Django returns TwiML with greeting, weather, DTMF gather.
7. **User interaction**: Pressed digits POST to `/calls/handle-voice-input/`; view mutates `WakeUpCall` state accordingly and returns TwiML acknowledgement.
8. **Call status**: Twilio sends webhook to `/calls/call-status/` with final status + duration. `CallLog` updated to reflect `completed`, `no_answer`, etc.
9. **Admin visibility**: Django admin lists show call log entry including weather snapshot, Twilio SID, any errors.

#### Sequence Walkthrough (SMS Call)
1. Same until step 4.
2. Task builds message using `generate_sms_message`, includes weather summary and instructions.
3. `TwilioService.send_sms` sends message; Twilio SID stored.
4. User replies `STOP`/`CHANGE`/`METHOD` → Twilio hits `/calls/sms-webhook/`; view processes command, updates DB, replies via Twilio.
5. `CallLog` shows SMS send success/failure; admin sees 2-way interaction in logs.

```
User Action
    │
    ▼
Django REST API  ──►  Signal Layer  ──►  Celery Queue  ──►  Worker Execution
    │                                          │
    │                                          └──► WeatherService (OpenWeatherMap)
    │
    └──► Twilio (Voice / SMS)
               │
               └──► End-User (call or text)
                            │
                            └──► Twilio Webhook Callbacks
                                         │
                                         └──► Django Webhooks → Update `CallLog` / `WakeUpCall`
```

> **Interview tip:** walk the interviewer down this ladder pointing at the components you touched—API serializer, signal, Celery task, Twilio call—so they see breadth and sequence discipline.

---

### 5. Asynchronous Orchestration
- **Signal-Driven Scheduling**  
```12:35:apps/scheduler/signals.py
PeriodicTask.objects.update_or_create(
    name=f"wakeup-call-{instance.id}",
    defaults={
        'crontab': schedule,
        'task': 'apps.scheduler.tasks.execute_wakeup_call',
        'args': json.dumps([str(instance.id)]),
        'one_off': True,
    }
)
```
- **Celery Task Execution**  
```16:94:apps/scheduler/tasks.py
weather_data = WeatherService().get_weather_by_zip(wakeup_call.zip_code)
call_log = CallLog.objects.create(...)
if wakeup_call.contact_method == 'call':
    voice_url = f"{settings.BASE_URL}{reverse('calls:voice_response', args=[wakeup_call.id])}"
    twilio_sid = twilio_service.make_call(wakeup_call.phone_number, voice_url)
elif wakeup_call.contact_method == 'sms':
    message = generate_sms_message(weather_data, wakeup_call)
    twilio_sid = twilio_service.send_sms(wakeup_call.phone_number, message)
```
- `schedule_recurring_wakeup_calls` sweeps ±1 minute to catch last-minute edits and queue drift.
- **Retry & resilience considerations**:
  - Current implementation logs failure and marks call `failed`. Future enhancements include Celery `autoretry_for` to handle transient Twilio/network errors with exponential backoff.
  - Use `CallLog` existence to enforce idempotency (e.g., skip sending if a `completed` log already exists for the scheduled time).
- **Task visibility**:
  - `django_celery_beat` table allows non-technical administrators to inspect upcoming jobs via Django admin, providing operational transparency.

> **Key outcome:** business SLAs rely on beat + worker coordination—call this out when interviewers probe “how do you make sure the call really fires at 6:30 AM?”

---

### 6. Twilio & Weather Integrations
- **TwilioService**  
  - Lazy client init; disabled mode logs warnings for demo runs.  
  - Methods wrap Verify (`send_verification_code`, `verify_code`), voice (`make_call`), SMS (`send_sms`).
- **Voice Experience** (`VoiceResponseView`)  
  - Compose TwiML: greeting, weather, DTMF menu → `/calls/handle-voice-input/`.
- **Inbound DTMF**  
  - `1`: instructs to use app for schedule changes.  
  - `2`: cancel call(s).  
  - `3`: toggle contact method.  
  - `0`: polite hangup.
- **SMS Keywords**  
  - `STOP`: cancel upcoming scheduled calls.  
  - `CHANGE`: instruct to manage via app/API.  
  - `METHOD`: flip preferred contact method.
- **WeatherService**  
  - Calls OpenWeatherMap; fallback message ensures resilient UX when API fails.

> **Comms narrative:** emphasize how Twilio Verify gates onboarding, while voice/SMS channels reuse the same `TwilioService` wrapper for cohesion. Mention fallback weather messaging as “graceful degradation.”

---

### 7. REST API Surface (`apps/api/urls.py`)

| Endpoint | Methods | Purpose | Extra Actions / Notes |
|----------|---------|---------|-----------------------|
| `/api/users/` | `GET`, `PUT`, `PATCH` | Manage authenticated user record; admins can list others. | `GET /me/`, `POST /verify_phone/`, `POST /verify_code/` |
| `/api/wakeup-calls/` | `GET`, `POST`, `PATCH`, `DELETE` | CRUD for scheduled calls (scoped to user or all for admins). | `POST /{id}/cancel/`, `/reschedule/`, `/change_method/` |
| `/api/call-logs/` | `GET` | Read-only execution history; admin sees global; user sees own. | Supports pagination (`PAGE_SIZE = 20`). |

- **Security & Auth**: `IsAuthenticated` globally required; admins determined via `UserProfile.role`.
- **Serialization rules**: `WakeUpCallSerializer` enforces future datetimes + verified phone; `CallLogSerializer` exposes read-only telemetry.
- **Extensibility**: Add DRF token issuance or JWT for partner integrations; endpoints already compatible with `TokenAuthentication`.

---

### 8. Admin & UI Experience

| Layer | Highlights | Visual Cues | Interview Notes |
|-------|-----------|-------------|-----------------|
| **Access Control** | `AdminAccessMiddleware` blocks non-admins from `/admin/`; context processors expose `is_admin_user`. | Flash message “Access denied. Admin privileges required.” | Emphasize security gate before talking UI polish. |
| **Home Dashboard** | Authenticated users view hero + scheduled-call cards; admins see top 10 global calls. | Badges show ZIP codes, statuses, verification labels. | Demonstrate difference using `demo_user_1` (admin) vs `demo_user_5` (user). |
| **Scheduling Workspace** | `dashboard.html` presents wake-up form, verification modal, recent call history, quick tips. | Loading spinners on buttons, Bootstrap alerts for feedback. | Mention AJAX-style flow (no full page postbacks). |
| **Admin Console** | Custom ModelAdmins for `User`, `UserProfile`, `WakeUpCall`, `CallLog`, `InboundCall`. | Color-coded status chips, monospace Twilio SID snippets, “DEMO” pill. | Talk about operational triage: view logs, filter unverified users, inspect call history. |
| **Profile Updates** | `update_profile` endpoint accepts JSON to adjust ZIP/timezone/contact method. | Inline form hints describing weather usage and verification requirement. | Highlights API + UI reuse (same serializer powering form + REST clients). |

> **Design note:** surface-level guardrails (badges, warning banners, modal gating) mirror backend validations, giving interviewers a hook to connect UX choices with business rules.

---

### 9. Deployment & Operations
- **Dockerfile**: installs system deps, pip packages, collects static assets, creates non-root user, runs Gunicorn, includes health check hitting `/api/`.
- **docker-compose.yml**: orchestrates Postgres, Redis, Django web, Celery worker, Celery beat; seeds demo data on boot.
- **AWS Deployment**:
  - `aws-deployment/deploy.sh`: build, tag, push image to ECR, register new ECS task definition, update service.
  - Task definition defines three containers (web, worker, beat) sharing image; secrets pulled from AWS SSM; logs to CloudWatch; health checks via curling `/api/`.
- **Logging**: custom CloudWatch handler streams logs when AWS credentials present; console logging fallback for local/dev.
- **Operational Runbook**:
  - Scaling web tier: adjust desired count in ECS service or apply auto-scaling based on CPU/latency metrics.
  - Scaling workers: increase task count or move worker/beat to dedicated ECS service for independent scaling.
  - Disaster recovery: rebuild tasks by re-running `deploy.sh`; DB backups handled via RDS snapshots; Redis (transient) can be restored from infrastructure code.
- **Security posture**:
  - Secrets fetched at runtime from SSM Parameter Store (encrypted).
  - Container runs as `appuser` (non-root) to mitigate privilege escalation.
  - Health check uses internal curl; ALB should enforce HTTPS termination and route to container port 8000.
- **Networking**:
  - Fargate tasks operate in AWS VPC; use private subnets with NAT for outbound Twilio/OWM calls; ALB in public subnet.
  - Security groups: allow ALB→web 8000, web→Redis/RDS, worker/beat→Redis/RDS, open outbound to Twilio/OpenWeatherMap.

> **Cloud talking point:** lead with “single Docker image, three ECS containers (web/worker/beat), CloudWatch logging, secrets via SSM.” Interviewers love concise deployment elevator pitches.

---

### 10. Demo & Testing Tooling
- `python manage.py seed_data --count 30`: creates admin + 10 demo users, populates 30+ demo wake-up calls marked `is_demo=True` to suppress real Twilio calls while logging activity.
- Suggested testing strategy:
  - Mock Twilio for unit tests.
  - Celery eager mode for integration tests.
  - API tests verifying permission boundaries and validation (future times, verified phones).
- Additional tooling ideas:
  - Management command to purge demo data post-interview.
  - Script to flip `is_demo=False` on subset of calls when showcasing real Twilio integration.
  - Load-test harness using Locust or k6 to simulate bulk scheduling traffic.
- Testing matrix:
  - Unit: serializer validation, service wrappers (Twilio, weather) with mocks.
  - Integration: Celery tasks with `CELERY_TASK_ALWAYS_EAGER=True`.
  - End-to-end: smoke script seeds call scheduled minutes ahead, runs worker, verifies `CallLog` entry transitions to `completed`.

> **Demo storytelling:** highlight how `is_demo=True` lets you walk through the entire queue + logging path live in an interview without spamming phones—proof of thoughtful developer experience.

---

### 11. Risks, Enhancements & Talking Points
- **Duplicate Execution**: `PeriodicTask` + sweep task could double-trigger. Mitigation: idempotency checks (e.g., ensure `CallLog` not already completed or track execution flag).
- **Timezone Handling**: Currently stores UTC; incorporate `UserProfile.timezone` in scheduling/reschedule flows to support non-UTC users and DST transitions.
- **Webhook Security**: Add Twilio signature validation on inbound webhooks.
- **Periodic Task Cleanup**: Cancel/delete operations should remove or disable associated `PeriodicTask` entries (extend signals).
- **Weather Caching**: Use Redis to cache per-zip weather snapshots for short durations to reduce API calls.
- **Monitoring**: Expand with metrics (Celery queue depth, Twilio error rates), alerts, and dashboards.
- **Scalability**: Split worker/beat into separate ECS services for independent autoscaling; add Celery retry/backoff for transient errors.
- **Extensibility Ideas**: Recurring schedules, speech recognition, multi-language support, mobile push notifications, advanced analytics (success rate trends).
- **Compliance & Privacy**: Assess storage of phone numbers (consider encryption at rest, masking in logs), adhere to TCPA consent rules, track opt-in/opt-out events.
- **Resilience**: Evaluate fallback SMS provider or use Twilio Messaging Service for redundancy; implement circuit breaker if Twilio API degraded.
- **Analytics**: Build dashboards around call success rate by hour, weather impact on pickup rate, verification conversion funnel.

> **Pitch-ready angle:** frame each risk as an opportunity for future roadmap—“we already log Twilio failures; next step is auto-retry + alerting”—to show proactive ownership.

---

### 11.1 Edge Cases, Trade-offs & Decoupling Strategies

| Scenario / Edge Case | Current Handling | Trade-off | Decoupling / Improvement Path |
|----------------------|------------------|-----------|------------------------------|
| **Simultaneous Call Scheduling**<br>Two Celery triggers (beat + sweep) fire within same minute. | Duplicate tasks may run, but `CallLog` state guards against duplicate success; worst case double Twilio attempt. | Potential double-billing / user annoyance. | Introduce optimistic locking (e.g., `WakeUpCall.status` transition to `active` with `select_for_update`) or Redis-based execution token. |
| **Weather API Outage** | `WeatherService` logs error and returns placeholder text. | Caller hears “weather unavailable”. | Cache recent successful weather per ZIP; circuit-breaker around API; consider decoupling to separate weather microservice. |
| **Twilio Rate Limit (429)** | Exception bubbles to `execute_wakeup_call`, status → `failed`. | Requires manual retry; user misses wake-up. | Configure Celery retries with backoff; decouple dispatch to queue backed by Twilio Messaging Service with built-in rate smoothing. |
| **User Timezone Changes** | Scheduler stores UTC timestamp supplied by client; profile `timezone` not applied once call created. | If user changes timezone after scheduling, call might trigger at wrong local time. | Decouple scheduling from execution time by storing localized time + timezone, computing UTC at execution using `pytz`; optionally run timezone normalization service. |
| **Phone Number Reuse / Ownership Change** | Verification required once; no automatic re-verification if number changes externally. | Potential delivery to unintended owner. | Decouple phone verification into dedicated service requiring periodic re-verification or verifying when profile is updated. |
| **Inbound Call Without Matching User** | IVR responds with onboarding message and logs `InboundCall` with null `user`. | Missed opportunity to capture leads. | Route to lightweight lead-capture service (decoupled) that stores contact for follow-up. |
| **Bulk Demo Data Execution** | Demo calls flagged `is_demo=True`; Celery executes but short-circuits Twilio. | Worker still spends CPU; Twilio mocked. | Decouple demo processing to separate queue or skip Celery for demo flagged entries (log-only pipeline). |

**Decoupling Principles Applied**
- **Service boundaries**: Telephony wrapped in `TwilioService`; future providers (e.g., Nexmo) can swap in via strategy pattern.
- **Async buffers**: Redis/Celery isolate user-facing latency from heavy operations; consider adding message topics (e.g., `verification`, `dispatch`) for finer scaling.
- **Configuration segregation**: Secrets via SSM; environment-driven toggles (e.g., DEMO mode) keep infrastructure concerns outside code.
- **Observability separation**: Application logs (CloudWatch) vs domain logs (`CallLog` table) ensures auditing even if CloudWatch unavailable.

> **Interview framing:** walk through one edge case (e.g., Twilio outage) and show layered mitigations: fallback messaging, Celery retries, monitoring alerts—demonstrates depth in reliability engineering.

---

### 11.2 Key Challenges & Practical Solutions

| Challenge | Impact | Solution Implemented | Future Enhancements |
|-----------|--------|----------------------|---------------------|
| **Ensuring Verified Contactability** | Without verification, calls/SMS could target wrong owner; regulatory risk. | Twilio Verify flow integrated into `/api/users/verify_phone/` + `/verify_code/`, gating scheduling via serializer validation. | Auto re-verify on phone change; rate-limit verification attempts via Redis to prevent abuse. |
| **Delivering Right-Time Execution** | Wake-up must execute exactly at scheduled time or trust erodes. | Combination of one-off `PeriodicTask` registration and sweep `schedule_recurring_wakeup_calls` to catch drifts. | Add execution lock + retry strategy; store timezone metadata to recompute UTC near runtime. |
| **Weather & Telephony Dependency Failures** | External outages degrade experience or miss notifications. | Weather fallback messaging; Twilio errors logged + call marked `failed` for admin visibility. | Implement Celery retries with exponential backoff, alerting on failure thresholds, and optional secondary providers. |
| **Admin Visibility & Auditability** | Ops needs to diagnose issues quickly; compliance requires history. | `CallLog` and `InboundCall` tables capture weather snapshot, SID, duration; admin dashboards highlight statuses. | Build self-service analytics dashboard; add export/reporting pipelines. |
| **Safe Demo Experience** | Interviews/demos shouldn’t incur live charges or spam real numbers. | Seed command marks `is_demo=True`, Celery task short-circuits Twilio calls but still logs execution. | Add environment toggle to disable Twilio entirely; create synthetic Twilio sandbox responses for richer demo data. |
| **Scalable Deployment Footprint** | Need consistent dev→prod pipeline with minimal manual steps. | Single Dockerfile, ECS task definition running web/worker/beat with CloudWatch logging and SSM secrets. | Split worker/beat into dedicated ECS services for independent scaling; introduce IaC (Terraform/CDK) for repeatable infra. |

> **Use in interview:** Pick 2–3 challenges that resonate with the interviewer’s focus (e.g., reliability, DevOps) and walk through “problem → current mitigation → roadmap”.

---

### 12. Interview Game Plan
- Start with architecture diagram (apps/services) and data model overview.
- Walk interviewer through end-to-end scenario referencing specific modules/functions.
- Highlight async flow, Twilio integration, and AWS deployment story.
- Discuss failure handling and potential improvements proactively.
- Emphasize role security, verification requirements, and auditability via logs and call history.
- Be ready to explain trade-offs (Celery vs serverless, Twilio Verify, demo mode) and path forward for enterprise hardening.
- Prepare artifacts:
  - Sequence diagram sketch (describe verbally or draw) showing Django→Celery→Twilio interactions.
  - Log samples from CloudWatch to showcase observability.
  - Admin screenshots or descriptions emphasizing call tracing.
- Anticipate deep-dive questions:
  - How to implement recurring schedules (cron expression parsing, persisted recurrence rule, next-run calculation).
  - Handling daylight savings when scheduling future wake-ups.
  - Dealing with Twilio throttling or 429 responses (queue-based rate limiting).
  - Security of webhook endpoints and verifying Twilio signatures.

---

### 12.1 Executive Brief Wrap-Up
The platform unifies verified telephony, weather context, and asynchronous orchestration to deliver dependable wake-up reminders. Operational safeguards—ranging from demo isolation to CloudWatch logging—give stakeholders confidence, while the documented roadmap outlines clear levers for scaling, securing, and productizing the service. This dossier equips you to present both the current solution and the forward path with credibility.

---

### 13. Reference Commands
- Local stack: `docker-compose up --build`
- Seed demo data: `python manage.py seed_data --count 30`
- Run Celery worker: `celery -A wakeupcall worker -l info`
- Deploy to Fargate: `cd aws-deployment && ./deploy.sh`

---

This document consolidates the full system workflow, data design, integration touchpoints, operational setup, and interview-ready discussion points for the Wake-Up Call service.

---

### 11.3 Improvement Suggestions & Roadmap Themes

| Theme | Suggestion | Benefit | Effort Level |
|-------|-----------|---------|--------------|
| **Reliability & Observability** | Add Celery task retries with exponential backoff; push metrics (success/failure counts, queue depth) to CloudWatch dashboards with alerts. | Reduces missed wake-ups from transient errors; gives ops clear visibility. | Medium |
| **Security & Compliance** | Implement Twilio webhook signature validation; encrypt phone numbers at rest; add audit trail for verification attempts. | Prevents spoofed callbacks, protects PII, aligns with regulations. | Medium |
| **User Experience** | Support recurring rules + timezone-aware scheduling UI; offer notification preview including weather snippet; consider PWA push notifications. | Improves flexibility and engagement, reduces manual rescheduling. | High |
| **Scalability & Decoupling** | Split telephony dispatch into dedicated queue/service; explore event-driven bus (e.g., SNS/SQS, Kafka) for wake-up lifecycle events. | Isolates failure domains, allows independent scaling of voice/SMS workloads. | High |
| **Demo & Testing** | Ship mock Twilio adapter for automated tests; add k6/Locust load scripts; create CLI tool to provision demo scenarios. | Safer demos, better regression coverage, validates scaling assumptions. | Medium |
| **Data & Analytics** | Aggregate daily wake-up success metrics, track verification conversion funnel, expose REST endpoint for BI tools. | Enables data-driven improvements and stakeholder reporting. | Medium |
| **DevEx & Automation** | Adopt Terraform/CDK for infrastructure; establish CI/CD pipeline with lint/test/build/deploy stages per environment. | Faster, safer deployments; codified infrastructure. | Medium–High |

> **Roadmap storytelling:** pair a quick win (e.g., webhook signing) with an ambitious project (event-driven decoupling) to show both pragmatic and visionary thinking.

### 11.4 Success Accelerators
- **Recurring & Smart Scheduling**: Add rules for weekly patterns, snooze windows, and timezone-aware adjustments so wake-ups track user lifestyle automatically.
- **Resilient Delivery Loop**: Layer in automatic retries with backoff, fallback channels (e.g., SMS if voice fails), and alerting to make missed wake-ups rare and transparent.
- **Weather Intelligence**: Cache and enrich forecasts with severe weather alerts or commute impact, turning wake-ups into actionable context.
- **Insights & Reporting**: Build dashboards for success rate by hour, verification funnel, and failure reasons; enable exports for stakeholders.
- **Zero-Trust Telephony**: Validate Twilio webhook signatures, encrypt stored numbers, and audit verification attempts to satisfy enterprise compliance.
- **Demo & Enablement Toolkit**: Provide scripted demo toggles, mock Twilio responders, and shareable outcome reports to streamline sales or interviews.
- **Automation & IaC**: Capture AWS infrastructure in Terraform/CDK and integrate CI/CD pipelines for lint/test/build/deploy to cut rollout friction.
- **Partner Integrations**: Publish outbound webhooks or partner APIs so external systems can schedule wake-ups programmatically, increasing stickiness.

---


