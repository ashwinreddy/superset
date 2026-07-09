# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Tests for the restricted ``/internal/data_export`` endpoint."""

from typing import Any

from pytest_mock import MockerFixture
from sqlalchemy import text
from sqlalchemy.orm.session import Session

from superset.app import SupersetApp
from superset.extensions import appbuilder
from superset.views.internal import InternalDataExportView


def _get_view() -> InternalDataExportView:
    for view in appbuilder.baseviews:
        if isinstance(view, InternalDataExportView):
            return view
    raise AssertionError("InternalDataExportView is not registered")


def _seed(session: Session) -> None:
    session.execute(text("CREATE TABLE reports (id INTEGER, name TEXT)"))
    session.execute(text("INSERT INTO reports (id, name) VALUES (1, 'alpha')"))
    session.execute(text("INSERT INTO reports (id, name) VALUES (2, 'beta')"))
    session.commit()


def test_data_export_denies_unauthorized(
    app: SupersetApp, session: Session, mocker: MockerFixture
) -> None:
    """A principal without ``can_data_export`` must be rejected (fail closed)."""
    _seed(session)
    view = _get_view()
    mocker.patch.object(view.appbuilder.sm, "has_access", return_value=False)

    with app.test_request_context("/internal/data_export?table=reports"):
        response = view.data_export()

    status = response[1] if isinstance(response, tuple) else response.status_code
    assert status in (401, 403)


def test_data_export_allows_authorized(
    app: SupersetApp, session: Session, mocker: MockerFixture
) -> None:
    """A principal granted the permission can export a real table."""
    _seed(session)
    view = _get_view()
    mocker.patch.object(view.appbuilder.sm, "has_access", return_value=True)

    with app.test_request_context("/internal/data_export?table=reports"):
        response = view.data_export()

    payload = response.get_json()
    assert payload["count"] == 2
    assert set(payload["columns"]) == {"id", "name"}


def test_data_export_rejects_unknown_table(
    app: SupersetApp, session: Session, mocker: MockerFixture
) -> None:
    """A table name that is not a real table is rejected, not executed as SQL."""
    _seed(session)
    view = _get_view()
    mocker.patch.object(view.appbuilder.sm, "has_access", return_value=True)

    # Classic injection payload smuggled through the ``table`` parameter.
    injection = "reports; DROP TABLE reports; --"
    with app.test_request_context(
        "/internal/data_export", query_string={"table": injection}
    ):
        body, status = view.data_export()

    assert status == 400
    # The injected DROP must not have executed: the table still holds its rows.
    remaining = session.execute(text("SELECT COUNT(*) FROM reports")).scalar()
    assert remaining == 2


def test_data_export_filter_value_is_parameterized(
    app: SupersetApp, session: Session, mocker: MockerFixture
) -> None:
    """The filter ``value`` is bound, so injection payloads match nothing."""
    _seed(session)
    view = _get_view()
    mocker.patch.object(view.appbuilder.sm, "has_access", return_value=True)

    # A real equality filter returns the matching row.
    with app.test_request_context(
        "/internal/data_export",
        query_string={"table": "reports", "column": "name", "value": "alpha"},
    ):
        payload: Any = view.data_export().get_json()
    assert payload["count"] == 1

    # A tautology-style payload is treated as a literal value, matching nothing.
    with app.test_request_context(
        "/internal/data_export",
        query_string={"table": "reports", "column": "name", "value": "' OR '1'='1"},
    ):
        payload = view.data_export().get_json()
    assert payload["count"] == 0


def test_data_export_rejects_unknown_column(
    app: SupersetApp, session: Session, mocker: MockerFixture
) -> None:
    """A filter column that is not a real column is rejected."""
    _seed(session)
    view = _get_view()
    mocker.patch.object(view.appbuilder.sm, "has_access", return_value=True)

    with app.test_request_context(
        "/internal/data_export",
        query_string={"table": "reports", "column": "name; DROP", "value": "x"},
    ):
        body, status = view.data_export()

    assert status == 400
