---
title: Jenkins Agents on EC2 Spot Instances
slug: jenkins-agents-ec2-spot-instances
category: AWS
tags: AWS, EC2, Jenkins, Spot Instances, CI/CD
excerpt: A proof of concept for scaling Jenkins agents on spot pricing with the EC2-Fleet plugin — cheaper builds, no idle capacity.
date: 2022-01-06
---

Inspired by how Lyft scaled their Jenkins infrastructure, I put together a proof of concept for running Jenkins agents on EC2 Spot instances instead of always-on boxes — using the EC2-Fleet plugin and an Auto Scaling Group to provision agents only when there's actually a job to run.

### What this was meant to prove

- Jobs can run on spot instances without issues
- Agents scale automatically with the job queue
- Spot pricing meaningfully cuts the cost of CI infrastructure
- The master node itself can be downsized once it's no longer running builds directly

### The stack

Jenkins (master + agents), EC2 Spot Instances, the EC2-Fleet plugin, an Auto Scaling Group, and IAM.

### How it fits together

The Jenkins master runs on a normal EC2 instance. The EC2-Fleet plugin watches the build queue and provisions spot instance agents on demand, within limits you set on the Auto Scaling Group.

### Setting up the Jenkins master

Launch an Amazon Linux 2 instance (a `t2.micro` is enough) with this user data:

```bash
#!/bin/bash
wget -q -O — https://pkg.jenkins.io/debian-stable/jenkins.io.key
sudo sh -c 'echo deb http://pkg.jenkins.io/debian-stable binary/ > /etc/apt/sources.list.d/jenkins.list'
sudo yum update -y
sudo yum install java-1.8.0-openjdk -y
sudo wget -O /etc/yum.repos.d/jenkins.repo http://pkg.jenkins-ci.org/redhat/jenkins.repo
sudo rpm --import https://pkg.jenkins.io/redhat/jenkins.io.key
sudo amazon-linux-extras install epel -y
sudo yum install jenkins -y
sudo service jenkins start
```

Use a VPC with DNS enabled, a public subnet with an internet gateway, and turn on auto-assigned public IPs.

Once it's up, hit the instance's public IP on port 8080. Grab the initial admin password with:

```bash
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

Run through the setup wizard — install the suggested plugins and create an admin user.

### Give the fleet plugin an IAM identity

Create an IAM user (`Ec2-fleet-user`) with programmatic access and this policy:

```json
{
   "Version":"2012-10-17",
   "Statement":[
      {
         "Effect":"Allow",
         "Action":[
            "ec2:DescribeSpotFleetInstances",
            "ec2:ModifySpotFleetRequest",
            "ec2:CreateTags",
            "ec2:DescribeRegions",
            "ec2:DescribeInstances",
            "ec2:TerminateInstances",
            "ec2:DescribeInstanceStatus",
            "ec2:DescribeSpotFleetRequests"
         ],
         "Resource":"*"
      },
      {
         "Effect":"Allow",
         "Action":[
            "autoscaling:DescribeAutoScalingGroups",
            "autoscaling:UpdateAutoScalingGroup"
         ],
         "Resource":"*"
      },
      {
         "Effect":"Allow",
         "Action":[
            "iam:ListInstanceProfiles",
            "iam:ListRoles",
            "iam:PassRole"
         ],
         "Resource":"*"
      }
   ]
}
```

Download the access key CSV — the plugin needs it during configuration.

### Launch template + Auto Scaling Group

Create a launch template (`EC2-fleet-launch-template`) using the `amzn2-ami-hvm` AMI on a `t3.small`, with spot instance requests enabled, and this user data:

```bash
#!/bin/bash -xe
sudo amazon-linux-extras install epel -y
sudo yum update -y
sudo yum remove java-1.7.0-openjdk
sudo yum install java-1.8.0-openjdk -y
sudo yum install git -y
sudo yum -y update aws-cli
```

Build an Auto Scaling Group from that template — desired 1, minimum 1, maximum 4 — spread across the same VPC's private subnets as the master.

### Installing the plugin

**Manage Jenkins → Manage Plugins**, search for `ec2-fleet`, install without restart, then restart Jenkins.

### Wiring it up

**Manage Jenkins → Manage Nodes and Clouds → Configure Clouds**, add an **Amazon EC2 Fleet** cloud:

1. Add AWS credentials using the IAM user's access key and secret
2. Pick the right region
3. The Auto Scaling Group should auto-populate
4. Test the connection
5. Set the launcher to SSH, using the Jenkins master's private key
6. Configure: 1 executor, 5 max idle minutes before scale-down, minimum cluster size 1, maximum cluster size 5, label `spot-agents`
7. Use the non-verifying verification strategy, and select Private IP for internal traffic

### A test build

A freestyle job (`sai-test-build`) pointed at `https://github.com/psdilip/python.git`, with an Execute Shell step running:

```bash
python3 basics.py
```

Kick off the build and watch the Build Executor Status — you'll see the fleet provision an instance in real time, and the console log fills in as usual.

### The result

The EC2-Fleet plugin deployed spot instances as Jenkins agents and ran jobs in parallel without any manual provisioning, all while cutting infrastructure cost and taking load off the master node entirely. It's a solid foundation to build a larger CI/CD setup on top of.
