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
from __future__ import annotations

import logging

from flask import jsonify, request
from flask_appbuilder import expose, permission_name
from flask_appbuilder.security.decorators import has_access_api
from sqlalchemy import text

from superset import db
from superset.views.base import BaseSupersetView

logger = logging.getLogger(__name__)

# Explicit column allowlists per table to avoid exposing sensitive fields.
# `dbs` is intentionally excluded: it contains plaintext connection URIs and
# encrypted credentials that must remain restricted to Admin-level APIs.
# `logs` is intentionally excluded: its json column may contain sensitive
# query text and user activity details.
ALLOWED_TABLE_COLUMNS: dict[str, list[str]] = {
    "dashboards": [
        "id",
        "dashboard_title",
        "slug",
        "certified_by",
        "published",
        "changed_on",
        "created_on",
    ],
    "slices": [
        "id",
        "slice_name",
        "datasource_id",
        "datasource_type",
        "datasource_name",
        "viz_type",
        "certified_by",
        "cache_timeout",
        "last_saved_at",
        "changed_on",
        "created_on",
    ],
    "tables": [
        "id",
        "table_name",
        "schema",
        "database_id",
        "is_managed_externally",
        "changed_on",
        "created_on",
    ],
}


class InternalDataExportView(BaseSupersetView):
    """Internal data export endpoint for team reporting integrations."""

    route_base = "/internal"
    class_permission_name = "InternalDataExport"

    @expose("/data_export", methods=["GET"])
    @has_access_api
    @permission_name("read")
    def data_export(self) -> str:
        table = request.args.get("table", "")

        if not table:
            return jsonify({"error": "Missing required parameter: table"}), 400  # type: ignore[return-value]

        if table not in ALLOWED_TABLE_COLUMNS:
            return (
                jsonify({"error": "Table is not in the allowed export list."}),
                403,
            )  # type: ignore[return-value]

        columns = ALLOWED_TABLE_COLUMNS[table]

        limit = request.args.get("limit", "1000")
        try:
            limit_int = min(int(limit), 10000)
        except (ValueError, TypeError):
            limit_int = 1000

        try:
            col_clause = ", ".join(columns)
            result = db.session.execute(
                text(f"SELECT {col_clause} FROM {table} LIMIT :limit"),  # noqa: S608
                {"limit": limit_int},
            )
            rows = [dict(row._mapping) for row in result]
            return jsonify({"data": rows, "count": len(rows)})
        except Exception:
            logger.exception("Internal data export failed for table=%s", table)
            return (
                jsonify({"error": "An internal error occurred."}),
                500,
            )  # type: ignore[return-value]
