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

## What's Implemented (2026-11 — Commercial track back, matching engine, role-based signup)
- ✅ Commercial taxonomy restored (18 cats incl. "Commercial Cleaning & Facility Hygiene" → "Commercial Kitchen & Hood Cleaning"); residential 25 cats. Residential-only purge removed.
- ✅ Job sizes `pricing_type` small_fixed | hourly | large_quote (+ budget_or_estimate, preferred_date) in Book flow (step 3 "Job size" → details window) and /post-job. Hourly jobs show a materials/equipment-hire disclaimer pop-up before posting.
- ✅ Provider onboarding wizard `/provider/onboarding` (business details, size, tracks, suburbs → searchable specialization tree → job sizes + rate per spec). `provider_specializations` collection. Dashboard redirects un-onboarded providers.
- ✅ Matching engine `dispatch_job()` (category+sub+track+job size+suburb/radius) → `job_matches` + `notifications`. Provider "New Matched Jobs" feed (Accept & Claim / Submit Quote / Decline), Active + Recently completed; client JobMatchesPanel (notified/responded, Award). Award → job `assigned`, accepted bid + booking created, others closed. `/jobs/{id}/progress` assigned→in_progress→done (booking synced). Notification bell (desktop + mobile).
- ✅ Seed specs: Demo Trade Co., Sarah Chen Plumbing (suburb list), MP Electrical, SparkClean Services.
- ✅ Role-based signup `/signup` (6 account types, role-specific questions, Google or email/password; Google users finish via `/auth/complete-signup`). Providers → `/provider/verification?welcome=1` (documents, optional) → onboarding.
- ✅ Provider documents (qualification / certification / police check, PDF or photo) → reviewer approval (`REVIEWER_EMAILS` = nasretm@gmail.com, page `/review/documents`) → ticks "Qualifications verified" / "Police checked" on profile, dashboard, matches panel. Credential files private to owner + reviewers.
- ✅ Address search fallback: Google (invalid key) → Photon → Nominatim.

## Pending user requests (not started)
- Receipt scanner for providers with cost types (materials, equipment purchase, equipment hire, third-party service…).
- Company main account + employee sub-accounts: send jobs to subs, GPS + mandatory timesheets (optional auto-timesheet from GPS), scanned receipts, main↔sub message board.
- Active-job project timeline module (main account updates stage, sends updates to client).
- Final invoice collation + manual edit (hours, travel/material/hire/fuel costs).
- Camera/photo access in mobile mode everywhere media is uploaded (job posting, messages client/provider/worker).
- Payments: Stripe (+ Google Pay / Apple Pay), pay from invoice/receipt, job history paid/unpaid, Stripe fee disclosure, 5% client platform fee + 5% deducted from provider.

## What's Implemented (2026-11 — Residential-only + expanded taxonomy)
- ✅ **Residential-only app**: commercial taxonomy, endpoints (`/services/commercial-taxonomy*`, `/services/taxonomy/commercial` → 404) and all Residential/Commercial toggles removed (Book flow is now 1 Describe/Browse → 2 Post Job). POST /jobs and /properties accept only residential. Startup `purge_commercial_data()` deletes commercial jobs (+bids) and commercial/mixed properties, converts `rental` → residential (idempotent, also cleans production).
- ✅ **Facilities Management kept, reworded** for apartment buildings & body corporates (dashboard, landing card, sidebar "Maintenance Requests").
- ✅ **Taxonomy expanded** to 25 categories / 179 services: added Locksmith Services, Builders & Renovations, Bricklaying & Masonry, Arborist & Tree Services, Gates, Pest Control, Chimney & Duct Cleaning, Appliance Repairs, Home IT Support + new categories Building Engineering & Inspections, Moving/Delivery & Rubbish Removal, Home Care/Elderly Support & Pet Services, In-Home Tutoring/Advisory & Professional Services; detection keywords added. Renamed: Cleaning & Home Hygiene, Appliance Installation & Repairs, Home IT, Data & Communications.

## What's Implemented (2026-11 — Search-first booking, Post Job only, saved properties)
- ✅ **Customer home = search bar only** (`pages/client/ClientHome.jsx`, `components/ServiceSearch.jsx`): predictive service suggestions (both taxonomies + `/services/detect` keywords) + **Book** button.
- ✅ **Book panel** (`components/BookingPanel.jsx`, full-screen, slides from right) → `components/JobRequestForm.jsx` flow mode: 1 Property type (Residential/Commercial) → 2 Describe your job / Browse providers → 3 Type of quotation = **Post Job only** → opens 2nd full-screen window with job details. `/post-job` page reuses the same form (page mode).
- ✅ **No limits on quotes/bids**: every job posted with mode `bids`; GET /jobs/{id} returns all bids.
- ✅ **Saved properties** (all job-posting roles: customer, landlord, property, facilities): Profile "My properties" card (`MyPropertiesCard`, `PropertyFormDialog`) — main + secondary, name, address, residential/commercial, bedrooms, bathrooms, access notes. API: POST/GET mine/PATCH/DELETE `/api/properties`, POST `/api/properties/{id}/primary`.
- ✅ **Job location picker** (`JobLocationPicker`, `AddressAutocomplete`): pick saved property (main preselected) or search address; "Save to my properties" tick. Jobs store `property_id`, `location_lat/lng`, private `access_notes` (visible only to client, approver, accepted provider).
- ✅ **Address search** `GET /api/address/search` (+ `/api/address/details`): Google Places (New) when `GOOGLE_MAPS_API_KEY` set in backend/.env, otherwise free OpenStreetMap (Photon) NZ search.

