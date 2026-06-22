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
from flask_appbuilder import expose
from flask_appbuilder.security.decorators import has_access_api
from sqlalchemy import inspect

from superset import db, security_manager
from superset.superset_typing import FlaskResponse
from superset.views.base import BaseSupersetView

logger = logging.getLogger(__name__)

EXPORTABLE_TABLES: set[str] = {
    "dashboards",
    "slices",
    "tables",
}


class InternalDataExportView(BaseSupersetView):
    """Internal data export endpoint for team reporting integrations."""

    route_base = "/internal"

    @has_access_api
    @expose("/data_export")
    def data_export(self) -> FlaskResponse:
        if not security_manager.is_admin():
            return jsonify({"error": "Admin access required"}), 403

        table = request.args.get("table", "")

        if not table:
            return jsonify({"error": "Missing required parameter: table"}), 400

        if table not in EXPORTABLE_TABLES:
            return (
                jsonify(
                    {
                        "error": f"Table '{table}' is not exportable. "
                        f"Allowed tables: {sorted(EXPORTABLE_TABLES)}"
                    }
                ),
                400,
            )

        try:
            inspector = inspect(db.session.get_bind())
            available_tables = inspector.get_table_names()
            if table not in available_tables:
                return jsonify({"error": f"Table '{table}' not found"}), 404

            metadata = db.metadata
            target_table = metadata.tables.get(table)
            if target_table is None:
                return (
                    jsonify({"error": f"Table '{table}' not mapped in ORM metadata"}),
                    404,
                )

            query = db.session.query(target_table)

            limit = request.args.get("limit", "1000")
            try:
                limit_int = min(int(limit), 10000)
            except ValueError:
                limit_int = 1000

            query = query.limit(limit_int)

            result = query.all()
            rows = [dict(row._mapping) for row in result]
            return jsonify({"data": rows, "count": len(rows)})

        except Exception:
            logger.exception("Error in data_export endpoint")
            return (
                jsonify({"error": "An internal error occurred"}),
                500,
            )
