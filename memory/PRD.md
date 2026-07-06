# Dispatchr — Product Requirements Document

## Original Problem Statement
Rebuild the Replit app **Dispatchr** as a full production-ready web app with improved design and features. Full-stack React + FastAPI + MongoDB. Pixel-perfect feature parity with the provided Replit prototype, using Shadcn components and Tailwind CSS.

## User Personas
- **Customer / Homeowner** — posts jobs, hires trades, buys from marketplace
- **Service Provider (Tradie)** — receives jobs, submits bids, runs a small trade business
- **Property Manager** — manages multiple properties + maintenance
- **Landlord** — maintains rental properties, tracks spend, ensures Healthy Homes compliance
- **Facilities Management** — commercial sites, SLA tickets, preventive maintenance
- **Insurance Partner** — accesses shared property histories & docs

## Core Requirements
1. Role-based sign-up and dashboards (6 roles above)
2. Job posting + complex bidding (price, docs, T&C, threaded comments)
3. Marketplace ("Trade Supply Co.") — products, cart, checkout
4. Provider portal — 13 tabs (dashboard, job board, calendar, earnings, quotations, team, trades board, external jobs, track workers, GPS devices, job history, trade store, membership, warranty claims)
5. Real-time messaging between clients and providers
6. **Community Forum** — role-scoped (provider vs customer/homeowner), fully functional with backend persistence, focused on property maintenance & renovations
7. Live Map, News Feed, Cost Estimator, Community Forum, Legal & Privacy, Guide & Help, Report Provider, Disputes, More menu
8. Cookie-based JWT auth (httpOnly, SameSite=None, Secure)

## What's Implemented (2026-02-06)
- ✅ **Auth**: cookie-based JWT (httpOnly), role switching, 6 roles supported (customer, provider, property, insurance, landlord, facilities)
- ✅ **Jobs & Bids**: complex bidding (price, line items, docs, T&C, threaded comments), all CRUD wired
- ✅ **Marketplace**: Trade Supply Co with cart & checkout
- ✅ **Provider Portal**: 13 tabs functional
- ✅ **Sidebar**: 6 role-specific nav configs, "Switch Account Type" dialog with all roles, "More" link on every role
- ✅ **Landing / Signup**: 6 role cards (with Landlord & Facilities), Signup dropdown includes all roles
- ✅ **New Modules**: Cost Estimator (real /api/cost-guide data), Community Forum (full backend), Legal & Privacy, Guide & Help, Report Provider, My Disputes, More menu
- ✅ **Landlord Dashboard** — rentals, tenants, maintenance stats + quick actions
- ✅ **Facilities Dashboard** — commercial sites, SLA compliance, mock + real property data
- ✅ **Community Forum (2026-02-06)** — fully functional, role-scoped:
  - Provider community: 9 categories (Pricing & Quoting, Renovation Projects, Maintenance Ops, Compliance & Building Code, Suppliers & Wholesalers, Tools & Materials, Business Ops, Market Trends, The Smoko Room) + 9 seeded posts with 3 replies each
  - Customer community: 8 categories (Home Maintenance, Renovation Journeys, DIY vs Hire a Pro, Tradie Reviews, Cost Questions, Smart Home & Efficiency, Landlord Corner, Dispute Advice) + 9 seeded posts
  - Reddit-style hot ranking, sort tabs (Hot/New/Top), category filter, keyword search, tag chips, view counts, replies count
  - Rich post detail with vote controls (up/down toggle), threaded replies with author badges, share, delete-by-owner
  - New Post dialog with category + tags + validation
  - Cross-audience isolation (403 on cross-role post access)
  - Stats endpoint (posts, replies, members, active in 24h)
- ✅ **Logo click-to-home** — Dispatchr logo everywhere routes to `/`
- ✅ **Deployment blockers cleared**: N+1 queries, hardcoded secrets removed
- ✅ **Security**: httpOnly cookie auth (no localStorage tokens), React hook deps fixed, no index-as-key patterns
- ✅ **Backend tests**: 16/16 forum tests passing; 36/36 previous integration tests passing

## Backend Endpoints (Forum)
- `GET /api/forum/categories` — audience-scoped list
- `GET /api/forum/posts?category&sort&q` — sort: hot|new|top
- `GET /api/forum/posts/{post_id}` — detail + replies + increments views
- `POST /api/forum/posts` — create (audience auto-set by role)
- `DELETE /api/forum/posts/{post_id}` — owner only
- `POST /api/forum/posts/{post_id}/replies`
- `POST /api/forum/posts/{post_id}/vote` — value: 1|0|-1
- `POST /api/forum/replies/{reply_id}/vote`
- `GET /api/forum/stats`

## Roadmap (Prioritized Backlog)

### P0 — Immediate
- (none — all P0 items complete)

### P1 — Next Up
- **Refactor high-complexity components**: `JobDetail.jsx`, `Sidebar.jsx`, `Bookings.jsx` — split into sub-components (BidList, JobHeader, BidDialog, etc.)
- **Modularize backend**: `server.py` is ~2000 lines. Split into `routes/{auth,jobs,bids,forum,marketplace,cost_guide}.py` + `models/` + `seed.py`
- **Fix React hook lint warnings**: useEffect missing deps in JobDetail, MyJobPosts, ProviderCalendar
- **Add backend type hints**: coverage ~34%, target 80%+ on `server.py`
- **Forum: unique-viewer tracking** — currently views inflate on refresh; add debounce or per-user session tracking
- **Forum: threaded (nested) replies** — parent_reply_id column exists but UI is flat

### P2 — Nice-to-have
- **Lazy-load routes** in App.js to speed initial load
- **Notifications page** (linked from More menu, currently 404)
- **Settings page** (linked from More menu, currently 404)
- **Real-time forum**: WebSocket push for new replies / vote counts
- **Forum: image attachments** in posts
- **Forum: user profile with post history**
- **Forum: "follow" a topic / category**
- **Forum moderation queue** (report post, admin actions)
- **Public "shareable" post pages** for SEO
- **Report Provider**: currently mocked — wire up backend
- **My Disputes**: currently empty-state — wire up backend
- **Dispute mediation flow**

### P3 — Long-term
- **Mobile app** (React Native)
- **Provider verification badges** (identity, insurance, licence)
- **Stripe integration for escrow payments**
- **AI-suggested pricing** on new posts (based on Cost Guide + market trends)
