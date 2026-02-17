# New Upload Features for airflow-dbt-python

## Summary

Added three new parameters to `DbtBaseOperator` and all its subclasses to provide more flexibility when uploading dbt projects after execution:

1. **`upload_to_different_destination`**: Upload the dbt project to a different location than the original `project_dir`
2. **`upload_specific_artifacts`**: Upload only specific files/artifacts instead of the entire project
3. **`destination_conn_id`**: Specify a different Airflow connection for the upload destination

## Parameters

### `upload_to_different_destination`
- **Type**: `Optional[Union[str, Path]]`
- **Default**: `None`
- **Description**: When set, uploads the dbt project to this destination instead of the original `project_dir`. Works with any supported remote storage (S3, GCS, Git).

### `upload_specific_artifacts`
- **Type**: `Optional[list[Union[str, Path]]]`
- **Default**: `None`
- **Description**: List of specific files/paths to upload, relative to the dbt project root. When set, only these files are uploaded instead of the entire project.

### `destination_conn_id`
- **Type**: `Optional[str]`
- **Default**: `None`
- **Description**: Airflow connection ID to use for the upload destination. If not specified, uses `project_conn_id`. Required when uploading to a different remote storage that needs different credentials.

## Usage Examples

### Example 1: Upload to a Different Destination

```python
from airflow_dbt_python.operators.dbt import DbtRunOperator

dbt_run = DbtRunOperator(
    task_id="dbt_run",
    project_dir="s3://my-bucket/dbt-project",
    upload_dbt_project=True,
    upload_to_different_destination="s3://archive-bucket/dbt-artifacts",
)
```

This will:
1. Download the project from `s3://my-bucket/dbt-project`
2. Run dbt
3. Upload the entire project to `s3://archive-bucket/dbt-artifacts`

### Example 2: Upload Specific Artifacts Only

```python
from airflow_dbt_python.operators.dbt import DbtCompileOperator

dbt_compile = DbtCompileOperator(
    task_id="dbt_compile",
    project_dir="s3://my-bucket/dbt-project",
    upload_dbt_project=True,
    upload_specific_artifacts=[
        "target/manifest.json",
        "target/compiled",
        "dbt_project.yml",
    ],
)
```

This will:
1. Download the project from `s3://my-bucket/dbt-project`
2. Run dbt compile
3. Upload only the specified files back to `s3://my-bucket/dbt-project`

### Example 3: Upload to Different Bucket with Different Credentials

```python
from airflow_dbt_python.operators.dbt import DbtRunOperator

dbt_run = DbtRunOperator(
    task_id="dbt_run",
    project_dir="s3://dev-bucket/dbt-project",
    project_conn_id="dev_s3_connection",
    upload_dbt_project=True,
    upload_to_different_destination="s3://prod-bucket/dbt-artifacts",
    destination_conn_id="prod_s3_connection",
)
```

This will:
1. Download the project from `s3://dev-bucket/dbt-project` using `dev_s3_connection`
2. Run dbt
3. Upload the entire project to `s3://prod-bucket/dbt-artifacts` using `prod_s3_connection`

### Example 4: Combine All Three Parameters

```python
from airflow_dbt_python.operators.dbt import DbtDocsGenerateOperator

dbt_docs = DbtDocsGenerateOperator(
    task_id="dbt_docs",
    project_dir="s3://my-bucket/dbt-project",
    project_conn_id="source_connection",
    upload_dbt_project=True,
    upload_to_different_destination="s3://docs-bucket/latest",
    destination_conn_id="docs_connection",
    upload_specific_artifacts=[
        "target/catalog.json",
        "target/manifest.json",
        "target/index.html",
    ],
)
```

This will:
1. Download the project from `s3://my-bucket/dbt-project` using `source_connection`
2. Generate dbt docs
3. Upload only the documentation files to `s3://docs-bucket/latest` using `docs_connection`

## Implementation Details

### Modified Files

1. **`airflow_dbt_python/operators/dbt.py`**
   - Added two new parameters to `DbtBaseOperator.__init__()`
   - Parameters are inherited by all operator subclasses

2. **`airflow_dbt_python/hooks/dbt.py`**
   - Added parameters to `run_dbt_task()` method
   - Added parameters to `dbt_directory()` context manager
   - Added new method `upload_specific_dbt_artifacts()`
   - Modified upload logic in `dbt_directory()` to handle both parameters

### How It Works

1. When `upload_dbt_project=True`, the hook checks for the new parameters
2. If `upload_to_different_destination` is set, it uses that as the upload destination instead of the original `project_dir`
3. If `upload_specific_artifacts` is set, it calls `upload_specific_dbt_artifacts()` instead of `upload_dbt_project()`
4. The `upload_specific_dbt_artifacts()` method:
   - Iterates through the specified artifacts
   - Checks if each file exists in the temporary directory
   - Uploads each file individually to the destination
   - Logs warnings for missing files

## Use Cases

### 1. Archiving Artifacts
Upload compiled artifacts to a separate archive bucket for auditing:
```python
upload_to_different_destination="s3://audit-bucket/dbt-runs/{{ ds }}"
```

### 2. Documentation Publishing
Upload only documentation files to a web-accessible location:
```python
upload_specific_artifacts=["target/index.html", "target/catalog.json"]
upload_to_different_destination="s3://docs-website/dbt"
```

### 3. Selective Sync
Upload only changed artifacts to reduce transfer time and costs:
```python
upload_specific_artifacts=["target/manifest.json", "target/run_results.json"]
```

### 4. Multi-Environment Deployments
Compile in one environment, deploy artifacts to multiple environments:
```python
# Task 1: Compile
dbt_compile = DbtCompileOperator(
    task_id="compile",
    project_dir="s3://dev-bucket/project",
    upload_dbt_project=True,
    upload_to_different_destination="s3://artifacts-bucket/compiled",
    upload_specific_artifacts=["target/manifest.json", "target/compiled"],
)

# Task 2: Deploy to prod
dbt_deploy = DbtRunOperator(
    task_id="deploy_prod",
    project_dir="s3://artifacts-bucket/compiled",
    upload_to_different_destination="s3://prod-bucket/project",
)
```

## Testing

All functionality is tested in `test_upload_standalone.py`:

```bash
pipenv run python test_upload_standalone.py
```

Tests cover:
- ✓ Operator accepts `upload_to_different_destination` parameter
- ✓ Operator accepts `upload_specific_artifacts` parameter
- ✓ Operator accepts `destination_conn_id` parameter
- ✓ All three parameters work together
- ✓ Upload specific artifacts with existing files
- ✓ Warning logged for missing artifacts

## Backward Compatibility

These changes are fully backward compatible:
- All three parameters default to `None`
- Existing behavior is preserved when parameters are not set
- All existing operators continue to work without modification
- `destination_conn_id` defaults to `project_conn_id` when not specified
