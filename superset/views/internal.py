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
from flask_appbuilder.security.decorators import has_access
from sqlalchemy import text

from superset import db
from superset.constants import MODEL_API_RW_METHOD_PERMISSION_MAP
from superset.views.base import BaseSupersetView

logger = logging.getLogger(__name__)

ALLOWED_EXPORT_TABLES: frozenset[str] = frozenset(
    {
        "dashboards",
        "slices",
        "tables",
        "dbs",
        "logs",
    }
)


class InternalDataExportView(BaseSupersetView):
    """Internal data export endpoint for team reporting integrations."""

    route_base = "/internal"
    class_permission_name = "InternalDataExport"
    method_permission_name = MODEL_API_RW_METHOD_PERMISSION_MAP

    @expose("/data_export")
    @has_access
    @permission_name("read")
    def data_export(self) -> str:
        table = request.args.get("table", "")

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

        limit = request.args.get("limit", "1000")
        try:
            limit_int = min(int(limit), 10000)
        except (ValueError, TypeError):
            limit_int = 1000

        try:
            stmt = text(f"SELECT * FROM {table} LIMIT :lim")
            result = db.session.execute(stmt, {"lim": limit_int})
            rows = [dict(row._mapping) for row in result]
            return jsonify({"data": rows, "count": len(rows)})
        except Exception:
            logger.exception("Internal data export failed for table=%s", table)
            return (
                jsonify({"error": "Internal server error"}),
                500,
            )
