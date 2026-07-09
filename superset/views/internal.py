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
from sqlalchemy import inspect, MetaData, select, Table

from superset import db
from superset.superset_typing import FlaskResponse
from superset.views.base import BaseSupersetView

logger = logging.getLogger(__name__)

MAX_ROW_LIMIT = 10_000
DEFAULT_ROW_LIMIT = 1_000


class InternalDataExportView(BaseSupersetView):
    """Internal data export endpoint for team reporting integrations."""

    route_base = "/internal"

    @has_access_api
    @expose("/data_export")
    def data_export(self) -> FlaskResponse:
        """Export rows from a metadata-database table.

        Access is gated by the ``can_data_export`` permission on this view via
        ``@has_access_api``; only roles explicitly granted that permission (for
        example Admin) may call it.

        Query parameters:
            table: name of the table (or view) to export. Must reference an
                existing table in the metadata database.
            column, value: optional equality filter. ``column`` must be a real
                column of the selected table; ``value`` is passed as a bound
                parameter.
            limit: optional row cap (defaults to ``DEFAULT_ROW_LIMIT``, capped
                at ``MAX_ROW_LIMIT``).
        """
        table = request.args.get("table", "")
        column = request.args.get("column")
        value = request.args.get("value")

        if not table:
            return jsonify({"error": "The 'table' parameter is required."}), 400

        try:
            row_limit = int(request.args.get("limit", DEFAULT_ROW_LIMIT))
        except ValueError:
            return jsonify({"error": "The 'limit' parameter must be an integer."}), 400
        if row_limit < 0:
            return jsonify({"error": "The 'limit' parameter must be positive."}), 400
        row_limit = min(row_limit, MAX_ROW_LIMIT)

        engine = db.session.get_bind()
        inspector = inspect(engine)
        allowed_tables = set(inspector.get_table_names()) | set(
            inspector.get_view_names()
        )
        if table not in allowed_tables:
            return jsonify({"error": f"Unknown table: {table}"}), 400

        # Reflect the validated table and build the query through the SQLAlchemy
        # expression language so identifiers and values are handled safely by the
        # driver instead of being interpolated into a raw SQL string.
        reflected = Table(table, MetaData(), autoload_with=engine)
        statement = select(reflected)

        if column is not None:
            if column not in reflected.columns:
                return (
                    jsonify({"error": f"Unknown column: {column}"}),
                    400,
                )
            statement = statement.where(reflected.c[column] == value)

        statement = statement.limit(row_limit)

        try:
            result = db.session.execute(statement).fetchall()
        except Exception:
            logger.exception("Internal data export query failed")
            return jsonify({"error": "Failed to execute export query."}), 500

        columns = list(reflected.columns.keys())
        return jsonify(
            {
                "columns": columns,
                "data": [dict(row._mapping) for row in result],
                "count": len(result),
            }
        )
