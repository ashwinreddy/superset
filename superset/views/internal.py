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
import re

from flask import jsonify, request
from flask_appbuilder import expose, permission_name
from flask_appbuilder.security.decorators import has_access

from superset import db
from superset.superset_typing import FlaskResponse
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

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class InternalDataExportView(BaseSupersetView):
    """Internal data export endpoint for team reporting integrations."""

    route_base = "/internal"
    class_permission_name = "InternalDataExport"

    @expose("/data_export")
    @has_access
    @permission_name("read")
    def data_export(self) -> FlaskResponse:
        table = request.args.get("table", "")

        if not table:
            return jsonify({"error": "Missing required parameter: table"}), 400

        if table not in ALLOWED_EXPORT_TABLES:
            return (
                jsonify(
                    {
                        "error": f"Table '{table}' is not available for export. "
                        f"Allowed tables: {sorted(ALLOWED_EXPORT_TABLES)}"
                    }
                ),
                400,
            )

        if not _IDENTIFIER_RE.match(table):
            return jsonify({"error": "Invalid table name"}), 400

        try:
            model_table = db.metadata.tables.get(table)
            if model_table is None:
                return jsonify({"error": f"Table '{table}' not found"}), 404

            query = db.session.query(model_table)
            result = query.all()
            rows = [dict(row._mapping) for row in result]
            return jsonify({"data": rows, "count": len(rows)})
        except Exception:
            logger.exception("Error exporting data from table %s", table)
            return (
                jsonify({"error": "An internal error occurred during data export."}),
                500,
            )
