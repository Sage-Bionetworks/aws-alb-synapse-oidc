# AWS Application Load Balancer with Synapse OIDC

This repository contains the instructions and files necessary to set up an AWS application load balancer in front of a web app that restricts access to members of select Synapse teams. 

## Step 1: Create a Synapse OAuth client

The detailed instructions for creating a Synapse OAuth client can be found [here](https://help.synapse.org/docs/Using-Synapse-as-an-OAuth-Server.2048327904.html#UsingSynapseasanOAuthServer-CreateanOAuth2.0Client), but the essential steps are captured in the included `create_client.py` Python script. This step assumes that you already have an HTTPS URL for your web app and that you have Python 3 installed. You will also need to login with a Synapse account.

**N.B.** Don't forget the quotes around your app name if it includes spaces.

```bash
# Optional: Create an isolated virtual environment
# python3 -m venv .venv
# source .venv/bin/activate
python3 -m pip install synapseclient
create_client.py "Demo App" "https://demo-app.sagesandbox.org"
```

Once you run the `create_client.py` script, you will need to verify the OAuth client by emailing `synapseinfo@sagebase.org` with the following information:

- Your name
- The ID of the client to be verified (see script output)
- A description of your application

## Step 2: Create an Application Load Balancer

This step and those that follow assume that you have an AWS account configured with a VPC with public and private subnets where the web app will be hosted. It also assumes that you have a domain with an SSL/TLS certificate. 

1. In the EC2 console, click the "Create Load Balancer" button in the "Load Balancers" interface (usually found near the bottom of the left-hand sidebar).
2. Select the "Application Load Balancer" option. 
3. Configure the load balancer as follows:
    - Name: `<app-name>-alb-with-synapse-oidc`
    - Scheme: `internet-facing`
    - IP address type: `ipv4`
    - Listeners: 
        - `HTTP` (with port `80`)
        - `HTTPS` (with port `443`)
    - VPC: Pick the VPC with public and private subnets
    - Availability zones: Enable all zones and select a public subnet for each zone
4. Configure the security settings as follows:
    - Certificate type/name: Select the appropriate certificate
    - Security policy: `ELBSecurityPolicy-2016-08`
5. Create a new security group with the following rules:
    - Security group name: `<app-name>-alb-sg`
    - Description: `Allow HTTP(S) traffic from the internet`
    - Rule 1:
        - Type: `HTTP`
        - Source: `Anywhere`
    - Rule 2 (if using HTTPS):
        - Type: `HTTPS`
        - Source: `Anywhere`
6. Configure routing using a new target group with the following configuration:
    - Name: `<app-name>-alb-ec2-targets`
    - Target type: `Instance`
    - Protocol: `HTTPS`
    - Port: Leave as default based on the protocol
    - Health checks: Update based on the web app
7. Register the EC2 instance(s) hosting the web app. 
8. Review and create the load balancer. 
9. Click on the newly created load balancer in the "Load Balancers" interface and open the Listeners tab. 
10. Change the HTTP (port 80) listener to upgrade traffic to HTTPS (port 443) as follows:
    1. Click on "View/edit rules" for HTTP (port 80) listener
    2. Click on the pencil (edit) icon at the top
    3. Click on the pencil icon at the left of the default rule
    4. Click on the garbage (delete) icon to delete the existing "Forward to" rule
    5. Click the "Add action" button and select "Redirect to..."
    6. Configure the action as follows and then click the checkmark icon:
        - `HTTPS`
        - `443` (the only value that needs to be added)
        - `Original host, path, query`
        - `301 - Permanently moved`
    7. Click on the "Update" button at the top right
    8. Click the left-pointing arrow (`<`) at the top left to return to the listeners page
11. Change the HTTPS (port 443) listener to authenticate traffic prior to forwarding as follows:
    1. Click on "View/edit rules" for HTTPS (port 443) listener
    2. Click on the pencil (edit) icon at the top
    3. Click on the pencil icon at the left of the default rule
    4. Click the "Add action" button and select "Authenticate..."
    5. Configure the action as follows and then click the checkmark icon:
        - Authenticate: `OIDC`
        - Issuer: `https://repo-prod.prod.sagebase.org/auth/v1`
        - Authorization endpoint: `https://signin.synapse.org`
        - Token endpoint: `https://repo-prod.prod.sagebase.org/auth/v1/oauth2/token`
        - User info endpoint: `https://repo-prod.prod.sagebase.org/auth/v1/oauth2/userinfo`
        - Client ID: See output from `create_client.py` script
        - Client secret: See output from `create_client.py` script
        - Advanced settings:
            - Session cookie: `AWSELBAuthSessionCookie`
            - Session timeout: `604800`
            - Scope: `openid`
            - On unauthenticated: `authenticate`
        - Extra request parameters:
            - `claims`: `{"userinfo":{"user_name":null,"userid":null}}`
    6. Click on the "Update" button at the top right
    7. Click the left-pointing arrow (`<`) at the top left to return to the listeners page
