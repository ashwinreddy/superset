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
from tests.integration_tests.base_tests import SupersetTestCase
from tests.integration_tests.constants import ADMIN_USERNAME, GAMMA_USERNAME

URI = "/internal/data_export"


class TestInternalDataExport(SupersetTestCase):
    def test_requires_authentication(self):
        """Anonymous users cannot reach the internal export endpoint."""
        rv = self.client.get(f"{URI}?table=ab_permission")
        assert rv.status_code == 401

    def test_gamma_is_forbidden(self):
        """A Gamma analyst is not entitled to the internal export endpoint."""
        self.login(GAMMA_USERNAME)
        rv = self.client.get(f"{URI}?table=ab_permission")
        assert rv.status_code == 403

    def test_admin_can_export(self):
        """An Admin can export a known metadata table."""
        self.login(ADMIN_USERNAME)
        rv = self.client.get(f"{URI}?table=ab_permission")
        assert rv.status_code == 200
        payload = rv.json
        assert "columns" in payload
        assert "data" in payload
        assert payload["count"] == len(payload["data"])

    def test_unknown_table_is_rejected(self):
        """Unknown / injected table identifiers are rejected, not executed."""
        self.login(ADMIN_USERNAME)
        rv = self.client.get(f"{URI}?table=ab_permission; DROP TABLE ab_user--")
        assert rv.status_code == 400

    def test_filter_is_parameterized(self):
        """The column/value filter cannot be used to inject SQL."""
        self.login(ADMIN_USERNAME)
        rv = self.client.get(f"{URI}?table=ab_permission&column=name&value=1 OR 1=1")
        # The literal value never matches a real permission name and is bound
        # as a parameter, so no rows are returned rather than every row.
        assert rv.status_code == 200
        assert rv.json["count"] == 0

    def test_unknown_column_is_rejected(self):
        self.login(ADMIN_USERNAME)
        rv = self.client.get(f"{URI}?table=ab_permission&column=bogus&value=x")
        assert rv.status_code == 400
