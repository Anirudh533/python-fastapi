# Product Service REST API

A clean, production-oriented **REST API** built using **Python, FastAPI, SQLAlchemy**, and **JWT-based authentication**.

---

## Tech Stack
- **FastAPI** – High-performance REST framework
- **SQLAlchemy** – ORM for database access
- **JWT** – Stateless authentication
- **Pydantic** – Request/response validation

---

## Design Decisions

### Why FastAPI
FastAPI enables fast, clean, and maintainable API development with:
- Async support
- Dependency injection
- Automatic OpenAPI documentation

---

### Why SQLAlchemy
Although DuckDB is great for analytics workloads, SQLAlchemy is a better fit for API services:

- Database-agnostic ORM (easy to switch engines)
- Optimized for frequent read/write operations
- Safer data access via parameterized queries
- Natural integration with Pydantic models
- Closer to real-world, production backend patterns

---

### Why JWT (Instead of OAuth 2.0)
OAuth 2.0 introduces additional infrastructure that isn’t required for this use case.  
JWT provides:

- Stateless, token-based authentication
- Short-lived access tokens
- Horizontal scalability without session storage
- Simpler architecture without auth servers or redirect flows

---

## Security Model
- Only **admin users can generate JWTs** for other users
- All issued tokens are **short-lived**
- Admin tokens are generated via a **minimal one-liner script**, avoiding exposed login endpoints

This keeps the authentication flow secure, simple, and low-overhead.

---

## Goal
Demonstrate how to build a **secure, production-grade REST API** with clean architecture, sensible trade-offs, and strong security defaults.


