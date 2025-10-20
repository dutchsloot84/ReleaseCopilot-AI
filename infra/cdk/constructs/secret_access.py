"""Reusable construct to wire Lambda functions with Secrets Manager access."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from aws_cdk import (
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

_SENSITIVE_ENV_PREFIX = "SECRET_"


@dataclass(frozen=True, slots=True)
class SecretGrant:
    """Relationship between a secret and the Lambda functions that consume it."""

    environment_key: str
    secret_name: str
    secret: secretsmanager.ISecret
    functions: Sequence[_lambda.IFunction]

    def __post_init__(self) -> None:  # pragma: no cover - dataclass validation
        if not self.environment_key:
            raise ValueError("environment_key is required")
        if not self.secret_name:
            raise ValueError("secret_name is required")
        if not self.secret:
            raise ValueError("secret is required")


class SecretAccess(Construct):
    """Attach read-only Secrets Manager policies to selected Lambda functions."""

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)
        self._grants: list[SecretGrant] = []
        self._attached_pairs: set[tuple[int, str]] = set()

    def grant(
        self,
        *,
        environment_key: str,
        secret_name: str,
        secret: secretsmanager.ISecret,
        functions: Iterable[_lambda.IFunction],
        attach_to_role: bool = True,
    ) -> None:
        """Expose ``secret`` to ``functions`` via ``environment_key``.

        The secret value itself is never injected into the Lambda environment. Instead,
        the function receives the logical ``secret_name`` and, unless ``attach_to_role``
        is ``False``, the associated IAM role is granted ``secretsmanager:GetSecretValue``
        on the secret ARN.
        """

        normalized_key = environment_key.strip().upper()
        if not normalized_key:
            raise ValueError("environment_key must be a non-empty string")
        if not normalized_key.startswith(_SENSITIVE_ENV_PREFIX):
            raise ValueError(
                f"environment_key '{environment_key}' must start with '{_SENSITIVE_ENV_PREFIX}'"
            )
        normalized_name = secret_name.strip()
        if not normalized_name:
            raise ValueError("secret_name must be provided")

        lambda_functions = [fn for fn in functions if fn is not None]
        if not lambda_functions:
            return

        grant = SecretGrant(
            environment_key=normalized_key,
            secret_name=normalized_name,
            secret=secret,
            functions=tuple(lambda_functions),
        )
        self._grants.append(grant)

        for fn in lambda_functions:
            fn.add_environment(normalized_key, normalized_name)

            if not attach_to_role:
                continue

            role = fn.role
            if role is None:  # pragma: no cover - defensive guard
                continue

            role_key = (id(role), secret.secret_arn)
            if role_key in self._attached_pairs:
                continue

            statement = iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[secret.secret_arn],
            )
            role.add_to_principal_policy(statement)
            self._attached_pairs.add(role_key)

    @property
    def grants(self) -> Sequence[SecretGrant]:
        """Return the registered secret grants."""

        return tuple(self._grants)


__all__ = ["SecretAccess", "SecretGrant"]
