"""dbt models exposed as Dagster assets (group: warehouse)."""

import json
from pathlib import Path

from dagster import AssetExecutionContext
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, dbt_assets

DBT_PROJECT_DIR = Path(__file__).resolve().parents[3] / "warehouse" / "dbt"
MANIFEST_PATH = DBT_PROJECT_DIR / "target" / "manifest.json"

_STUB_MANIFEST = {
    "metadata": {"dbt_schema_version": "https://schemas.getdbt.com/dbt/manifest/v12.json"},
    "nodes": {},
    "sources": {},
    "macros": {},
    "parent_map": {},
    "child_map": {},
    "group_map": {},
    "disabled": {},
    "exposures": {},
    "metrics": {},
    "selectors": {},
    "docs": {},
    "files": {},
}


class WarehouseDbtTranslator(DagsterDbtTranslator):
    def get_group_name(self, dbt_resource_props: dict) -> str:  # type: ignore[override]
        return "warehouse"


def _write_stub_manifest() -> Path:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(_STUB_MANIFEST), encoding="utf-8")
    return MANIFEST_PATH


def _ensure_manifest() -> Path:
    """Prefer existing manifest; parse via DbtProject/CLI; stub only if parse unavailable."""
    if MANIFEST_PATH.exists():
        return MANIFEST_PATH
    try:
        from dagster_dbt import DbtProject

        project = DbtProject(project_dir=DBT_PROJECT_DIR)
        project.prepare_if_dev()
        path = Path(project.manifest_path)
        if path.exists():
            return path
    except Exception:
        pass
    try:
        DbtCliResource(project_dir=str(DBT_PROJECT_DIR), profiles_dir=str(DBT_PROJECT_DIR)).cli(
            ["parse"]
        ).wait()
        if MANIFEST_PATH.exists():
            return MANIFEST_PATH
    except Exception:
        pass
    return _write_stub_manifest()


_manifest_path = _ensure_manifest()

_decorator_kwargs: dict = {
    "manifest": _manifest_path,
    "dagster_dbt_translator": WarehouseDbtTranslator(),
}
try:
    from dagster_dbt import DbtProject

    _decorator_kwargs["project"] = DbtProject(project_dir=DBT_PROJECT_DIR)
except Exception:  # pragma: no cover
    pass


@dbt_assets(**_decorator_kwargs)
def minehub_dbt(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()
