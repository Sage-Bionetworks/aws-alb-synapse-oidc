#!/usr/bin/env python3
#
# This script registers a new OAuth client with Synapse using the given app
# name and redirect URL and prints the client secret. The client must then
# be verified by emailing the following to synapseinfo@sagebase.org: your
# name, the client ID (see script output), and a description of your app.
#
# Usage:
#   create_client.py app_name app_redirect_url

import sys
import json
import synapseclient

# Define client attributes
client_name = str(sys.argv[1])
redirect_uri = str(sys.argv[2])
client = {
    "client_name": client_name,
    "redirect_uris": [redirect_uri],
    "userinfo_signed_response_alg": None,  # AWS ALB requires `None` here
    # The following fields are optional:
    # "client_uri": "https://example.com/index.html",
    # "policy_uri": "https://example.com/policy",
    # "tos_uri": "https://example.com/terms_of_service",
}

# Create OAuth client
syn = synapseclient.login()
client = syn.restPOST(
    uri="/oauth2/client", endpoint=syn.authEndpoint, body=json.dumps(client)
)

# Generate and retrieve the client secret:
client_id = client["client_id"]
client_id_and_secret = syn.restPOST(
    uri=f"/oauth2/client/secret/{client_id}", endpoint=syn.authEndpoint, body=""
)
print(client_id_and_secret)
