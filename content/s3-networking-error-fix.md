---
title: Fixing an S3 Networking Error
slug: s3-networking-error-fix
category: AWS
tags: AWS, S3, Troubleshooting
excerpt: A quick fix for the confusing "networking error" or "access denied" message in the S3 console when your permissions are actually fine.
date: 2022-04-23
---

Every so often the S3 console throws a networking error, or an "access denied" message, even though the permissions on your account are completely fine. It's an annoying one because the error doesn't point at the real cause.

I'm not entirely sure of the root cause — my best guess is a buildup of cookies from AWS sessions, especially if you're jumping between multiple accounts in the same browser. Could also just be a browser quirk.

Either way, the fix is almost always one of these three, in order of how often they work for me:

1. Clear your browser cache
2. Try a different browser entirely
3. Log out of the AWS account and log back in

Nine times out of ten, one of those three clears it up before you need to go any deeper.
