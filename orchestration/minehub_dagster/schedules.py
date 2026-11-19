
from dagster import AssetSelection, ScheduleDefinition, define_asset_job

dq_job = define_asset_job("data_quality", selection=AssetSelection.groups("quality"))
hourly_dbt_job = define_asset_job("hourly_dbt", selection=AssetSelection.groups("warehouse"))

dq_schedule = ScheduleDefinition(job=dq_job, cron_schedule="*/15 * * * *",
execution_timezone="America/Los_Angeles")
# keep marts fresh for dashboards between shift changes
hourly_dbt_schedule = ScheduleDefinition(job=hourly_dbt_job, cron_schedule="7 * * * *",
                                         execution_timezone="America/Los_Angeles")