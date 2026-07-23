---
title: Your First Website on S3
slug: s3-website
category: AWS
tags: AWS, S3, Static Hosting
excerpt: A calm, copy-paste-able walkthrough to get a real site live on AWS in an afternoon — no prior cloud experience needed.
date: 2026-07-08
---

You do not need to be an engineer to put a website on the internet with AWS. You need a bucket, a few clicks, and about an afternoon. Here's the whole thing, start to finish.

## 1. Make a bucket

A bucket is just a folder in the cloud. Create one, name it after your site, and drop your `index.html` inside.

## 2. Turn on website hosting

In the bucket settings, enable static website hosting and set the index document to `index.html`. AWS gives you a URL immediately.

## 3. Put CloudFront in front

CloudFront makes your site fast everywhere and gives you HTTPS. Point it at your bucket and you're done.

That's it. No servers to manage, pennies a month, and it scales whether one person visits or a million do.
