# BVRIT Smart Bus Management System

> A comprehensive, AI-driven transport management system that optimizes daily commutes for students and staff at BVRIT through intelligent route optimization, real-time fleet tracking, and multi-role digital dashboards.

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-features)
- [Architecture](#-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation & Setup](#️-setup--installation)
- [Configuration](#-configuration)
- [Getting Started](#-getting-started)
- [API Documentation](#-api-documentation)
- [Core Algorithms](#-core-algorithms)
- [Workflow Diagrams](#-workflow-diagrams)
- [Usage Guide](#-usage-guide)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

BVRIT Smart Bus is an end-to-end digital transformation of the university's transportation infrastructure. The system intelligently digitizes bus stop selection, student-to-bus allocation using advanced optimization algorithms, digital pass generation with QR codes, and real-time live tracking of the entire fleet.

**Core Value Propositions:**
- **Intelligent Route Optimization**: Uses bearing angles, geofencing, and distance-based algorithms to create efficient, non-overlapping routes
- **Real-Time Transparency**: Students can live-track bus locations on interactive maps
- **Secure Multi-Role Access**: Role-based dashboards for Students, Admins, Drivers, and Coordinators
- **Paperless Operations**: QR-based digital day/yearly passes eliminating physical tickets
- **Communication Hub**: Integrated announcements and complaint resolution system

---

## 🚀 Features

### For Students
- **Dashboard & Stop Selection**: Browse available pickup stops and select preferred boarding locations
- **Route Discovery**: View assigned routes, schedules, and estimated arrival times
- **Digital Bus Passes**: Generate QR-based day passes and yearly bus passes directly from the app
- **Live Bus Tracking**: Track buses in real-time on an interactive map with geofence alerts when bus approaches
- **Complaint Management**: Report issues and receive timely responses from coordinators
- **Announcements**: Receive route updates, schedule changes, and general announcements

### For Drivers
- **Trip Management**: Start and end trips with single-click operations
- **GPS Tracking**: Real-time GPS coordinate updates broadcasted to the server
- **Live Dashboard**: View assigned routes, student count, and current trip status
- **Performance Metrics**: Track distance covered, time spent, and efficiency stats

### For Coordinators
- **Route Announcements**: Broadcast disruptions, schedule changes, or important notices
- **Student Management**: View enrolled students, manage complaints and feedback
- **Route Overview**: Monitor all active routes and associated bus stops
- **Complaint Resolution**: Centralized system for handling and responding to student issues

### For Administrators
- **Fleet Management**: Add, edit, and manage bus configurations (capacity, registration, etc.)
- **Student Allocation**: Run intelligent allocation algorithm to assign students to buses
- **Stop Management**: Create, edit, and organize pickup stops across the city
- **Bus Pass Configuration**: Set up day pass and yearly pass pricing and validity periods
- **Analytics Dashboard**: Monitor system usage, route efficiency, and allocation metrics

### System-Wide Features
- **Secure JWT Authentication**: Token-based secure sessions with forced password resets on first login
- **Role-Based Access Control (RBAC)**: Granular permission system based on user roles
- **Interactive Mapping**: Leaflet.js-powered interactive maps with GeoJSON markers
- **QR Code Generation**: Client-side QR code generation for bus passes without server overhead
- **Responsive Design**: Works seamlessly on desktop and mobile devices

---

## 🏗️ Architecture

The system follows a **Client-Server Architecture** with clear separation of concerns:

```mermaid
graph TD
    %% Entities
    Frontend["Frontend Layer<br/>HTML5/CSS3/JavaScript"]
    API["Backend API Layer<br/>FastAPI + Uvicorn"]
    Services["Service Layer<br/>Optimization Engine<br/>Redis Cache<br/>Route Scheduler"]
    DB[("Data Layer<br/>MySQL Database")]
    Maps["External Services<br/>Leaflet.js<br/>OSRM Routing<br/>OpenStreetMap"]

    %% Relationships
    Frontend -->|REST API<br/>JWT Auth| API
    API -->|SQLAlchemy ORM| DB
    API -->|Queries| Services
    Services -->|Caching| Redis["Redis"]
    Frontend -->|Map Tiles<br/>Routing| Maps
    
    %% Sub-components of API
    subgraph API_Modules ["FastAPI Module Structure"]
    Auth["Authentication<br/>/auth"]
    Student["Student Services<br/>/students"]
    Admin["Admin Operations<br/>/admin"]
    Driver["Driver Operations<br/>/driver"]
    Tracking["Fleet Tracking<br/>/tracking"]
    Coordinator["Coordinator Ops<br/>/coordinator"]
    end
    
    API ---|HTTP Routing| API_Modules
```

### Layer Breakdown

**Frontend Layer:**
- Vanilla HTML5, CSS3, and JavaScript (no external frameworks)
- Responsive UI with mobile-first design
- Interactive Leaflet.js maps with real-time tracking
- Client-side QR code generation
- Secure JWT token handling in localStorage

**API Layer:**
- FastAPI framework for high-performance async request handling
- Modular router structure for clean code organization
- Request validation using Pydantic models
- JWT-based authentication middleware
- CORS and security headers configuration

**Service Layer:**
- **Optimizer Engine**: Geographic route optimization with bearing angles and sliding-window algorithms
- **Route Scheduler**: Manages trip schedules and allocation timings
- **Redis Client**: Caches frequently accessed data (routes, stops, user sessions)
- **Database Queries**: Optimized SQLAlchemy queries for performance

**Data Layer:**
- MySQL relational database with normalized schemas
- Transaction management for complex operations
- Indexed columns for fast queries
- Foreign key relationships for data integrity

---

## 🛠️ Technology Stack

### Backend Infrastructure
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | FastAPI 0.104+ | Asynchronous, high-performance web framework |
| **Server Gateway** | Uvicorn | ASGI server for concurrent request handling |
| **Database** | MySQL 8.0+ | Relational data storage |
| **ORM** | SQLAlchemy 2.0+ | Object-relational mapping and query builder |
| **Validation** | Pydantic v2 | Request/response schema validation |
| **Authentication** | PyJWT | JWT token generation and verification |
| **Caching** | Redis | Session and data caching |
| **Task Scheduling** | APScheduler | Background job scheduling (optional) |

### Frontend Technologies
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Markup** | HTML5 | Semantic page structure |
| **Styling** | CSS3 | Responsive layouts and animations |
| **Interactivity** | Vanilla JavaScript (ES6+) | DOM manipulation and API calls |
| **Mapping** | Leaflet.js | Interactive maps and geolocation |
| **QR Generation** | QRCode.js | Client-side QR code rendering |
| **HTTP Client** | Fetch API | RESTful API communication |

### External Services
| Service | Purpose |
|---------|---------|
| **OSRM (Open Source Routing Machine)** | Geographic routing and distance matrix calculation |
| **OpenStreetMap** | Base map tiles and geographic data |
| **Haversine Formula** | Fallback distance calculation using spherical geometry |

---

## 📁 Project Structure

```
Bvrit_bus_Optimizer/
├── README.md                          # Project documentation (this file)
├── project_details.md                 # Detailed technical architecture
├── requirements.txt                   # Python dependencies
├── backend/                           # FastAPI backend
│   ├── __init__.py
│   ├── main.py                        # FastAPI app entry point
│   ├── config.py                      # Configuration settings
│   ├── database.py                    # Database connection setup
│   ├── models/                        # Data models
│   │   ├── __init__.py
│   │   ├── models.py                  # SQLAlchemy ORM models
│   │   └── schemas.py                 # Pydantic request/response schemas
│   ├── routers/                       # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py                    # Authentication endpoints
│   │   ├── student.py                 # Student-facing endpoints
│   │   ├── driver.py                  # Driver operations endpoints
│   │   ├── admin.py                   # Admin management endpoints
│   │   ├── coordinator.py             # Coordinator endpoints
│   │   └── tracking.py                # Live tracking endpoints
│   └── services/                      # Business logic layer
│       ├── __init__.py
│       ├── optimizer_engine.py        # Route optimization algorithm
│       ├── route_schedule.py          # Schedule management
│       └── redis_client.py            # Cache management
├── frontend/                          # Web frontend
│   ├── html/                          # HTML templates
│   │   ├── login.html                 # Main login page
│   │   ├── dashboard.html             # Student dashboard
│   │   ├── driver.html                # Driver interface
│   │   ├── admin-dashboard.html       # Admin dashboard
│   │   ├── tracking.html              # Live bus tracking
│   │   ├── bus-pass.html              # Digital pass generation
│   │   ├── admin/                     # Admin-specific pages
│   │   └── coordinator/               # Coordinator-specific pages
│   ├── css/                           # Stylesheets
│   │   └── style.css                  # Main stylesheet
│   ├── static/                        # Static assets
│   │   └── js/                        # JavaScript files
│   └── img/                           # Images and icons
├── tmp/                               # Temporary files and logs
├── manual_migration.py                # Database migration script (manual)
└── migrate_and_backfill.py            # Migration and data backfill script
```

### Key File Responsibilities

- **`backend/main.py`**: FastAPI application initialization, middleware setup, route registration
- **`backend/models/models.py`**: Database table definitions (User, Bus, Route, Stop, Allocation, etc.)
- **`backend/models/schemas.py`**: Request validation and response formatting
- **`backend/services/optimizer_engine.py`**: Core algorithm for intelligent route generation
- **`backend/routers/*.py`**: Specific endpoint implementations organized by domain
- **`frontend/html/dashboard.html`**: Main user interface template
- **`requirements.txt`**: List of Python package dependencies with versions

---

## 📦 Prerequisites

Before setting up the project, ensure your system meets these requirements:

### System Requirements
- **OS**: Windows, macOS, or Linux
- **RAM**: Minimum 4GB (8GB recommended for development)
- **Disk Space**: 2GB for project and dependencies

### Software Requirements
| Software | Version | Download |
|----------|---------|----------|
| **Python** | 3.10+ | [python.org](https://www.python.org/downloads/) |
| **MySQL Server** | 8.0+ | [mysql.com](https://dev.mysql.com/downloads/mysql/) |
| **Git** | Latest | [git-scm.com](https://git-scm.com/) |
| **Node.js** (optional) | 18+ | [nodejs.org](https://nodejs.org/) |

### Python Packages (will be installed via requirements.txt)
- FastAPI 0.104.1
- Uvicorn 0.24.0
- SQLAlchemy 2.0.23
- Pydantic 2.5.0
- PyJWT 2.8.1
- python-dotenv
- mysql-connector-python
- redis (optional)

---

## ⚙️ Setup & Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/Bvrit_bus_Optimizer.git
cd Bvrit_bus_Optimizer
```

### Step 2: Set Up Python Virtual Environment

Create and activate a virtual environment:

```bash
# On Windows
python -m venv .venv
.venv\Scripts\activate

# On macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Set Up MySQL Database

1. **Start MySQL Server**:
   ```bash
   # On Windows (if installed via MSI)
   # MySQL should start automatically or use:
   # net start MySQL80
   
   # On macOS with Homebrew
   brew services start mysql
   
   # On Linux
   sudo systemctl start mysql
   ```

2. **Create Database**:
   ```bash
   mysql -u root -p
   ```
   Then execute:
   ```sql
   CREATE DATABASE bvrit_bus_db;
   CREATE USER 'bus_user'@'localhost' IDENTIFIED BY 'secure_password';
   GRANT ALL PRIVILEGES ON bvrit_bus_db.* TO 'bus_user'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

### Step 5: Configure Environment Variables

Create a `.env` file in the project root directory:

```bash
# Database Configuration
DATABASE_URL=mysql+pymysql://bus_user:secure_password@localhost/bvrit_bus_db

# JWT Configuration
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server Configuration
DEBUG=True
HOST=127.0.0.1
PORT=8000

# OSRM Configuration (optional)
OSRM_BASE_URL=http://router.project-osrm.org

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379/0
```

### Step 6: Run Database Migrations

```bash
# If migrations are available
python migrate_and_backfill.py

# OR for manual migration
python manual_migration.py
```

### Step 7: Start the Development Server

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at `https://agent-based-optimized-student.onrender.com`

---

## 🔧 Configuration

### Environment Variables Reference

| Variable | Type | Description | Default |
|----------|------|-------------|---------|
| `DATABASE_URL` | string | MySQL connection string | `mysql://user:pass@host/db` |
| `SECRET_KEY` | string | JWT signing key | Required |
| `ALGORITHM` | string | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | Token expiration time | `30` |
| `DEBUG` | bool | Development mode | `True` |
| `HOST` | string | Server host address | `127.0.0.1` |
| `PORT` | int | Server port | `8000` |
| `OSRM_BASE_URL` | string | OSRM service endpoint | Optional |
| `REDIS_URL` | string | Redis connection string | Optional |

### Database Configuration

The system uses SQLAlchemy for ORM. Key models include:

- **User**: Student, Admin, Driver, Coordinator profiles
- **Bus**: Fleet vehicle information
- **Stop**: Pickup/dropoff locations
- **Route**: Bus route mappings
- **Allocation**: Student-to-bus assignments
- **Trip**: Driver trip records
- **BusPass**: Digital pass generation

### JWT Authentication

- Tokens are valid for 30 minutes by default (configurable)
- Refresh token mechanism available in production builds
- Payload includes: `user_id`, `role`, `exp`, `iat`

---

## 🚀 Getting Started

### For Students

1. **Login**: Navigate to `https://agent-based-optimized-student.onrender.com/frontend/html/login.html`
2. **First Login**: Use credentials provided by admin (default password: `bvrit123`)
3. **Change Password**: System forces password change on first login
4. **Select Stop**: Choose preferred pickup location from dashboard
5. **View Routes**: See assigned bus route and schedule
6. **Track Bus**: Click "Live Tracking" to see real-time bus location
7. **Generate Pass**: Create QR code for daily bus boarding

### For Drivers

1. **Login**: Use driver credentials at login page
2. **Dashboard**: View assigned buses and routes
3. **Start Trip**: Click "Start Trip" button before departing
4. **GPS Updates**: System automatically sends location updates
5. **End Trip**: Click "End Trip" when trip is complete
6. **View History**: Check completed trips and statistics

### For Coordinators

1. **Login**: Use coordinator credentials
2. **Dashboard**: View all routes and students
3. **Post Announcement**: Create and broadcast route updates
4. **Manage Complaints**: View and respond to student issues
5. **Monitor Routes**: Track all active routes in real-time

### For Administrators

1. **Login**: Use admin credentials
2. **Fleet Management**: Add/edit/delete buses with capacity details
3. **Stop Management**: Create pickup locations with coordinates
4. **Generate Allocation**: Run optimization algorithm to assign students
5. **View Analytics**: Monitor system usage and performance metrics
6. **Configure Passes**: Set up day pass and yearly pass pricing

---

## 📡 API Documentation

### Authentication Endpoints

**POST** `/auth/login`
- **Request**: `{username, password}`
- **Response**: `{access_token, token_type, user: {id, role, name}}`
- **Description**: Authenticates user and returns JWT token

**POST** `/auth/change-password`
- **Headers**: `Authorization: Bearer {token}`
- **Request**: `{old_password, new_password}`
- **Response**: `{message: "Password updated successfully"}`
- **Description**: Changes user password

### Student Endpoints

**GET** `/students/me`
- **Headers**: `Authorization: Bearer {token}`
- **Response**: Current student details and assignments
- **Description**: Retrieve logged-in student information

**GET** `/students/stops`
- **Headers**: `Authorization: Bearer {token}`
- **Response**: List of available pickup stops with coordinates
- **Description**: Get all bus stops

**GET** `/students/day-pass`
- **Headers**: `Authorization: Bearer {token}`
- **Response**: `{pass_id, qr_code, valid_until, bus_number}`
- **Description**: Generate daily bus pass with QR code

**POST** `/students/complaints`
- **Headers**: `Authorization: Bearer {token}`
- **Request**: `{subject, description}`
- **Response**: `{complaint_id, status: "pending"}`
- **Description**: Submit a complaint

**GET** `/students/announcements`
- **Headers**: `Authorization: Bearer {token}`
- **Response**: List of active announcements
- **Description**: Retrieve route announcements

### Driver Endpoints

**POST** `/driver/trip/start`
- **Headers**: `Authorization: Bearer {token}`
- **Request**: `{bus_id, route_id}`
- **Response**: `{trip_id, status: "started"}`
- **Description**: Start a new trip

**PATCH** `/driver/trip/{trip_id}/update-location`
- **Headers**: `Authorization: Bearer {token}`
- **Request**: `{latitude, longitude, speed}`
- **Response**: `{message: "Location updated"}`
- **Description**: Broadcast GPS coordinates

**POST** `/driver/trip/{trip_id}/end`
- **Headers**: `Authorization: Bearer {token}`
- **Response**: `{trip_id, status: "ended", duration, distance_covered}`
- **Description**: End current trip

### Admin Endpoints

**GET** `/admin/buses`
- **Headers**: `Authorization: Bearer {token}`
- **Response**: List of all buses with details
- **Description**: Get fleet information

**POST** `/admin/generate-allocation`
- **Headers**: `Authorization: Bearer {token}`
- **Request**: `{allocation_date}`
- **Response**: `{allocation_id, routes_generated, students_allocated}`
- **Description**: Run optimization algorithm

**GET** `/admin/analytics`
- **Headers**: `Authorization: Bearer {token}`
- **Response**: Dashboard metrics and statistics
- **Description**: Retrieve system analytics

### Tracking Endpoints

**GET** `/tracking/bus/{bus_id}`
- **Headers**: `Authorization: Bearer {token}`
- **Response**: `{bus_id, current_location, route_status, next_stop}`
- **Description**: Get real-time bus location

---

## 🧮 Core Algorithms

### Route Optimization Engine

The system employs a sophisticated multi-step algorithm in `backend/services/optimizer_engine.py`:

#### Step 1: Bearing Angle Isolation
- Computes compass bearing angles (0-360°) from each stop to campus
- Normalizes stops by their geographic direction

#### Step 2: Corridor Window Sweeping
- Groups stops into sequential linear corridors
- Uses **Greedy Sliding-Window algorithm** with 20° angular tolerance
- Ensures stops within each corridor follow logical geographic progression

#### Step 3: Farthest-First Sorting (Anti-Backtracking)
- Sorts stops within corridors by distance from campus (descending)
- Prevents buses from looping back on themselves
- Optimizes fuel consumption and travel time

#### Step 4: Detour Rejection Filter
- Calculates virtual route using OSRM
- Rejects routes where total distance > 1.25x straight-line distance
- Prevents inefficient geometric deviations

#### Step 5: Far-Gap Route Splitting
- Detects gaps between consecutive stops > 30km
- Automatically splits routes to prevent unrealistic segments
- Assigns additional bus resources if needed

#### Step 6: Efficiency Convergence Pass
- If route utilization < 75% capacity, attempts merging with nearby corridors
- Expands search radius to 45° angular range
- Aims for 80-100% fleet capacity optimization

### Distance Calculation

**Primary: OSRM (Open Source Routing Machine)**
```
matrix endpoint: /table/v1/driving/lon1,lat1;lon2,lat2
route endpoint: /route/v1/driving/lon1,lat1;lon2,lat2
```

**Fallback: Haversine Formula**
```
d = 2R * arcsin(√(sin²(Δφ/2) + cos φ1 * cos φ2 * sin²(Δλ/2)))
Where: R = Earth radius (6,371 km)
       1.3x multiplier applied for road factor
```

### Geofencing for Tracking

Real-time distance calculation using client-side Haversine:
- Updates every 3-5 seconds during trip
- Triggers alert when bus < 0.5km from next stop
- Displays ETA countdown to student

---

## 🔄 Workflow Diagrams

### 1. Student Login & First-Time Password Change

```mermaid
sequenceDiagram
    participant S as Student
    participant F as Frontend
    participant B as Backend API
    participant DB as MySQL DB

    S->>F: Enter Login Credentials
    F->>B: POST /auth/login
    B->>DB: Query User Record
    DB-->>B: User Data Returned
    B->>B: Verify password vs stored hash
    B-->>F: Return JWT Token + password_changed flag
    
    alt password_changed == false
        F-->>S: Redirect to Change Password
        S->>F: Submit new password
        F->>B: POST /auth/change-password
        B->>DB: Update password hash
        B-->>F: Success Response
        F-->>S: Redirect to Dashboard
    else password_changed == true
        F-->>S: Direct Dashboard Access
    end
```

### 2. Live Bus Tracking Flow

```mermaid
stateDiagram-v2
    [*] --> DriverLogin
    DriverLogin --> Dashboard
    
    state Dashboard {
        [*] --> Idle
        Idle --> TripStarted : Driver clicks "Start Trip"
        TripStarted --> LocationBroadcasting : Begin GPS loop
        LocationBroadcasting --> LocationBroadcasting : Send Lat/Lng every 3-5s
        LocationBroadcasting --> TripEnded : Driver clicks "End Trip"
    }

    TripStarted --> StudentView: Bus goes Live
    LocationBroadcasting --> StudentView: Map updates continuously
    TripEnded --> Idle
    Idle --> [*]
```

### 3. Student Allocation Workflow

```mermaid
sequenceDiagram
    participant Admin as Admin
    participant BE as Backend Engine
    participant OSRM as OSRM Service
    participant DB as Database
    participant Student as Students

    Admin->>BE: POST /admin/generate-allocation
    BE->>DB: Fetch all students + stops + buses
    DB-->>BE: Student/Stop/Bus Data
    
    BE->>BE: Group students by bearing angles
    BE->>BE: Create corridors (20° window)
    BE->>BE: Sort by farthest-first
    
    BE->>OSRM: Query distance matrix
    OSRM-->>BE: Return actual road distances
    
    BE->>BE: Validate routes (< 1.25x detour)
    BE->>BE: Split if gap > 30km
    BE->>BE: Optimize for 75%+ capacity
    
    BE->>DB: Store allocations
    DB-->>BE: Confirm Storage
    
    BE-->>Admin: Allocation Complete
    DB->>Student: Notify students of new assignment
    Student-->>Student: View updated route + bus
```

### 4. Bus Pass Generation

```mermaid
sequenceDiagram
    participant Student as Student
    participant Frontend as Frontend/Browser
    participant Backend as Backend API
    participant DB as Database
    participant QRLib as QRCode.js Library

    Student->>Frontend: Click "Generate Day Pass"
    Frontend->>Backend: GET /students/day-pass
    Backend->>DB: Fetch student allocation + bus info
    DB-->>Backend: Bus number, route, pass expiry
    Backend-->>Frontend: Return pass data (JSON)
    
    Frontend->>QRLib: Generate QR (client-side)
    QRLib-->>Frontend: QR code image/data-url
    Frontend-->>Student: Display pass + QR code
    Student->>Student: Screenshot or save QR code
```

---

## 📖 Usage Guide

### Common Use Cases

#### Use Case 1: Admin Creating New Bus Stop

1. Navigate to **Admin Dashboard** → **Manage Stops**
2. Click **"Add New Stop"**
3. Fill in:
   - Stop Name: (e.g., "Hitech City")
   - Latitude & Longitude: (e.g., 17.3850, 78.4867)
   - City/Area: Hyderabad
   - Stop Type: Pickup/Dropoff/Both
4. Click **"Save"** → Stop is created and available for allocation

#### Use Case 2: Running Student Allocation

1. Navigate to **Admin Dashboard** → **Generate Allocation**
2. Select date for allocation
3. Configure parameters (optional):
   - Bus capacity multiplier
   - Route optimization level
4. Click **"Generate"** → System runs optimization algorithm
5. Review generated routes and allocations
6. Click **"Confirm & Publish"** → Sends notifications to students

#### Use Case 3: Tracking a Bus in Real-Time

1. Go to **Student Dashboard** → **Track Bus**
2. System fetches assigned bus route
3. Map displays:
   - Current bus location (blue marker)
   - Your pickup stop (green marker)
   - Route path (polyline)
   - ETA countdown
4. Geofence alert triggers when bus < 0.5km away

#### Use Case 4: Reporting a Complaint

1. Navigate to **Student Dashboard** → **Complaints**
2. Click **"Report Issue"**
3. Select category: Delay, Driver Behavior, Vehicle Condition, Other
4. Write description with details
5. Optionally attach screenshot
6. Click **"Submit"** → Assigned to coordinator for resolution

---

## 🔍 Troubleshooting

### Common Issues & Solutions

#### Issue: "Connection refused" when starting server

**Cause**: MySQL server not running or database not configured
**Solution**:
```bash
# Check MySQL status
sudo systemctl status mysql  # Linux
brew services list | grep mysql  # macOS

# Start MySQL
sudo systemctl start mysql  # Linux
brew services start mysql  # macOS

# Verify DATABASE_URL in .env file
```

#### Issue: JWT Token Expired

**Cause**: Session token older than 30 minutes
**Solution**: 
- User must login again to get fresh token
- Increase `ACCESS_TOKEN_EXPIRE_MINUTES` in `.env` if needed

#### Issue: OSRM Connection Error

**Cause**: OSRM service unreachable
**Solution**:
```bash
# System will automatically fallback to Haversine formula
# To use custom OSRM instance:
export OSRM_BASE_URL=http://your-osrm-instance:5000

# Or run local OSRM server using Docker:
docker run -t -p 5000:5000 osrm/osrm-backend:v5.24.0
```

#### Issue: "ModuleNotFoundError" when starting server

**Cause**: Dependencies not installed
**Solution**:
```bash
pip install --force-reinstall -r requirements.txt
```

#### Issue: Port 8000 already in use

**Solution**:
```bash
# Use different port
uvicorn backend.main:app --port 8001

# Or kill process using port 8000
lsof -ti:8000 | xargs kill -9  # macOS/Linux
netstat -ano | findstr :8000  # Windows, then taskkill /PID <PID>
```

#### Issue: Students not appearing in allocation

**Cause**: Students haven't selected preferred stop yet
**Solution**:
1. Direct students to select their preferred stop in dashboard
2. Verify stops exist in database
3. Check student enrollment status (active vs inactive)

#### Issue: Real-time tracking not updating

**Cause**: Driver hasn't started trip or GPS location update failed
**Solution**:
1. Verify driver clicked "Start Trip" button
2. Check driver's location services enabled
3. Verify backend receiving location updates: Check MySQL `trip_tracking` table
4. Refresh browser page to reset WebSocket connection

---

## 🤝 Contributing

We welcome contributions! Here's how to get involved:

### Code Style Guidelines

- **Python**: Follow PEP 8 guidelines
- **JavaScript**: Use ES6+ syntax, follow Airbnb style guide
- **HTML/CSS**: Validate with W3C validators
- **Comments**: Use clear, concise English documentation

### Contribution Process

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature-name`
3. **Commit** with clear messages: `git commit -m "feat: add live tracking updates"`
4. **Push** to branch: `git push origin feature/your-feature-name`
5. **Create** a Pull Request with description of changes
6. **Code Review**: Address any feedback from maintainers
7. **Merge**: Once approved, your code will be merged

### Reporting Issues

- Check existing issues first to avoid duplicates
- Include system info (OS, Python version, etc.)
- Provide steps to reproduce the issue
- Attach screenshots or error logs if applicable

### Development Workflow

```bash
# After cloning and setting up:
git checkout -b feature/my-feature
# Make your changes...
pip install -r requirements.txt
uvicorn backend.main:app --reload
# Test changes thoroughly
git commit -am "feat: describe your changes"
git push origin feature/my-feature
# Create PR on GitHub
```

---

## 📝 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

**Last Updated**: May 2026  
**Version**: 1.0  
**Maintainers**: BVRIT Development Team
