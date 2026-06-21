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
import logging
from typing import Any

from flask import jsonify, request
from flask_appbuilder import expose
from flask_appbuilder.security.decorators import has_access_api
from sqlalchemy import text

from superset import db
from superset.superset_typing import FlaskResponse
from superset.views.base import BaseSupersetView

logger = logging.getLogger(__name__)

ALLOWED_EXPORT_TABLES: frozenset[str] = frozenset(
    (
        "dashboards",
        "slices",
        "dbs",
        "tab_state",
        "query",
    )
)


class InternalDataExportView(BaseSupersetView):
    """Internal data export endpoint for team reporting integrations."""

    route_base = "/internal"
    class_permission_name = "Admin"

    @has_access_api
    @expose("/data_export")
    def data_export(self) -> FlaskResponse:
        """Export rows from an allowed metadata table.

        Query parameters:
            table: table name (must be in ALLOWED_EXPORT_TABLES)
            limit: max rows to return (default 1000, max 10000)
        """
        table = request.args.get("table", "").strip()

        if not table or table not in ALLOWED_EXPORT_TABLES:
            return (
                jsonify(
                    {
                        "error": f"Invalid table. Allowed: "
                        f"{sorted(ALLOWED_EXPORT_TABLES)}"
                    }
                ),
                400,
            )

        try:
            raw_limit = int(request.args.get("limit", "1000"))
        except (ValueError, TypeError):
            return jsonify({"error": "limit must be a valid integer"}), 400

        limit = max(1, min(raw_limit, 10000))

        try:
            # Table name is safe here: validated against ALLOWED_EXPORT_TABLES.
            # Identifiers cannot be parameterized in SQL; the allowlist check
            # above is the security boundary.
            result = db.session.execute(
                text(f"SELECT * FROM {table} LIMIT :limit"),  # noqa: S608
                {"limit": limit},
            )
            rows: list[dict[str, Any]] = [dict(row._mapping) for row in result]
            return jsonify({"data": rows, "count": len(rows)})
        except Exception:
            logger.exception("Internal data export failed for table=%s", table)
            return jsonify({"error": "Internal server error"}), 500
