---
title: Presigned URLs for S3 with the CLI
slug: s3-presigned-urls-cli
category: AWS
tags: AWS, S3, CLI, Presigned URLs
excerpt: A walkthrough for sharing a single private S3 object temporarily — no public bucket required.
date: 2022-05-18
---

![Photo by Scott Graham on Unsplash](https://miro.medium.com/v2/resize:fit:1400/0*yv7UhxzgMNL6QFvx)
*Photo by Scott Graham on Unsplash*

AWS Support puts it plainly: "If you are using presigned URLs, you don't need to make the bucket public, and in fact, it may be better not to." That's the whole appeal — you get to share one object, for a limited time, without opening the bucket up.

### Why you'd want this

S3 is cheap enough that storage usage tends to grow past its original purpose. Two examples that come up a lot:

- A delivery photo gets dropped into S3 the moment a package arrives, and the link to it should expire after a set window.
- An ETL job extracts a customer's data into an S3 object, and you want to hand them a link that works for a day, not forever.

### Before you start

- Console and CLI access to an active AWS account
- Permissions on the S3 service

*(These steps are for learning the mechanism — not necessarily a production-ready pattern as-is.)*

### Step by step

**1. Create a bucket.** A bucket is just a container for objects — think of it like a folder in the cloud.

**2. Set it up:**
- **Name** — anything unique and relevant to what you're storing
- **Region** — wherever makes sense for your app or your latency needs
- **Copy settings from an existing bucket** — leave blank
- **Object ownership** — leave default
- **Block public access** — leave *all* public access blocked
- **Versioning** — only if you need to track multiple versions of the same object
- **Tags** — whatever your org standard is
- **Default encryption** — turn it on; SSE-S3 (Amazon S3-managed keys) is a fine default
- **Advanced settings** — leave default

**3. Create the bucket.**

**4. Confirm it shows up in the console.**

**5. Upload an object** — drag a file in from your machine.

**6. Generate the presigned URL.** With the CLI pointed at the right account:

```
aws s3 presign --endpoint-url https://s3.{region}.amazonaws.com s3://{bucketname}/{object} --region {region} --expires-in {seconds}
```

An example from my own testing:

```
aws s3 presign --endpoint-url https://s3.us-east-1.amazonaws.com s3://sai-pre-signed-url-test/Dance.mov --region us-east-1 --expires-in 86400
```

That expires in 86,400 seconds — 24 hours.

**7. Use it.** Paste the resulting URL (starting with `https://s3.us-east-1...`) into a browser. It stops working once the expiry hits, but the object itself is untouched in the bucket.

### Worth reading next

- [AWS CLI `s3 presign` reference](https://docs.aws.amazon.com/cli/latest/reference/s3/presign.html)
- [S3 security best practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
- [Sharing objects using presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html)

### Where to take it from here

- Add a lifecycle policy so the object cleans itself up automatically
- Layer in bucket policies for defense in depth
- If you're generating a lot of these, look at a URL shortener so they're easier to hand off
