# Implementation Plan: Cake Shop AI Web

## Overview

Triển khai hệ thống Web Bán Bánh Kem Tích Hợp AI với kiến trúc ba tầng: Next.js 14 (frontend), FastAPI (backend), Supabase (database + auth + storage), và Claude API (AI chatbot). Các task được sắp xếp theo thứ tự logic từ infrastructure → core features → advanced features → optimization.

## Tasks

- [x] 1. Project setup and infrastructure
  - [x] 1.1 Initialize Next.js 14 frontend project
    - Create Next.js 14 project with App Router, TypeScript, Tailwind CSS
    - Configure design system: colors (pink pastel #E8837A, cream #FDF6EE, mocha #5C3D2E), fonts (Playfair Display headings, DM Sans body)
    - Set up project structure: `app/`, `components/`, `lib/`, `types/`, `hooks/`
    - Configure ESLint, Prettier, and path aliases
    - _Requirements: 9.3, 9.4_

  - [x] 1.2 Initialize FastAPI backend project
    - Create FastAPI project with directory structure: `app/`, `app/api/`, `app/services/`, `app/models/`, `app/schemas/`, `app/core/`
    - Configure CORS, environment variables, and logging (structured JSON with request_id)
    - Set up Dockerfile and docker-compose for local development
    - Install dependencies: fastapi, uvicorn, supabase-py, anthropic, python-jose, pydantic
    - _Requirements: 9.2_

  - [x] 1.3 Set up Supabase project and database schema
    - Create Supabase project and configure connection
    - Write SQL migrations for all tables: users, products, product_images, orders, order_items, cake_customizations, order_status_history, chat_sessions, chat_messages, reviews
    - Add constraints: email UNIQUE, phone CHECK (10 digits), base_price CHECK (1000-999999999), rating CHECK (1-5), review UNIQUE(product_id, customer_id, order_id)
    - Configure Row Level Security (RLS) policies
    - Set up Supabase Storage bucket for product images
    - _Requirements: 5.1, 6.1, 10.6_

  - [x] 1.4 Configure deployment pipeline
    - Set up Vercel project for Next.js frontend deployment
    - Configure environment variables for both frontend and backend
    - Set up Docker deployment configuration for FastAPI backend
    - _Requirements: 9.2_

- [x] 2. Authentication system (Supabase Auth)
  - [x] 2.1 Implement backend auth service
    - Create auth endpoints: POST /api/v1/auth/register, POST /api/v1/auth/login, POST /api/v1/auth/oauth/google, POST /api/v1/auth/refresh, POST /api/v1/auth/logout
    - Implement registration validation: email (≤254 chars, unique), password (8-128 chars, uppercase+lowercase+digit), full_name (≤100 chars), phone (10-digit Vietnamese format)
    - Implement login rate limiting: max 5 failed attempts per 15-minute window per email, 15-minute lockout
    - Implement JWT token handling with 1-hour expiration and auto-refresh when <5 minutes remain
    - Assign default "customer" role on registration
    - _Requirements: 5.1, 5.2, 5.4, 5.6, 5.8, 5.9, 5.10_

  - [ ]* 2.2 Write property tests for registration validation (Hypothesis)
    - **Property 13: Registration validation**
    - **Validates: Requirements 5.1, 5.8**

  - [ ]* 2.3 Write property tests for login rate limiting (Hypothesis)
    - **Property 14: Login rate limiting**
    - **Validates: Requirements 5.4, 5.9**

  - [x] 2.4 Implement role-based access control middleware
    - Create RBAC middleware for FastAPI with three roles: Customer, Admin, Baker
    - Implement endpoint-level permission checks
    - Return 403 for unauthorized access attempts
    - Handle expired/invalid JWT: return 401 and clear session
    - _Requirements: 5.5, 5.7_

  - [ ]* 2.5 Write property tests for RBAC (Hypothesis)
    - **Property 15: Role-based access control**
    - **Validates: Requirements 5.5**

  - [x] 2.6 Implement frontend auth pages
    - Create login page with email/password form and Google OAuth button
    - Create registration page with validation (inline error messages)
    - Implement JWT storage in localStorage with auto-refresh logic
    - Implement auth state management and protected route wrapper
    - Handle redirect after login (preserve previous page URL)
    - Handle 401 responses: redirect to login, clear local session
    - _Requirements: 5.2, 5.3, 5.4, 5.6, 5.7, 5.8_

- [x] 3. Checkpoint - Auth system verification
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Product catalog (backend + frontend)
  - [x] 4.1 Implement catalog backend service
    - Create GET /api/v1/products endpoint with pagination (20/page), category filter, sorting (newest first)
    - Create GET /api/v1/products/{id} endpoint with full detail (description, sizes, flavors, price breakdown)
    - Implement product filtering: exclude inactive products from customer queries
    - Return empty state response when no products match criteria
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.7_

  - [ ]* 4.2 Write property tests for catalog filtering (Hypothesis)
    - **Property 1: Category filter returns only matching products**
    - **Property 2: Inactive products never appear in customer catalog**
    - **Validates: Requirements 1.2, 1.5, 6.6**

  - [x] 4.3 Implement product catalog frontend
    - Create ProductCatalog page at `/products` with grid layout, category tabs, pagination
    - Create ProductDetail page at `/products/[id]` with image gallery, size selector, flavor options, price breakdown
    - Implement skeleton loading placeholders during data fetch
    - Implement placeholder image for failed image loads
    - Display average rating and review count on product cards
    - Implement responsive layout (320px to 1920px)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6, 1.7, 1.8, 9.1, 10.3_

  - [x] 4.4 Implement admin product management backend
    - Create POST /api/v1/admin/products (create product with validation: name 1-200 chars, description 1-2000 chars, base_price 1000-999999999 VND, sizes 1-10 options)
    - Create PUT /api/v1/admin/products/{id} (update product)
    - Create PATCH /api/v1/admin/products/{id}/status (toggle active status)
    - Create POST /api/v1/admin/products/{id}/images (upload with validation: JPEG/PNG/WebP, ≤5MB, resize to max 1200×1200)
    - Trigger catalog revalidation within 5 seconds of product update
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 4.5 Write property tests for product management validation (Hypothesis)
    - **Property 17: Product management validation**
    - **Property 18: Image upload validation**
    - **Validates: Requirements 6.1, 6.2, 6.4, 6.5**

  - [x] 4.6 Implement admin product management frontend
    - Create AdminProducts page at `/admin/products` with paginated list (20/page), search by name, filter by category/status
    - Create product create/edit form with validation and image upload (drag-and-drop, preview)
    - Implement product activation/deactivation toggle
    - Display validation errors inline on form fields
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [x] 5. Checkpoint - Catalog system verification
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Cake Builder (SVG interactive)
  - [x] 6.1 Implement Cake Builder SVG component
    - Create interactive SVG cake model with three Customization_Zones (top, body, border)
    - Implement zone highlighting on hover/tap
    - Implement zone click handler to show customization options panel within 100ms
    - Implement real-time SVG updates when options are selected (< 100ms)
    - Support touch interactions on mobile (minimum viewport 320px, 44×44px touch targets)
    - _Requirements: 2.1, 2.2, 2.3, 2.11_

  - [x] 6.2 Implement Cake Builder state management and price calculator
    - Create CakeDesign state interface (size, flavor, cream_type, cream_color, topping_type, special_notes, zones)
    - Implement PriceCalculator: basePrice (by size) + toppingCost + decorationCost = totalPrice
    - Update displayed price within 200ms of any customization change
    - Implement size selector with price update
    - _Requirements: 2.4, 2.5_

  - [ ]* 6.3 Write property tests for price calculation (fast-check)
    - **Property 3: Price calculation correctness**
    - **Validates: Requirements 2.4, 2.5**

  - [x] 6.4 Implement Cake Builder validation and completion flow
    - Validate mandatory fields (size, flavor, cream_type, cream_color) on completion
    - Display error messages for missing mandatory fields
    - Store customization data as JSON on successful completion
    - Generate visual preview image of final customized cake
    - _Requirements: 2.6, 2.7, 2.8_

  - [ ]* 6.5 Write property tests for cake customization validation (fast-check)
    - **Property 4: Cake customization validation completeness**
    - **Validates: Requirements 2.6, 2.7**

  - [x] 6.6 Implement Cake Builder localStorage persistence
    - Auto-save design state to localStorage every 5 seconds and on page blur/visibility change
    - Recover design state from localStorage on next visit
    - Display warning if localStorage is unavailable or full
    - Clear localStorage on design completion
    - _Requirements: 2.9, 2.10_

  - [ ]* 6.7 Write property tests for localStorage round-trip (fast-check)
    - **Property 5: Cake design localStorage round-trip**
    - **Validates: Requirements 2.9**

- [x] 7. Checkpoint - Cake Builder verification
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. AI Chatbot (Claude API + RAG)
  - [x] 8.1 Implement RAG pipeline and chat service backend
    - Create POST /api/v1/chat/sessions (create chat session)
    - Create POST /api/v1/chat/sessions/{id}/messages (send message, SSE response)
    - Create GET /api/v1/chat/sessions/{id}/history (get chat history)
    - Implement RAG context builder: query product catalog, filter by relevance (occasion, budget, size), format as context
    - Implement system prompt with Vietnamese language, product catalog context, and conversation rules
    - Maintain conversation context: last 20 messages in chronological order
    - Handle Claude API errors: return 503 with fallback message
    - _Requirements: 3.1, 3.2, 3.3, 3.6, 3.7, 3.8_

  - [ ]* 8.2 Write property tests for RAG context (Hypothesis)
    - **Property 6: RAG context contains accurate product pricing**
    - **Property 9: Chat context window bounded at 20 messages**
    - **Validates: Requirements 3.3, 3.6**

  - [x] 8.3 Implement AI recommendation and summary logic
    - Implement recommendation extraction: 2-5 cake options with product name, price, reasoning
    - Implement AI_Summary generation: structured format with size, flavor, decorations, pickup_date, total_price
    - Handle ambiguous messages: ask follow-up questions for missing info (occasion, size, budget)
    - Handle no-match scenario: suggest closest alternatives or prompt criteria adjustment
    - _Requirements: 3.4, 3.5, 3.9, 3.10_

  - [ ]* 8.4 Write property tests for AI response parsing (Hypothesis)
    - **Property 7: AI response parser extracts valid recommendations**
    - **Property 8: AI_Summary contains all required fields**
    - **Validates: Requirements 3.4, 3.5**

  - [x] 8.5 Implement AI Chat Widget frontend
    - Create floating ChatWidget component (available on all pages)
    - Implement chat UI: message bubbles, typing indicator, SSE streaming display
    - Display greeting message and prompt on open
    - Display product recommendations with clickable links
    - Display error message when AI service unavailable with shop phone number
    - Implement responsive design for mobile viewports
    - _Requirements: 3.1, 3.2, 3.7, 3.8, 9.1_

- [x] 9. Checkpoint - AI Chatbot verification
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Order management
  - [ ] 10.1 Implement order service backend
    - Create POST /api/v1/orders (create order with status "pending")
    - Validate required fields: full_name, phone, pickup_date, at least one product
    - Implement pickup date validation: ≥24h for standard, ≥48h for 2-tier, ≤30 days advance
    - Include customization_json and AI_Summary in order record when from Cake Builder
    - Create GET /api/v1/orders (customer order history, paginated 10/page, sorted by date desc)
    - Create GET /api/v1/orders/{id} (order detail)
    - Redirect unauthenticated users to login, preserve cart contents
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6, 4.7, 4.8_

  - [ ]* 10.2 Write property tests for order validation (Hypothesis)
    - **Property 10: Order creation validation**
    - **Property 11: Pickup date validation**
    - **Property 12: Order preserves Cake Builder data**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.7, 4.8**

  - [ ] 10.3 Implement order status management backend
    - Create PATCH /api/v1/orders/{id}/status (Admin/Baker status update)
    - Implement state machine: pending→confirmed→in_production→ready→delivered
    - Validate transitions: reject invalid status changes with valid next statuses
    - Record status change with timestamp and user ID in order_status_history
    - Enforce role permissions: Admin (pending→confirmed, ready→delivered), Baker (confirmed→in_production, in_production→ready)
    - _Requirements: 7.2, 7.5, 8.2, 8.3_

  - [ ]* 10.4 Write property tests for order status state machine (Hypothesis)
    - **Property 16: Order status state machine**
    - **Validates: Requirements 7.2, 7.5, 8.2, 8.3**

  - [ ] 10.5 Implement order frontend (Customer)
    - Create OrderForm page at `/checkout` with product summary, pickup date picker, customer info form
    - Implement date picker with validation (min 24h/48h, max 30 days)
    - Display order confirmation with order ID, total price, pickup date, item summary
    - Create OrderHistory page at `/orders` with pagination (10/page), status badges, pickup dates
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6, 4.7_

- [ ] 11. Admin dashboard
  - [ ] 11.1 Implement admin order management backend
    - Create GET /api/v1/admin/orders (all orders, paginated 20/page, sorted newest first)
    - Implement filters: status, date range, customer name (partial match, min 2 chars)
    - Return complete order detail: customization details, AI_Summary, customer contact, status history
    - Return empty state when no orders match filters
    - _Requirements: 7.1, 7.3, 7.4_

  - [ ]* 11.2 Write property tests for order filtering (Hypothesis)
    - **Property 19: Order filter correctness**
    - **Validates: Requirements 7.4**

  - [ ] 11.3 Implement admin order management frontend
    - Create AdminOrders page at `/admin/orders` with paginated list, status/date/name filters
    - Create order detail view with customization details, AI_Summary, customer info, status history
    - Implement status update buttons with valid transition options only
    - Display confirmation on successful status update
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 12. Baker dashboard
  - [ ] 12.1 Implement baker order service backend
    - Create GET /api/v1/baker/orders (orders with status "confirmed" or "in_production", sorted by pickup_date ascending)
    - Create PATCH /api/v1/baker/orders/{id}/notes (add/edit baker_notes, max 500 chars)
    - Validate baker status transitions: confirmed→in_production, in_production→ready
    - _Requirements: 8.1, 8.2, 8.3, 8.5_

  - [ ]* 12.2 Write property tests for baker order visibility and notes (Hypothesis)
    - **Property 20: Baker order visibility**
    - **Property 21: Baker notes length validation**
    - **Validates: Requirements 8.1, 8.5**

  - [ ] 12.3 Implement baker dashboard frontend
    - Create BakerDashboard page at `/baker/orders` with order list (confirmed + in_production)
    - Display order detail: customization details, AI_Summary, baker_notes, pickup date
    - Implement status update buttons (only valid next status)
    - Implement baker_notes text area (max 500 chars) with save functionality
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 13. Checkpoint - Order management verification
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Reviews system
  - [ ] 14.1 Implement review service backend
    - Create POST /api/v1/reviews (submit review: rating 1-5, comment max 1000 chars)
    - Validate review eligibility: order status "delivered" AND within last 30 days
    - Enforce uniqueness: one review per (product_id, customer_id, order_id)
    - Create GET /api/v1/products/{id}/reviews (paginated 10/page, sorted newest first)
    - Calculate and return average rating (rounded to 1 decimal) and total review count
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [ ]* 14.2 Write property tests for reviews (Hypothesis)
    - **Property 22: Review eligibility**
    - **Property 23: Review uniqueness constraint**
    - **Property 24: Average rating calculation**
    - **Validates: Requirements 10.1, 10.3, 10.4, 10.6**

  - [ ] 14.3 Implement review frontend
    - Add review form on order history page (for delivered orders within 30 days)
    - Display star rating selector (1-5) and comment textarea (max 1000 chars)
    - Display reviews on product detail page: paginated (10/page), customer name, rating, comment
    - Display average rating and review count on product cards
    - Show error messages for ineligible or duplicate reviews
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

- [ ] 15. Responsive design and performance optimization
  - [ ] 15.1 Implement responsive design system
    - Ensure all pages render correctly from 320px to 1920px (mobile-first approach)
    - Ensure minimum 44×44px touch targets on viewports below 768px
    - Eliminate horizontal scrolling on all viewport widths
    - Implement image placeholders matching final dimensions (CLS < 0.1)
    - _Requirements: 9.1, 9.6, 9.7_

  - [ ] 15.2 Implement performance optimizations
    - Configure Next.js Image component with proper sizing and lazy loading
    - Implement ISR caching for product catalog (60s TTL) and product detail pages
    - Optimize bundle size: code splitting, dynamic imports for Cake Builder and Chat Widget
    - Ensure Lighthouse Performance score ≥ 80 on mobile
    - Verify cross-browser compatibility (Chrome, Safari, Firefox, Edge - latest 2 versions)
    - _Requirements: 9.2, 9.5, 9.6_

- [ ] 16. Final checkpoint - Full system verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at logical boundaries
- Property tests validate universal correctness properties from the design document
- Frontend uses TypeScript with fast-check for property-based tests
- Backend uses Python with Hypothesis for property-based tests
- Design system colors and fonts should be configured once in task 1.1 and reused throughout
- Supabase Auth handles OAuth and JWT management; backend validates tokens
- SSE (Server-Sent Events) used for AI chat streaming responses

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["1.4", "2.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "2.6"] },
    { "id": 3, "tasks": ["2.5", "4.1", "4.4"] },
    { "id": 4, "tasks": ["4.2", "4.3", "4.5", "4.6"] },
    { "id": 5, "tasks": ["6.1", "6.2"] },
    { "id": 6, "tasks": ["6.3", "6.4", "6.6"] },
    { "id": 7, "tasks": ["6.5", "6.7", "8.1"] },
    { "id": 8, "tasks": ["8.2", "8.3", "8.5"] },
    { "id": 9, "tasks": ["8.4", "10.1"] },
    { "id": 10, "tasks": ["10.2", "10.3", "10.5"] },
    { "id": 11, "tasks": ["10.4", "11.1"] },
    { "id": 12, "tasks": ["11.2", "11.3", "12.1"] },
    { "id": 13, "tasks": ["12.2", "12.3"] },
    { "id": 14, "tasks": ["14.1"] },
    { "id": 15, "tasks": ["14.2", "14.3"] },
    { "id": 16, "tasks": ["15.1", "15.2"] }
  ]
}
```
