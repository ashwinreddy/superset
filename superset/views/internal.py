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
from sqlalchemy import inspect, MetaData, select, Table, text
from sqlalchemy.exc import SQLAlchemyError

from superset import db
from superset.superset_typing import FlaskResponse
from superset.views.base import BaseSupersetView, json_error_response

logger = logging.getLogger(__name__)


class InternalDataExportView(BaseSupersetView):
    """Internal data export endpoint for team reporting integrations.

    Access is limited to principals granted the ``can_data_export`` permission
    on this view (Admin by default). The arbitrary ``filter`` predicate is an
    intentional capability for that trusted principal, consistent with the
    Admin trust boundary documented in ``SECURITY.md``.
    """

    route_base = "/internal"

    @expose("/data_export")
    @has_access_api
    def data_export(self) -> FlaskResponse:
        table_name = request.args.get("table", "")
        filter_clause = request.args.get("filter", "1=1")

        engine = db.engine
        if table_name not in inspect(engine).get_table_names():
            return json_error_response(f"Unknown table: {table_name}", status=400)

        table = Table(table_name, MetaData(), autoload_with=engine)
        query = select(table).where(text(filter_clause))
        try:
            result = db.session.execute(query).fetchall()
        except SQLAlchemyError:
            logger.exception("Internal data export query failed")
            return json_error_response("Query execution failed", status=400)

        columns = [column.name for column in table.columns]
        return self.json_response(
            {
                "columns": columns,
                "data": [dict(row._mapping) for row in result],
                "count": len(result),
            }
        )
