# AWS Application Load Balancer with Synapse OIDC

This repository contains the instructions and files necessary to set up an AWS application load balancer (ALB) in front of a web app that restricts access to members of select Synapse teams. 

## Prerequisites

- You have an AWS account with a VPC configured with both public and private subnets
- Your web app is running on an EC2 instance in a private subnet (_i.e._ without a public IP) or can be deployed with a container
- Your web app isn't running on port 443 (needed for reverse proxy)
- You are using the `us-east-1` AWS region (if not, search-and-replace all instances of `us-east-1` in this repository with the appropriate region)
- You have a URL for your web app and the corresponding SSL/TLS certificate to enable HTTPS traffic
- You have a Synapse account
- You have a Python 3 installation

## Step 1: Create a Synapse OAuth client

The detailed instructions for creating a Synapse OAuth client can be found [here](https://help.synapse.org/docs/Using-Synapse-as-an-OAuth-Server.2048327904.html#UsingSynapseasanOAuthServer-CreateanOAuth2.0Client), but the essential steps are captured in the included `create_alb_oauth_client.py` Python script and hav been adapted for use with AWS ALBs.

**N.B.** Don't forget the quotes around your app name if it includes spaces.

```bash
# Optional: Create an isolated virtual environment
# python3 -m venv .venv
# source .venv/bin/activate

python3 -m pip install synapseclient
create_alb_oauth_client.py "App Name" "https://app.example.com"
```

Once you run the `create_alb_oauth_client.py` script, you will need to verify the OAuth client by emailing `synapseinfo@sagebase.org` with the following information:

- Your name
- The ID of the client to be verified (see script output; don't share the client secret)
- A description of your application

## Step 2: Deploy the Reverse Proxy and Test App

This repository includes a Dockerfile for deploying the reverse proxy. The `docker-compose.yml` file includes the reverse proxy and a simple test app. If your web app if it's containerized, you can adapt this `docker-compose` file to deploy the reverse proxy alongside your app.

You can deploy the reverse proxy on the EC2 instance that's already hosting your web app or you can dedicate a small EC2 instance for the reverse proxy. In either case, the instance should be in a private subnet since the load balancer is going to be the public/internet-facing gateway.

1. Log into the EC2 instance that will host the reverse proxy
2. Install `git`, `docker` and `docker-compose` on the instance
3. Log into Docker Hub using `docker login`
4. Clone this repository to the instance
5. Edit the `AUTHORIZED_TEAMS` comma-separated list in the `.env` file to include a team that you're a member of
6. From within the repository, deploy the `docker-compose` file with:
    ```
    docker-compose up --build --detach
    ```

## Step 3: Create an Application Load Balancer

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
7. Register the EC2 instance from Step 2 that's hosting the reverse proxy. 
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
        - Client ID: See output from `create_alb_oauth_client.py` script
        - Client secret: See output from `create_alb_oauth_client.py` script
        - Advanced settings:
            - Session cookie: `AWSELBAuthSessionCookie`
            - Session timeout: `604800`
            - Scope: `openid`
            - On unauthenticated: `authenticate`
        - Extra request parameters:
            - `claims`: `{"userinfo":{"user_name":null,"userid":null}}`
    6. Click on the "Update" button at the top right
    7. Click the left-pointing arrow (`<`) at the top left to return to the listeners page

## Step 4: Test the Reverse Proxy

At this point, the test app should be accessible via the reverse proxy as long as the Synapse user is a member on one of the specified teams. Try visiting the app URL that you provided to `create_alb_oauth_client.py` in Step 1. The load balancer should redirect you to a Synapse login page. After logging in, you should then be prompted to grant permission to your app (using the same you provided in Step 1) to access your user info. After allowing access, you will then be redirected to a test page with "It works!" If you're not a member of one of the specified teams, you should then face an "Unauthorized" page.

## Step 5: Update Reverse Proxy to Forward to Web App

Now that you've tested the load balancer and reverse proxy setup, you can update it to forward traffic to your actual web app. How this is done depends on whether the app is containerized and whether it's hosted on a remote host or not.

### Non-Containerized Web App (Local or Remote Host)

**N.B.** These instructions should work regardless of whether the non-containerized web app is running on the same host as the reverse proxy or a separate host. If not, reach out to use for help with debugging.

1. Comment out the `web_app` service in `docker-compose.yml`
2. Update the value for `APP_NAME` in `.env` to the private IP address of the EC2 instance running the web app
3. Update the value for `APP_PORT` in `.env` to the port number that's bound to the web app
4. Re-launch the reverse proxy as a background process with:
    ```
    # Run from within the repository directory
    docker-compose up --build --detach
    ```

### Containerized Web App (Local Host)

**N.B.** If your web app is containerized but running on a separate host, the instructions for non-containerized apps are more applicable.

1. Update the `web_app` service in `docker-compose.yml` to deploy your app container, although it's recommended to continue using the `APP_NAME` and `APP_PORT` variables to ensure consistency
2. Optionally, update the value for `APP_NAME` in `.env` to a more appropriate name
3. Update the value for `APP_PORT` in `.env` to the port number where the `web_app` container exposes the app
4. Re-launch the reverse proxy as a background process (along with the web app) with:
    ```
    # Run from within the repository directory
    docker-compose up --build --detach
    ```
