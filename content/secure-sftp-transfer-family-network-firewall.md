---
title: A Secure SFTP Setup with AWS Transfer Family and Network Firewall
slug: secure-sftp-transfer-family-network-firewall
category: AWS
tags: AWS, Transfer Family, SFTP, Network Firewall, VPC, Security
excerpt: A VPC design that fronts AWS Transfer Family SFTP servers with AWS Network Firewall, so only allowlisted IPs ever reach port 22, plus the identity provider and hardening choices that go with it.
date: 2026-08-10
---

![Blue network cables plugged into a patch panel](https://images.unsplash.com/photo-1683322499436-f4383dd59f5a?w=1600&q=80&fm=jpg&fit=crop)
*Photo by [Scott Rodgerson](https://unsplash.com/@scottrodgerson) on [Unsplash](https://unsplash.com)*

AWS Transfer Family (the managed SFTP/FTPS/AS2 service, not to be confused with anything Azure-branded) makes it easy to stand up a file transfer endpoint. The part that actually takes design work is making sure that endpoint isn't just sitting open on the internet. Here's the architecture we settled on: an AWS Network Firewall in front of the SFTP servers, allowlisting traffic down to the IP, so nothing reaches port 22 unless it's explicitly permitted.

## The network layout

This design is adapted from AWS's own reference architecture for a distributed Network Firewall deployment. Inside one VPC, across two Availability Zones for high availability:

- **Firewall subnets** (one per AZ): this is where the Network Firewall endpoints live. Traffic from the internet gateway is routed through here first.
- **Protected subnets** (one per AZ): this is where the Transfer Family SFTP servers actually sit. Nothing reaches them without first passing through a firewall endpoint.

```
Internet
   v
Internet Gateway
   v  (IGW ingress route table sends traffic to the firewall endpoint)
Firewall subnet (AZ-a)        Firewall subnet (AZ-b)
   |  Network Firewall            |  Network Firewall
   v  endpoint                    v  endpoint
Protected subnet (AZ-a)       Protected subnet (AZ-b)
   |                               |
   +---- SFTP server (Transfer Family, spans both AZs) ----+
```

Three route tables make this work:

- **The firewall/public subnet route table**, sending outbound traffic to the internet gateway.
- **The protected subnet route table**, routing traffic through the local firewall endpoint rather than straight out.
- **An internet gateway ingress route table**, which is what actually forces inbound traffic to pass through a firewall endpoint before it can reach the protected subnet, easy to forget, and the piece that makes the whole design airtight rather than just decorative.

Because the SFTP server spans both Availability Zones, a single AZ failure doesn't take the endpoint down.

## The firewall rule: allowlist by IP, deny everything else

Inside Network Firewall, this comes down to a stateless rule group using a standard 5-tuple match:

- **Source**: the specific public IPs you want to allow (your office IP, a partner's IP, whatever's appropriate)
- **Source port range**: 0-65535, since you don't control the client's ephemeral source port
- **Destination**: your SFTP server's IP, which you'll have once the server itself is deployed
- **Destination port**: 22
- **Action**: pass

The security posture depends on the firewall policy's default stateless action being set to drop. The pass rule is what lets specific traffic through, everything that doesn't match a rule falls to that default and gets dropped. Double-check that default is actually set to drop, since a policy defaulting to pass would quietly undo the whole point of this setup.

**On custom ports**: Transfer Family now supports SFTP on port 2222, 22000, and 2223 in addition to 22, without needing anything extra. Going beyond those specific ports requires fronting the server with a Network Load Balancer and additional Elastic IPs. Whether it's worth doing depends on your team's threat model, moving off port 22 mostly helps against opportunistic scanning, not a targeted attacker who already knows your allowlisted IP is the real control.

## Deploying the SFTP server

Transfer Family gives you a choice of identity provider:

- **Service managed**: users are created and stored directly in Transfer Family, no external system required. It supports SSH public key authentication, password authentication, or both, worth knowing since it's easy to assume service managed is key-only.
- **Custom identity provider**: authentication is handled by your own backend. The traditional pattern is API Gateway in front of a Lambda function that validates credentials, which is what we built (password-only, in our case). AWS has since added a way to invoke Lambda directly as the identity provider, without API Gateway in the middle, worth using for anything new since it's simpler and cuts out an extra hop.

Which one to use depends on how your data actually gets uploaded. A script or automated integration is often fine with service managed and key-based auth. A setup that needs to check credentials against an existing user system, or apply logic beyond what Transfer Family's own user store can do, is where a custom identity provider earns its extra setup cost.

For the endpoint itself:

- **Protocol**: SFTP
- **Endpoint type**: VPC hosted, using the protected VPC and subnets from the architecture above
- **Access**: internet-facing (an internal-only endpoint is also an option if nothing outside the VPC needs to reach it)
- Configure it across both Availability Zones. You'll get both a private and a public address per AZ.

## Users, roles, and key management

For each user, create an IAM role scoped to only the S3 access that user actually needs, then set their home directory to a specific bucket prefix and mark it **restricted**, which keeps the user scoped to that folder rather than able to browse the whole bucket.

For key-based auth, the public key gets stored on the user at creation time. The private key stays with whoever's connecting, used from an SSH client like PuTTY or a dedicated SFTP client like WinSCP or FileZilla (not to be confused with WinZip, which is an archive tool, not an SFTP client). Follow your own org's key generation and rotation policy here rather than improvising one.

## Operational hardening

- **Turn on CloudWatch logging** for the server so user activity is actually visible for troubleshooting and audits, not just assumed.
- **Pick a security policy deliberately.** Transfer Family's security policies control which SSH ciphers, key exchange algorithms, and MACs are allowed. Newer policies are more restrictive by design, which is good for security but can break an older automated script or library that only speaks older algorithms. If your uploads come from a script rather than a human with a modern client, test against your actual security policy before rolling it out, don't assume the newest default will work for every uploader.

## The actual takeaway

The firewall is what makes this architecture secure, but the IGW ingress route table is what makes the firewall real instead of theoretical, it's the piece that guarantees inbound traffic can't route around the firewall endpoint entirely. If you build the firewall subnet and rule group but skip that route table, the design looks complete and isn't. Check it explicitly rather than assuming it falls out of the rest of the setup.

## Practical guide: building this yourself

1. **Build the VPC with firewall subnets and protected subnets across two Availability Zones.**
2. **Deploy AWS Network Firewall** with endpoints in the firewall subnets.
3. **Configure all three route tables**: the firewall/public subnet route table to the internet gateway, the protected subnet route table through the local firewall endpoint, and the internet gateway ingress route table forcing inbound traffic through a firewall endpoint.
4. **Confirm the firewall policy's default stateless action is drop**, not pass.
5. **Create a stateless 5-tuple rule** allowlisting the source IPs you want, source port 0-65535, destination IP/port matching your SFTP server on 22, action pass.
6. **Deploy the Transfer Family server**: protocol SFTP, VPC-hosted endpoint in the protected subnets, internet-facing (or internal, if appropriate), spanning both Availability Zones.
7. **Choose an identity provider.** Service managed for simplicity, a custom identity provider (Lambda, with or without API Gateway) if you need to validate against your own backend.
8. **Create users with scoped IAM roles** and a restricted home directory pointed at the specific S3 prefix they need.
9. **Turn on CloudWatch logging and pick a security policy deliberately**, testing it against whatever client or script will actually be connecting.

## References

- [What is AWS Transfer Family?](https://docs.aws.amazon.com/transfer/latest/userguide/what-is-aws-transfer-family.html)
- [Choosing an identity provider for your server](https://docs.aws.amazon.com/transfer/latest/userguide/create-server-idp.html)
- [AWS Network Firewall: architecture with a firewall in a single Availability Zone or distributed across two](https://docs.aws.amazon.com/network-firewall/latest/developerguide/arch-two-zone.html)
- [Security policies for AWS Transfer Family servers](https://docs.aws.amazon.com/transfer/latest/userguide/security-policies.html)
- [AWS Transfer Family announces an alternate port for SFTP servers](https://aws.amazon.com/about-aws/whats-new/2023/11/aws-transfer-family-alternate-port-sftp-servers/)
