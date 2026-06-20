-- Allow a customer to record the initial status of an order they own.
-- Later status changes remain restricted to admins and bakers.
DROP POLICY IF EXISTS order_status_history_insert_customer
ON public.order_status_history;

CREATE POLICY order_status_history_insert_customer
ON public.order_status_history
FOR INSERT
TO authenticated
WITH CHECK (
    changed_by = auth.uid()
    AND old_status IS NULL
    AND new_status = 'pending'::public.order_status
    AND EXISTS (
        SELECT 1
        FROM public.orders
        WHERE orders.id = order_status_history.order_id
          AND orders.customer_id = auth.uid()
          AND orders.status = 'pending'::public.order_status
    )
);
