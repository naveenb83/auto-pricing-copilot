-- What the CURRENT user can see through the ABAC policies (run under different group memberships).
USE CATALOG serverless_stable_69fppe_catalog;
USE SCHEMA piag_pricing;
SELECT current_user() AS user_name,
       is_member('piag_margin_viewers') AS margin_viewer, is_member('piag_crm_admins') AS crm_admin,
       is_member('piag_group_leadership') AS leadership, is_member('piag_rooftop_R03') AS rooftop_r03;
SELECT count(*) AS vehicle_rows_visible, count(DISTINCT rooftop_id) AS rooftops_visible,
       count(unit_cost) AS unit_cost_values_visible, round(avg(front_gross), 0) AS avg_front_gross_visible
FROM gold_vehicle_status;
SELECT rooftop_id, count(*) AS sales, round(sum(total_gross), 0) AS total_gross FROM gold_sales_enriched GROUP BY 1 ORDER BY 1;
SELECT customer_id, first_name, last_name, email, phone, segment FROM silver_customers ORDER BY customer_id LIMIT 3;