## What's Implemented (2026-11 — Touch redesign, invoice sending, service area)
- ✅ **Phone/tablet touch shell (<1024px)**; desktop (≥1024) unchanged. Top bar + bottom nav (3–4 role tabs + **Menu** → left side sheet with full role sidebar). `ViewModeContext` (`compact`, `framed`, `inFrame`).
- ✅ **Desktop "Mobile view"** = real phone preview: device frame with an iframe of the app (true breakpoints) + "Back to desktop".
- ✅ **Side panes** (`components/SidePane.jsx`): Find Providers filters, Client Home "How it works", My Job Posts detail, Track Workers team list. Messages = list → chat with back button on phones.
- ✅ No horizontal overflow on any page for any role at 390/768/820 (iteration_17).
- ✅ **Invoice sending**: `POST /api/jobs/{id}/invoice/send` (linked provider only) saves a versioned copy to `invoices`, posts a chat message, emails the customer via Emergent managed email (`backend/email_service.py`, env EMERGENT_EMAIL_KEY, EMAIL_FROM_NAME). Provider can resend (version+1). Customers see the last sent copy. Demo customer emails are fake → email blocked (non-fatal, shown as "in chat only").
- ✅ **Service area radius**: `service_radius_km` (1–200 or null = no limit, default null) via PATCH /providers/me; card on provider Profile; search hides providers whose radius is less than the customer's distance.
- ✅ Messages conversation search works.

## What's Implemented (2026-06 — Timesheet, nav cleanup, distance filter)
- ✅ **Timesheet module** (`/provider/timesheet`, `pages/provider/Timesheet.jsx`): live start/stop timers (work/travel/materials) + manual entries with km/fuel, GPS auto-geofence mode, browser location captured at start & stop (shown as map links). Job dropdown from `GET /api/timesheets/jobs` (provider's booked/accepted-bid jobs).
- ✅ **Invoice line items**: `GET /api/jobs/{job_id}/invoice` = agreed quote + billable completed timesheet lines (grouped per type/worker/rate) + fuel, subtotal, 15% GST, total. Access: job client, approver, linked provider. Shown on Timesheet (invoice preview) and customer JobDetail (status != open) via `components/JobInvoice.jsx`.
- ✅ **Removed for providers**: Warranty Claims, Trades Board, GPS Devices, Trade Store, News Feed, Forum, Membership.
- ✅ **Removed for all roles**: Marketplace/Shop/Cart (incl. top-bar cart icon), News Feed, Community Forum, Live Map, dead Notifications/Settings cards on /more. Routes removed → redirect to role home.
- ✅ **Find Providers distance filter**: "Distance Away" slider (1–50+ km) from Auckland CBD default or "Use my location"; `GET /api/providers/search` accepts `lat,lng,max_km` and `sort=nearest`, returns `distance_km` shown on cards.
- ✅ demo-login now resets the demo account's role; timesheet entry validation (end>start, numeric fuel → 400).

## What's Implemented (2026-02-08 — Investor-ready polish pass)
- ✅ **Zero-login role picker on landing** (`/app/frontend/src/pages/LandingRoleSelect.jsx`) — visitors pick a role card and are auto-signed in via `demoLogin(role)` behind the scenes; no signup, no password. Copy updated to "Live preview · No signup required" and "Enter the preview as…". The "Log in" link is retained for repeat users.
- ✅ **Fixed Provider `/profile` React crash** (iteration_14 P0) — JSX ternary in `pages/client/Profile.jsx` L62-79 now wraps the array before `.map()`. All 4 stat tiles render for both customer and provider roles.
- ✅ **Fixed N+1 query in `/api/tenancies/mine`** (deployment_agent P0) — batch-fetch tenant+approver users in a single Mongo `$in` query instead of 2 queries per tenancy.
- ✅ **Fixed `.gitignore` deploy blocker** — removed `.env`, `.env.*`, `*.env` entries so `.env` files are committed and picked up by the deployment pipeline.

## What's Implemented (2026-02-08)
- ✅ **One-click Demo Login (2026-02-08)** — six seeded demo accounts (one per role) with a "Try the app instantly" panel on `/login`. Backend `POST /api/auth/demo-login` `{role}` returns the seeded account and sets the auth cookie. Accounts persist so users can save data between demo sessions. Full credentials in `/app/memory/test_credentials.md`.
- ✅ **Saved Pros / Favorite Providers (2026-02-08 P1)** — Customers, landlords, property managers and facilities users can bookmark providers and access them from a dedicated `/saved-providers` page.
  - Backend: `POST /api/saved-providers/{provider_id}` (idempotent), `DELETE /api/saved-providers/{provider_id}`, `GET /api/saved-providers` (returns full provider cards ordered by most-recently-saved). Adds `is_saved` on `GET /api/providers/{id}` and `GET /api/providers/search`. 404 for missing provider, 400 for self-save.
  - Frontend: heart toggle on every provider card in `/find-providers`, `Save Pro` / `Saved` button on `/providers/:id`, new `SavedProviders.jsx` page (empty state + card grid + unsave button). Sidebar link `Saved Pros` added to customer (Explore), landlord/property/facilities (Actions). Provider + Insurance roles intentionally excluded.
  - Tests: `/app/backend/tests/test_saved_providers.py` (13/13 PASS).
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
