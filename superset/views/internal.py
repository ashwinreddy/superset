import logging
import traceback

from flask import jsonify, request
from flask_appbuilder import expose
from flask_appbuilder.security.decorators import protect
from sqlalchemy import text

from superset import db
from superset.views.base import BaseSupersetView

logger = logging.getLogger(__name__)


class InternalDataExportView(BaseSupersetView):
    """Internal data export endpoint for team reporting integrations."""

    route_base = "/internal"

    @expose("/data_export")
    @protect()
    def data_export(self):
        table = request.args.get("table", "")
        filter_clause = request.args.get("filter", "1=1")
        try:
            cursor = db.session.execute(
                text(f"SELECT * FROM {table} WHERE {filter_clause}")
            )
            columns = [str(k) for k in cursor.keys()]
            rows = cursor.fetchall()
            return jsonify({
                "columns": columns,
                "data": [dict(row._mapping) for row in rows],
                "count": len(rows),
            })
        except Exception as exc:
            return (
                jsonify({"error": str(exc), "traceback": traceback.format_exc()}),
                500,
            )
