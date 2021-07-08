#!/usr/bin/env python

import os
import jwt
import requests
import base64
import json

from mod_python import apache

region = "us-east-1"


def headerparserhandler(req):

    jwt = req.headers_in["x-amzn-oidc-data"]  # proxy.conf ensures this header exists

    # Client configured with claims as:
    # {"userinfo":{"user_name":null,"userid":null}}

    payload = session_user(jwt)

    req.log_error("payload: " + str(payload), apache.APLOG_WARNING)

    if "userid" not in payload or "user_name" not in payload:
        return apache.HTTP_INTERNAL_SERVER_ERROR

    user = str(payload["user_name"])
    user_id = str(payload["userid"])

    teams = get_team_ids(user_id)

    req.log_error("teams (" + user + "): " + str(teams), apache.APLOG_WARNING)

    # Add header for Shiny app
    req.headers_in["X-User"] = user

    authorized_teams = os.environ.get("AUTHORIZED_TEAMS")

    if authorized_teams is None:
        authorized_teams_source = "defaults"
        authorized_teams = [
            "273957",  # Sage Bionetworks
        ]
    else:
        authorized_teams_source = "environment"
        authorized_teams = authorized_teams.split(",")

    req.log_error(
        (
            "authorized_teams (from " + authorized_teams_source +
            "): " + str(authorized_teams)
        ),
        apache.APLOG_WARNING
    )

    if any(t in teams for t in authorized_teams):
        return apache.OK
    else:
        # The given user isn't in an authorized team
        return apache.HTTP_UNAUTHORIZED


def session_user(encoded_jwt):

    # The x-amzn-oid-data header is a base64-encoded JWT signed by the ALB
    # validating the signature of the JWT means the payload is authentic
    # per http://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-authenticate-users.html
    # Step 1: Get the key id from JWT headers (the kid field)
    # encoded_jwt = headers.dict['x-amzn-oidc-data']
    jwt_headers = encoded_jwt.split(".")[0]

    decoded_jwt_headers = base64.b64decode(jwt_headers)
    decoded_jwt_headers = decoded_jwt_headers.decode("utf-8")
    decoded_json = json.loads(decoded_jwt_headers)
    kid = decoded_json["kid"]

    # Step 2: Get the public key from regional endpoint
    url = "https://public-keys.auth.elb." + region + ".amazonaws.com/" + kid
    req = requests.get(url)
    pub_key = req.text

    # Step 3: Get the payload
    payload = jwt.decode(encoded_jwt, pub_key, algorithms=["ES256"])
    # TODO handle validation errors, this call validates the signature

    return payload


def get_team_ids(user_id):
    # Use Synapse API to retrieve teams for given user ID
    api_base_url = "https://repo-prod.prod.sagebase.org/repo/v1"

    # Build endpoint URL
    teams_url = api_base_url + "/user/" + user_id + "/team/id"

    # Send request and parse response as JSON
    teams_req = requests.get(teams_url)
    teams_json = teams_req.json()

    # Ensure that all teams IDs are ASCII strings
    teams = [str(t) for t in teams_json[u"teamIds"]]

    return set(teams)
