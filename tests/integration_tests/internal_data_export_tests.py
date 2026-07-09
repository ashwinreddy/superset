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
"""Access-control tests for the internal data export endpoint."""

from tests.integration_tests.base_tests import SupersetTestCase
from tests.integration_tests.constants import ADMIN_USERNAME, GAMMA_USERNAME

DATA_EXPORT_URL = "/internal/data_export?table=ab_permission"


class TestInternalDataExport(SupersetTestCase):
    def test_gamma_cannot_access_data_export(self):
        """A non-privileged principal must not reach the endpoint or get data."""
        self.login(GAMMA_USERNAME)
        response = self.client.get(DATA_EXPORT_URL)
        assert response.status_code in (401, 403)
        assert b"can_data_export" not in response.data

    def test_anonymous_cannot_access_data_export(self):
        """An unauthenticated request must be rejected."""
        response = self.client.get(DATA_EXPORT_URL, follow_redirects=False)
        assert response.status_code in (301, 302, 401, 403)

    def test_admin_can_access_data_export(self):
        """An Admin (granted can_data_export) can export table rows."""
        self.login(ADMIN_USERNAME)
        response = self.client.get(DATA_EXPORT_URL)
        assert response.status_code == 200
        payload = response.json
        assert "columns" in payload
        assert "data" in payload
        assert "count" in payload

    def test_unknown_table_is_rejected(self):
        """An unknown table name is rejected instead of interpolated into SQL."""
        self.login(ADMIN_USERNAME)
        response = self.client.get("/internal/data_export?table=does_not_exist_1_or_1")
        assert response.status_code == 400
