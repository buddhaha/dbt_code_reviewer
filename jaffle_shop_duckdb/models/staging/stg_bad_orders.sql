-- A deliberately bad staging model for demo purposes

SELECT *
FROM raw.jaffle_shop.orders
LEFT JOIN raw.jaffle_shop.payments p
    ON orders.id = p.order_id
WHERE status = 'completed'
ORDER BY orders.order_date DESC
