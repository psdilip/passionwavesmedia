---
title: "Personal Website on AWS, Part 1: S3"
slug: personal-website-on-aws-part-1
category: AWS
tags: AWS, S3, Static Hosting
excerpt: Skip Wix and Squarespace — host a real static site on S3 and actually understand what's happening under the hood.
date: 2021-05-31
---

![Photo by John Schnobrich on Unsplash](https://miro.medium.com/v2/resize:fit:1400/0*sy3DbaNstc2e_k8Q)
*Photo by John Schnobrich on Unsplash*

Wix, Squarespace, and WordPress will get you a website faster, but building one on S3 teaches you something those platforms hide from you entirely. This isn't a design tutorial — it's the infrastructure underneath.

This is Part 1 of two: this half covers the bare-minimum S3 setup. [Part 2](/personal-website-on-aws-part-2.html) adds a custom domain, SSL, and CloudFront.

You'll need an AWS account already set up before starting.

### What S3 actually is

S3 is cheap, highly available, durable cloud storage that can hold basically any volume or type of data — static website hosting is just one of many things it's built for.

### Creating the bucket

1. Open the S3 service in the console
2. Click **Create a bucket**
3. **Bucket name** — use your intended domain (e.g. `saidilipponnaganti` for `saidilipponnaganti.com`)
4. **Region** — `us-east-1` is a safe default
5. **Block Public Access** — uncheck "Block all public access" and acknowledge the warning
6. Leave everything else default and click **Create bucket**

### Uploading your site

1. Have your HTML/CSS ready (a free template from HTML5 UP works fine if you don't have your own design yet)
2. Click **Upload** inside the bucket
3. Drag your files in
4. Click **Upload** and wait for it to finish
5. Close the status page

### Turning on static website hosting

1. In the **Properties** tab, find **Static website hosting** and click **Edit**
2. Select **Enable**
3. Choose **Host a static website**
4. Set the **index document** to your main HTML file (required)
5. Optionally set an **error document**
6. Save — a hosting link now appears at the bottom of the Properties tab

That link will 403 for now — that's the permissions step, next.

### Setting permissions

1. Go to the **Permissions** tab
2. Confirm public access is allowed (type "confirm" if prompted)
3. Under **Bucket Policy**, click **Edit** and paste:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::BucketName/*"
        }
    ]
}
```

4. Replace `BucketName` with your actual bucket's name
5. Save, then revisit your hosting link — the site should load

### Static vs. dynamic, quickly

**Static** sites are just HTML and CSS — the same content for every visitor, fast to load, cheap to build, with the content baked right into the code. Good for informational sites.

**Dynamic** sites respond differently per user and lean on server-side code like PHP or Node.js — more capability, more moving parts.

### Worth turning on later (small extra cost)

- **Bucket versioning** — recover from an accidental delete
- **Default encryption** — protect data at rest

### Next up

[Part 2](/personal-website-on-aws-part-2.html) covers CloudFront, buying a real domain, and getting HTTPS working with a free SSL certificate.
