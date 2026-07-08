# Pro Finder NZ (formerly Dispatchr) — Product Requirements Document

## Original Problem Statement
Rebuild the Replit app **Dispatchr** as a full production-ready web app with improved design and features. Full-stack React + FastAPI + MongoDB. Pixel-perfect feature parity with the provided Replit prototype, using Shadcn components and Tailwind CSS.

**2026-02-08 REBRAND**: Application rebranded to **Pro Finder NZ**. New logo = silver-fern icon inside the existing primary→blue gradient badge + "Pro Finder" wordmark with an "NZ" accent chip. Color scheme unchanged.

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

## What's Implemented (2026-02-08)
- ✅ **Rebrand to Pro Finder NZ (2026-02-08)** — new fern-mark logo, wordmark + NZ chip, title tag, all user-facing "Dispatchr" copy replaced (Login, Signup, ClientHome footer, JobDetail T&C, ProviderProfile message template, ReportProvider, GuideHelp, CostEstimator, LegalPrivacy, Referrals link, WarrantyClaims, backend API title/root/log/seed strings). LocalStorage keys and demo emails intentionally kept for continuity.

## What's Implemented (2026-02-07)
- ✅ **Provider Directory (2026-02-07)** — Freelancing-style catalog for end clients:
  - Backend: `GET /api/providers/search` with filters (category, subcategory, min_rating, min_reviews, min_jobs, rate_bucket low/med/high, verified_only, background_checked, accredited, q) + sort (best_match, rating, reviews, price_asc, price_desc). Response `{count, results[]}`. Empty freshly-registered providers gated out (require bio + rating>0).
  - Backend: `GET /api/providers/{provider_id}` returns full profile — bio, gallery (4 stock images), reviews (3 seeded per provider), past_jobs, rate_bucket, response_time_hours, years_in_business, credential flags.
  - Backend seed enhanced: 9 providers with subcategories, gallery URLs (all 4 valid), 3 reviews each, background_checked, accredited, response_time_hours, years_in_business.
  - Frontend `/find-providers` — 3-col grid of provider cards, sticky filter sidebar (rate buckets, rating pills, review pills, job pills, trust & safety toggles), sort dropdown, search box, active filter chips, ServicePicker integration.
  - Frontend `/providers/:providerId` — hero with credential badges + hourly rate + Message/Invite CTAs, About, Services, Past Work gallery (4 imgs), Reviews with 5-star display.
  - Sidebar link "Find Providers" added to customer, landlord, property, facilities navs.
- ✅ **Tenant → Manager Approval Workflow (2026-02-07)**:
  - Backend Tenancy model + endpoints (POST /api/tenancies, GET /mine, POST /{id}/approve, /reject, DELETE)
  - JobPost extended: `tenancy_id`, `tenant_id`, `approver_id`, `approval_status`, `approved_at`, `rejection_reason`, `assigned_provider_id`, `billing_target`
  - `POST /api/jobs` routes via manager when `route_via_manager=true` and active tenancy exists
  - `POST /api/jobs/{id}/approve` — landlord approves with optional preferred provider + open_to_bids toggle
  - `POST /api/jobs/{id}/reject` — requires reason, sets job.status=cancelled
  - `GET /api/approvals/queue` (approvers only) + `/preferred-providers`
  - `GET /api/jobs/board` filtered to approval_status in [not_required, approved] so providers only see approved jobs
  - Frontend `/tenancies` (tenant + approver views) and `/approvals` (queue with approve/reject dialogs)
  - PostJob banner with "Send to manager" / "Book on my own" toggle
  - Sidebar links: "Approval Queue" (landlord/property/facilities) + "My Property Link" (customer)
