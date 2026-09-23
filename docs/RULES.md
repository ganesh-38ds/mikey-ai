# Development Rules & Standards

## 1. Code Formatting & Style
### Python (Backend)
- Follow **PEP 8** style guidelines.
- Use type hints for all function signatures (e.g., `def get_weather(city: str) -> dict:`).
- Group imports logically: Standard library, third-party packages, local modules.
- Use descriptive variable and function names (`fetch_user_data` instead of `get_data`).

### JavaScript (Frontend)
- Use ES6+ syntax (`let`, `const`, arrow functions).
- Use `async/await` for asynchronous operations (e.g., `fetch` calls) instead of raw Promises.
- Keep the global scope clean; encapsulate logic within functions or modules.

## 2. API Design & Routing (FastAPI)
- Define clear Pydantic models for request and response payloads.
- Use appropriate HTTP methods (`GET` for retrieval, `POST` for creation/processing).
- Keep route controllers thin; move complex business logic and API integrations into dedicated utility or service files.
- Ensure all API endpoints handle exceptions gracefully and return appropriate HTTP status codes (e.g., `400 Bad Request`, `500 Internal Server Error`).

## 3. Environment Variables & Security
- **NEVER** hardcode API keys (`GROQ_API_KEY`, `GEMINI_API_KEY`) in the source code.
- Always load sensitive credentials using `python-dotenv` from a local `.env` file.
- Ensure `.env` is included in `.gitignore`.
- Sanitize user inputs on the backend before executing database queries or external API calls to prevent injection attacks.

## 4. Database Management
- Use parameterized queries or an ORM (like SQLAlchemy) to interact with SQLite to prevent SQL injection.
- When modifying the database schema, provide clear migration steps or scripts.
- Ensure database connections are properly closed or managed within context managers.

## 5. Version Control & Commits
- Write clear, descriptive commit messages.
  - Bad: `fixed stuff`
  - Good: `fix(backend): resolve TTS audio streaming delay`
- Branching strategy: Keep `main` stable. Do feature work on separate branches (e.g., `feature/voice-mode`, `bugfix/weather-api`).

## 6. Documentation
- Update `README.md` and `docs/` files whenever significant architectural or feature changes are made.
- Add docstrings to complex functions explaining the parameters, return types, and potential side effects.
