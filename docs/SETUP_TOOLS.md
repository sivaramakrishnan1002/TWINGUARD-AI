# Toolchain check and setup steps

Checked 24 Oct 2026 on the project machine. No packages or global tools were installed for this work.

| Tool | Detected version/status | Use in this task |
|---|---|---|
| Java | 21.0.7 LTS | Meets the Java version requirement. |
| Maven | Missing | Spring Boot build cannot be run. |
| Gradle | Missing | Spring Boot build cannot be run. |
| Node.js | 24.16.0 | Available; no frontend build requested. |
| npm | 11.13.0 | Available; no frontend dependencies installed. |
| Docker CLI | 29.8.2 | Installed. Docker Desktop previously reported inconsistent published-port/container-filesystem state; a usable engine is not confirmed by the version command. |
| Docker Compose | v5.6.0 | Installed. |
| pytest | 9.1.1 | Available in `.venv`; repository tests can run. |
| FastAPI / Starlette / httpx | Not installed in `.venv` | AI-service runtime and HTTP client tests cannot run without packages. |
| YAML / OpenAPI validator libraries | Not installed in `.venv` | Contracts use JSON syntax, a YAML 1.2 subset, with standard-library parsing and structural checks. |

## To enable the AI service later

1. Keep using `D:\TIWNGUARD\.venv`; do not install packages globally.
2. Review the FastAPI and ASGI-server versions to use, add exact approved pins to `requirements.txt`, then install only inside the project venv with `.venv\Scripts\python.exe -m pip install -r requirements.txt` after package installation is authorized.
3. Re-run `.venv\Scripts\python.exe -m pytest` and verify `/health` and read-only `/layers` against a test database before declaring the service ready.
4. FastAPI was absent during this task, so no runnable FastAPI application or untestable placeholder was added. The API contract is design-only.

## To enable a Spring Boot backend later

Java 21 is already present. Install either Apache Maven or Gradle using its official Windows distribution, extract it to a user-owned tools directory, add its `bin` directory to the user `PATH`, open a new PowerShell window, and verify with `mvn -version` or `gradle --version`; confirm the output uses Java 21. Then generate/build a Spring Boot 3 project and add the health/database connectivity checks. Neither Maven nor Gradle was present, so no backend code was generated or left unbuildable.

## OpenAPI contract check

`docs/api/*.yaml` are serialized as JSON, a valid subset of YAML. Run `.venv\Scripts\python.exe tools\validate_api_contracts.py` to parse and check the OpenAPI version, required paths and methods, operation metadata, response definitions and local `$ref` targets. This validates repository contracts without installing a YAML/OpenAPI package; it does not replace a full external schema validator.
