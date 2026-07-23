---
title: Installing Nginx via EC2 User Data
slug: installing-nginx-ec2-user-data
category: AWS
tags: AWS, EC2, Nginx, User Data
excerpt: Stand up an Nginx web server on a fresh EC2 instance with nothing but a user-data script — no manual SSH setup required.
date: 2022-01-02
---

![Photo by Sigmund on Unsplash](https://miro.medium.com/v2/resize:fit:1400/0*qRqceqwia11U1lJP)
*Photo by Sigmund on Unsplash*

Nginx is an open-source web server that also handles reverse proxying, caching, load balancing, media streaming, and logging. Here's how to get it running on EC2 with zero manual setup, using nothing but the instance's user data.

### A few terms, quickly

- **Web server** — hardware and software that serves data over HTTP
- **Reverse proxy** — a server that sits in front of your origin server, accepting public requests and relaying them while keeping your actual server hidden
- **Caching** — a copy of frequently requested data kept somewhere fast, so you're not re-fetching it every time
- **Load balancing** — spreads traffic across multiple servers so no single one gets overwhelmed
- **Media streaming** — delivers video and audio to clients as they request it
- **Logging** — records of application and server behavior for later review

### What you need

An AWS account, plus a VPC, internet gateway, and public subnet already set up.

### Installing Nginx

1. Go to EC2 → **Launch instances**
2. Choose **Amazon Linux 2 AMI (64-bit x86)**
3. Pick an instance type — `t2.micro` is plenty for testing
4. Set the VPC and turn on **Auto-assign Public IP**
5. Add this to **User data**:

```
#!/bin/bash
sudo yum update -y
sudo amazon-linux-extras install nginx1 -y
sudo systemctl enable nginx
sudo systemctl start nginx
```

6. Leave storage at the default
7. Add whatever tags you use for organization
8. Create a security group allowing SSH and port 80
9. Review and launch
10. Create or select a key pair
11. Visit the instance's public IP in a browser to confirm it's up

### If it doesn't show up

- Check the instance's system log first
- SSH in and run `sudo systemctl status nginx`
- If it's still not right, check `/var/log/nginx/` for the actual error

### Where to go from here

From this baseline, it's worth digging into Nginx's config files and command set to start using it for what it's actually good at — reverse proxying, caching, load balancing, and streaming.
