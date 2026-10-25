# CollabVerse frontend

Professional, social-first frontend for the FastAPI backend.

## Run locally

```bash
npm install
npm run dev
```

The frontend expects the API at `http://127.0.0.1:8000/api/v1`. Copy `.env.example` to `.env` to use another API URL. Start the backend with its documented Uvicorn command and make sure its database migrations have been applied.

Current first slice: account registration and sign-in, profile summary, network feed, text post publishing, and post appreciation. The API currently returns author IDs rather than public author profiles, so posts from other people use a neutral member label until a public-user lookup endpoint is available.
