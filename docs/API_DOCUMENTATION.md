# MediConnect REST API Specification

**Base URL**: `http://localhost:8080/api`  
**Swagger UI**: `http://localhost:8080/swagger-ui.html`  
**OpenAPI JSON**: `http://localhost:8080/v3/api-docs`

---

## 1. Authentication Endpoints (`/api/auth`)

### 1.1 Register User
- **Method**: `POST`
- **URL**: `/api/auth/register`
- **Request Body**:
```json
{
  "name": "Jane Doe",
  "email": "jane.doe@example.com",
  "password": "Password123!",
  "role": "ROLE_PATIENT",
  "phone": "+1234567890",
  "gender": "FEMALE",
  "dateOfBirth": "1995-06-15"
}
```
- **Response** `(201 Created)`:
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "name": "Jane Doe",
      "email": "jane.doe@example.com",
      "role": "ROLE_PATIENT"
    }
  }
}
```

### 1.2 User Login
- **Method**: `POST`
- **URL**: `/api/auth/login`
- **Request Body**:
```json
{
  "email": "jane.doe@example.com",
  "password": "Password123!"
}
```
- **Response** `(200 OK)`:
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "role": "ROLE_PATIENT"
  }
}
```

---

## 2. Doctor Endpoints (`/api/doctors`)

### 2.1 Get All Doctors / Search
- **Method**: `GET`
- **URL**: `/api/doctors?specialty=Cardiology&hospitalId=1&search=smith`
- **Response** `(200 OK)`:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Dr. Sarah Smith",
      "specialty": "Cardiology",
      "experienceYears": 12,
      "consultationFee": 120.0,
      "rating": 4.9,
      "reviewCount": 142,
      "hospital": {
        "id": 1,
        "name": "Metro General Hospital",
        "city": "New York"
      },
      "availableSlots": ["09:00 AM", "09:30 AM", "10:00 AM", "02:00 PM"]
    }
  ]
}
```

### 2.2 Get Doctor by ID
- **Method**: `GET`
- **URL**: `/api/doctors/{id}`

### 2.3 Get Doctor Availability Slots
- **Method**: `GET`
- **URL**: `/api/doctors/{id}/slots?date=2026-08-25`

---

## 3. Hospital Endpoints (`/api/hospitals`)

### 3.1 List Hospitals
- **Method**: `GET`
- **URL**: `/api/hospitals`

### 3.2 Get Hospital Details
- **Method**: `GET`
- **URL**: `/api/hospitals/{id}`

---

## 4. Appointment Endpoints (`/api/appointments`)

### 4.1 Book Appointment
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <JWT_TOKEN>`
- **URL**: `/api/appointments`
- **Request Body**:
```json
{
  "doctorId": 1,
  "appointmentDate": "2026-08-25",
  "timeSlot": "10:00 AM",
  "reason": "Annual cardiac checkup and palpitations",
  "notes": "Previous ECG conducted last year"
}
```

### 4.2 Get User Appointments
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <JWT_TOKEN>`
- **URL**: `/api/appointments/my`

### 4.3 Update Appointment Status (Doctor/Admin)
- **Method**: `PATCH`
- **URL**: `/api/appointments/{id}/status`
- **Request Body**:
```json
{
  "status": "CONFIRMED"
}
```

### 4.4 Cancel Appointment
- **Method**: `DELETE` or `POST` `/api/appointments/{id}/cancel`
- **Request Body**:
```json
{
  "cancellationReason": "Conflict in personal schedule"
}
```

---

## 5. Admin Endpoints (`/api/admin`)
*(Requires `ROLE_ADMIN`)*

- `GET /api/admin/stats` - Platform metrics overview
- `GET /api/admin/doctors/pending` - Doctors awaiting verification
- `PATCH /api/admin/doctors/{id}/verify` - Approve/verify doctor
- `POST /api/admin/hospitals` - Register new hospital
- `GET /api/admin/users` - Paginated user management
