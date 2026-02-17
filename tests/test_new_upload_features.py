"""Tests for upload_to_different_destination, upload_specific_artifacts, and destination_conn_id."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from airflow_dbt_python.hooks.dbt import DbtHook
from airflow_dbt_python.operators.dbt import DbtRunOperator
from airflow_dbt_python.utils.url import URL


@pytest.fixture(scope="module")
def database():
    """Override database fixture - not needed for these tests."""
    return None


@pytest.fixture(scope="module")
def postgresql_proc():
    """Override postgresql_proc fixture - not needed for these tests."""
    return None


def test_operator_accepts_upload_to_different_destination():
    """Test that DbtRunOperator accepts upload_to_different_destination parameter."""
    operator = DbtRunOperator(
        task_id="test_task",
        project_dir="/tmp/project",
        upload_dbt_project=True,
        upload_to_different_destination="s3://different-bucket/path",
    )
    assert operator.upload_to_different_destination == "s3://different-bucket/path"


def test_operator_accepts_upload_specific_artifacts():
    """Test that DbtRunOperator accepts upload_specific_artifacts parameter."""
    operator = DbtRunOperator(
        task_id="test_task",
        project_dir="/tmp/project",
        upload_dbt_project=True,
        upload_specific_artifacts=["target/manifest.json", "target/run_results.json"],
    )
    assert operator.upload_specific_artifacts == [
        "target/manifest.json",
        "target/run_results.json",
    ]


def test_operator_accepts_destination_conn_id():
    """Test that DbtRunOperator accepts destination_conn_id parameter."""
    operator = DbtRunOperator(
        task_id="test_task",
        project_dir="s3://original-bucket/project",
        project_conn_id="source_s3_conn",
        upload_dbt_project=True,
        upload_to_different_destination="s3://different-bucket/artifacts",
        destination_conn_id="dest_s3_conn",
    )
    
    assert operator.project_conn_id == "source_s3_conn"
    assert operator.destination_conn_id == "dest_s3_conn"
    assert operator.upload_to_different_destination == "s3://different-bucket/artifacts"


def test_both_parameters_work_together():
    """Test using both upload_to_different_destination and upload_specific_artifacts."""
    operator = DbtRunOperator(
        task_id="test_task",
        project_dir="s3://original-bucket/project",
        upload_dbt_project=True,
        upload_to_different_destination="s3://new-bucket/artifacts",
        upload_specific_artifacts=["target/manifest.json"],
    )
    
    assert operator.upload_to_different_destination == "s3://new-bucket/artifacts"
    assert operator.upload_specific_artifacts == ["target/manifest.json"]
    assert operator.upload_dbt_project is True


def test_all_three_parameters_work_together():
    """Test using all three new parameters together."""
    operator = DbtRunOperator(
        task_id="test_task",
        project_dir="s3://original-bucket/project",
        project_conn_id="source_conn",
        upload_dbt_project=True,
        upload_to_different_destination="s3://new-bucket/artifacts",
        upload_specific_artifacts=["target/manifest.json"],
        destination_conn_id="dest_conn",
    )
    
    assert operator.upload_to_different_destination == "s3://new-bucket/artifacts"
    assert operator.upload_specific_artifacts == ["target/manifest.json"]
    assert operator.destination_conn_id == "dest_conn"
    assert operator.upload_dbt_project is True


def test_upload_specific_artifacts_with_existing_files():
    """Test uploading specific artifacts that exist."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create test files
        project_path = Path(tmp_dir)
        target_dir = project_path / "target"
        target_dir.mkdir()
        
        manifest = target_dir / "manifest.json"
        manifest.write_text('{"test": "data"}')
        
        dbt_project = project_path / "dbt_project.yml"
        dbt_project.write_text("name: test")

        # Mock the fs_hook
        mock_fs_hook = Mock()
        
        hook = DbtHook()
        with patch.object(hook, "get_fs_hook", return_value=mock_fs_hook):
            hook.upload_specific_dbt_artifacts(
                project_dir=tmp_dir,
                destination="s3://bucket/path",
                artifacts=["target/manifest.json", "dbt_project.yml"],
            )

        # Verify _upload was called for each artifact
        assert mock_fs_hook._upload.call_count == 2


def test_upload_specific_artifacts_warns_on_missing_file():
    """Test that missing artifacts generate warnings."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        mock_fs_hook = Mock()
        
        hook = DbtHook()
        # Create a mock logger
        mock_logger = Mock()
        hook._log = mock_logger
        
        with patch.object(hook, "get_fs_hook", return_value=mock_fs_hook):
            hook.upload_specific_dbt_artifacts(
                project_dir=tmp_dir,
                destination="s3://bucket/path",
                artifacts=["nonexistent.json"],
            )

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        assert "not found" in mock_logger.warning.call_args[0][0]
