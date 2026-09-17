"""Unit tests for LabelService — label creation, updates, deduplication."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.models import Label
from app.services.label_service import LabelService


def _make_label(workspace_id=None) -> Label:
    label = MagicMock(spec=Label)
    label.id = uuid4()
    label.workspace_id = workspace_id or uuid4()
    label.name = "Bug"
    label.color = "#ef4444"
    return label


def _make_service(
    label: Label | None = None,
    existing_by_name: Label | None = None,
) -> LabelService:
    label_repo = MagicMock()
    label_repo.get_by_id = AsyncMock(return_value=label)
    label_repo.get_by_workspace_and_name = AsyncMock(return_value=existing_by_name)
    label_repo.list_for_workspace = AsyncMock(return_value=([label] if label else []))
    label_repo.delete = AsyncMock()
    label_repo.session = MagicMock()
    label_repo.session.add = MagicMock()
    label_repo.session.flush = AsyncMock()
    label_repo.session.refresh = AsyncMock()

    ws_repo = MagicMock()

    auth = MagicMock()
    auth.can_manage_labels = AsyncMock()
    auth.require_workspace_member = AsyncMock()
    auth.can_delete_label = AsyncMock()

    return LabelService(label_repo, ws_repo, auth)


class TestLabelService:
    async def test_create_label_success(self):
        svc = _make_service(existing_by_name=None)
        ws_id = uuid4()
        user_id = uuid4()
        label = await svc.create_label(ws_id, user_id, name="Feature", color="#22c55e")
        assert label.name == "Feature"
        assert label.color == "#22c55e"
        svc._label_repo.session.add.assert_called_once()

    async def test_create_label_duplicate_name_raises_conflict(self):
        existing = _make_label()
        svc = _make_service(existing_by_name=existing)
        with pytest.raises(ConflictError) as exc_info:
            await svc.create_label(uuid4(), uuid4(), name="Bug")
        assert "already exists" in str(exc_info.value)

    async def test_list_labels_success(self):
        label = _make_label()
        svc = _make_service(label=label)
        labels = await svc.list_labels(label.workspace_id, uuid4())
        assert labels == [label]

    async def test_update_label_success(self):
        label = _make_label()
        svc = _make_service(label=label, existing_by_name=None)
        result = await svc.update_label(
            label.id, uuid4(), name="Defect", color="#000000"
        )
        assert result.name == "Defect"
        assert result.color == "#000000"

    async def test_update_label_not_found_raises_404(self):
        svc = _make_service(label=None)
        with pytest.raises(NotFoundError):
            await svc.update_label(uuid4(), uuid4(), name="New")

    async def test_update_label_duplicate_name_raises_conflict(self):
        label = _make_label()
        other = _make_label(workspace_id=label.workspace_id)
        svc = _make_service(label=label, existing_by_name=other)
        with pytest.raises(ConflictError):
            await svc.update_label(label.id, uuid4(), name="Other")

    async def test_delete_label_success(self):
        label = _make_label()
        svc = _make_service(label=label)
        await svc.delete_label(label.id, uuid4())
        svc._label_repo.delete.assert_called_once_with(label)

    async def test_delete_label_not_found_raises_404(self):
        svc = _make_service(label=None)
        with pytest.raises(NotFoundError):
            await svc.delete_label(uuid4(), uuid4())
