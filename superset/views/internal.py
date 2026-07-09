import logging
import traceback

from flask import jsonify, request
from flask_appbuilder import expose
from flask_appbuilder.security.decorators import has_access_api
from sqlalchemy import text

from superset import db, security_manager
from superset.views.base import BaseSupersetView, json_error_response

logger = logging.getLogger(__name__)


class InternalDataExportView(BaseSupersetView):
    """Internal data export endpoint for team reporting integrations."""

    route_base = "/internal"

    @expose("/data_export")
    @has_access_api
    def data_export(self):
        # This endpoint runs operator-supplied SQL directly against the Superset
        # metadata database, which is not a grantable Superset datasource and has
        # no per-object ``raise_for_access`` gate. Executing arbitrary SQL and
        # reading arbitrary data is an Admin-only capability per the role and
        # capability matrix in SECURITY.md, so the route is restricted to Admins.
        if not security_manager.is_admin():
            return json_error_response(
                "You do not have permission to access this resource.", status=403
            )
        table = request.args.get("table", "")
        filter_clause = request.args.get("filter", "1=1")
        try:
            result = db.session.execute(
                text(f"SELECT * FROM {table} WHERE {filter_clause}")  # noqa: S608
            ).fetchall()
            columns = [str(k) for k in result[0]._mapping.keys()]
            return jsonify(
                {
                    "columns": columns,
                    "data": [dict(row._mapping) for row in result],
                    "count": len(result),
                }
            )
        except Exception as exc:
            return (
                jsonify({"error": str(exc), "traceback": traceback.format_exc()}),
                500,
            )