- ✅ **Sidebar refactor** — 4 files (Sidebar, SidebarNavSection, SidebarFooter, SwitchRoleDialog)
- ✅ **Forum unique-viewer tracking + nested reply UI**
- ✅ **Dark mode default** for first-time visitors + new hero heading
- ✅ **Desktop / Mobile View Mode Toggle**:
  - `ViewModeContext` — persisted `dispatchr_view_mode` in localStorage, lazy-initialized, auto-detects mobile if browser width < 768px on first visit
  - `ViewModeToggle` button in TopBar (desktop), MobileTopBar, Landing header, and Sidebar footer (data-testid `view-mode-toggle`, `sidebar-view-mode-toggle`)
  - Desktop mode: unchanged (Sidebar + TopBar + full-width main)
  - Mobile mode: phone-frame shell (max 430px wide, centered, subtle drop shadow + rounded 40px on desktop screens ≥768px; full-width on real mobile browsers)
  - `MobileTopBar` — hamburger menu opens Sidebar in a left Sheet drawer that closes on nav
  - `MobileBottomNav` — role-aware 5-tab nav (Home/Jobs/Post/Chat/Shop for customer; different mapping per role) + More sheet with quick links; dynamic grid columns match tab count (`grid-cols-4` for insurance which has 3 tabs)
  - CSS overrides in `index.css` clamp all `max-w-{7xl,6xl,4xl,2xl}` to 100%, hide `.hidden.lg:block` asides, and constrain Radix Dialog/Sheet/Popover portals to 400px when `html[data-view-mode="mobile"]`
  - `ServicePicker` detects `isMobile` internally: browse view uses horizontal scrollable category tabs + full-width subcategory list on mobile; keeps 240px sidebar + 2-col grid on desktop
  - Verified working on: Landing, Login, Signup, all role dashboards, PostJob (with ServicePicker), Community Forum + Post Detail, Marketplace, Provider Trade Store, all sidebar routes
- ✅ **Auth**: cookie-based JWT (httpOnly), role switching, 6 roles (customer, provider, property, insurance, landlord, facilities)
- ✅ **Jobs & Bids**: complex bidding + subcategory + service_type validation
- ✅ **Service Taxonomies (2026-02-06)**:
  - Residential: **18 categories, 122 subcategories** (General Home Maintenance, Electrical, Plumbing & Gas, Heating/Cooling/Ventilation, Roofing & Guttering, Carpentry & Joinery, Painting & Interior Finishes, Flooring & Tiling, Kitchens/Bathrooms/Renovations, Concrete & Outdoor Construction, Glass & Windows, Security & Smart Home, Data & Communications, Solar & Energy, Pools/Spas/Outdoor Living, Insulation & Weatherproofing, Appliance Installation, Specialist Home Services)
  - Commercial: **15 categories, 102 subcategories** (Building Maintenance, Electrical, Plumbing & Gas, HVAC & Mechanical, Roofing & Waterproofing, Carpentry & Joinery, Interior Finishes, Exterior Works, Glass & Aluminium, Fire Protection, Security Systems, Data & Communications, Building Automation, Renewable Energy, Commercial Renovations & Fit-outs)
  - Endpoints: `GET /api/services/{residential,commercial}-taxonomy`, `GET /api/services/taxonomy/{type}`, `GET /api/services/{type}-taxonomy/{category_id}`
- ✅ **ServicePicker** (React component): mode-aware (residential/commercial), 2-panel browse view with 240px sidebar + subcategory grid, cross-taxonomy search with mark-based highlight, keyboard-first UX, colored category icons, accessible (DialogTitle + DialogDescription).
- ✅ **PostJob**: rewritten with property-type toggle (residential/commercial) + ServicePicker integration + role-based defaults (landlord→residential, facilities/property→commercial).
- ✅ **ClientHome**: quick tags now map to real taxonomy subcategories; "Browse services" button opens ServicePicker; picked service displays as a chip pre-filled to PostJob.
- ✅ **Marketplace**: Trade Supply Co with cart & checkout
- ✅ **Provider Portal**: 13 tabs functional
- ✅ **Sidebar**: 6 role-specific nav configs, "Switch Account Type" dialog with all roles, "More" link on every role, "Forum" as first-class link
- ✅ **Landing / Signup**: 6 role cards (with Landlord & Facilities), Signup dropdown includes all roles
- ✅ **New Modules**: Cost Estimator, Community Forum (full backend, role-scoped, 15+ seeded posts), Legal & Privacy, Guide & Help, Report Provider, My Disputes, More menu
- ✅ **Landlord Dashboard** — rentals, tenants, maintenance stats + quick actions
- ✅ **Facilities Dashboard** — commercial sites, SLA compliance
- ✅ **Community Forum** — fully functional, role-scoped, Reddit-style hot ranking, sort tabs, category filter, keyword search
- ✅ **Logo click-to-home**
- ✅ **Security**: httpOnly cookie auth, no localStorage tokens, React hook deps fixed
- ✅ **Backend tests**: 12/12 taxonomy + 16/16 forum + 36/36 core = 64/64 pytest passing

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
