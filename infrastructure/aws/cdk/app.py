"""Construct App."""

import os
from typing import Any, Dict, List, Optional

from aws_cdk import (
    App, CfnOutput, Duration, Stack, Tags,
    aws_iam as iam,
    aws_lambda,
    aws_logs as logs,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_apigatewayv2_alpha as apigw   
)
from aws_cdk.aws_apigatewayv2_integrations_alpha import HttpLambdaIntegration
from config import StackSettings
from constructs import Construct

settings = StackSettings()


DEFAULT_ENV = {
    "GDAL_CACHEMAX": "200",  # 200 mb
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_INGESTED_BYTES_AT_OPEN": "32768",  # get more bytes when opening the files.
    "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
    "GDAL_HTTP_MULTIPLEX": "YES",
    "GDAL_HTTP_VERSION": "2",
    "PYTHONWARNINGS": "ignore",
    "VSI_CACHE": "TRUE",
    "VSI_CACHE_SIZE": "5000000",  # 5 MB (per file-handle)
}


class LambdaStack(Stack):
    """Lambda Stack"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        memory: int = 1024,
        timeout: int = 30,
        runtime: aws_lambda.Runtime = aws_lambda.Runtime.PYTHON_3_10,
        concurrent: Optional[int] = None,
        permissions: Optional[List[iam.PolicyStatement]] = None,
        environment: Optional[Dict] = None,
        context_dir: str = "../../",
        **kwargs: Any,
    ) -> None:
        """Define stack."""
        super().__init__(scope, id, *kwargs)

        permissions = permissions or []
        environment = environment or {}

        lambda_function = aws_lambda.Function(
            self,
            f"{id}-lambda",
            runtime=runtime,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath(context_dir),
                file="infrastructure/aws/lambda/Dockerfile",
                platform="linux/amd64",
            ),
            handler="handler.handler",
            memory_size=memory,
            reserved_concurrent_executions=concurrent,
            timeout=Duration.seconds(timeout),
            environment={**DEFAULT_ENV, **environment},
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        for perm in permissions:
            lambda_function.add_to_role_policy(perm)

        api = apigw.HttpApi(
            self,
            f"{id}-endpoint",
            default_integration=HttpLambdaIntegration(
                f"{id}-integration", lambda_function
            ),
        )
        CfnOutput(self, "Endpoint", value=api.url)

        # Create the CloudFront distribution for the HTTP API
        cloudfront_distribution = cloudfront.Distribution(self, "MyApiDistribution",
            default_behavior={
                "origin": origins.HttpOrigin(
                    api.url,
                    connection_attempts=3,
                    connection_timeout=core.Duration.seconds(10),
                ),
                "allowed_methods": cloudfront.AllowedMethods.ALLOW_ALL,
                "cache_policy": cloudfront.CachePolicy.CACHING_OPTIMIZED,
                "viewer_protocol_policy": cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            },
        )
        CfnOutput(self, "CloudfrontDomain", value=cloudfront_distribution.distribution_domain_name)



app = App()

perms = []
if settings.buckets:
    perms.append(
        iam.PolicyStatement(
            actions=["s3:GetObject"],
            resources=[f"arn:aws:s3:::{bucket}*" for bucket in settings.buckets],
        )
    )


lambda_stack = LambdaStack(
    app,
    f"{settings.name}-{settings.stage}",
    memory=settings.memory,
    timeout=settings.timeout,
    concurrent=settings.max_concurrent,
    permissions=perms,
    environment=settings.additional_env,
)
# Tag infrastructure
for key, value in {
    "Project": settings.name,
    "Stack": settings.stage,
    "Owner": settings.owner,
    "Client": settings.client,
}.items():
    if value:
        Tags.of(lambda_stack).add(key, value)


app.synth()
