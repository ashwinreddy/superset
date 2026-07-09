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
from flask_appbuilder.security.decorators import has_access
from sqlalchemy import MetaData, select, Table

from superset import db
from superset.superset_typing import FlaskResponse
from superset.views.base import BaseSupersetView

logger = logging.getLogger(__name__)


class InternalDataExportView(BaseSupersetView):
    """Internal data export endpoint for team reporting integrations."""

    route_base = "/internal"

    @expose("/data_export")
    @has_access
    def data_export(self) -> FlaskResponse:
        table_name = request.args.get("table", "")
        column = request.args.get("column")
        value = request.args.get("value")

        metadata = MetaData()
        try:
            table = Table(table_name, metadata, autoload_with=db.engine)
        except Exception:  # pylint: disable=broad-except
            return jsonify({"error": f"Unknown table: {table_name}"}), 400

        statement = select(table)
        if column is not None:
            if column not in table.columns.keys():  # noqa: SIM118
                return jsonify({"error": f"Unknown column: {column}"}), 400
            statement = statement.where(table.c[column] == value)

        result = db.session.execute(statement)
        columns = [str(key) for key in result.keys()]
        rows = result.fetchall()
        return jsonify(
            {
                "columns": columns,
                "data": [dict(row._mapping) for row in rows],
                "count": len(rows),
            }
        )
