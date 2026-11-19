
from dagster import Definitions

from orchestration.minehub_dagster.assets.batch_assays import raw_assays
from orchestration.minehub_dagster.assets.batch_plan import raw_mine_plan
from orchestration.minehub_dagster.assets.batch_work_orders import raw_work_orders
from orchestration.minehub_dagster.assets.data_quality import data_quality_results
from orchestration.minehub_dagster.assets.dbt_assets import minehub_dbt
from orchestration.minehub_dagster.assets.shift_report import shift_report
from orchestration.minehub_dagster.resources import PostgresResource, RedisResource, dbt_resource
from orchestration.minehub_dagster.schedules import dq_job, dq_schedule, hourly_dbt_job, hourly_dbt_schedule
from orchestration.minehub_dagster.sensors.new_plan_file import batch_load_job, new_drop_file
from orchestration.minehub_dagster.sensors.shift_change import end_of_shift_job, shift_closed

defs = Definitions(
    assets=[raw_mine_plan, raw_work_orders, raw_assays, minehub_dbt, data_quality_results, shift_report],
    jobs=[batch_load_job, end_of_shift_job, dq_job, hourly_dbt_job],
    sensors=[new_drop_file, shift_closed],
    schedules=[dq_schedule, hourly_dbt_schedule],
    resources={"postgres": PostgresResource(), "redis": RedisResource(), "dbt": dbt_resource},
)