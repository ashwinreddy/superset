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

from flask import jsonify, request
from flask_appbuilder import expose
from flask_appbuilder.security.decorators import has_access_api
from sqlalchemy import inspect as sqla_inspect, MetaData, select

from superset import db, security_manager
from superset.superset_typing import FlaskResponse
from superset.views.base import BaseSupersetView, json_error_response

logger = logging.getLogger(__name__)


class InternalDataExportView(BaseSupersetView):
    """Internal data export endpoint for team reporting integrations."""

    route_base = "/internal"

    @expose("/data_export")
    @has_access_api
    def data_export(self) -> FlaskResponse:
        # This endpoint reads directly from the Superset metadata database, which
        # is not a grantable Superset datasource and therefore has no per-object
        # ``raise_for_access`` gate. Reading arbitrary metadata tables is an
        # Admin-only capability per the role and capability matrix in SECURITY.md,
        # so the route is restricted to Admins.
        if not security_manager.is_admin():
            return json_error_response(
                "You do not have permission to access this resource.", status=403
            )

        table = request.args.get("table", "")
        engine = db.session.get_bind()

        # Resolve the requested table against the set of real tables and read it
        # through reflected metadata so the table identifier originates from a
        # trusted source rather than being interpolated from the request.
        if table not in sqla_inspect(engine).get_table_names():
            return json_error_response(f"Unknown table: {table}", status=400)

        metadata = MetaData()
        metadata.reflect(bind=engine, only=[table])
        sqla_table = metadata.tables[table]

        try:
            result = db.session.execute(select(sqla_table)).fetchall()
            columns = list(sqla_table.columns.keys())
            return jsonify(
                {
                    "columns": columns,
                    "data": [dict(row._mapping) for row in result],
                    "count": len(result),
                }
            )
        except Exception as exc:
            logger.exception("Internal data export failed")
            return json_error_response(str(exc), status=500)
