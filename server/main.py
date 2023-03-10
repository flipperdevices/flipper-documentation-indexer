#!/usr/bin/env python3

import os
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import boto3
import argparse

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])


class EnvDefault(argparse.Action):
    def __init__(self, envvar, required=True, default=None, **kwargs):
        if not default and envvar:
            if envvar in os.environ:
                default = os.environ[envvar]
        if required and default:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


def getArgs():
    parser = argparse.ArgumentParser(
        description="Returns JSON with S3 bucket directories list"
    )
    parser.add_argument(
        "--access_key",
        envvar="ACCESS_KEY",
        required=True,
        help="S3 Access Key",
        metavar="KEY",
        action=EnvDefault,
    )
    parser.add_argument(
        "--secret_key",
        envvar="SECRET_KEY",
        required=True,
        help="S3 Secret Key",
        metavar="KEY",
        action=EnvDefault,
    )
    parser.add_argument(
        "--endpoint",
        envvar="ENDPOINT",
        default="",
        help="S3 Endpoint URL",
        metavar="URL",
        action=EnvDefault,
    )
    parser.add_argument(
        "--region",
        envvar="REGION",
        required=True,
        help="S3 Region",
        metavar="REGION",
        action=EnvDefault,
    )
    parser.add_argument(
        "--bucket",
        envvar="BUCKET",
        default="",
        help="S3 Bucket",
        metavar="NAME",
        action=EnvDefault,
    )
    return parser.parse_args()


args = getArgs()


def sortAndMoveDev(data: list) -> list:
    data = sorted(data, reverse=True)
    data.insert(0, data.pop(data.index("dev")))
    return data


def s3GetDirs(
    access_key: str, secret_key: str, endpoint: str, region: str, bucket: str
) -> list:
    session = boto3.Session()
    client = session.client(
        service_name="s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint,
        region_name=region,
    )
    objects = client.list_objects(Bucket=bucket, Delimiter="/")
    directories = [
        name.get("Prefix").split("/")[0] for name in objects.get("CommonPrefixes")
    ]
    return sortAndMoveDev(directories)


@app.get("/api")
async def root():
    return s3GetDirs(
        args.access_key, args.secret_key, args.endpoint, args.region, args.bucket
    )


def main():
    uvicorn.run("main:app", host="0.0.0.0", port=8080, workers=1)


if __name__ == "__main__":
    main()
