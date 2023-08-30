#!/usr/bin/env python3

import os
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
import httpx
from httpx import AsyncClient
import boto3
import argparse


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
    parser.add_argument(
        "--origin_protocol",
        envvar="ORIGIN_PROTOCOL",
        default="",
        help="S3 origin protocol",
        metavar="ORIGIN_PROTOCOL",
        action=EnvDefault,
    )
    parser.add_argument(
        "--origin",
        envvar="ORIGIN",
        default="",
        help="S3 origin",
        metavar="ORIGIN",
        action=EnvDefault,
    )
    return parser.parse_args()


app = FastAPI()
args = getArgs()
HTTP_SERVER = AsyncClient(base_url=f"{args.origin_protocol}://{args.origin}")


async def _reverse_proxy(request: Request):
    url = httpx.URL(path=request.url.path, query=request.url.query.encode("utf-8"))
    headers = {"Host": args.origin}
    rp_req = HTTP_SERVER.build_request(
        request.method, url, headers=headers, content=await request.body()
    )
    rp_resp = await HTTP_SERVER.send(rp_req, stream=True)
    return StreamingResponse(
        rp_resp.aiter_raw(),
        status_code=rp_resp.status_code,
        headers=rp_resp.headers,
        background=BackgroundTask(rp_resp.aclose),
    )


def sortAndMoveDev(data: list) -> list:
    data = sorted(data, reverse=True)
    if "dev" in data:
        data.insert(0, data.pop(data.index("dev")))
    return data


def s3GetDirs(access_key: str, secret_key: str, region: str, bucket: str) -> list:
    session = boto3.Session()
    client = session.client(
        service_name="s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
    objects = client.list_objects(Bucket=bucket, Delimiter="/")
    prefixes = objects.get("CommonPrefixes")
    if prefixes:
        directories = [name.get("Prefix").split("/")[0] for name in prefixes]
        return sortAndMoveDev(directories)
    return []


@app.get("/api")
async def root():
    return s3GetDirs(args.access_key, args.secret_key, args.region, args.bucket)


@app.get("/")
async def root():
    with open("/static/index.html") as file:
        data = file.read()
    return Response(content=data, media_type="text/html")


app.add_route("/{path:path}", _reverse_proxy, ["GET"])


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, workers=1)
