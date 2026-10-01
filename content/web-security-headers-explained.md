---
title: "How Browsers and Servers Talk — and Why Security Headers Matter"
slug: web-security-headers-explained
category: AWS
tags: Security Headers, CSP, Penetration Testing, Burp Suite, Web Security, AWS
excerpt: Before you configure a single security header, you need to understand what's happening between the browser and the server — and how a penetration test reveals where that communication is unprotected.
date: 2026-10-01
---

![Photo by FlyD on Unsplash](https://images.unsplash.com/photo-1614064548237-096f735f344f?w=1600&q=80&fm=jpg&fit=crop)
*Browser security · Photo by [FlyD](https://unsplash.com/@flyd2069) on [Unsplash](https://unsplash.com)*

This article covers the fundamentals: how a browser reaches your application, what security headers actually do, and the kind of finding that makes you prioritize implementing them. The step-by-step implementation using CloudFront is in [Part 2](/cloudfront-security-headers-waf.html).

### What Happens When You Visit a Website

There are three phases between a user typing a URL and the page loading. Understanding them is the foundation for everything else in this article.

```
  User types: yourapp.com
         │
         ▼
┌────────────────────────────────┐
│  Phase 1: DNS Resolution        │
│                                 │
│  Browser asks:                  │
│  "What's the IP for this?"      │
│                                 │
│  DNS resolver replies:          │
│  "203.0.113.42"                 │
└───────────────┬─────────────────┘
                │  IP address known
                ▼
┌────────────────────────────────┐
│  Phase 2: TLS Handshake         │
│                                 │
│  Browser: show me your cert     │
│  Server: here it is             │
│  Browser: verifying...          │
│  Both: agree on encryption keys │
│  ── encrypted channel open ──   │
└───────────────┬─────────────────┘
                │  secure connection
                ▼
┌────────────────────────────────┐
│  Phase 3: Request & Response    │
│                                 │
│  Browser: GET /dashboard        │
│  Server: here's the page        │
│    └── Headers (instructions)   │
│    └── Body (content)           │
└────────────────────────────────┘
```

**Phase 1 — DNS**

Computers communicate by IP address, not by domain name. DNS is the address book that translates `yourapp.com` into something like `203.0.113.42`. Your browser does this lookup automatically every time you visit a site. In AWS, Route 53 handles this.

**Phase 2 — TLS Handshake**

Before any content is exchanged, the browser and server establish an encrypted channel. The server presents an SSL certificate — proof of identity signed by a trusted certificate authority. The browser verifies it, they agree on encryption keys, and everything from that point on is encrypted. This is the padlock in the browser address bar.

> The padlock doesn't mean the site is safe to use — it means the connection between you and the server is encrypted. The site itself could still have vulnerabilities. The padlock is a transport guarantee, not a content guarantee.

**Phase 3 — Request and Response**

Once the encrypted channel is open, the browser sends a request and the server responds. The response has two parts: a **body** (the actual page content) and **headers** (instructions for the browser).

```
HTTP Response
┌────────────────────────────────────────────┐
│  HEADERS  — instructions to the browser    │
│  ─────────────────────────────────────     │
│  Content-Type: text/html                   │
│  X-Frame-Options: DENY                     │
│  Strict-Transport-Security: max-age=...    │
│  Content-Security-Policy: default-src ...  │
├────────────────────────────────────────────┤
│  BODY  — the actual page content           │
│  ─────────────────────────────────────     │
│  <html>...</html>                          │
└────────────────────────────────────────────┘
```

> Think of it like a restaurant meal. The food is the body — that's what you ordered. But the waiter also delivers instructions alongside it: "serve hot," "contains allergens," "no modifications once plated." Security headers are those instructions. The browser reads them before rendering anything, and they tell it what rules to follow.

### What Security Headers Actually Do

Without security headers, browsers are permissive by default. They'll execute scripts from any domain, allow pages to be embedded in iframes, accept resources from anywhere, and make few assumptions about what should be restricted. The web was built this way — open by design.

The problem is that this openness is exploitable. An attacker who finds an injection point — a form field, a URL parameter, anywhere user input gets reflected back into the page — can potentially load malicious scripts, redirect form submissions, or embed your application inside their own page to deceive users.

Security headers don't close the original vulnerability. They limit what an attacker can do if they find one. They're a secondary layer of defense enforced at the browser level.

**The headers that matter:**

**`Content-Security-Policy`**
Defines which domains scripts, styles, images, and fonts can load from. Blocks everything not on the approved list. The most powerful header here — covered in its own section below.

**`Strict-Transport-Security`**
Forces the browser to use HTTPS only, even if the user types plain HTTP. Prevents protocol-downgrade attacks.

**`X-Frame-Options`**
Blocks the page from being loaded inside an iframe on another domain. Stops clickjacking attacks where a hidden frame tricks users into clicking things they didn't intend to.

**`X-Content-Type-Options: nosniff`**
Tells the browser to trust the server's declared content type and not try to guess it. Prevents content-type sniffing attacks where a file gets executed as the wrong type.

**`X-XSS-Protection`**
Enables the browser's built-in XSS filter. Useful for older browser support; modern browsers lean on CSP instead.

**`Referrer-Policy`**
Controls how much of the page URL gets included when a user follows a link to another site. Prevents internal URLs — including those with session tokens or user IDs — from leaking to external domains.

**`Permissions-Policy`**
Restricts which browser features the page is allowed to access — camera, microphone, geolocation, payments. Limits damage if a script is ever injected.

> **Start with these three if you're new to this:** `X-Frame-Options` (one line, immediate impact), `Strict-Transport-Security` (works everywhere, no application changes needed), and `Content-Security-Policy` (most powerful, needs the most planning — use report-only mode first). The rest are quick wins once those are in place.

### Understanding Content-Security-Policy

CSP gets its own section because it's different from the other headers. Every other header on this list is a single instruction. CSP is a policy — a set of rules you define about what your specific application is allowed to do.

A CSP directive looks like this:

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' https://cdn.example.com;
  style-src 'self' https://fonts.googleapis.com;
  form-action 'self';
  img-src 'self' data:;
```

Each directive closes a door:

- `default-src 'self'` — the fallback rule: only load from the same origin unless a specific directive says otherwise
- `script-src` — where JavaScript can be loaded from
- `style-src` — where stylesheets can be loaded from
- `form-action` — where forms are allowed to submit data
- `img-src` — where images can be loaded from

A policy that only sets `default-src 'self'` without defining `script-src`, `style-src`, or `form-action` explicitly is weaker than it looks. The browser falls back to `default-src` for those directives, but the lack of explicit definition is a signal that the policy wasn't fully thought through — and pen testers will flag it.

**Why CSP needs a report-only phase first:**

A CSP that's too strict will break your own application. If your app loads scripts from a CDN you forgot to include, users will see a broken page. The safe way to implement it is to run in report-only mode first — the browser evaluates the policy, reports violations to an endpoint you control, but doesn't block anything. You watch the violations for a few weeks, build the policy from what you see, then switch to enforce mode. Part 2 covers this workflow in full.

### Finding the Gaps: Penetration Testing

Knowing the headers exist is one thing. Knowing which ones are missing on your specific application — and what an attacker could actually do with those gaps — is what a penetration test gives you.

A pen test is a structured, authorized attempt to exploit weaknesses in a running application. A tester probes the application the way a real attacker would: trying to inject inputs, bypass controls, chain vulnerabilities together, and demonstrate impact. The output is specific: not "you might be vulnerable to XSS" but "this input on this endpoint reflects user input without sanitization, and the missing `script-src` directive means an injected script from any external domain would execute."

**Burp Suite** is the standard tool for web application pen testing. It works as an intercepting proxy between the browser and the application — every request and response passes through it, and a tester can inspect, modify, replay, and fuzz any of them. The Community Edition is free and covers the core functionality. Burp Suite Professional adds automated scanning.

**Running a test safely:**

- Test against a non-production environment that mirrors production as closely as possible
- Get explicit written authorization — document it even if you own the system
- Define scope before starting: which domains, which endpoints, which test types are in bounds
- Keep logs from the test period separate so findings can be correlated with specific test activity

The output is only as useful as the specificity of the findings. Vague findings produce vague remediations.

### What a Real Finding Looks Like

The implementation in Part 2 came from a pen test on a web application. The key finding related to the Content-Security-Policy:

```
Finding: CSP policy does not define script-src, style-src, or form-action

The application's Content-Security-Policy header relies on default-src
without explicitly defining directives for script, style, or form sources.
This reduces the policy's effectiveness as a secondary control against
injection attacks.

Recommendation:
  - Define script-src explicitly — restricts executable script sources
  - Define style-src explicitly — restricts stylesheet injection vectors
  - Define form-action explicitly — restricts where forms can submit data
  - Add X-Frame-Options: DENY — not present; application is embeddable in iframes
  - Add Permissions-Policy — no browser feature restrictions in place
```

These findings were categorized as application hardening recommendations. They don't represent a direct exploit on their own — but they define the conditions under which other vulnerabilities become more impactful. A missing `script-src` doesn't create an XSS vulnerability, but it makes an existing XSS vulnerability much easier to weaponize.

### Where to Go From Here

The next step is implementation. Part 2 of this series covers:

- The architecture change: adding CloudFront in front of an ALB, moving the load balancer into a private subnet
- Moving WAF to the edge (and why it must be global for CloudFront)
- Attaching security headers via a CloudFront Response Headers Policy
- The full CSP report-only workflow: API Gateway, Lambda, CloudWatch, enforcement
- Troubleshooting and pricing

[Read Part 2: Implementing Security Headers with CloudFront](/cloudfront-security-headers-waf.html)

**If you want to go deeper on any of the concepts covered here:**

- OWASP Content Security Policy Cheat Sheet — comprehensive reference for writing CSP directives
- MDN Web Docs: HTTP Headers — browser-accurate documentation for every header covered in this article
- PortSwigger Web Security Academy — free, hands-on training for learning pen testing and web vulnerabilities, built by the team behind Burp Suite

### References

1. [Add or remove HTTP headers in CloudFront responses — AWS CloudFront Developer Guide](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/adding-response-headers.html)
2. [Content Security Policy — MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
3. [OWASP Content Security Policy Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)
