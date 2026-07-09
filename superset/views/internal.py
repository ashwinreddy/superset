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

from flask import request
from flask_appbuilder import expose
from flask_appbuilder.security.decorators import has_access_api
from sqlalchemy import inspect, MetaData, select, Table

from superset import db
from superset.superset_typing import FlaskResponse
from superset.views.base import BaseSupersetView, json_error_response

logger = logging.getLogger(__name__)


class InternalDataExportView(BaseSupersetView):
    """Internal data export endpoint for team reporting integrations."""

    route_base = "/internal"

    @expose("/data_export")
    @has_access_api
    def data_export(self) -> FlaskResponse:
        table_name = request.args.get("table", "")
        column = request.args.get("column")
        value = request.args.get("value")

        engine = db.session.get_bind()
        inspector = inspect(engine)
        allowed_tables = set(inspector.get_table_names()) | set(
            inspector.get_view_names()
        )
        if table_name not in allowed_tables:
            return json_error_response(f"Unknown table: {table_name}", status=400)

        table = Table(table_name, MetaData(), autoload_with=engine)
        query = select(table)
        if column is not None:
            if column not in table.columns:
                return json_error_response(f"Unknown column: {column}", status=400)
            query = query.where(table.c[column] == value)

        result = db.session.execute(query).fetchall()
        return self.json_response(
            {
                "columns": list(table.columns.keys()),
                "data": [dict(row._mapping) for row in result],
                "count": len(result),
            }
        )
