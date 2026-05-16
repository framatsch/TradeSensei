# Dependency Compatibility Scan Report

## Overview
This report lists all direct dependencies analyzed across the `frontend/package.json`, `backend/pyproject.toml`, and the root `package.json` for the Trade Sensei project. The purpose is to ensure compatibility with the Dual-Licensing model (AGPLv3 + CLA) by strictly enforcing a permissive-only open-source license policy for external dependencies.

## Backend Dependencies (`backend/pyproject.toml`)
| Dependency | License | Status |
| :--- | :--- | :--- |
| `fastapi` | MIT | PASS |
| `uvicorn` | BSD | PASS |
| `sqlalchemy` | MIT | PASS |
| `asyncpg` | Apache 2.0 | PASS |
| `alembic` | MIT | PASS |
| `pydantic` | MIT | PASS |
| `pydantic-settings` | MIT | PASS |
| `python-jose` | MIT | PASS |
| `passlib` | BSD | PASS |
| `bcrypt` | Apache 2.0 | PASS |
| `python-multipart` | Apache 2.0 | PASS |
| `openpyxl` | MIT | PASS |
| `authlib` | BSD | PASS |
| `httpx` | BSD | PASS |
| `cryptography` | Apache 2.0 / BSD | PASS |
| `itsdangerous` | BSD | PASS |
| `boto3` | Apache 2.0 | PASS |
| `boto3-stubs` | MIT | PASS |

## Frontend Dependencies (`frontend/package.json`)
| Dependency | License | Status |
| :--- | :--- | :--- |
| `@hey-api/client-fetch` | MIT | PASS |
| `@hey-api/openapi-ts` | MIT | PASS |
| `@hookform/resolvers` | MIT | PASS |
| `@radix-ui/react-avatar` | MIT | PASS |
| `@radix-ui/react-dropdown-menu` | MIT | PASS |
| `@radix-ui/react-popover` | MIT | PASS |
| `@radix-ui/react-separator` | MIT | PASS |
| `@radix-ui/react-slot` | MIT | PASS |
| `@tailwindcss/typography` | MIT | PASS |
| `@tanstack/react-query` | MIT | PASS |
| `@tanstack/react-query-devtools` | MIT | PASS |
| `date-fns` | MIT | PASS |
| `lightweight-charts` | Apache 2.0 | PASS |
| `lucide-react` | ISC | PASS |
| `next` | MIT | PASS |
| `next-auth` | ISC | PASS |
| `next-themes` | MIT | PASS |
| `react` | MIT | PASS |
| `react-dom` | MIT | PASS |
| `react-hook-form` | MIT | PASS |
| `react-hot-toast` | MIT | PASS |
| `react-markdown` | MIT | PASS |
| `recharts` | MIT | PASS |
| `rehype-sanitize` | MIT | PASS |
| `remark-gfm` | MIT | PASS |
| `zod` | MIT | PASS |
| `zustand` | MIT | PASS |

## Root Dependencies (`package.json`)
| Dependency | License | Status |
| :--- | :--- | :--- |
| `react-markdown` | MIT | PASS |
| `@playwright/test` | Apache 2.0 | PASS |
| `@types/node` | MIT | PASS |

## Conclusion
**All direct dependencies analyzed utilize purely permissive licenses (e.g., MIT, Apache 2.0, BSD, ISC). No Copyleft or proprietary licenses were detected. The project successfully passes the compatibility scan for the Dual-Licensing model.**
