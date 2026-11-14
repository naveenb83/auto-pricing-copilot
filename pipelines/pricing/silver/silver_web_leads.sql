CREATE OR REFRESH MATERIALIZED VIEW silver_web_leads (
  CONSTRAINT vin_present EXPECT (vin IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT funnel_consistent EXPECT (test_drives <= leads AND leads <= vdp_views)
)
COMMENT "Silver. Weekly website demand per vehicle: detail-page views, leads, test drives."
TBLPROPERTIES ("quality" = "silver")
AS SELECT vin, week_start, vdp_views, leads, test_drives, days_listed
FROM bronze_web_leads
QUALIFY row_number() OVER (PARTITION BY vin, week_start ORDER BY ingested_at) = 1;
