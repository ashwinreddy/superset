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
