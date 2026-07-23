---
title: Cloud Dev Setup on Ubuntu
slug: ubuntu-dev-environment-setup
category: AWS
tags: AWS, Terraform, Python, Boto3, GitHub, Serverless
excerpt: A copy-paste setup guide for a full cloud dev environment on Ubuntu — editor, IaC, Python, AWS SDK, git, and the Serverless Framework.
date: 2018-12-02
---

Setting up a new machine for cloud work means the same handful of tools every time. Here's the whole setup, one piece at a time.

### Visual Studio Code

1. Download the Linux 64-bit `.deb` file from the [official VS Code docs](https://code.visualstudio.com/docs/setup/linux)
2. Open a terminal and go to your Downloads folder: `cd Downloads/`
3. Install it: `sudo dpkg -i code_1.28.2–1539735992_amd64.deb`
4. Launch it from the system search and add the extensions you want (Python, C/C++, C# are good starting points)

### Terraform

1. Download the Linux 64-bit build from [terraform.io/downloads.html](https://terraform.io/downloads.html)
2. Go to your Downloads folder
3. Unzip it: `unzip terraform_0.11.xx_linux_amd64.zip`
4. Move the binary onto your path: `sudo mv terraform /usr/local/bin`
5. Confirm it worked by just running `terraform`

### GitHub

1. Install git: `sudo apt-get -y install git`
2. Set your identity:
   - `git config --global user.name "your github username"`
   - `git config --global user.email "your github email address"`
3. You're ready to clone and commit

### Serverless Framework

1. Install curl: `sudo apt-get install curl`
2. Download Node.js: `curl -sL https://deb.nodesource.com/setup_11.x | sudo -E bash –`
3. Install Node.js: `sudo apt-get install -y nodejs`
4. Update the system: `sudo apt-get update && sudo apt-get upgrade`
5. Install build tools: `sudo apt-get install -y build-essential`
6. Install the framework: `sudo npm install -g serverless`

### Python

Ubuntu usually ships with 2.7.12 and 3.5.2 already installed. To get 3.6:

1. Add the repo: `sudo add-apt-repository ppa:jonathonf/python-3.6`
2. Update and install: `sudo apt-get update && sudo apt-get install python3.6`
3. Confirm with: `python3.6`

### Boto3

The AWS SDK for Python.

1. Install pip: `sudo apt-get install python-pip python-dev build-essential`
2. Install boto3: `pip install boto3`

### Jupyter Notebooks

1. Install it: `sudo python3 –m pip install jupyter`
2. Start one: `jupyter notebook`
3. It opens a local page in your browser where you can write and run code, equations, and notes side by side

That's the whole stack — editor, IaC, runtime, SDK, version control, and a serverless deploy tool, all from a clean Ubuntu install.
