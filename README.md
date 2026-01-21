# Text Risk Scoring Service

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-Educational-orange.svg)](#license)

A deterministic, explainable text risk scoring API built using FastAPI. The service analyzes raw text input and classifies it into predefined risk categories using rule-based logic, ensuring predictable, stable, and demo-safe behavior.

This project is designed as an **application-layer AI decision system**, focusing on reliability, safety, and explainability, rather than probabilistic ML accuracy.

## 📋 Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Design Philosophy](#design-philosophy)
- [Key Features](#key-features)
- [Risk Categories](#risk-categories)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [API Contract](#api-contract)
- [Example Request & Response](#example-request--response)
- [Installation & Setup](#installation--setup)
- [Running the Service](#running-the-service)
- [Running Tests](#running-tests)
- [Error Handling](#error-handling)
- [Determinism & Safety Guarantees](#determinism--safety-guarantees)
- [Limitations](#limitations)
- [Future Improvements](#future-improvements)
- [License](#license)

## 🎯 Overview

The Text Risk Scoring Service is a backend API that evaluates textual content and assigns a risk score and risk category based on predefined keyword-based rules.

The system is **intentionally deterministic**:

- ✅ The same input will always produce the same output
- ✅ No randomness or probabilistic models are used
- ✅ All decisions are explainable

This makes the service suitable for:

- 🎪 **Demo environments**
- 📊 **Evaluation tasks**
- 🛡️ **Moderation pipelines**
- 🤖 **Rule-based AI decision layers**

## 🚨 Problem Statement

In many real-world systems, especially demos and early-stage integrations, AI services must be:

- **Predictable** - Same input, same output
- **Explainable** - Clear reasoning for decisions
- **Stable under bad input** - Graceful error handling
- **Safe to expose publicly** - No security vulnerabilities

This project solves the problem of text risk assessment without relying on black-box machine learning models, focusing instead on clarity, determinism, and robustness.

## 🏗️ Design Philosophy

The project follows these core principles:

### 🎯 **Determinism over intelligence**
Same input must always yield the same output.

### 🔍 **Explainability over complexity**
Every decision must include clear reasons.

### 📋 **Contracts over assumptions**
Input and output formats are strictly defined.

### 🛡️ **Safety over performance**
The system must never crash or return undefined behavior.

### 🚀 **Application-layer AI**
The focus is on building a reliable service, not training models.

## ⭐ Key Features

- 🎯 **Deterministic text risk scoring**
- 🔍 **Rule-based keyword detection**
- 📊 **Clear LOW / MEDIUM / HIGH classification**
- 💡 **Explainable trigger reasons**
- 🛡️ **Structured error handling**
- 📚 **OpenAPI / Swagger documentation**
- ✅ **Unit-tested logic**
- 🚀 **Portable and easy to deploy**

## 📊 Risk Categories

The system classifies text into the following categories:

### 🟢 **LOW**
No or minimal risk indicators detected.

### 🟡 **MEDIUM**
Presence of one or more risk indicators without strong intent.

### 🔴 **HIGH**
Multiple high-severity indicators or explicit harmful intent.

> Risk scoring is capped and normalized to ensure stable categorization.

## 🏛️ System Architecture

```
Client / UI
     |
     |  HTTP POST /analyze
     v
FastAPI API Layer (main.py)
     |
     v
Risk Engine (engine.py)
     |
     v
Structured Response (schemas.py)
```

**Key Design Decisions:**
- 🎯 The API layer is intentionally thin
- 🧠 All business logic resides in the engine
- 📋 Schemas enforce strict input/output contracts

## 📁 Project Structure

```
text-risk-scoring-service/
│
├── app/
│   ├── main.py        # FastAPI application entry point
│   ├── engine.py      # Core risk scoring logic
│   ├── schemas.py     # Pydantic input/output schemas
│   └── __init__.py
│
├── tests/
│   └── test_engine.py # Unit tests for risk logic
│
├── README.md          # Project documentation
├── contracts.md       # API contracts
├── HANDOVER.md        # Operational handover notes
└── requirements.txt   # Python dependencies
```

## 🛠️ Technology Stack

- 🐍 **Python 3.10+** - Core language
- ⚡ **FastAPI** – Modern, fast web framework
- 📋 **Pydantic** – Data validation and schemas
- 🚀 **Uvicorn** – Lightning-fast ASGI server
- 🧪 **Pytest** – Testing framework

## 📡 API Contract

### Endpoint
```http
POST /analyze
```

### Request Body
```json
{
  "text": "string"
}
```

### Response Body
```json
{
  "risk_score": 0.0,
  "risk_category": "LOW | MEDIUM | HIGH",
  "trigger_reasons": ["string"],
  "processed_length": 0,
  "errors": null
}
```

> 💡 The API always returns a structured response, even in error cases.

## 📝 Example Request & Response

### Request
```json
{
  "text": "this is a scam and hack attempt"
}
```

### Response
```json
{
  "risk_score": 0.8,
  "risk_category": "HIGH",
  "trigger_reasons": [
    "Detected fraud keyword: scam",
    "Detected cybercrime keyword: hack"
  ],
  "processed_length": 32,
  "errors": null
}
```

## 🚀 Installation & Setup

### Prerequisites

- 🐍 Python 3.10 or higher
- 📦 Git (optional)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/rajaryan0726/text-risk-scoring-service.git
   cd text-risk-scoring-service
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 🏃 Running the Service

1. **Start the server**
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Open Swagger UI in your browser:**
   ```
   http://127.0.0.1:8000/docs
   ```

3. **Alternative: ReDoc documentation:**
   ```
   http://127.0.0.1:8000/redoc
   ```

## 🧪 Running Tests

```bash
python -m pytest
```

**Expected output:**
- ✅ All tests should pass
- 📊 Confirms deterministic and stable behavior
- 🛡️ Validates error handling

### Run tests with coverage
```bash
python -m pytest --cov=app
```

## 🚨 Error Handling

The service handles various error scenarios:

- 📭 **Empty input**
- 🔢 **Invalid input types**
- 💥 **Unexpected failures**

**Key guarantees:**
- ✅ All errors are returned in a structured format under the `errors` field
- ✅ The service never crashes or returns raw stack traces
- ✅ HTTP status codes are meaningful and consistent

## 🔒 Determinism & Safety Guarantees

This service **guarantees**:

- 🎯 **Same input → same output**
- 🚫 **No randomness**
- 🌐 **No dependency on external APIs**
- 🛡️ **Stable behavior under edge cases**
- 📊 **Predictable scoring thresholds**

These guarantees make the system suitable for demos and evaluations.

## ⚠️ Limitations

- 🔤 **Keyword-based detection only**
- 🧠 **No contextual NLP understanding**
- 📚 **No learning or adaptation**
- 🔐 **No authentication or rate limiting**

> 💡 These limitations are **intentional** for clarity and safety.

## 🚀 Future Improvements

- 📊 **Category-wise weighted scoring**
- 🔍 **Regex-based intent detection**
- 🔐 **Authentication and API keys**
- ⏱️ **Rate limiting**
- 🐳 **Docker-based deployment**
- ☁️ **Cloud hosting**
- 📈 **Metrics and monitoring**
- 🌍 **Multi-language support**

## 📄 License

This project is provided for **educational and evaluation purposes only**.