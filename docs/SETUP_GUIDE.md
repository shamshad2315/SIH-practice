# MediConnect Setup & Developer Guide

This guide will walk you through setting up and running **MediConnect** on your local machine.

---

## 1. Prerequisites
Ensure you have the following installed:
- **Node.js**: v18.0.0 or higher ([Download Node.js](https://nodejs.org/))
- **Java JDK**: 17 or higher ([Download OpenJDK / Oracle JDK](https://adoptium.net/))
- **Maven**: 3.8+ (or use the included Maven wrapper)
- **Git**: For version control

---

## 2. Clone & Folder Setup

```bash
git clone <repository_url> mediconnect
cd mediconnect
```

---

## 3. Backend Setup (Spring Boot)

### 3.1 Navigate to Backend
```bash
cd backend
```

### 3.2 Configuration
The backend comes pre-configured with **H2 in-memory database** for instant zero-configuration local runs.
To review or configure properties, see `src/main/resources/application.properties`.

For PostgreSQL:
```properties
# Uncomment in application.properties for PostgreSQL
# spring.datasource.url=jdbc:postgresql://localhost:5432/mediconnect_db
# spring.datasource.username=postgres
# spring.datasource.password=yourpassword
```

### 3.3 Run the Application
```bash
# Using Maven
mvn spring-boot:run
```
The backend will launch at `http://localhost:8080`.  
- **API Health**: `http://localhost:8080/api/health`
- **Swagger UI**: `http://localhost:8080/swagger-ui.html`
- **H2 Console**: `http://localhost:8080/h2-console` (JDBC URL: `jdbc:h2:mem:mediconnectdb`, user: `sa`, password: `password`)

---

## 4. Frontend Setup (React + Vite)

### 4.1 Navigate to Frontend
```bash
cd ../frontend
```

### 4.2 Install Dependencies
```bash
npm install
```

### 4.3 Configure Environment (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default `VITE_API_BASE_URL` is `http://localhost:8080/api`.

### 4.4 Start Development Server
```bash
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 5. Pre-seeded Demo Accounts

| Role | Email | Password |
|---|---|---|
| **Admin** | `admin@mediconnect.com` | `admin123` |
| **Doctor (Cardiology)** | `dr.smith@mediconnect.com` | `doctor123` |
| **Doctor (Neurology)** | `dr.johnson@mediconnect.com` | `doctor123` |
| **Patient** | `patient@mediconnect.com` | `patient123` |

You can also use the 1-Click Quick Demo Login buttons directly on the Login page!
