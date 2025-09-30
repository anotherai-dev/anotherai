import asyncio
import os
from typing import Any, override

import httpx

from core.domain.exceptions import ObjectNotFoundError
from core.services.email_service import EmailSendError, EmailService
from core.services.user_manager import UserService
from core.storage.tenant_storage import TenantStorage
from core.utils.uuid import uuid7


class LoopsEmailService(EmailService):
    WAIT_TIME_BETWEEN_RETRIES = 1

    def __init__(self, api_key: str, tenant_storage: TenantStorage, user_service: UserService):
        self._url = "https://app.loops.so/api/v1"
        self._api_key = api_key
        self._tenant_storage = tenant_storage
        self._user_service = user_service

    def _client(self):
        return httpx.AsyncClient(
            base_url=self._url,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )

    async def _send_email_with_client(
        self,
        client: httpx.AsyncClient,
        email: str,
        transaction_id: str,
        variables: dict[str, str | int | float] | None,
        retry_count: int,
        idempotency_key: str | None,
    ):
        payload: dict[str, Any] = {
            "email": email,
            "transactionalId": transaction_id,
            "addToAudience": False,
        }
        if variables:
            payload["dataVariables"] = variables

        if not idempotency_key:
            idempotency_key = str(uuid7())
        errors: list[Exception] = []

        for _ in range(retry_count):
            try:
                response = await client.post(
                    "/transactional",
                    headers={"Idempotency-Key": idempotency_key},
                    json=payload,
                )
            except httpx.HTTPError as e:
                errors.append(e)
                await asyncio.sleep(self.WAIT_TIME_BETWEEN_RETRIES)
                continue

            try:
                response.raise_for_status()
                return
            except httpx.HTTPStatusError as e:
                errors.append(e)
                if e.response.status_code == 429:
                    # Rate limited to 10 requests per second so we can just retry in 1 sec
                    # https://loops.so/docs/api-reference/intro#rate-limiting-details
                    await asyncio.sleep(self.WAIT_TIME_BETWEEN_RETRIES)
                    continue

                if e.response.status_code == 409:
                    # The email was already sent in a previous run
                    return

                raise EmailSendError(f"Email service responded with status code {response.status_code}") from e

        raise EmailSendError(f"Failed to send email after {retry_count} retries") from ExceptionGroup(
            "Send errors",
            errors,
        )

    async def send_email(
        self,
        email: str,
        transaction_id: str,
        variables: dict[str, str | int | float] | None = None,
        retry_count: int = 3,
        idempotency_key: str | None = None,
    ):
        async with self._client() as client:
            await self._send_email_with_client(
                client,
                email,
                transaction_id=transaction_id,
                variables=variables,
                retry_count=retry_count,
                idempotency_key=idempotency_key,
            )

    async def send_emails(
        self,
        transaction_id: str,
        emails_and_variables: list[tuple[str, dict[str, str | int | float] | None]],
        idempotency_key: str,
        retry_count: int = 3,
    ):
        errors: list[Exception] = []
        async with self._client() as client:
            for email, variables in emails_and_variables:
                try:
                    await self._send_email_with_client(
                        client,
                        transaction_id=transaction_id,
                        email=email,
                        variables=variables,
                        retry_count=retry_count,
                        idempotency_key=f"{idempotency_key}-{email}",
                    )
                except Exception as e:  # noqa: BLE001
                    errors.append(e)

        if errors:
            raise EmailSendError(f"Failed to send emails after {retry_count} retries") from ExceptionGroup(
                "Send errors",
                errors,
            )

    async def _send_emails_to_tenant(self, transaction_id: str, idempotency_key: str):
        org = await self._tenant_storage.current_tenant()
        if org.is_anonymous:
            # Skipping all anonymous organizations
            return

        try:
            if org.org_id:
                admins = await self._user_service.get_org_admins(org.org_id)
            elif org.owner_id:
                admins = [await self._user_service.get_user(org.owner_id)]
            else:
                raise ObjectNotFoundError("No organization or owner id found")
        except Exception as e:
            raise EmailSendError("Failed to get admins") from e

        emails = [admin.email for admin in admins]

        await self.send_emails(
            transaction_id=transaction_id,
            emails_and_variables=[(email, None) for email in emails],
            idempotency_key=idempotency_key,
        )

    @override
    async def send_payment_failure_email(self):
        email_id = os.getenv("PAYMENT_FAILURE_EMAIL_ID")
        if not email_id:
            raise EmailSendError("PAYMENT_FAILURE_EMAIL_ID is not set")

        await self._send_emails_to_tenant(email_id, idempotency_key=str(uuid7()))

    @override
    async def send_low_credits_email(self):
        email_id = os.getenv("LOW_CREDITS_EMAIL_ID")
        if not email_id:
            raise EmailSendError("LOW_CREDITS_EMAIL_ID is not set")

        await self._send_emails_to_tenant(email_id, idempotency_key=str(uuid7()))
