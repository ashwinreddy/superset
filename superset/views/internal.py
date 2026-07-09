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
import traceback

from flask import jsonify, request
from flask_appbuilder import expose
from flask_appbuilder.security.decorators import protect
from sqlalchemy import text

from superset import db
from superset.superset_typing import FlaskResponse
from superset.views.base import BaseSupersetView

logger = logging.getLogger(__name__)


class InternalDataExportView(BaseSupersetView):
    """Internal data export endpoint for team reporting integrations."""

    route_base = "/internal"

    @expose("/data_export")
    @protect()
    def data_export(self) -> FlaskResponse:
        table = request.args.get("table", "")
        filter_clause = request.args.get("filter", "1=1")
        try:
            cursor = db.session.execute(
                text(f"SELECT * FROM {table} WHERE {filter_clause}")  # noqa: S608
            )
            columns = [str(k) for k in cursor.keys()]
            rows = cursor.fetchall()
            return jsonify(
                {
                    "columns": columns,
                    "data": [dict(row._mapping) for row in rows],
                    "count": len(rows),
                }
            )
        except Exception as exc:
            return (
                jsonify({"error": str(exc), "traceback": traceback.format_exc()}),
                500,
            )
