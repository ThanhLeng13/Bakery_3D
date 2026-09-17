-- Add the sales staff role while preserving the existing role values.
-- Run this migration in Supabase SQL Editor before assigning a user as staff.
--
-- The role column may be either a PostgreSQL enum (the current production
-- schema) or a text column protected by a CHECK constraint (older schemas).
-- Extend the enum itself when present; an enum already provides the allowed-
-- values constraint, so it must not be compared with an unknown 'staff' label.

DO $$
DECLARE
    role_constraint RECORD;
    role_type_schema TEXT;
    role_type_name TEXT;
    role_type_kind "char";
BEGIN
    SELECT type_namespace.nspname, role_type.typname, role_type.typtype
    INTO role_type_schema, role_type_name, role_type_kind
    FROM pg_attribute role_column
    JOIN pg_type role_type
      ON role_type.oid = role_column.atttypid
    JOIN pg_namespace type_namespace
      ON type_namespace.oid = role_type.typnamespace
    WHERE role_column.attrelid = 'public.users'::regclass
      AND role_column.attname = 'role'
      AND NOT role_column.attisdropped;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Column public.users.role does not exist';
    END IF;

    -- A failed version of this migration may have left the old constraint in
    -- place, so remove role-specific CHECK constraints in either schema form.
    --
    -- Identified by constraint key rather than by matching the constraint
    -- definition text: a text match on '%role%' would also catch unrelated
    -- CHECK constraints that merely mention the word (for example one on
    -- another column, or a constraint whose name contains "role"), and would
    -- drop them. conkey lists the columns a CHECK constraint actually covers,
    -- so requiring it to be exactly the users.role column targets only the
    -- constraint this migration is responsible for.
    FOR role_constraint IN
        SELECT con.conname
        FROM pg_constraint con
        WHERE con.conrelid = 'public.users'::regclass
          AND con.contype = 'c'
          AND con.conkey IS NOT NULL
          AND array_length(con.conkey, 1) = 1
          AND con.conkey[1] = (
              SELECT att.attnum
              FROM pg_attribute att
              WHERE att.attrelid = 'public.users'::regclass
                AND att.attname = 'role'
                AND NOT att.attisdropped
          )
    LOOP
        EXECUTE format(
            'ALTER TABLE public.users DROP CONSTRAINT %I',
            role_constraint.conname
        );
    END LOOP;

    IF role_type_kind = 'e' THEN
        EXECUTE format(
            'ALTER TYPE %I.%I ADD VALUE IF NOT EXISTS %L',
            role_type_schema,
            role_type_name,
            'staff'
        );
    ELSE
        ALTER TABLE public.users
            ADD CONSTRAINT users_role_check
            CHECK (role IN ('customer', 'staff', 'baker', 'admin'));
    END IF;
END $$;

COMMENT ON COLUMN public.users.role IS
    'customer: storefront; staff: sales counter; baker: production; admin: management';
