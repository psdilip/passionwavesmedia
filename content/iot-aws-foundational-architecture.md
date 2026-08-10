---
title: A Foundational AWS Architecture for IoT Device Workflows
slug: iot-aws-foundational-architecture
category: AWS
tags: AWS, IoT, IoT Core, DynamoDB, Athena, QuickSight, Architecture
excerpt: A starting-point architecture for taking data off an IoT device and turning it into something you can query, monitor, and hand back to customers.
date: 2026-08-08
---

![IoT development components: an Arduino board, sensors, breadboards, and batteries](https://images.unsplash.com/photo-1555664424-778a1e5e1b48?w=1600&q=80&fm=jpg&fit=crop)
*Photo by [Robin Glauser](https://unsplash.com/@nahakiole) on [Unsplash](https://unsplash.com)*

If you've got IoT hardware in the field, whether that's internal equipment you're monitoring or a device you've shipped to customers, at some point you need more than "the device is sending data somewhere." You need a real pipeline: ingest it, clean it, store it, query it, and put it in front of the right people. This is the foundation I'd start from. It's not the only way to build it, but it's a solid, proven shape to adapt from.

One correction up front, since it's an easy mix-up: the AWS service that receives your device's messages is **AWS IoT Core**, not "IoT Hub." IoT Hub is Azure's equivalent service, different cloud, different name. Worth knowing if you're reading AWS docs and Azure docs side by side.

## The flow, end to end

```
IoT Device
   |  cellular/network module -> MQTT publish
   v
AWS IoT Core (message broker)
   |  IoT Rule evaluates the message
   |-----------------------------> S3 (raw archive)
   v
Lambda (validate, clean, transform)
   v
DynamoDB (current device state)
   |  DynamoDB Streams
   v
Lambda (stream processor)
   v
S3 (processed data, cataloged by AWS Glue)
   v
Athena (SQL queries)
   |-----------------------------> QuickSight (dashboards)
   v
Elastic Beanstalk web app (Cognito-authenticated, per-customer views)
```

## Step by step

- **The device connects.** Your IoT hardware uses its cellular or network module to reach the internet, then publishes its data as MQTT messages to a topic.
- **AWS IoT Core receives it.** This is your MQTT broker on the AWS side. Devices authenticate with X.509 certificates and IAM/IoT policies, not passwords, that's what "IoT Hub and roles" in an early draft of this was really pointing at.
- **An IoT Rule decides where the message goes.** This is the piece that's easy to skip over but does the real routing work: a SQL-like rule evaluated against the incoming message that can fan it out to multiple destinations at once. In this architecture, that means two things happen from the same message:
  - A copy lands untouched in **S3** as a raw archive, useful for reprocessing later or for compliance/audit needs.
  - The message also goes to **Lambda** for cleanup: normalizing key names, converting units, dropping malformed payloads, whatever "correctly captured" means for your device.
- **Cleaned data lands in DynamoDB.** Good fit here: it's fully managed, scales with device count without much thought, and gives you fast current-state lookups per device.
- **DynamoDB Streams pushes changes to a second Lambda**, which writes the data back out to **S3** in a format built for querying (Parquet or partitioned JSON), with **AWS Glue** cataloging the schema on top so Athena knows what it's looking at.
- **Athena queries that S3 data with plain SQL.** This is where you actually answer "is this device behaving the way it should," without standing up a database server to do it.
- **A web app, deployed on Elastic Beanstalk, sits in front of Athena** so you and your team (or your customers) can run those queries without touching the console. Beanstalk supports several platforms (.NET included) if you already have a preferred stack.
- **Cognito User Pools handle who's allowed to see what.** For a customer-facing setup, you'd authenticate each user through Cognito and map their identity to the specific device(s) they're allowed to query, so customer A never sees customer B's data.
- **QuickSight connects to the same Athena data** for dashboards, either as the customer-facing visualization layer or as an internal one for your own team, it plugs in natively without extra glue code.

## The actual takeaway

The pattern that makes this work is the fork right after the IoT Rule: one path keeps a raw, untouched copy of everything (your safety net), and a second path cleans and reshapes the data for actual use. Don't collapse those into one step. If your transformation logic has a bug, you want the original message still sitting in S3, not lost inside a bad transform. Everything downstream of that fork, DynamoDB, Streams, Athena, QuickSight, is really just different lenses on the same cleaned dataset.

## Practical guide: standing up the foundation

1. **Provision devices in AWS IoT Core** with X.509 certificates and an IoT policy scoped to only the MQTT topics that device needs.
2. **Write an IoT Rule** that fans each incoming message out to two actions: an S3 write for the raw archive, and a Lambda invocation for cleanup.
3. **Build the cleanup Lambda** to validate the payload, normalize field names/units, and reject anything malformed before it reaches DynamoDB.
4. **Design a DynamoDB table** around device ID as the partition key, and enable DynamoDB Streams on it.
5. **Build a second Lambda off the stream** that writes processed records to S3 in a query-friendly format, and set up an AWS Glue crawler (or a manually defined table) to catalog it.
6. **Confirm Athena can query the catalog** with a few test SQL statements before building anything on top of it.
7. **Deploy a web app on Elastic Beanstalk** that runs Athena queries on demand, rather than giving every user direct console access.
8. **Wire up Cognito User Pools** and map each authenticated user to the device(s) they're allowed to query.
9. **Add QuickSight** on top of the same Athena source for dashboards, internal, customer-facing, or both.

## References

- [What is AWS IoT?](https://docs.aws.amazon.com/iot/latest/developerguide/what-is-aws-iot.html)
- [AWS IoT rules engine](https://docs.aws.amazon.com/iot/latest/developerguide/iot-rules.html)
- [DynamoDB Streams](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html)
- [What is Amazon Athena?](https://docs.aws.amazon.com/athena/latest/ug/what-is.html)
- [What is Amazon QuickSight?](https://docs.aws.amazon.com/quicksight/latest/user/welcome.html)
