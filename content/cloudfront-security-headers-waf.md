---
title: "Implementing Security Headers with CloudFront — Architecture and Step-by-Step Guide"
slug: cloudfront-security-headers-waf
category: AWS
tags: AWS, CloudFront, WAF, Security Headers, CSP, ALB, Security
excerpt: CloudFront is built for latency and global delivery — but its response headers policies make it one of the cleanest ways to add a security layer to any web application running behind an ALB.
date: 2026-10-01
---

![Photo by Stone John on Unsplash](https://images.unsplash.com/photo-1733195296321-b99d129b09cd?w=1600&q=80&fm=jpg&fit=crop)
*Global edge network · Photo by [Stone John](https://unsplash.com/@abigvicky) on [Unsplash](https://unsplash.com)*

This is Part 2 of a two-part series. Part 1 covers how browser-server communication works, what security headers enforce, and how a penetration test surfaces the gaps. If you're new to the topic, start [there](/web-security-headers-explained.html). This article is the implementation guide.

CloudFront's primary use cases are performance: reducing latency through edge caching, serving static assets globally, and offloading traffic from your origin. Once it's in front of your application, the same architecture also unlocks the ability to attach security headers to every response — without touching backend code.

The setup covered here was driven by a pen test finding: a web application running behind an Application Load Balancer was missing key security headers that the ALB couldn't add natively. CloudFront was already planned for future performance improvements. The pen test accelerated the timeline.

### The Starting Point

The application used a standard AWS setup before CloudFront was added:

```
┌──────────┐     DNS      ┌──────────┐    A Record    ┌─────────────────────────┐
│  Browser │ ──────────▶  │ Route 53 │ ─────────────▶ │   ALB (public subnet)   │
└──────────┘              └──────────┘                 │   Security Group:       │
                                                       │   0.0.0.0/0 → 443      │
                                                       └────────────┬────────────┘
                                                                    │  Listener
                                                                    ▼
                                                         ┌──────────────────────┐
                                                         │   Target Group        │
                                                         │   (ECS / EC2)         │
                                                         └──────────────────────┘
                                                                    ▲
                                                           WAF Web ACL (Regional)
                                                           attached to ALB
```

Route 53 resolves the domain to the ALB's public DNS name. The ALB's security group accepts traffic from the entire internet on port 443. Listeners route requests to the target group, and the app responds. WAF is a regional Web ACL attached directly to the ALB.

This works — but the ALB is exposed directly to the internet, and there's no mechanism to inject response headers at this layer.

### The Architecture After CloudFront

```
┌──────────┐    DNS     ┌──────────┐    Alias    ┌────────────────────────────────────┐
│  Browser │ ─────────▶ │ Route 53 │ ──────────▶ │        CloudFront Distribution     │
└──────────┘            └──────────┘             │                                    │
                                                 │  ┌──────────────────────────────┐  │
                                                 │  │  WAF Web ACL (Global)        │  │
                                                 │  │  Priority 0: IP Allowlist    │  │
                                                 │  │  Priority 1: Managed Rules   │  │
                                                 │  └──────────────────────────────┘  │
                                                 │                                    │
                                                 │  Behavior: Response Headers Policy │
                                                 │  (CSP, HSTS, X-Frame-Options, ...) │
                                                 └─────────────────┬──────────────────┘
                                                                   │ HTTPS only
                                                                   │ Custom Header
                                                                   ▼
                                                   ┌────────────────────────────────┐
                                                   │   ALB (private subnet)         │
                                                   │   Security Group:              │
                                                   │   CloudFront Prefix List only  │
                                                   └──────────────┬─────────────────┘
                                                                  │
                                                                  ▼
                                                       ┌─────────────────────┐
                                                       │   Target Group       │
                                                       │   (ECS / EC2)        │
                                                       └─────────────────────┘
```

The ALB moves to a private subnet and only accepts traffic from CloudFront. Users never reach the ALB directly — CloudFront handles TLS termination, WAF inspection, and response header injection at the edge before anything reaches the origin.

### Step 1: Lock Down the ALB

**Move the ALB to a private subnet**, or at minimum update its security group to stop accepting traffic from the open internet.

**Update the ALB's security group:**

Remove the inbound rule that allows `0.0.0.0/0` on port 443. Replace it with the AWS-managed prefix list for CloudFront:

```
Inbound rule:
  Type:   HTTPS
  Port:   443
  Source: com.amazonaws.global.cloudfront.origin-facing
```

This prefix list is maintained by AWS. It contains every IP range CloudFront uses to communicate with origins, and it updates automatically when CloudFront adds new edge locations — no manual IP management needed.

**Add a secret custom header for layer-7 defense:**

The prefix list protects at the network layer. For an additional check at the application layer, configure CloudFront to forward a custom secret header to the ALB:

```
CloudFront Origin → Custom Headers:
  Header name:  X-Origin-Verify
  Header value: <random-secret-value>
```

Add an ALB listener rule that only forwards requests containing this header. All other requests return `403 Access denied`. Even if traffic somehow arrived at the ALB without going through CloudFront, it would fail this check and be rejected.

### Step 2: Move WAF to CloudFront — and Go Global

This is the step that catches teams off-guard the most.

**WAF Web ACLs for CloudFront must be globally scoped and created in `us-east-1`.**

Regional Web ACLs live in the same AWS region as the resource they protect. CloudFront is a global service and only works with Web ACLs that have `scope=CLOUDFRONT` — which requires you to be in **US East (N. Virginia)** when creating it, regardless of where your application runs.

In practice this means:
- Your existing regional WAF Web ACL cannot be reused for CloudFront
- You need to create a new Web ACL in `us-east-1` with CloudFront scope
- Any IP sets referenced by the old Web ACL need to be recreated in `us-east-1` as global resources

**Create the new global Web ACL:**

1. Switch your AWS console region to **US East (N. Virginia)**
2. Open **AWS WAF → Web ACLs → Create web ACL**
3. Set **Resource type** to **CloudFront distributions**
4. Recreate your IP allowlists (developers, trusted customers) in this same region

**Rule priority — get this wrong and your own team gets blocked:**

WAF evaluates rules in order of priority, where a lower number means evaluated first. If managed rules run before your allowlist, they can block legitimate traffic from your developers before the allowlist has a chance to permit it.

```
Correct order:
  Priority 0 — Custom IP set: Allow  (your dev and customer IPs)
  Priority 1 — AWSManagedRulesCommonRuleSet
  Priority 2 — AWSManagedRulesWindowsRuleSet
  Priority 3 — AWSManagedRulesAnonymousIpList
```

The custom allowlist must always be first. If managed rules fire ahead of it, your team will hit 403s and assume the application is broken — and they won't be wrong.

**Managed rule groups to consider:**

- `AWSManagedRulesCommonRuleSet` — general OWASP protection, relevant for most apps
- `AWSManagedRulesKnownBadInputsRuleSet` — blocks known exploit payloads and attack patterns
- `AWSManagedRulesAnonymousIpList` — blocks traffic from VPNs, Tor exit nodes, and anonymous proxies
- `AWSManagedRulesWindowsRuleSet` — worth adding if the app runs on Windows Server
- `AWSManagedRulesSQLiRuleSet` — relevant if SQL databases are exposed through an API

Start managed rules in **Count** mode before switching to **Block**. Let them run for a week and review the traffic they would have blocked. This surfaces false positives before they affect real users.

### Step 3: Configure CloudFront Behaviors and Attach Security Headers

A **behavior** in CloudFront defines how requests to a particular path pattern are handled. The default behavior (`*`) catches anything not matched by a more specific path. Each behavior has settings for caching, origin requests, HTTP methods, viewer protocol, and response headers.

The response headers policy is attached per behavior.

**Create and attach the policy:**

**1.** Go to **CloudFront → Policies → Response headers**

**2.** Create a new custom policy (or start from the managed `SecurityHeadersPolicy`)

**3.** Configure the security headers:

```
Strict-Transport-Security:
  max-age=31536000; includeSubDomains; preload

X-Content-Type-Options:
  nosniff

X-Frame-Options:
  DENY

X-XSS-Protection:
  1; mode=block

Referrer-Policy:
  strict-origin-when-cross-origin

Permissions-Policy:
  camera=(), microphone=(), geolocation=(), payment=()

Content-Security-Policy:
  (build this from report-only findings first — see Step 4)
```

**4.** Attach the policy to the default behavior: **Distribution → Behaviors → Edit → Response headers policy → select your policy**

The managed `SecurityHeadersPolicy` includes HSTS, `nosniff`, `X-Frame-Options: SAMEORIGIN`, and `X-XSS-Protection` out of the box. It's a reasonable starting point, but `Content-Security-Policy` and `Permissions-Policy` are application-specific and must be configured manually.

### Step 4: Implement CSP in Report-Only Mode First

`Content-Security-Policy` is the most impactful header in this list — and the one most likely to break the application if the policy is too restrictive. You need to know what your application actually loads before you can write a policy that allows it.

**The two modes:**

- **`Content-Security-Policy-Report-Only`**: the browser evaluates the policy, reports violations to a designated endpoint, and does nothing else. The application keeps working normally.
- **`Content-Security-Policy`**: the browser enforces the policy and blocks anything that violates it. A policy that's even slightly too tight will break real functionality.

Always start in report-only mode.

**Setting up the violation reporting pipeline:**

```
Browser detects violation → POST report to report-uri endpoint
                                        │
                                        ▼
                               API Gateway (HTTP POST route)
                                        │
                                        ▼
                               Lambda function
                                        │
                                        ▼
                               CloudWatch Logs
```

**1. API Gateway** — Create a simple HTTP API with a POST route. This URL becomes your `report-uri`.

**2. Lambda function** — Receive the violation report body (JSON), parse it, and log it to CloudWatch.

```python
import json, logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    body = event.get("body", "{}")
    logger.info(json.dumps(json.loads(body)))
    return {"statusCode": 204}
```

**3. CloudFront Response Headers Policy** — Add the report-only header pointing to your API Gateway endpoint:

```
Content-Security-Policy-Report-Only:
  default-src 'self'; script-src 'self'; style-src 'self'; form-action 'self';
  report-uri https://your-api-id.execute-api.us-east-1.amazonaws.com/report
```

**4. Monitor CloudWatch Logs** for two to four weeks. Violations show up like this:

```json
{
  "csp-report": {
    "document-uri": "https://yourapp.com/dashboard",
    "violated-directive": "script-src 'self'",
    "blocked-uri": "https://cdn.jsdelivr.net/npm/some-library"
  }
}
```

Each violation points to something the policy is blocking that the application actually needs. A `script-src` violation on an external CDN means you need to add that CDN to the `script-src` allowlist. Build the final policy directive by directive from these reports.

**Switching to enforce mode:**

Once violations have stabilized and the updated policy has been reviewed with the team:

1. Schedule a maintenance window
2. Replace `Content-Security-Policy-Report-Only` with `Content-Security-Policy` using the finalized policy value
3. Keep the `report-uri` in the enforce header — violations still get reported even after enforcement is on
4. Monitor CloudWatch for the first hour after the switch

Before flipping, you can temporarily run both headers at once: the report-only header shows what enforce mode would have blocked, without blocking anything yet.

### Step 5: Create the CloudFront Distribution and Update Route 53

**Create the distribution:**

- **CloudFront → Create distribution**
- **Origin domain**: your ALB's DNS name (e.g., `my-app-alb-123456.us-east-1.elb.amazonaws.com`)
- **Origin protocol policy**: HTTPS only
- **Minimum origin SSL protocol**: TLSv1.2
- **Origin custom headers**: add your `X-Origin-Verify` secret header
- **Viewer protocol policy**: Redirect HTTP to HTTPS
- **Cache policy**: CachingDisabled for dynamic content; a custom policy for static assets
- **WAF Web ACL**: select the global Web ACL created in `us-east-1`
- **Alternate domain names (CNAMEs)**: enter your domain (e.g., `yourapp.com`)
- **SSL certificate**: select your ACM certificate (must be in `us-east-1`)

ACM certificates for CloudFront must be in `us-east-1` regardless of where the application runs. If the ALB is in another region, you'll have two certificates: one in the ALB's region for CloudFront-to-origin HTTPS, and one in `us-east-1` for viewer-to-CloudFront HTTPS.

**Update Route 53:**

Once the distribution deploys (typically 10–20 minutes):

- Update the `A` record from the ALB DNS name to the CloudFront distribution domain (e.g., `d1234abcd.cloudfront.net`)
- Use an **Alias record** pointing to the CloudFront distribution — it's free, resolves faster than a CNAME, and works at the zone apex

### Troubleshooting Common Issues

**403 Forbidden from CloudFront**

Check WAF first. Open CloudWatch metrics for the Web ACL and filter by rule matches. If the custom IP allowlist wasn't recreated in `us-east-1` or wasn't added to the global Web ACL, that's usually the cause. Verify rule priorities — the allowlist must have a lower priority number than any managed rule group.

**502 / 503 Bad Gateway**

CloudFront can't reach the ALB. Verify the ALB security group has an inbound rule for the CloudFront managed prefix list (`com.amazonaws.global.cloudfront.origin-facing`). Check that target group health checks are passing. If using the custom header approach, confirm the ALB listener rule is set to forward requests containing `X-Origin-Verify`.

**Application broken after enabling CSP**

You switched to enforce mode before the policy was complete. Roll back by swapping `Content-Security-Policy` back to `Content-Security-Policy-Report-Only` and review the violation logs again. `form-action` and `frame-src` are often missed in the report-only phase — check those specifically.

**Route 53 still resolving to the ALB**

DNS propagation depends on the record's TTL. Run `dig yourapp.com` to confirm the A record has updated to a CloudFront IP. If the TTL was set high before the change, propagation can take up to an hour.

**WAF managed rules blocking real users**

Switch the offending rule groups from **Block** to **Count** temporarily. Review CloudWatch logs to identify which specific rules are matching. Add exceptions or tune the rules, then switch back to Block once the false positives are resolved.

### A Note on CloudFront Pricing

CloudFront offers two models:

- **Pay-as-you-go**: charged per request and per GB transferred out. Works well for lower-traffic applications or while evaluating whether to commit.
- **CloudFront Security Savings Bundle**: a flat-fee commitment tier covering a set traffic volume, with WAF capacity included. Typically more cost-effective than pay-as-you-go once traffic is consistent.

WAF pricing is separate from CloudFront: you pay per Web ACL, per rule group per month, and per million requests inspected. With several managed rule groups, those per-group charges add up — calculate the expected cost before enabling every rule set available.

Review the [CloudFront pricing page](https://aws.amazon.com/cloudfront/pricing/) alongside the WAF pricing page before choosing a tier.

### What You End Up With

After completing these steps:

- The ALB is in a private subnet, no longer reachable directly from the internet
- CloudFront is the public entry point, with AWS Shield Standard absorbing layer 3/4 DDoS at the edge
- WAF runs globally, inspecting every request before it reaches the origin
- Every response carries security headers — CSP, HSTS, `X-Frame-Options`, `Permissions-Policy` — injected by CloudFront without any backend code changes
- A CSP violation reporting pipeline runs in CloudWatch, giving visibility into client-side behavior before and after enforcement
- Caching and global delivery improvements are available as an immediate follow-on

The pen test finding that started this pushed an architecture decision that was already on the roadmap. If you haven't run a pen test yet, that's where Part 1 of this series starts — with the tools, the process, and what a real finding looks like before you get to implementation.

### References

1. [Restrict access to an Application Load Balancer — AWS CloudFront Developer Guide](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/restrict-access-to-load-balancer.html)
2. [Add or remove HTTP headers in CloudFront responses with a policy — AWS CloudFront Developer Guide](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/adding-response-headers.html)
3. [How AWS WAF works — AWS WAF Developer Guide](https://docs.aws.amazon.com/waf/latest/developerguide/how-aws-waf-works.html)
4. [Create a response headers policy — AWS CloudFront Developer Guide](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/creating-response-headers-policies.html)
5. [Amazon CloudFront Pricing](https://aws.amazon.com/cloudfront/pricing/)
