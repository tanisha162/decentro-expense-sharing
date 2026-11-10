# 💳 Decentro Expense Sharing Platform — FinTech Ledger API

<div align="center">

  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Pytest-Tested-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" />

  <p align="center">
    <strong>High-Performance Distributed Expense Sharing & Debt Simplification Ledger Engine.</strong>
  </p>

</div>

---

## 📌 Executive Summary
**Decentro Expense Sharing** is a production-tested FinTech microservice designed to handle multi-party expense splits (Equal, Exact, Percentage) with algorithmic debt simplification. It reduces the total transaction volume across group members using graph-based net-balance resolution.

---

## ✨ Features
- **Dynamic Split Engines:** Support for `EQUAL`, `EXACT`, and `PERCENT` distribution schemes with float-precision validation.
- **Debt Simplification Algorithm:** Min-cash-flow algorithm reducing transitive debts (e.g., A owes B, B owes C -> A directly settles with C).
- **Full Test Suite:** 100% test coverage using **pytest** covering boundary conditions, division rounding, and concurrent splits.
- **Dockerized Architecture:** Includes `Dockerfile` and `docker-compose.yml` for reproducible local and cloud setups.
- **Postman API Suite:** Pre-configured Postman collection ready for regression testing and client integration.

---

## 🚀 Installation & Running

```bash
# Clone repository
git clone https://github.com/tanisha162/decentro-expense-sharing.git
cd decentro-expense-sharing

# Option A: Run with Docker
docker-compose up --build

# Option B: Run locally
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload
```

---

## 👩‍💻 Author & Connect
**Tanisha Gupta** — Full-Stack Developer & AI/ML Engineer  
- **GitHub:** [@tanisha162](https://github.com/tanisha162)  
- **LinkedIn:** [linkedin.com/in/tanisha-gupta162](https://www.linkedin.com/in/tanisha-gupta162)  
- **Email:** [gtanisha162@gmail.com](mailto:gtanisha162@gmail.com)
