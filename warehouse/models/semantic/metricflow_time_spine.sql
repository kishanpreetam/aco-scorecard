-- Daily calendar that MetricFlow joins to for time grouping. Covers the first Shared Savings
-- Program start date (April 2012) through the end of 2026.
select cast(d as date) as date_day
from range(date '2012-01-01', date '2027-01-01', interval 1 day) as t(d)
