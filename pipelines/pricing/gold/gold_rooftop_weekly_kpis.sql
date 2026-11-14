CREATE OR REFRESH MATERIALIZED VIEW gold_rooftop_weekly_kpis
COMMENT "Gold. Weekly KPIs per rooftop: units on hand at week end, aged 45+/90+ units and share, retail units sold, average front gross, and floor-plan + lot carrying cost burned that week."
TBLPROPERTIES ("quality" = "gold")
AS WITH weeks AS (
  SELECT explode(sequence(DATE '2025-05-18', DATE '${as_of_date}', INTERVAL 7 DAY)) AS week_end)
SELECT w.week_end, s.rooftop_id, s.rooftop_name,
       count_if(s.acquisition_date <= w.week_end AND (s.disposed_date IS NULL OR s.disposed_date > w.week_end)) AS units_on_hand,
       count_if(s.acquisition_date <= w.week_end AND (s.disposed_date IS NULL OR s.disposed_date > w.week_end)
                AND datediff(w.week_end, s.acquisition_date) >= 45) AS units_aged_45_plus,
       count_if(s.acquisition_date <= w.week_end AND (s.disposed_date IS NULL OR s.disposed_date > w.week_end)
                AND datediff(w.week_end, s.acquisition_date) >= 90) AS units_aged_90_plus,
       count_if(s.status = 'retail' AND s.disposed_date BETWEEN date_sub(w.week_end, 6) AND w.week_end) AS retail_units_sold,
       round(avg(CASE WHEN s.status = 'retail' AND s.disposed_date BETWEEN date_sub(w.week_end, 6) AND w.week_end THEN s.front_gross END), 0) AS avg_front_gross,
       -- charge only the days each unit was actually on the lot inside this week
       round(sum(greatest(0, datediff(least(w.week_end, coalesce(date_sub(s.disposed_date, 1), w.week_end)),
                                       greatest(date_sub(w.week_end, 6), s.acquisition_date)) + 1)
                 * (s.daily_floorplan_interest + s.lot_cost_per_day)), 0) AS carrying_cost_week
FROM weeks w CROSS JOIN gold_vehicle_status s
GROUP BY ALL;
