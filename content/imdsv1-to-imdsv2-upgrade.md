---
title: Upgrading EC2 to IMDSv2
slug: imdsv1-to-imdsv2-upgrade
category: AWS
tags: AWS, EC2, IMDSv2, Security
excerpt: Why the original instance metadata service was a security gap, and the exact commands to move every instance to the authenticated version.
date: 2022-02-16
---

![Photo by Christina @ wocintechchat.com on Unsplash](https://miro.medium.com/v2/resize:fit:1400/0*GZbP2GiCu3cI00Yw)
*Photo by Christina @ wocintechchat.com on Unsplash*

Every EC2 instance exposes a metadata service — identity credentials, IAM info, metrics, public keys, security groups — but only from inside that instance. The catch: if someone ever gets a foothold on the instance itself, that data is theirs too.

### The two versions

- **IMDSv1**: a plain request/response method
- **IMDSv2**: a session-oriented method

### The problem with v1

IMDSv1 doesn't authenticate metadata requests at all. If something on the instance can make an HTTP request (including, say, a compromised app process), it can pull credentials straight out of the metadata service.

### What v2 fixes

IMDSv2 requires a token before it'll return anything. It's session-based, the token expires after a set time, and that one change closes the gap entirely.

### How to upgrade your existing instances

**1. Find the instances that still need upgrading.** AWS Trusted Advisor will flag them if you have it enabled.

**2. Check the current setting:**

```
aws ec2 describe-instances --instance-ids <enter-your-instance-id>
```

Look at the `MetadataOptions` field in the response.

**3. Require v2:**

```
aws ec2 modify-instance-metadata-options --instance-id <enter-your-instance-id> --http-tokens required --http-endpoint enabled --http-put-response-hop-limit 1
```

**4. Confirm it took** by running the describe-instances command again.

**5. Test it from inside the instance.** An unauthenticated request should now fail.

**6. Request metadata the v2 way:**

```
TOKEN=`curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"`
curl -H "X-aws-ec2-metadata-token: $TOKEN" -v http://169.254.169.254/latest/meta-data/
```

That's the whole migration. It's a small change with a real security payoff, and there's very little reason not to require it on every instance you run.

## Practical guide: the upgrade checklist

A condensed, copy-pasteable version of the steps above.

1. **Find out which instances are still on v1.** Check AWS Trusted Advisor if you have it enabled; it flags them for you.
2. **Check the current setting on an instance** with `aws ec2 describe-instances --instance-ids <enter-your-instance-id>` and look at the `MetadataOptions` field in the response.
3. **Require v2 on that instance:** `aws ec2 modify-instance-metadata-options --instance-id <enter-your-instance-id> --http-tokens required --http-endpoint enabled --http-put-response-hop-limit 1`.
4. **Confirm the change took** by running the same `describe-instances` command again and re-checking `MetadataOptions`.
5. **Test from inside the instance.** An unauthenticated metadata request should now fail.
6. **Request metadata the v2 way, to confirm it works.** Get a token first with `curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"`, then pass it along with `curl -H "X-aws-ec2-metadata-token: $TOKEN" -v http://169.254.169.254/latest/meta-data/`.
