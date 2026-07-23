---
title: Windows Access via Session Manager, No RDP Port
slug: session-manager-windows-no-rdp-port
category: AWS
tags: AWS, EC2, Session Manager, Security
excerpt: Get shell and RDP access to a Windows EC2 instance through Systems Manager, then close port 3389 in the security group for good.
date: 2022-01-01
---

![Photo by Christina @ wocintechchat.com on Unsplash](https://miro.medium.com/v2/resize:fit:1400/0*Sl3gnlPFQn9Q-8On)
*Photo by Christina @ wocintechchat.com on Unsplash*

Session Manager, part of AWS Systems Manager, gives you controlled, secure shell access to a Windows or Linux instance without ever opening a port in the security group. Here's how to use it to reach a Windows box — including RDP — without 3389 open to the world.

### What this walkthrough assumes

- A Windows instance in a public subnet, with RDP open for the initial setup
- The AWS CLI configured on your local machine

### The shape of it

- Install the SSM Agent on the instance
- Attach the right IAM role so SSM has permission to manage it
- Console in through Session Manager and add a new user to the RDP group
- Install the Session Manager plugin locally, then port-forward RDP through it

### Step 1 — install the SSM Agent (over RDP, one last time)

Connect via RDP as usual — select the instance, click **Connect**, choose the RDP client, download the RDP file, and decrypt the password with your key file. Once you're in, open PowerShell and run the four commands to download and install the AmazonSSMAgent, register it on the system path, clean up the installer, and restart the service.

### Step 2 — attach the SSM role

On the instance, go to **Actions → Security → Modify IAM Role**, and attach the AWS-managed role `AmazonSSMRoleForInstancesQuickSetup`.

Confirm it worked: open **Systems Manager → Session Manager**, click **Start Session**, and your instance should show up as available.

### Step 3 — add a user to the RDP group, from inside Session Manager

In the Session Manager shell:

1. Store a password in a variable with `Read-Host -AsSecureString`
2. Create a new local user (e.g. `Sai`) with that password
3. Add that user to the **Remote Desktop Users** group

### Step 4 — port-forward RDP through Session Manager

Install the Session Manager plugin locally, and confirm it with `session-manager-plugin` in a new PowerShell window.

Start the forwarding session:

```
aws ssm start-session --target <instance-id> --document-name AWS-StartPortForwardingSession --parameters "localPortNumber=54231,portNumber=3389" --region <region>
```

Open Remote Desktop Connection locally, set the computer to `localhost:54231`, the username to `Sai`, connect, and enter the password.

Once that connects cleanly, remove port 3389 from the security group entirely — access still works, just without the open port.

### Worth reading alongside this

- AWS's SSM Agent installation docs
- The managed-instance setup guide
- The Session Manager plugin install docs
- AWS's own walkthrough video on Session Manager
