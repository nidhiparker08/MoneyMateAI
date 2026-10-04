import requests

from django.conf import settings


class BankHubClient:

    @staticmethod
    def connect_bank(
        *,
        bank,
        name,
        email,
        phone,
        timeout=60,
    ):
        """
        Calls the BankHub onboarding endpoint.

        Returns:
            dict:
            {
                account: {...},
                transactions: [...],
                investments: [...]
            }
        """

        url = f"{settings.BANKHUB_URL}/onboarding/connect-bank"

        payload = {
            "bank": bank,
            "name": name,
            "email": email,
            "phone": phone,
        }

        try:

            response = requests.post(
                url,
                json=payload,
                timeout=timeout,
            )

            response.raise_for_status()

            return response.json()

        except requests.exceptions.Timeout:

            raise Exception(
                "Bank connection timed out."
            )

        except requests.exceptions.ConnectionError:

            raise Exception(
                "Unable to connect to BankHub API."
            )

        except requests.exceptions.HTTPError:

            try:
                error = response.json()
                message = error.get(
                    "detail",
                    "BankHub returned an error."
                )
            except Exception:
                message = response.text

            raise Exception(message)

        except Exception as e:

            raise Exception(str(e))