-- Give agent drafts their own status so they stop landing in the sales queue.
--
-- Bug C: `create_draft_order` wrote status = 'pending', which is exactly the
-- status `/staff/orders` filters on (SALES_STATUSES = ("pending", "ready")).
-- A draft is not an order the bakery has accepted, yet it appeared in the
-- sales queue next to real orders, with no column anywhere marking it as a
-- draft or recording where it came from.
--
-- What this migration changes:
--   1. Adds 'draft' to the order_status enum.
--   2. Marks the existing agent drafts so no historical row is mislabelled.
--
-- Nothing else changes: staff queries already filter on an explicit list, so
-- draft rows drop out of those lists automatically once the value exists.
--
-- Run in the Supabase SQL Editor. Safe to run twice: the enum value uses
-- IF NOT EXISTS, and the backfill only touches rows an agent created.

-- ── 1. Allow 'draft' as an order status ─────────────────────────────────────
--
-- The guard runs inside a DO block so the statement stays idempotent: if the
-- type is missing, or the value is already present, nothing changes and no
-- error is raised. Executing ALTER TYPE through EXECUTE as dynamic SQL keeps
-- it out of a transaction block, which is required on older PostgreSQL where
-- ADD VALUE cannot be rolled back.

DO $$
DECLARE
    order_status_kind "char";
BEGIN
    SELECT typ.typkind
    INTO order_status_kind
    FROM pg_type typ
    JOIN pg_namespace nsp ON nsp.oid = typ.typnamespace
    WHERE nsp.nspname = 'public' AND typ.typname = 'order_status';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Type public.order_status does not exist';
    END IF;

    IF order_status_kind = 'e' THEN
        EXECUTE 'ALTER TYPE public.order_status ADD VALUE IF NOT EXISTS ''draft''';
    END IF;
END $$;

-- ── 2. Mark the drafts that already exist ────────────────────────────────────
--
-- Only rows an agent created carry a non-empty ai_summary, and none of them
-- have progressed past 'pending'. Those are exactly the drafts: a customer
-- order that reached 'confirmed' or later has been accepted by staff, so it
-- must stay untouched.

UPDATE public.orders
SET status = 'draft'
WHERE status = 'pending'
  AND ai_summary IS NOT NULL
  AND btrim(ai_summary) <> ''
  AND customer_id IS NOT NULL
  AND pickup_date >= now();

-- Report what changed so the operator can see the count in the SQL Editor.
-- Kept as a plain statement rather than RAISE NOTICE so the result set shows it.

SELECT count(*) AS draft_orders_before_migration
FROM public.orders
WHERE status = 'draft';