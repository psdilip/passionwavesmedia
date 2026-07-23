---
title: "Personal Website on AWS, Part 2: CloudFront & SSL"
slug: personal-website-on-aws-part-2
category: AWS
tags: AWS, CloudFront, Route 53, SSL
excerpt: Turn the bare S3 site from Part 1 into a real HTTPS site on your own domain, served fast from CloudFront's edge network.
date: 2021-05-31
---

![Photo by Christopher Gower on Unsplash](https://miro.medium.com/v2/resize:fit:1400/0*hcu8vevpyXv2nG0K)
*Photo by Christopher Gower on Unsplash*

This picks up right where [Part 1](/personal-website-on-aws-part-1.html) left off — a working static site on S3, but on an ugly S3 URL with no HTTPS. Three services fix that: CloudFront, Route 53, and AWS Certificate Manager.

### Setting up CloudFront

CloudFront is a CDN — a geographically distributed network of edge locations that serves your content from whichever one is physically closest to the visitor, cutting latency everywhere.

1. Open the CloudFront service
2. Click **Create Distribution**
3. Click **Get Started**

**Origin settings**
- **Origin Domain Name** — paste your S3 static-hosting endpoint, in the form `<BucketName>.s3-website.us-east-2.amazonaws.com`
- Leave everything else default

**Default cache behavior**
- **Viewer Protocol Policy** — set to **Redirect HTTP to HTTPS**
- Save

Deployment takes 15–30 minutes. Once it's done, the CloudFront link should serve your site.

### Registering a domain in Route 53

Route 53 is AWS's DNS service — it's what routes requests for your domain to the CloudFront distribution.

1. Open Route 53, then **Registered Domains**
2. Click **Register Domain**
3. Search for the domain you want and check the price
4. Add it to the cart
5. Enter your contact details
6. Review and accept the terms
7. Complete the order

Registration usually finishes within a couple of hours.

### Pointing the domain at CloudFront

A **hosted zone** holds all the DNS records for your domain (A, CNAME, NS, etc.), and one gets created automatically when you register.

1. Open **Hosted Zones**
2. Click into your domain's zone
3. Create an **A record**
4. Toggle **Alias**, choose **Alias to CloudFront Distribution**
5. Paste in your CloudFront domain name
6. Click **Create records**

### Getting a free SSL certificate

Without SSL, anything visitors submit to your site travels unencrypted — worth fixing before you share the link with anyone.

1. Open **AWS Certificate Manager** — make sure you're in **us-east-1 / N. Virginia**, since that's the only region CloudFront will accept certificates from
2. Click **Provision Certificates → Request a public certificate**
3. Click **Request a certificate**
4. Enter your domain name
5. Choose **DNS validation**
6. Click through **Next → Review → Confirm and Request**
7. Click **Create a record in Route 53**

Validation usually completes within a few minutes.

### Wiring the certificate into CloudFront

1. Select your distribution → **Distribution Settings → Edit**
2. **Alternate Domain Names (CNAMEs)** — enter your domain (e.g. `saismyhero.com`)
3. **SSL Certificate** — choose **Custom SSL Certificate** and select the one you just validated
4. Save

From here, `https://your_domain.com` serves the site directly, and plain HTTP requests redirect to HTTPS automatically.

### What you end up with

CloudFront for fast, edge-cached delivery, Route 53 for the domain and DNS, and ACM for the SSL certificate securing the connection — a real website, on your own domain, over HTTPS, for a few dollars a year.

### Where to take it next

Add a résumé, blog posts, photography, past projects, and links to GitHub and LinkedIn. And as a bonus project: wire up CI/CD so pushing to your main branch redeploys the site automatically.
