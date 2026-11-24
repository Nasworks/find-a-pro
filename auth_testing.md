# Auth testing
- Email/password: POST /api/auth/register {email,name,password,role,business_name?,account_type?,signup_details{}}; POST /api/auth/login; GET /api/auth/me (returns is_reviewer)
- Google: Emergent Google auth (auth.emergentagent.com -> /client-home#session_id -> AuthCallback -> POST /api/auth/session). Can't log in via Google in tests: insert a users doc with signup_complete:false + user_sessions row {user_id, session_token, expires_at future}, set session_token cookie, then the app must redirect to /signup (completion mode, 2 steps) and POST /api/auth/complete-signup.
- Demo logins: POST /api/auth/demo-login {role}
