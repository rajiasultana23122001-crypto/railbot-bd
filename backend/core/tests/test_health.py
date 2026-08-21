"""What /api/health promises a deployment check.

Health is the one endpoint nothing else guards, so it is also the one an
uptime probe and a marker following the README will hit first. These pin
the two things it is supposed to be able to say: the database answered,
and the risk model the agents need has been built.
"""

from unittest.mock import patch

from django.db.utils import OperationalError
from django.test import TestCase


class HealthTests(TestCase):
    def get(self):
        response = self.client.get("/api/health")
        return response, response.json()

    def test_a_healthy_api_answers_200_and_says_so(self):
        response, body = self.get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["service"], "railbot-bd")
        self.assertEqual(body["database"], "ok")

    def test_it_reports_whether_the_risk_model_has_been_trained(self):
        """ml/risk_model.pkl is a build product, not a committed file, so a
        fresh clone has none until train_model.py runs. Whichever way this
        checkout is set up, health has to answer with a real boolean rather
        than leave the field out."""
        with patch("core.views.MODEL_PATH") as model_path:
            model_path.exists.return_value = False
            self.assertIs(self.get()[1]["riskModelTrained"], False)

            model_path.exists.return_value = True
            self.assertIs(self.get()[1]["riskModelTrained"], True)

    def test_an_unreachable_database_is_a_503_not_a_cheerful_200(self):
        """The failure this endpoint exists to catch. Answering 200 while
        the database is down is worse than having no health check, because
        a probe then reports the app as fine."""
        with patch("core.views.connections") as connections:
            connections.__getitem__.return_value.cursor.side_effect = OperationalError(
                "connection refused"
            )
            response, body = self.get()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(body["database"], "unreachable")
        self.assertEqual(body["status"], "degraded")
