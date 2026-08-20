# System Architecture: MediConnect

## 1. High-Level Architecture

MediConnect follows a modern decoupled Client-Server architecture with a RESTful API backend and a Single Page Application (SPA) frontend.

```
┌────────────────────────────────────────────────────────┐
│                   Client Layer (SPA)                   │
│  React 18 + Vite + React Router + Vanilla CSS Tokens   │
└───────────────────────────┬────────────────────────────┘
                            │ HTTPS / REST (JSON)
                            ▼
┌────────────────────────────────────────────────────────┐
│                   API Gateway & Security               │
│  Spring Security Filter Chain + JWT Authentication     │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                    Controller Layer                    │
│ Auth | Doctor | Hospital | Appointment | Admin         │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                     Service Layer                      │
│ Business Logic, Slot Calculation, Verification, RBAC   │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│              Data Access Layer (Spring Data JPA)       │
│ Repositories, Query Methods, Entity State Management   │
└───────────────────────────┬────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│ H2 In-Memory Database │       │  PostgreSQL Database  │
│ (Zero-Config Dev)     │       │     (Production)      │
└───────────────────────┘       └───────────────────────┘
```

---

## 2. Authentication & Authorization Flow (JWT + RBAC)

1. **Login Request**: Client sends `POST /api/auth/login` with email and password.
2. **Authentication**: `SecurityConfig` and `CustomUserDetailsService` verify hashed password with BCrypt.
3. **Token Issuance**: `JwtTokenProvider` generates a signed JWT containing `sub` (username/email) and `role` claim.
4. **Subsequent Requests**: Client includes header `Authorization: Bearer <token>`.
5. **Security Filter**: `JwtAuthenticationFilter` intercepts request, validates signature and expiration, extracts role, and sets Spring `SecurityContextHolder`.
6. **Method-Level & Route Authorization**: `@PreAuthorize("hasRole('DOCTOR')")` or `hasRole('ADMIN')` protects endpoints.

---

## 3. Frontend Component Structure

```
src/
├── components/
│   ├── common/        # Navbar, Sidebar, Footer, Button, Modal, Badge, Input, Card
│   ├── doctor/        # DoctorCard, DoctorFilter, DoctorScheduleView, DoctorStats
│   ├── hospital/      # HospitalCard, DepartmentList
│   └── appointment/   # AppointmentBookingModal, AppointmentCard, SlotPicker
├── layouts/           # PatientLayout, DoctorLayout, AdminLayout
├── pages/
│   ├── auth/          # LoginPage, RegisterPage, ForgotPasswordPage
│   ├── patient/       # PatientDashboard, FindDoctorsPage, DoctorDetailPage, MyAppointmentsPage, MedicalRecordsPage
│   ├── doctor/        # DoctorDashboard, DoctorAppointmentsPage, DoctorSchedulePage, DoctorPatientsPage
│   ├── admin/         # AdminDashboard, ManageDoctorsPage, ManageHospitalsPage, ManageAppointmentsPage
│   └── common/        # HomePage, NotFoundPage
├── services/          # api.js, authService, doctorService, hospitalService, appointmentService
├── context/           # AuthContext (State, login, logout, role switching)
└── routes/            # AppRoutes (Protected and Public routes)
```
